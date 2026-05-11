"use strict";

// Downloader HTTPS avec :
//   - Suivi des redirects (HF redirige vers cdn-lfs.huggingface.co)
//   - Reprise via Range header (un crash en plein milieu d'un téléchargement
//     2 GB ne fait pas tout recommencer)
//   - Vérification taille exacte (les fichiers HF ont une taille connue)
//   - Liste dynamique pour MiniLM via l'API HF
//
// Aucune dépendance externe : utilise uniquement les modules Node.js
// stdlib (https, fs, path) pour rester aussi léger que possible et
// éviter d'embarquer axios/got dans l'asar.

const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");
const https = require("https");
const {
  STATIC_MANIFEST,
  MINILM_REPO,
  MINILM_REL_DIR,
  hfUrl,
  hfApiTree,
} = require("./model_manifest");

const USER_AGENT = "MeetingAssistant/0.1 (electron downloader)";
// Timeout INACTIVITÉ : si aucun byte ne transite pendant N secondes →
// abort (vrai blocage, pas un download lent). Réinitialisé à chaque chunk
// reçu côté `data` listener. 120s = robuste sur 4G/wifi capricieux.
const IDLE_TIMEOUT_MS = 120_000;
const MAX_RETRIES_PER_FILE = 3;
const RETRY_BACKOFF_MS = 2_000;

// ── HTTP helpers ────────────────────────────────────────────────────────

// Résout un Location: header (potentiellement relatif type "/path/file")
// contre l'URL courante. HF/cdn-lfs retourne parfois du relatif après le
// premier redirect, ce qui crashe https.get(rawRelativeString).
function resolveRedirectUrl(rawLocation, currentUrl) {
  if (!rawLocation) {
    throw new Error(`Redirect sans header Location depuis ${currentUrl}`);
  }
  // new URL(absolute) marche tel quel ; new URL(relative, base) résout.
  return new URL(rawLocation, currentUrl).toString();
}

function httpsGetJson(url) {
  return new Promise((resolve, reject) => {
    const req = https.get(
      url,
      { headers: { "User-Agent": USER_AGENT, Accept: "application/json" } },
      (res) => {
        if ([301, 302, 307, 308].includes(res.statusCode)) {
          res.resume();
          try {
            const next = resolveRedirectUrl(res.headers.location, url);
            return resolve(httpsGetJson(next));
          } catch (e) { return reject(e); }
        }
        if (res.statusCode !== 200) {
          res.resume();
          return reject(new Error(`HTTP ${res.statusCode} on ${url}`));
        }
        let body = "";
        res.on("data", (c) => (body += c));
        res.on("end", () => {
          try { resolve(JSON.parse(body)); } catch (e) { reject(e); }
        });
      }
    );
    req.on("error", reject);
    req.setTimeout(IDLE_TIMEOUT_MS, () => {
      req.destroy(new Error(`Timeout on ${url}`));
    });
  });
}

// Télécharge un fichier vers `destPath`. Reprend si partiel. Si une
// erreur réseau survient en cours de download, réessaie jusqu'à
// MAX_RETRIES_PER_FILE fois (en reprenant via Range — ne re-télécharge
// pas ce qui a déjà été écrit).
async function downloadOne(url, destPath, expectedBytes, onProgress) {
  await fsp.mkdir(path.dirname(destPath), { recursive: true });

  // Cleanup initial : si le fichier local est plus gros qu'attendu (corruption),
  // on supprime pour repartir à zéro.
  try {
    const stat = await fsp.stat(destPath);
    if (expectedBytes && stat.size === expectedBytes) {
      if (onProgress) onProgress(stat.size, expectedBytes);
      return; // déjà complet
    }
    if (expectedBytes && stat.size > expectedBytes) {
      await fsp.unlink(destPath);
    }
  } catch { /* fichier absent, OK */ }

  let attempt = 0;
  let lastErr = null;
  while (attempt < MAX_RETRIES_PER_FILE) {
    attempt++;
    try {
      await downloadOneAttempt(url, destPath, expectedBytes, onProgress);
      return;  // succès
    } catch (err) {
      lastErr = err;
      console.warn(`[downloader] tentative ${attempt}/${MAX_RETRIES_PER_FILE} échouée pour ${url}: ${err.message}`);
      if (attempt < MAX_RETRIES_PER_FILE) {
        // Backoff progressif avant retry — laisse le réseau se stabiliser
        await new Promise(r => setTimeout(r, RETRY_BACKOFF_MS * attempt));
      }
    }
  }
  throw new Error(`Échec après ${MAX_RETRIES_PER_FILE} tentatives : ${lastErr.message}`);
}

// Une tentative de download. Calcule le startByte FRAIS à chaque appel
// pour reprendre depuis l'état actuel du fichier (utile entre retries).
function downloadOneAttempt(url, destPath, expectedBytes, onProgress) {
  return new Promise(async (resolve, reject) => {
    let startByte = 0;
    try {
      const stat = await fsp.stat(destPath);
      if (expectedBytes && stat.size === expectedBytes) {
        if (onProgress) onProgress(stat.size, expectedBytes);
        return resolve();
      }
      if (expectedBytes && stat.size < expectedBytes) {
        startByte = stat.size;
      }
    } catch { /* fichier absent : fresh */ }

    let settled = false;
    const safeReject = (err) => {
      if (settled) return;
      settled = true;
      reject(err);
    };
    const safeResolve = () => {
      if (settled) return;
      settled = true;
      resolve();
    };

    const fetch = (currentUrl, redirectsLeft) => {
      const opts = { headers: { "User-Agent": USER_AGENT } };
      if (startByte > 0) opts.headers["Range"] = `bytes=${startByte}-`;

      const req = https.get(currentUrl, opts, (res) => {
        if ([301, 302, 307, 308].includes(res.statusCode)) {
          res.resume();
          if (redirectsLeft <= 0) {
            return safeReject(new Error(`Too many redirects on ${url}`));
          }
          let next;
          try { next = resolveRedirectUrl(res.headers.location, currentUrl); }
          catch (e) { return safeReject(e); }
          return fetch(next, redirectsLeft - 1);
        }
        if (res.statusCode !== 200 && res.statusCode !== 206) {
          res.resume();
          return safeReject(new Error(
            `HTTP ${res.statusCode} for ${currentUrl}`));
        }
        // Si on a demandé Range et le serveur a renvoyé 200 (ignore Range),
        // on doit repartir de 0 — réécrit le fichier complètement.
        if (startByte > 0 && res.statusCode === 200) {
          startByte = 0;
        }

        const total = expectedBytes
          || (parseInt(res.headers["content-length"] || "0", 10) + startByte);
        let received = startByte;

        const out = fs.createWriteStream(destPath, {
          flags: startByte > 0 ? "a" : "w",
        });

        // Idle timeout RESET à chaque chunk reçu — détecte un vrai stall
        // (= aucun byte pendant IDLE_TIMEOUT_MS) plutôt qu'un download lent.
        let idleTimer = null;
        const armIdleTimer = () => {
          if (idleTimer) clearTimeout(idleTimer);
          idleTimer = setTimeout(() => {
            req.destroy(new Error(
              `Pas de données depuis ${IDLE_TIMEOUT_MS / 1000}s sur ${currentUrl}`));
          }, IDLE_TIMEOUT_MS);
        };
        const clearIdleTimer = () => {
          if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; }
        };

        armIdleTimer();
        res.on("data", (chunk) => {
          received += chunk.length;
          armIdleTimer();
          if (onProgress) onProgress(received, total);
        });
        res.pipe(out);
        out.on("finish", () => out.close((err) => {
          clearIdleTimer();
          if (err) safeReject(err);
          else safeResolve();
        }));
        out.on("error", (err) => { clearIdleTimer(); safeReject(err); });
        res.on("error", (err) => { clearIdleTimer(); safeReject(err); });
      });
      req.on("error", safeReject);
    };
    fetch(url, 8);
  });
}

// ── MiniLM dynamic listing ──────────────────────────────────────────────

// Fichiers MiniLM strictement nécessaires pour sentence-transformers en
// inférence Python. Aligné sur prepare_assets.py pour cohérence avec
// l'ancien chemin "tout packagé". On EXCLUT :
//   - README.md, .gitattributes, train_script.py, data_config.json (meta/training)
//   - pytorch_model.bin, rust_model.ot, tf_model.h5 (variantes du modèle, on
//     garde model.safetensors qui est le format de référence)
//   - onnx/, openvino/ (exports pour autres runtimes, pas utilisés ici)
const MINILM_KEEP_PATTERNS = [
  /^config\.json$/,
  /^config_sentence_transformers\.json$/,
  /^modules\.json$/,
  /^sentence_bert_config\.json$/,
  /^special_tokens_map\.json$/,
  /^tokenizer\.json$/,
  /^tokenizer_config\.json$/,
  /^vocab\.txt$/,
  /^model\.safetensors$/,
  /^1_Pooling\//,
  /^2_Normalize\//,
];

function shouldKeepMinilmFile(p) {
  return MINILM_KEEP_PATTERNS.some((re) => re.test(p));
}

async function listMinilmFiles() {
  // ?recursive=true expanse les sous-dossiers (1_Pooling/, 2_Normalize/)
  // que l'API renvoie sinon comme des entrées "directory" sans contenu.
  // Sans ça : on rate 1_Pooling/config.json → SentenceTransformer crashe à
  // l'init (Pooling.__init__() missing 'embedding_dimension').
  const url = hfApiTree(MINILM_REPO) + "?recursive=true";
  const tree = await httpsGetJson(url);
  return tree.filter(
    (e) => e.type === "file" && shouldKeepMinilmFile(e.path)
  );
}

// ── Manifest assembly ────────────────────────────────────────────────────

async function buildFullManifest() {
  const minilmFiles = await listMinilmFiles();
  const minilmItems = minilmFiles.map((f) => ({
    label: `MiniLM — ${f.path}`,
    url: hfUrl(MINILM_REPO, f.path),
    relPath: path.posix.join(MINILM_REL_DIR, f.path),
    bytes: f.size,
  }));
  return [...STATIC_MANIFEST, ...minilmItems];
}

// Vérifie présence + taille exacte de TOUS les fichiers requis. Retourne
// true seulement si tout est déjà OK localement (= pas de download requis).
async function allPresent(destRoot) {
  let manifest;
  try {
    manifest = await buildFullManifest();
  } catch {
    // Pas d'internet → on ne peut pas vérifier le manifeste MiniLM. On
    // se rabat sur le manifeste statique pour au moins vérifier le LLM.
    manifest = STATIC_MANIFEST;
  }
  for (const it of manifest) {
    const p = path.join(destRoot, it.relPath);
    try {
      const st = await fsp.stat(p);
      if (it.bytes && st.size !== it.bytes) return false;
    } catch { return false; }
  }
  return true;
}

// Télécharge tous les fichiers manquants. `onItem` est appelé fréquemment
// avec un objet de progression — utilisé par le main pour mettre à jour
// la fenêtre d'attente.
async function downloadAll(destRoot, onItem) {
  const items = await buildFullManifest();
  const totalBytes = items.reduce((a, b) => a + (b.bytes || 0), 0);
  let cumulative = 0;

  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    const dest = path.join(destRoot, it.relPath);

    let lastReportedAt = 0;
    await downloadOne(it.url, dest, it.bytes, (received) => {
      const now = Date.now();
      if (now - lastReportedAt > 200) {
        lastReportedAt = now;
        if (onItem) onItem({
          label: it.label,
          itemIndex: i,
          itemCount: items.length,
          itemReceivedBytes: received,
          itemTotalBytes: it.bytes || 0,
          totalReceivedBytes: cumulative + received,
          totalBytes,
        });
      }
    });
    cumulative += it.bytes || 0;
    if (onItem) onItem({
      label: it.label,
      itemIndex: i,
      itemCount: items.length,
      itemReceivedBytes: it.bytes || 0,
      itemTotalBytes: it.bytes || 0,
      totalReceivedBytes: cumulative,
      totalBytes,
    });
  }
}

module.exports = { downloadAll, allPresent, buildFullManifest };
