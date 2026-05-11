"use strict";

const { app, BrowserWindow, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const { spawn } = require("child_process");
const http = require("http");
const treeKill = require("tree-kill");
const { downloadAll, allPresent } = require("./downloader");

const BACKEND_PORT = 8000;
const BACKEND_HOST = "127.0.0.1";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const HEALTH_PATH = "/api/health";
const HEALTH_TIMEOUT_MS = 90_000;

const isDev = !app.isPackaged;

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
  return `<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"/>
<title>Meeting Assistant — Installation</title>
<style>
  html,body{margin:0;padding:0;height:100%;background:#0b0b0f;color:#e6e6ec;
    font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;}
  body{display:flex;flex-direction:column;justify-content:center;
    align-items:center;padding:32px;text-align:center;}
  h1{font-size:18px;font-weight:600;margin:0 0 8px;}
  .sub{font-size:13px;color:#9aa0a6;margin-bottom:32px;max-width:420px;
    line-height:1.5;}
  .label{font-size:13px;color:#cfd2d8;margin-bottom:8px;
    height:18px;font-variant-numeric:tabular-nums;}
  .bar-wrap{width:100%;max-width:480px;height:8px;background:#1f2024;
    border-radius:4px;overflow:hidden;}
  .bar{height:100%;width:0%;background:linear-gradient(90deg,#4c7eff,#7c5cff);
    transition:width .15s linear;}
  .stats{font-size:12px;color:#7d828c;margin-top:12px;
    font-variant-numeric:tabular-nums;}
  .err{color:#ff6b6b;margin-top:24px;font-size:13px;max-width:480px;
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
    backgroundColor: "#0b0b0f",
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
  const lbl = `${p.itemIndex + 1}/${p.itemCount} — ${p.label}`;
  const stats = `${fmtBytes(p.totalReceivedBytes)} / ${fmtBytes(p.totalBytes)} (${pct} %)`;
  const safeLbl = JSON.stringify(lbl);
  const safeStats = JSON.stringify(stats);
  try {
    await downloadWindow.webContents.executeJavaScript(`
      document.getElementById('bar').style.width = '${pct}%';
      document.getElementById('lbl').textContent = ${safeLbl};
      document.getElementById('stats').textContent = ${safeStats};
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

async function ensureModelsDownloaded() {
  // Dev : utilise les fichiers locaux du repo, pas de download.
  if (isDev) return;
  const root = modelsRoot();
  await fs.promises.mkdir(root, { recursive: true });
  if (await allPresent(root)) {
    console.log("[electron] Tous les modèles sont déjà présents — skip download");
    return;
  }
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

// ── Window ───────────────────────────────────────────────────────────────────
let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 900,
    minHeight: 600,
    title: "Meeting Assistant",
    backgroundColor: "#0b0b0f",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.setMenuBarVisibility(false);

  // Open external links in the system browser, not in-app.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
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

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
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
      await ensureModelsDownloaded();
      // 2) Démarre le backend Python.
      startBackend();
      // 3) Attend que /api/health réponde.
      await waitForBackend();
      // 4) Affiche la fenêtre principale.
      createWindow();
    } catch (err) {
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
    // Quit on all platforms — this is a Windows-only desktop app and we don't
    // want a hidden background process eating RAM after the user closes the UI.
    app.quit();
  });

  app.on("before-quit", stopBackend);
  app.on("will-quit", stopBackend);
}

module.exports = { BACKEND_URL };
