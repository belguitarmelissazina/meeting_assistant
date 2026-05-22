"use strict";

const { app, BrowserWindow, Notification, Tray, Menu, nativeImage, nativeTheme, shell, ipcMain } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const http = require("http");
const treeKill = require("tree-kill");
const { autoUpdater } = require("electron-updater");
const { downloadAll, allPresent } = require("./downloader");

const BACKEND_PORT = 8000;
const BACKEND_HOST = "127.0.0.1";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const HEALTH_PATH = "/api/health";
const HEALTH_TIMEOUT_MS = 90_000;

const isDev = !app.isPackaged;

// ── Compat réseau entreprise (proxy authentifié) ─────────────────────────
// DOIT être appelé AVANT app.whenReady(). Autorise Chromium (donc le module
// `net` du downloader) à s'authentifier automatiquement auprès du proxy
// d'entreprise via les identifiants Windows de la session (NTLM / Kerberos /
// Negotiate). Sans ça, un proxy authentifié renvoie 407 et le téléchargement
// timeout — cas le plus fréquent en grand compte (RTE, banques, etc.).
// `*` = autorise pour tous les serveurs (le proxy étant interne, pas de
// risque de fuite de creds vers l'extérieur : ils ne partent qu'au proxy).
app.commandLine.appendSwitch("auth-server-allowlist", "*");
app.commandLine.appendSwitch("auth-negotiate-delegate-allowlist", "*");

// Icône de l'app (barre des tâches / fenêtres). Sur Windows on prend l'.ico
// multi-tailles (rendu net en 16-32px) ; sinon le PNG. Packagée via
// build.files ; ce chemin résout en dev ET dans l'asar.
const APP_ICON = path.join(
  __dirname,
  process.platform === "win32" ? "icon.ico" : "icon.png"
);

// En production, les modèles sont téléchargés au premier lancement dans
// le dossier userData (writable sans admin) plutôt que packagés dans
// l'installer (économise ~2.3 GB sur le .exe d'install).
function modelsRoot() {
  return path.join(app.getPath("userData"), "assets");
}

// ── Path resolution ──────────────────────────────────────────────────────────
// In production (packaged), assets and the PyInstaller backend live under
// `process.resourcesPath`. In dev, we point at the source tree so the same
// Electron shell works against `python -m backend.run_app server`.
function resolveResources() {
  if (isDev) {
    const repoRoot = path.resolve(__dirname, "..");
    return {
      backendExe: null, // dev uses python interpreter, see startBackend()
      modelsDir: path.join(repoRoot, "models"),
      sherpaDir: path.join(repoRoot, "sherpa-onnx-streaming-zipformer-fr-kroko"),
      pretrainedDir: path.join(repoRoot, "pretrained_models"),
      llamaBinDir: path.join(repoRoot, "bin", "llama"),
      minilmDir: path.join(repoRoot, "assets", "models_hf", "all-MiniLM-L6-v2"),
      webappOut: path.join(repoRoot, "webapp", "out"),
      repoRoot,
    };
  }
  const res = process.resourcesPath;
  // Production : les BINAIRES restent embarqués dans resources/ (backend
  // PyInstaller, llama-server.exe, webapp statique). Les MODÈLES ML
  // pèsent ~2.3 GB et sont téléchargés au premier lancement dans
  // userData (~/AppData/Roaming/meeting-assistant/assets/) — voir
  // ensureModelsDownloaded().
  const userAssets = modelsRoot();
  return {
    backendExe: path.join(res, "backend", "backend.exe"),
    modelsDir: path.join(userAssets, "models"),
    sherpaDir: path.join(userAssets, "sherpa-onnx-streaming-zipformer-fr-kroko"),
    pretrainedDir: path.join(userAssets, "pretrained_models"),
    llamaBinDir: path.join(res, "assets", "bin", "llama"),  // toujours packagé
    minilmDir: path.join(userAssets, "models_hf", "all-MiniLM-L6-v2"),
    webappOut: path.join(res, "webapp-out"),
    repoRoot: res,
  };
}

// ── Backend lifecycle ────────────────────────────────────────────────────────
let backendProc = null;

function startBackend() {
  const r = resolveResources();
  const env = {
    ...process.env,
    BACKEND_PORT: String(BACKEND_PORT),
    BACKEND_HOST,
    MODELS_DIR: r.modelsDir,
    SHERPA_DIR: r.sherpaDir,
    PRETRAINED_DIR: r.pretrainedDir,
    LLAMA_BIN_DIR: r.llamaBinDir,
    MINILM_DIR: r.minilmDir,
    HF_HUB_OFFLINE: "1",
    TRANSFORMERS_OFFLINE: "1",
    PYTHONIOENCODING: "utf-8",
  };

  let cmd, args, cwd;
  if (isDev) {
    cmd = process.env.PYTHON_BIN || "python";
    args = ["-u", "-m", "backend.run_app", "server"];
    cwd = r.repoRoot;
  } else {
    if (!fs.existsSync(r.backendExe)) {
      throw new Error(`backend.exe not found at ${r.backendExe}`);
    }
    cmd = r.backendExe;
    args = ["server"];
    cwd = path.dirname(r.backendExe);
  }

  console.log(`[electron] spawn backend: ${cmd} ${args.join(" ")}`);
  backendProc = spawn(cmd, args, {
    cwd,
    env,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  backendProc.stdout.on("data", (b) => process.stdout.write(`[backend] ${b}`));
  backendProc.stderr.on("data", (b) => process.stderr.write(`[backend] ${b}`));
  backendProc.on("exit", (code, signal) => {
    console.log(`[electron] backend exited (code=${code}, signal=${signal})`);
    backendProc = null;
  });
}

function stopBackend() {
  if (!backendProc || backendProc.killed) return;
  const pid = backendProc.pid;
  // tree-kill: uvicorn + llama-server.exe both spawn child processes; SIGTERM
  // on the root pid alone leaves orphans behind on Windows.
  treeKill(pid, "SIGTERM", (err) => {
    if (err) console.error(`[electron] tree-kill error: ${err}`);
  });
}

// Variante "promise" pour les chemins qui DOIVENT attendre la mort effective
// du process (typiquement avant un autoUpdater.quitAndInstall : tant que
// backend.exe / llama-server.exe tiennent les fichiers, l'installeur NSIS
// reste bloqué sur l'écrasement de resources/backend/_internal/*).
function stopBackendAndWait(timeoutMs = 6000) {
  return new Promise((resolve) => {
    if (!backendProc || backendProc.killed) return resolve();
    const proc = backendProc;
    const pid = proc.pid;
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      resolve();
    };
    proc.once("exit", finish);
    treeKill(pid, "SIGKILL", (err) => {
      if (err) console.error(`[electron] tree-kill error: ${err}`);
    });
    // Filet de sécurité : on n'attend jamais plus de timeoutMs, même si
    // tree-kill échoue silencieusement. Vaut mieux une MAJ qui continue
    // qu'une app bloquée sur le dialog "Redémarrer".
    setTimeout(finish, timeoutMs);
  });
}

function waitForBackend() {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const tryOnce = () => {
      const req = http.get(`${BACKEND_URL}${HEALTH_PATH}`, (res) => {
        if (res.statusCode === 200) {
          res.resume();
          resolve();
        } else {
          res.resume();
          retry();
        }
      });
      req.setTimeout(2000, () => { req.destroy(); retry(); });
      req.on("error", retry);
    };
    const retry = () => {
      if (Date.now() - start > HEALTH_TIMEOUT_MS) {
        reject(new Error("backend health-check timeout"));
        return;
      }
      setTimeout(tryOnce, 500);
    };
    tryOnce();
  });
}

// ── First-launch model download ──────────────────────────────────────────────
// HTML inline (data URI) pour la fenêtre de progression : pas besoin de
// fichier supplémentaire à packager, ni de webpack pour un mini bandeau.
function downloadProgressHtml() {
  // Couleurs alignées sur le splash et webapp/app/globals.css. Le thème suit
  // la préférence système (clair/sombre) via @media prefers-color-scheme.
  return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<title>Meeting Assistant — Installation</title>
<style>
  :root{
    --surface:251 247 243; --ink:31 27 24; --ink-muted:90 82 77;
    --brand:171 55 35; --border:232 221 212; --accent:47 114 140;
  }
  @media (prefers-color-scheme: dark){
    :root{
      --surface:18 20 24; --ink:240 234 227; --ink-muted:165 155 145;
      --brand:215 95 78; --border:45 50 58; --accent:120 180 205;
    }
  }
  html,body{margin:0;padding:0;height:100%;
    background:rgb(var(--surface));color:rgb(var(--ink));
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
  body{display:flex;flex-direction:column;justify-content:center;
    align-items:center;padding:32px;text-align:center;box-sizing:border-box;}
  h1{font-size:18px;font-weight:600;margin:0 0 8px;color:rgb(var(--ink));}
  .sub{font-size:13px;color:rgb(var(--ink-muted));margin-bottom:32px;
    max-width:420px;line-height:1.5;}
  .label{font-size:13px;color:rgb(var(--ink-muted));margin-bottom:8px;
    height:18px;font-variant-numeric:tabular-nums;}
  .bar-wrap{width:100%;max-width:480px;height:8px;
    background:rgb(var(--border));border-radius:4px;overflow:hidden;}
  .bar{height:100%;width:0%;transition:width .15s linear;
    background:linear-gradient(90deg,rgb(var(--accent)),rgb(var(--brand)));}
  .stats{font-size:12px;color:rgb(var(--ink-muted));margin-top:12px;
    font-variant-numeric:tabular-nums;}
  .source{font-size:11px;margin-top:10px;padding:3px 10px;border-radius:10px;
    display:inline-block;}
  .source.github{background:rgb(var(--accent) / 0.15);color:rgb(var(--accent));}
  .source.hf{background:rgb(var(--brand) / 0.15);color:rgb(var(--brand));}
  .source.pending{background:rgb(var(--border));color:rgb(var(--ink-muted));}
  .err{color:rgb(var(--brand));margin-top:24px;font-size:13px;max-width:480px;
    display:none;}
</style></head>
<body>
  <h1>Préparation de Meeting Assistant</h1>
  <p class="sub">Téléchargement des modèles d'IA (~2,3 Go) — uniquement au
  premier lancement. Les fichiers sont stockés sous votre dossier
  utilisateur et ne seront pas re-téléchargés ensuite.</p>
  <div class="label" id="lbl">Initialisation…</div>
  <div class="bar-wrap"><div class="bar" id="bar"></div></div>
  <div class="stats" id="stats">&nbsp;</div>
  <div><span class="source pending" id="source">source : …</span></div>
  <div class="err" id="err"></div>
</body></html>`;
}

function fmtBytes(b) {
  if (!b) return "0 o";
  const k = 1024;
  const units = ["o", "Ko", "Mo", "Go"];
  const i = Math.min(units.length - 1, Math.floor(Math.log(b) / Math.log(k)));
  return `${(b / Math.pow(k, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
}

let downloadWindow = null;

async function showDownloadWindow() {
  downloadWindow = new BrowserWindow({
    width: 560,
    height: 360,
    resizable: false,
    minimizable: true,
    maximizable: false,
    icon: APP_ICON,
    // Couleur de fond AVANT peinture du HTML : on suit le thème système
    // (sombre vs clair) pour éviter un flash de la mauvaise couleur. Le
    // contenu (body) prend ensuite le relais via prefers-color-scheme.
    backgroundColor: nativeTheme.shouldUseDarkColors ? "#121418" : "#FBF7F3",
    title: "Meeting Assistant — Installation",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  downloadWindow.setMenuBarVisibility(false);
  await downloadWindow.loadURL(
    "data:text/html;charset=utf-8," + encodeURIComponent(downloadProgressHtml())
  );
  return downloadWindow;
}

async function pushProgress(p) {
  if (!downloadWindow || downloadWindow.isDestroyed()) return;
  const pct = p.totalBytes
    ? ((p.totalReceivedBytes / p.totalBytes) * 100).toFixed(1)
    : 0;
  // Juste le compteur de fichiers, pas le nom du modèle (inutile pour
  // l'utilisateur final).
  const lbl = `Fichier ${p.itemIndex + 1} / ${p.itemCount}`;
  const stats = `${fmtBytes(p.totalReceivedBytes)} / ${fmtBytes(p.totalBytes)} (${pct} %)`;
  // Pastille source (diagnostic entreprise) : GitHub via net.request (chemin
  // nominal, proxy-aware) ou HuggingFace (fallback). À retirer pour la
  // version grand public une fois le réseau RTE validé.
  let srcText = "source : …";
  let srcClass = "source pending";
  if (p.source === "github") {
    srcText = "source : GitHub";
    srcClass = "source github";
  } else if (p.source === "huggingface") {
    srcText = "source : HuggingFace (secours)";
    srcClass = "source hf";
  }
  const safeLbl = JSON.stringify(lbl);
  const safeStats = JSON.stringify(stats);
  const safeSrc = JSON.stringify(srcText);
  const safeSrcClass = JSON.stringify(srcClass);
  try {
    await downloadWindow.webContents.executeJavaScript(`
      document.getElementById('bar').style.width = '${pct}%';
      document.getElementById('lbl').textContent = ${safeLbl};
      document.getElementById('stats').textContent = ${safeStats};
      var s = document.getElementById('source');
      if (s) { s.textContent = ${safeSrc}; s.className = ${safeSrcClass}; }
    `, true);
  } catch { /* fenêtre fermée entre-temps, ignore */ }
}

async function pushError(msg) {
  if (!downloadWindow || downloadWindow.isDestroyed()) return;
  const safe = JSON.stringify(String(msg));
  try {
    await downloadWindow.webContents.executeJavaScript(`
      const e = document.getElementById('err');
      e.style.display = 'block';
      e.textContent = ${safe};
    `, true);
  } catch { /* ignore */ }
}

// Écrit un diagnostic réseau dans %APPDATA%\Meeting Assistant\proxy-debug.log
// (que l'utilisateur peut retrouver et envoyer). Log ce que Chromium résout
// comme proxy pour les hôtes de téléchargement — clé pour debugger un échec
// en entreprise sans avoir à ouvrir les DevTools.
async function logNetworkDiagnostics() {
  try {
    const { session } = require("electron");
    const targets = [
      "https://api.github.com",
      "https://github.com",
      "https://objects.githubusercontent.com",
      "https://huggingface.co",
    ];
    const lines = [`===== Diagnostic réseau ${new Date().toISOString()} =====`];
    for (const url of targets) {
      try {
        const p = await session.defaultSession.resolveProxy(url);
        lines.push(`  ${url}  →  ${p}`);
      } catch (e) {
        lines.push(`  ${url}  →  ERREUR ${e && e.message}`);
      }
    }
    const text = lines.join("\n") + "\n";
    console.log("[net-diag]\n" + text);
    try {
      const logPath = path.join(app.getPath("userData"), "proxy-debug.log");
      fs.appendFileSync(logPath, text);
      console.log("[net-diag] écrit dans", logPath);
    } catch { /* écriture log best-effort */ }
  } catch (e) {
    console.warn("[net-diag] échec:", e && e.message);
  }
}

async function ensureModelsDownloaded() {
  // Dev : utilise les fichiers locaux du repo, pas de download.
  if (isDev) return;
  const root = modelsRoot();
  await fs.promises.mkdir(root, { recursive: true });
  if (await allPresent(root)) {
    console.log("[electron] Tous les modèles sont déjà présents — skip download");
    return;
  }
  // Diagnostic réseau AVANT le download (utile si ça échoue : on saura quel
  // proxy Chromium voit pour github/HF).
  await logNetworkDiagnostics();
  console.log(`[electron] Téléchargement des modèles vers ${root}…`);
  await showDownloadWindow();
  try {
    await downloadAll(root, (p) => { pushProgress(p); });
    if (downloadWindow && !downloadWindow.isDestroyed()) {
      downloadWindow.close();
      downloadWindow = null;
    }
  } catch (err) {
    console.error("[electron] Download error:", err);
    await pushError(`Erreur de téléchargement : ${err.message}\n\nVérifiez votre connexion internet et relancez l'application. Les fichiers déjà téléchargés ne seront pas re-téléchargés.`);
    throw err;  // remonte au caller pour quitter proprement
  }
}

// ── Splash de démarrage ───────────────────────────────────────────────────────
// Affichée IMMÉDIATEMENT (avant le spawn backend) pour que l'app paraisse
// s'ouvrir instantanément, au lieu de laisser l'utilisateur devant un écran
// vide pendant le cold-start de backend.exe + waitForBackend(). Remplacée
// par la fenêtre principale dès que /api/health répond.
let splashWindow = null;

function splashHtml() {
  // Couleurs alignées sur webapp/app/globals.css. Le thème suit la
  // préférence système via @media prefers-color-scheme (= comportement
  // par défaut de l'app quand l'utilisateur n'a pas forcé un thème).
  return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<title>Meeting Assistant</title>
<style>
  :root{
    --surface:251 247 243; --ink:31 27 24; --ink-muted:90 82 77;
    --brand:171 55 35; --border:232 221 212; --accent:47 114 140;
  }
  @media (prefers-color-scheme: dark){
    :root{
      --surface:18 20 24; --ink:240 234 227; --ink-muted:165 155 145;
      --brand:215 95 78; --border:45 50 58; --accent:120 180 205;
    }
  }
  html,body{margin:0;padding:0;height:100%;
    background:rgb(var(--surface));color:rgb(var(--ink));
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
    overflow:hidden;-webkit-user-select:none;user-select:none;}
  body{display:flex;flex-direction:column;justify-content:center;
    align-items:center;padding:32px;text-align:center;box-sizing:border-box;
    border:1px solid rgb(var(--border));
    background-image:
      radial-gradient(circle at 0% 0%, rgb(var(--accent) / 0.08), transparent 45%),
      radial-gradient(circle at 100% 100%, rgb(var(--brand) / 0.06), transparent 50%);}
  .spinner{width:42px;height:42px;border-radius:50%;
    border:3px solid rgb(var(--border));border-top-color:rgb(var(--brand));
    animation:spin .8s linear infinite;margin-bottom:24px;}
  @keyframes spin{to{transform:rotate(360deg);}}
  h1{font-size:17px;font-weight:600;margin:0 0 8px;color:rgb(var(--ink));}
  .sub{font-size:13px;color:rgb(var(--ink-muted));margin:0;}
</style></head>
<body>
  <div class="spinner"></div>
  <h1>Meeting Assistant</h1>
  <p class="sub">Démarrage…</p>
</body></html>`;
}

async function showSplash() {
  splashWindow = new BrowserWindow({
    width: 460,
    height: 280,
    frame: false,
    resizable: false,
    maximizable: false,
    fullscreenable: false,
    center: true,
    show: false,
    icon: APP_ICON,
    // Fallback avant peinture du HTML. La fenêtre n'est révélée qu'après
    // loadURL (show:false) donc pas de flash réel ; on garde le crème
    // clair de l'app (--surface light) comme couleur neutre.
    backgroundColor: "#FBF7F3",
    title: "Meeting Assistant",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  splashWindow.setMenuBarVisibility(false);
  await splashWindow.loadURL(
    "data:text/html;charset=utf-8," + encodeURIComponent(splashHtml())
  );
  if (splashWindow && !splashWindow.isDestroyed()) splashWindow.show();
  return splashWindow;
}

function closeSplash() {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.close();
  }
  splashWindow = null;
}

// ── Window ───────────────────────────────────────────────────────────────────
let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "Meeting Assistant",
    icon: APP_ICON,
    backgroundColor: "#0b0b0f",
    // Ne pas peindre une fenêtre blanche : on attend `ready-to-show`, puis
    // on affiche la fenêtre ET on ferme le splash dans la même frame.
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.setMenuBarVisibility(false);

  // Le titre de la fenêtre reste « Meeting Assistant » : on empêche la page
  // (<title> du webapp) de l'écraser.
  mainWindow.on("page-title-updated", (e) => e.preventDefault());

  // Idempotent : `reveal()` ne doit s'exécuter QU'UNE fois. Sinon le timer
  // de secours rappellerait mainWindow.show() après coup — et comme une
  // fenêtre réduite est isVisible()===false, ça la dé-minimiserait tout seul.
  let revealed = false;
  let revealTimer = null;
  const reveal = () => {
    if (revealed) return;
    revealed = true;
    if (revealTimer) {
      clearTimeout(revealTimer);
      revealTimer = null;
    }
    if (mainWindow && !mainWindow.isDestroyed() && !mainWindow.isVisible()) {
      mainWindow.show();
    }
    closeSplash();
  };
  mainWindow.once("ready-to-show", reveal);
  // Filet de sécurité : si `ready-to-show` ne se déclenche pas (rare), on
  // révèle quand même au bout de 8 s pour ne jamais rester bloqué sur le splash.
  revealTimer = setTimeout(reveal, 8000);

  // Open external links in the system browser, not in-app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });

  // Recherche native dans la page (Ctrl+F sur le compte rendu ouvert).
  // On relaie le résultat (match courant / total) au renderer.
  mainWindow.webContents.on("found-in-page", (_e, result) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("find:result", result);
    }
  });

  const r = resolveResources();
  if (isDev && process.env.ELECTRON_DEV_URL) {
    // Optional: point at `next dev` at http://localhost:3000 for hot reload.
    mainWindow.loadURL(process.env.ELECTRON_DEV_URL);
  } else {
    const indexHtml = path.join(r.webappOut, "index.html");
    if (!fs.existsSync(indexHtml)) {
      throw new Error(`webapp index.html not found at ${indexHtml}`);
    }
    mainWindow.loadFile(indexHtml);
  }

  // Intercept fermeture fenêtre → on cache au tray par défaut (opt-OUT).
  // Comportement « close = quit » disponible via setting `quitOnClose` ou
  // si l'utilisateur a explicitement cliqué « Quitter » (isQuitting).
  mainWindow.on("close", (e) => {
    if (isQuitting || userPrefs.quitOnClose) return;
    e.preventDefault();
    mainWindow.hide();
    // Au 1er close en mode tray, on prévient l'utilisateur que l'app
    // continue de tourner — sinon confusion classique « j'ai fermé mais
    // c'est encore là ?! ». Le renderer affiche la popup et set un flag
    // dans localStorage pour ne pas la réafficher.
    mainWindow.webContents.send("tray:first-hide-hint");
  });

  mainWindow.on("closed", () => {
    if (revealTimer) {
      clearTimeout(revealTimer);
      revealTimer = null;
    }
    mainWindow = null;
  });
}

// ── Find-in-page (Ctrl+F dans le compte rendu) ───────────────────────────────
ipcMain.on("find:start", (_e, text, options) => {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const q = (text || "").trim();
  if (!q) {
    mainWindow.webContents.stopFindInPage("clearSelection");
    return;
  }
  mainWindow.webContents.findInPage(q, options || {});
});

ipcMain.on("find:stop", () => {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.stopFindInPage("clearSelection");
});

// Le renderer signale que les préférences (quitOnClose, launchAtStartup)
// ont été modifiées dans les Paramètres → main resynchronise son cache et
// applique le flag Login Item Windows si besoin.
ipcMain.on("settings:changed", async () => {
  await loadUserPrefs();
});

// Boutons « Ouvrir l'app » du popup tray → réouvre la fenêtre principale
// (et navigue vers un job/meeting précis si demandé). Le popup se ferme
// automatiquement via son listener blur.
ipcMain.on("tray-popup:open-main-app", (_e, payload) => {
  if (trayPopupWindow && trayPopupWindow.isVisible()) trayPopupWindow.hide();
  showMainWindow();
  if (payload?.jobId && mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("tray:open-job", { jobId: payload.jobId });
  } else if (payload?.meetingId && mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("notification:open-meeting", { meetingId: payload.meetingId });
  }
});

// Bouton « Quitter » du popup tray → quit complet de l'app (= bypass
// du mode tray opt-out, comme un Quitter du menu contextuel).
ipcMain.on("tray-popup:quit-app", () => {
  isQuitting = true;
  app.quit();
});

// Boutons « Démarrer/Arrêter » du popup tray → on délègue aux mêmes
// fonctions que le menu clic-droit, pour que les notifications, l'auto-
// ouverture de l'app et la gestion liveReportReady soient identiques
// quelle que soit la source du déclenchement.
ipcMain.on("tray-popup:start-recording", (_e, payload) => {
  if (trayPopupWindow && trayPopupWindow.isVisible()) trayPopupWindow.hide();
  trayStartRecording(payload?.eventId || null);
});
ipcMain.on("tray-popup:stop-recording", () => {
  if (trayPopupWindow && trayPopupWindow.isVisible()) trayPopupWindow.hide();
  trayStopRecording();
});

// ── System tray (mode arrière-plan) ──────────────────────────────────────
// L'app vit en tray par défaut (opt-OUT) : fermer la fenêtre cache l'app,
// le process Electron + backend continuent → notifications fonctionnent
// même fenêtre fermée. L'utilisateur quitte via clic-droit sur l'icône
// tray → « Quitter ». Setting « quitOnClose » dans les Paramètres pour
// revenir au comportement « close = quit » standard.
//
// L'icône tray a 2 états visuels :
//   - normal : icon.ico de l'app
//   - recording : on superpose un point rouge (généré au runtime via canvas
//     ImageData) pour signaler en permanence qu'une captation est en cours.

let tray = null;
let trayRefreshTimer = null;
// Flag posé quand l'utilisateur clique « Quitter » dans le menu tray ou
// fait Ctrl+Q : permet à window.on("close") de SAVOIR qu'on veut vraiment
// quitter (et donc laisser passer le close au lieu d'intercepter).
let isQuitting = false;
// Cache des préférences utilisateur (rechargé sur changement via IPC).
const userPrefs = { quitOnClose: false, launchAtStartup: false };
// État local pour le menu : qu'est-ce qu'on affiche dans le tray ?
const trayState = {
  recording: false,           // enregistrement en cours côté backend ?
  recordingStartedAt: null,   // ms epoch pour calculer la durée live
  recordingCalendar: null,    // snapshot agenda de l'enreg en cours (avec end time si dispo)
  upcomingMeeting: null,      // { id, subject, startMs } si réunion d'agenda imminente
};

// Notif « Fin de réunion — pensez à arrêter » : timer programmé à l'heure
// de fin déclarée dans l'agenda. _endReminderEventId mémorise l'event id
// pour ne pas re-scheduler si on refresh pendant la même session
// d'enregistrement (refreshTrayState tourne toutes les 4 s).
let _endReminderTimeout = null;
let _endReminderEventId = null;

async function loadUserPrefs() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/settings`);
    if (!res.ok) return;
    const d = await res.json();
    userPrefs.quitOnClose = !!d.quitOnClose;
    userPrefs.launchAtStartup = !!d.launchAtStartup;
    // Synchronise le flag Windows si différent de la pref persistée.
    applyLaunchAtStartup(userPrefs.launchAtStartup);
  } catch { /* backend pas prêt → on retentera */ }
}

function applyLaunchAtStartup(enabled) {
  if (process.platform !== "win32") return;
  app.setLoginItemSettings({
    openAtLogin: !!enabled,
    // --hidden = on démarre direct minimisé dans le tray plutôt que
    // d'afficher la fenêtre au login (= l'app est là « au cas où », pas
    // une nuisance au démarrage).
    args: enabled ? ["--hidden"] : [],
  });
}

function fmtDuration(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60);
  const ss = s % 60;
  return `${m.toString().padStart(2, "0")}:${ss.toString().padStart(2, "0")}`;
}

function buildTrayMenu() {
  const items = [];
  if (trayState.recording) {
    const elapsed = trayState.recordingStartedAt
      ? fmtDuration(Date.now() - trayState.recordingStartedAt)
      : "00:00";
    items.push({
      label: `● Enregistrement en cours · ${elapsed}`,
      enabled: false,
    });
    items.push({
      label: "🛑 Arrêter et générer le compte rendu",
      click: () => trayStopRecording(),
    });
    items.push({ type: "separator" });
  } else {
    items.push({
      label: "🎙 Démarrer un enregistrement (hors agenda)",
      click: () => trayStartRecording(null),
    });
    // Si une réunion d'agenda commence dans <15 min, raccourci dédié pour
    // la lancer en 1 clic avec ses participants/contexte pré-câblés.
    const u = trayState.upcomingMeeting;
    if (u && u.startMs - Date.now() < 15 * 60_000) {
      const startD = new Date(u.startMs);
      const hh = String(startD.getHours()).padStart(2, "0");
      const mm = String(startD.getMinutes()).padStart(2, "0");
      items.push({
        label: `⏭ Démarrer pour « ${u.subject} » (${hh}:${mm})`,
        click: () => trayStartRecording(u.id),
      });
    }
    items.push({ type: "separator" });
  }
  items.push({
    label: "Ouvrir Meeting Assistant",
    click: () => showMainWindow(),
  });
  items.push({ type: "separator" });
  items.push({
    label: "Quitter",
    click: () => {
      isQuitting = true;
      app.quit();
    },
  });
  return Menu.buildFromTemplate(items);
}

function refreshTrayMenu() {
  if (!tray) return;
  tray.setContextMenu(buildTrayMenu());
  // Tooltip = info au survol.
  const tip = trayState.recording
    ? "Meeting Assistant — Enregistrement en cours"
    : "Meeting Assistant";
  tray.setToolTip(tip);
}

function setupTray() {
  if (tray) return;
  tray = new Tray(APP_ICON);
  tray.setToolTip("Meeting Assistant");
  // Clic gauche : popup riche custom (style OneDrive/Teams) — UI Next.js
  // dans une BrowserWindow borderless ancrée à l'icône.
  tray.on("click", () => toggleTrayPopup());
  // Clic droit : menu contextuel textuel classique (raccourci pour les
  // utilisateurs qui préfèrent les menus système Windows).
  refreshTrayMenu();
  // Refresh régulier pour : (a) timer enregistrement, (b) state récup
  // depuis /api/record/status si l'utilisateur a démarré ailleurs,
  // (c) maj de la réunion imminente.
  trayRefreshTimer = setInterval(refreshTrayState, 4000);
  refreshTrayState();
}

function teardownTray() {
  if (trayRefreshTimer) clearInterval(trayRefreshTimer);
  trayRefreshTimer = null;
  if (trayPopupWindow && !trayPopupWindow.isDestroyed()) {
    trayPopupWindow.destroy();
  }
  trayPopupWindow = null;
  if (tray) tray.destroy();
  tray = null;
}

// ── Popup riche du tray (BrowserWindow borderless ancrée à l'icône) ─────
// Crée lazy au 1er clic, garde en mémoire ensuite (réouvertures rapides).
// Hide sur blur (clic hors de la popup) — comme OneDrive/Teams.

let trayPopupWindow = null;
const TRAY_POPUP_WIDTH = 340;
const TRAY_POPUP_HEIGHT = 480;

function createTrayPopupWindow() {
  if (trayPopupWindow && !trayPopupWindow.isDestroyed()) return trayPopupWindow;
  const r = resolveResources();
  trayPopupWindow = new BrowserWindow({
    width: TRAY_POPUP_WIDTH,
    height: TRAY_POPUP_HEIGHT,
    show: false,
    frame: false,             // sans bordure ni titre Windows
    resizable: false,
    movable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,        // n'apparaît pas dans la barre des tâches
    alwaysOnTop: true,        // reste au-dessus pendant qu'on regarde
    // PAS de transparent:true ici — sous Windows ça casse complètement la
    // réception des clics dans le webview (le popup s'affiche mais aucun
    // bouton ne réagit). On garde frame:false + un backgroundColor opaque
    // qui matche le thème de la card, et le contenu (bg-surface) prend le
    // relais une fois React monté. Sacrifice esthétique : les coins du
    // popup sont rectangulaires au lieu d'arrondis — un compromis
    // acceptable pour avoir un popup fonctionnel.
    backgroundColor: "#1a1d23",
    title: "Meeting Assistant — Aperçu",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  trayPopupWindow.setMenuBarVisibility(false);
  // Charge la route /tray-popup du Next.js (dev = serveur, prod = fichier statique).
  if (isDev && process.env.ELECTRON_DEV_URL) {
    trayPopupWindow.loadURL(`${process.env.ELECTRON_DEV_URL}/tray-popup`);
  } else {
    // Next.js static export SANS trailingSlash → app/tray-popup/page.tsx
    // devient out/tray-popup.html (à la racine, même niveau qu'index.html).
    // C'est CRUCIAL pour que assetPrefix "./" résolve les assets vers
    // out/_next/ (et non out/tray-popup/_next/ qui n'existe pas → popup nu).
    trayPopupWindow.loadFile(path.join(r.webappOut, "tray-popup.html"));
  }
  // Hide automatique quand on perd le focus (clic n'importe où ailleurs).
  trayPopupWindow.on("blur", () => {
    if (trayPopupWindow && trayPopupWindow.isVisible()) trayPopupWindow.hide();
  });
  return trayPopupWindow;
}

function positionTrayPopup() {
  if (!tray || !trayPopupWindow) return;
  const trayBounds = tray.getBounds();
  const { screen } = require("electron");
  const display = screen.getDisplayMatching(trayBounds);
  // On centre horizontalement sur l'icône tray, et on place AU-DESSUS de
  // l'icône (la barre des tâches Windows est en bas par défaut). Clamp
  // dans les limites de l'écran pour éviter de déborder.
  let x = Math.round(trayBounds.x + trayBounds.width / 2 - TRAY_POPUP_WIDTH / 2);
  let y = Math.round(trayBounds.y - TRAY_POPUP_HEIGHT - 12);
  const workArea = display.workArea;
  // Clamp horizontal (8 px de marge).
  x = Math.max(workArea.x + 8, Math.min(x, workArea.x + workArea.width - TRAY_POPUP_WIDTH - 8));
  // Si la tray est en HAUT (barre des tâches en haut), on tombe sous l'icône.
  if (y < workArea.y) y = trayBounds.y + trayBounds.height + 12;
  trayPopupWindow.setPosition(x, y, false);
}

function toggleTrayPopup() {
  const w = createTrayPopupWindow();
  if (w.isVisible()) {
    w.hide();
    return;
  }
  positionTrayPopup();
  w.show();
  w.focus();
}

function showMainWindow() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    mainWindow.show();
    mainWindow.focus();
  }
}

async function refreshTrayState() {
  // (a) état enregistrement
  let changed = false;
  try {
    const r = await fetch(`${BACKEND_URL}/api/record/status`);
    if (r.ok) {
      const d = await r.json();
      const wasRec = trayState.recording;
      trayState.recording = !!d.recording;
      trayState.recordingStartedAt = d.startedAt || null;
      trayState.recordingCalendar = d.calendar || null;
      if (wasRec !== trayState.recording) changed = true;

      // Programme (ou annule) la notif « Fin de réunion » selon l'état
      // d'enregistrement courant et la présence d'une heure de fin d'agenda.
      // On ne notifie que si l'enregistrement vient d'une réunion d'agenda
      // avec un end time futur — un hors-agenda n'a pas de fin connue.
      scheduleEndOfMeetingReminder();
    }
  } catch { /* backend KO */ }

  // (b) réunion imminente (la plus proche dans les 30 prochaines min)
  try {
    const r = await fetch(`${BACKEND_URL}/api/calendar/upcoming?days=1`);
    if (r.ok) {
      const d = await r.json();
      const now = Date.now();
      let best = null;
      for (const m of d.meetings || []) {
        const t = Date.parse(m.start);
        if (!Number.isFinite(t)) continue;
        if (t < now - 60_000) continue;
        if (t - now > 30 * 60_000) continue;
        if (!best || t < best.startMs) {
          best = { id: m.id, subject: m.subject || "(sans objet)", startMs: t };
        }
      }
      const prev = trayState.upcomingMeeting;
      if (JSON.stringify(prev) !== JSON.stringify(best)) {
        trayState.upcomingMeeting = best;
        changed = true;
      }
    }
  } catch { /* ignore */ }

  // (c) icône tray = normal ou « recording » (point rouge en surimpression)
  if (tray) {
    tray.setImage(makeTrayIcon(trayState.recording));
  }

  // Toujours rebâtir le menu (timer live), même si rien n'a structurellement
  // changé — c'est le seul moyen de mettre à jour le compteur MM:SS.
  refreshTrayMenu();
}

// Génère un PNG en mémoire = icône de base + (si recording) un disque rouge
// en bas à droite. Pas de fichier supplémentaire à packager.
let _baseTrayImageCache = null;
function makeTrayIcon(recording) {
  if (!_baseTrayImageCache) {
    _baseTrayImageCache = nativeImage.createFromPath(APP_ICON);
  }
  if (!recording) return _baseTrayImageCache;
  // Note : Electron ne fournit pas d'API trivial pour composer 2 images
  // côté main process sans dépendre de canvas. On retombe sur l'icône
  // normale et c'est le menu/tooltip qui signale le recording. Acceptable
  // pour la v1 — on pourra ajouter une vraie icône-rouge.ico packagée
  // plus tard si on veut un visuel plus marqué.
  return _baseTrayImageCache;
}

async function trayStartRecording(eventId) {
  // Si on lance depuis une réunion d'agenda, on rapatrie son contexte
  // (participants/sujet) pour que le pipeline ait les bons noms.
  let payload = { enableLiveLlm: true };
  if (eventId) {
    try {
      const r = await fetch(`${BACKEND_URL}/api/calendar/upcoming?days=1`);
      if (r.ok) {
        const d = await r.json();
        const m = (d.meetings || []).find((mm) => mm.id === eventId);
        if (m) {
          payload = {
            enableLiveLlm: true,
            participants: (m.attendees || [])
              .map((a) => a.name)
              .filter(Boolean)
              .join(", "),
            entreprises: "",
            contexte: `Réunion : ${m.subject}\n${m.location || ""}`.trim(),
            calendar: {
              eventId: m.id,
              subject: m.subject,
              start: m.start,
              end: m.end,
              location: m.location,
              organizer: m.organizer?.name || m.organizer?.address,
              attendees: (m.attendees || [])
                .map((a) => a.name)
                .filter(Boolean),
            },
          };
        }
      }
    } catch { /* ignore — on fera un hors-agenda */ }
  }
  try {
    const r = await fetch(`${BACKEND_URL}/api/record/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    // Pas de notif « Enregistrement démarré » : l'utilisateur vient de
    // déclencher l'action, le feedback visuel (icône tray qui change,
    // app qui affiche le timer) suffit. On limite les notifs aux moments
    // où l'utilisateur N'EST PAS devant l'app.
    refreshTrayState();
  } catch (e) {
    new Notification({
      title: "Meeting Assistant",
      body: `Échec du démarrage : ${e.message}`,
      icon: APP_ICON,
    }).show();
  }
}

async function trayStopRecording() {
  try {
    const r = await fetch(`${BACKEND_URL}/api/record/stop`, { method: "POST" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();

    // Notif tirée UNIQUEMENT si le CR est prêt immédiatement (live LLM
    // a tout fait pendant la captation). Sinon pas de notif — on n'embête
    // pas l'utilisateur, l'app s'ouvre direct sur le brouillon et il
    // recevra de toute façon une notif « CR prêt » plus tard via
    // pollCrReadyOnce quand le batch sera fini.
    if (d?.liveReportReady) {
      _crReadySeen.add(d.jobId);
      const notif = new Notification({
        title: "✓ Compte rendu prêt",
        body: "Cliquez pour le consulter.",
        icon: APP_ICON,
      });
      if (d?.jobId && mainWindow && !mainWindow.isDestroyed()) {
        notif.on("click", () => {
          showMainWindow();
          mainWindow.webContents.send("tray:open-job", { jobId: d.jobId });
        });
      }
      notif.show();
    }

    // Auto-ouverture immédiate de la fenêtre principale sur le job
    // (que ce soit le brouillon ou le CR prêt). Même si l'utilisatrice
    // ne clique pas la notif, elle retrouve directement sa réunion en
    // basculant sur la fenêtre. Délai 100 ms pour donner le temps à
    // mainWindow.show() de réveiller le renderer avant l'IPC.
    if (d?.jobId && mainWindow && !mainWindow.isDestroyed()) {
      showMainWindow();
      setTimeout(() => {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("tray:open-job", { jobId: d.jobId });
        }
      }, 100);
    }
    refreshTrayState();
  } catch (e) {
    new Notification({
      title: "Meeting Assistant",
      body: `Échec de l'arrêt : ${e.message}`,
      icon: APP_ICON,
    }).show();
  }
}

// ── Notification « Compte rendu prêt » au passage running → done ────────
// Poll régulier des jobs en cours pour repérer la transition. Une fois
// notifié pour un job, on l'oublie pour ne pas re-notifier.
const _crReadySeen = new Set();
let _crReadyPollTimer = null;
let _crReadyKnownRunning = new Set();  // jobs vus running au tour précédent

async function pollCrReadyOnce() {
  try {
    const r = await fetch(`${BACKEND_URL}/api/jobs`);
    if (!r.ok) return;
    const d = await r.json();
    const newRunning = new Set();
    for (const j of d.jobs || []) {
      if (j.status === "running" || j.status === "queued" || j.status === "pending") {
        newRunning.add(j.id);
      } else if (j.status === "done"
                 && _crReadyKnownRunning.has(j.id)
                 && !_crReadySeen.has(j.id)) {
        // Transition running → done détectée → notif.
        _crReadySeen.add(j.id);
        const label = j.label || `Réunion ${j.id.slice(0, 8)}`;
        const n = new Notification({
          title: "Compte rendu prêt",
          body: `${label} — cliquez pour consulter.`,
          icon: APP_ICON,
        });
        n.on("click", () => {
          showMainWindow();
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send("tray:open-job", { jobId: j.id });
          }
        });
        n.show();
      }
    }
    _crReadyKnownRunning = newRunning;
  } catch { /* ignore */ }
}

function setupCrReadyNotifications() {
  pollCrReadyOnce();
  _crReadyPollTimer = setInterval(pollCrReadyOnce, 5000);
}

function teardownCrReadyNotifications() {
  if (_crReadyPollTimer) clearInterval(_crReadyPollTimer);
  _crReadyPollTimer = null;
}

// ── Notifications natives 5 min avant chaque réunion d'agenda ───────────────
// Poll régulièrement le backend pour la liste des réunions à venir, puis
// programme une notification Windows toast pour chacune à -5 min. Clic →
// la fenêtre Meeting Assistant revient au premier plan et on signale au
// renderer (page.tsx) la réunion à ouvrir via IPC.
//
// État local :
//  - `scheduledNotifs` mappe meetingId → timeoutId pour éviter de re-scheduler
//    (le poll tourne toutes les 5 min, mais une réunion à -7 min serait
//    schedulée AU 1er poll qui la voit, pas re-schedulée aux suivants).
//  - `notifiedIds` mappe meetingId → true une fois la notif tirée pour ne
//    pas re-notifier si elle est encore dans la fenêtre des 5 min suivants.

const NOTIFY_LEAD_MIN = 5;          // minutes avant la réunion
const NOTIFY_POLL_MS = 5 * 60_000;   // toutes les 5 min
const NOTIFY_LOOKAHEAD_MS = 60 * 60_000;  // schedule les réunions des 60 min à venir

const scheduledNotifs = new Map();   // meetingId → timeoutId
const notifiedIds = new Set();        // meetingId déjà notifiés (évite doublons)
let notifyPollTimer = null;

async function pollUpcomingForNotifications() {
  try {
    const res = await fetch(`${BACKEND_URL}/api/calendar/upcoming?days=1`);
    if (!res.ok) return;  // pas connecté à Microsoft, ou backend KO — on retentera
    const data = await res.json();
    const meetings = Array.isArray(data?.meetings) ? data.meetings : [];

    // Index des jobs existants pour skipper les réunions déjà enregistrées
    // (sinon on notifie pour une réunion dont l'utilisateur a déjà le CR).
    let recordedEventIds = new Set();
    try {
      const jr = await fetch(`${BACKEND_URL}/api/jobs`);
      if (jr.ok) {
        const jd = await jr.json();
        for (const j of jd?.jobs || []) {
          const eid = j?.calendar?.eventId;
          if (eid) recordedEventIds.add(eid);
        }
      }
    } catch { /* ignore */ }

    const now = Date.now();
    for (const m of meetings) {
      if (!m.id || !m.start) continue;
      if (recordedEventIds.has(m.id)) continue;
      if (scheduledNotifs.has(m.id)) continue;
      if (notifiedIds.has(m.id)) continue;
      const startMs = Date.parse(m.start);
      if (Number.isNaN(startMs)) continue;
      const notifyAt = startMs - NOTIFY_LEAD_MIN * 60_000;
      const delay = notifyAt - now;
      // Ignore les réunions trop loin (on retentera au prochain poll) et
      // celles déjà passées de plus d'une minute (notif inutile).
      if (delay > NOTIFY_LOOKAHEAD_MS) continue;
      if (delay < -60_000) continue;
      const safeDelay = Math.max(0, delay);
      const tid = setTimeout(() => {
        scheduledNotifs.delete(m.id);
        notifiedIds.add(m.id);
        showMeetingNotification(m);
      }, safeDelay);
      scheduledNotifs.set(m.id, tid);
      console.log(
        `[notif] programmée dans ${Math.round(safeDelay / 1000)}s : "${m.subject}"`
      );
    }
  } catch (e) {
    console.warn("[notif] poll a levé :", e && e.message);
  }
}

function scheduleEndOfMeetingReminder() {
  // Cas 1 : pas / plus d'enregistrement → on annule tout timer en attente.
  if (!trayState.recording) {
    if (_endReminderTimeout) {
      clearTimeout(_endReminderTimeout);
      _endReminderTimeout = null;
    }
    _endReminderEventId = null;
    return;
  }
  // Cas 2 : recording + agenda avec eventId + end time → on programme la
  // notif, à condition de ne pas l'avoir DÉJÀ programmée pour ce même
  // event (refresh tourne toutes les 4 s, on évite l'accumulation de
  // timers identiques).
  const eventId = trayState.recordingCalendar?.eventId;
  const endStr = trayState.recordingCalendar?.end;
  if (!eventId || !endStr) {
    // Enregistrement hors agenda OU pas d'heure de fin → pas de rappel.
    if (_endReminderTimeout) {
      clearTimeout(_endReminderTimeout);
      _endReminderTimeout = null;
    }
    _endReminderEventId = null;
    return;
  }
  if (_endReminderEventId === eventId && _endReminderTimeout) return;
  // Nouveau / changement d'event → reset le timer précédent
  if (_endReminderTimeout) clearTimeout(_endReminderTimeout);
  const endMs = Date.parse(endStr);
  if (!Number.isFinite(endMs)) return;
  const delay = endMs - Date.now();
  // Si on a déjà dépassé l'heure de fin (utilisateur a démarré tard,
  // la réunion tourne en overtime), on ne notifie pas — l'utilisateur
  // est conscient que ça déborde.
  if (delay <= 0) {
    _endReminderEventId = eventId;  // empêche re-scheduling sur le même event
    return;
  }
  _endReminderTimeout = setTimeout(() => {
    _endReminderTimeout = null;
    // Re-vérification au moment de tirer : peut-être que l'utilisateur a
    // arrêté l'enregistrement avant l'heure de fin.
    if (!trayState.recording) return;
    if (trayState.recordingCalendar?.eventId !== eventId) return;
    showEndOfMeetingNotification(trayState.recordingCalendar);
  }, delay);
  _endReminderEventId = eventId;
}

function showEndOfMeetingNotification(calendar) {
  const subject = calendar?.subject || "Réunion";
  const n = new Notification({
    title: "Fin de réunion",
    body: `${subject} est terminée — pensez à arrêter l'enregistrement.`,
    icon: APP_ICON,
  });
  n.on("click", () => {
    showMainWindow();
  });
  n.show();
}

function showMeetingNotification(meeting) {
  if (!Notification.isSupported()) {
    console.warn("[notif] Notifications non supportées sur cette plateforme");
    return;
  }
  const startDate = new Date(meeting.start);
  const hh = String(startDate.getHours()).padStart(2, "0");
  const mm = String(startDate.getMinutes()).padStart(2, "0");
  const subject = meeting.subject || "Réunion sans objet";
  const n = new Notification({
    title: `Réunion à ${hh}:${mm} — ${subject}`,
    body: `Commence dans ${NOTIFY_LEAD_MIN} min. Cliquez pour ouvrir Meeting Assistant et enregistrer.`,
    icon: APP_ICON,
    silent: false,
  });
  n.on("click", () => {
    // Ramène la fenêtre principale au premier plan…
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
      // …puis signale au renderer la réunion à ouvrir (page.tsx → setSelected).
      mainWindow.webContents.send("notification:open-meeting", { meetingId: meeting.id });
    }
  });
  n.show();
}

function setupMeetingNotifications() {
  if (isDev) {
    // En dev on garde la feature active (utile pour tester) mais sans bug
    // si le backend met du temps à se lever : on poll quand même.
  }
  // 1er poll immédiat puis toutes les 5 min en boucle.
  pollUpcomingForNotifications();
  notifyPollTimer = setInterval(pollUpcomingForNotifications, NOTIFY_POLL_MS);
}

function teardownMeetingNotifications() {
  if (notifyPollTimer) clearInterval(notifyPollTimer);
  notifyPollTimer = null;
  for (const tid of scheduledNotifs.values()) clearTimeout(tid);
  scheduledNotifs.clear();
}

// ── Mise à jour automatique (GitHub privé, electron-updater) ─────────────────
// Télécharge en fond, installe au redémarrage. L'utilisateur ne désinstalle
// jamais rien. En dev (app non packagée) : no-op. Toute erreur est silencieuse
// (un poste hors-ligne ou un souci réseau ne doit pas bloquer l'app).
function setupAutoUpdate() {
  if (isDev) return;
  try {
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on("update-downloaded", (info) => {
      const { dialog } = require("electron");
      const win =
        mainWindow && !mainWindow.isDestroyed() ? mainWindow : undefined;
      dialog
        .showMessageBox(win, {
          type: "info",
          buttons: ["Redémarrer maintenant", "Plus tard"],
          defaultId: 0,
          cancelId: 1,
          title: "Mise à jour",
          message: "Une nouvelle version de Meeting Assistant est prête.",
          detail: `Version ${
            info && info.version ? info.version : ""
          } — elle s'installera au redémarrage de l'application.`,
        })
        .then(async (r) => {
          if (r.response !== 0) return;
          // CRUCIAL : on doit attendre que backend.exe + llama-server.exe
          // soient VRAIMENT morts avant que NSIS écrase les fichiers, sinon
          // l'installeur reste bloqué sur "Accès refusé". L'ancienne version
          // de ce handler appelait stopBackend() (fire-and-forget) puis
          // quitAndInstall immédiatement → gel observé sur les postes de
          // test.
          await stopBackendAndWait();
          autoUpdater.quitAndInstall();
        })
        .catch(() => {});
    });

    autoUpdater.on("error", (e) => {
      console.error(
        "[updater] error:",
        e == null ? "unknown" : e.stack || e.message || String(e)
      );
    });

    autoUpdater.checkForUpdates().catch((e) => {
      console.error("[updater] checkForUpdates failed:", e && e.message);
    });
  } catch (e) {
    console.error("[updater] setup failed:", e && e.message);
  }
}

// ── App lifecycle ────────────────────────────────────────────────────────────
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(async () => {
    try {
      // 1) Vérifie/télécharge les modèles ML (premier lancement uniquement).
      //    Bloque tant que les ~2.3 GB ne sont pas en place — sinon le
      //    backend planterait au démarrage sur "FileNotFoundError".
      //    (Cette étape a sa propre fenêtre de progression.)
      await ensureModelsDownloaded();
      // 2) Splash immédiat : l'utilisateur voit une fenêtre en <1 s pendant
      //    tout le cold-start backend (étapes 3-4), au lieu d'un écran vide.
      await showSplash();
      // 3) Démarre le backend Python.
      startBackend();
      // 4) Attend que /api/health réponde.
      await waitForBackend();
      // 5) Crée la fenêtre principale ; elle remplace le splash dès qu'elle
      //    est prête à peindre (voir `reveal()` dans createWindow()).
      createWindow();
      // 6) Vérifie les mises à jour en arrière-plan (prod uniquement).
      setupAutoUpdate();
      // 7) Charge les préférences utilisateur (quitOnClose, launchAtStartup).
      //    Asynchrone, ne bloque pas le démarrage. Synchronise au passage le
      //    flag Windows de lancement au démarrage avec la pref persistée.
      await loadUserPrefs();
      // 8) System tray : icône + menu contextuel. L'app peut désormais
      //    être réduite à l'icône tray quand l'utilisateur ferme la fenêtre.
      setupTray();
      // 9) Notifications natives 5 min avant chaque réunion d'agenda.
      //    Poll continu : 1er tick immédiat, puis toutes les 5 min.
      setupMeetingNotifications();
      // 10) Notifs « compte rendu prêt » au passage running → done.
      setupCrReadyNotifications();
      // 11) Démarrage hidden via --hidden (cas « lancer au démarrage Windows »)
      //     → on minimise direct au tray pour ne pas s'imposer à l'utilisateur
      //     qui vient d'ouvrir sa session.
      if (process.argv.includes("--hidden") && mainWindow) {
        mainWindow.once("ready-to-show", () => mainWindow?.hide());
      }
    } catch (err) {
      closeSplash();
      console.error("[electron] startup failure:", err);
      const { dialog } = require("electron");
      dialog.showErrorBox(
        "Meeting Assistant",
        `Le démarrage a échoué.\n\n${err.message}`
      );
      app.quit();
    }
  });

  app.on("window-all-closed", () => {
    // En mode TRAY (opt-out) : NE PAS quitter quand la fenêtre se ferme,
    // sinon le backend Python meurt et on perd les notifications + la
    // possibilité d'enregistrer depuis le tray. L'app ne quitte VRAIMENT
    // que si l'utilisateur clique « Quitter » dans le menu tray (qui pose
    // isQuitting=true) ou si quitOnClose est activé.
    if (isQuitting || userPrefs.quitOnClose) {
      app.quit();
    }
  });

  // before-quit signale qu'on quitte pour de bon → on flag pour que les
  // listeners de close laissent passer (au lieu d'intercepter en hide).
  app.on("before-quit", () => { isQuitting = true; });
  app.on("before-quit", stopBackend);
  app.on("will-quit", stopBackend);
  app.on("will-quit", teardownMeetingNotifications);
  app.on("will-quit", teardownCrReadyNotifications);
  app.on("will-quit", teardownTray);
}

// AppUserModelID — IMPORTANT sous Windows pour que les toast notifications
// affichent le bon nom d'app (« Meeting Assistant ») et la bonne icône
// dans le centre de notifications, au lieu de « electron.app.Default » qui
// est le comportement par défaut. Doit matcher l'appId de package.json.
if (process.platform === "win32") {
  app.setAppUserModelId("com.yele.meeting-assistant");
}

module.exports = { BACKEND_URL };
