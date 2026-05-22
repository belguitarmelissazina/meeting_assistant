"use strict";

// Downloader des modèles ML, basé sur le module `net` d'ELECTRON (et non
// `https` de Node). Pourquoi : `net` utilise la pile réseau de Chromium, donc
// il honore AUTOMATIQUEMENT :
//   - le proxy système / PAC / WPAD d'entreprise (le gros point bloquant chez
//     les clients type RTE : leur navigateur passe par un proxy, mais Node
//     `https.get` fait du direct → bloqué par le pare-feu → timeout)
//   - l'authentification proxy
//   - l'inspection SSL d'entreprise (certificats injectés dans le store Windows)
//   - le drop automatique de l'en-tête Authorization sur une redirection
//     cross-origin (github.com → objects.githubusercontent.com), comme un
//     navigateur — indispensable pour les assets de repo GitHub privé.
//
// Bref : se comporte exactement comme Edge/Chrome, qui marchent partout en
// entreprise. C'est un surensemble de `https.get` (gère aussi le direct sans
// proxy), donc aucune régression en usage normal.
//
// Fonctionnalités conservées de l'ancienne version :
//   - Reprise via Range (un crash à 1,8 Go sur le LLM ne recommence pas tout)
//   - Vérification taille exacte + retries avec backoff
//   - Source PRIMAIRE GitHub Releases (whitelist entreprise) + FALLBACK
//     HuggingFace si GitHub indisponible.

const fs = require("fs");
const fsp = require("fs/promises");
const path = require("path");
const { net } = require("electron"); // pile réseau Chromium (proxy-aware)
const {
  FULL_MANIFEST,
  GH_OWNER,
  GH_REPO,
  GH_RELEASE_TAG,
} = require("./model_manifest");

const USER_AGENT = "MeetingAssistant/0.1 (electron downloader)";
const IDLE_TIMEOUT_MS = 120_000;
const MAX_RETRIES_PER_FILE = 3;
const RETRY_BACKOFF_MS = 2_000;

// ── Lecture du READ token (repo GitHub privé) ────────────────────────────
// Prod : token gravé dans app-update.yml (electron-builder l'y écrit).
// Dev  : env var GH_READ_TOKEN (sinon GitHub privé → 401 → fallback HF).
let _ghTokenCache = null;
let _ghTokenLoaded = false;

function getGithubReadToken() {
  if (_ghTokenLoaded) return _ghTokenCache;
  _ghTokenLoaded = true;
  const fromEnv = (process.env.GH_READ_TOKEN || "").trim();
  if (fromEnv) {
    _ghTokenCache = fromEnv;
    return _ghTokenCache;
  }
  const resourcesPath = process.resourcesPath;
  if (!resourcesPath) {
    _ghTokenCache = null;
    return null;
  }
  try {
    const yml = fs.readFileSync(path.join(resourcesPath, "app-update.yml"), "utf-8");
    const m = yml.match(/^\s*token\s*:\s*['"]?([A-Za-z0-9_\-.~+/=]+)['"]?\s*$/m);
    _ghTokenCache = m ? m[1].trim() : null;
  } catch {
    _ghTokenCache = null;
  }
  return _ghTokenCache;
}

// ── HTTP helpers (net.request) ───────────────────────────────────────────

function isGithubHost(urlStr) {
  try {
    const h = new URL(urlStr).hostname;
    // github.com ET api.github.com (api.github.com finit par .github.com)
    return h === "github.com" || h.endsWith(".github.com");
  } catch {
    return false;
  }
}

// Résolution des assets de la release GitHub privée. On NE peut PAS
// télécharger via l'URL navigateur (github.com/.../releases/download/...)
// avec un token (404 sur repo privé) — il faut l'URL API de chaque asset.
// On fait UN appel API au premier besoin, puis on cache la map {nom → url API}.
let _ghAssetMap = null;

function ghApiJson(url, token) {
  return new Promise((resolve, reject) => {
    const req = net.request({ method: "GET", url, redirect: "follow" });
    req.setHeader("User-Agent", USER_AGENT);
    req.setHeader("Accept", "application/vnd.github+json");
    req.setHeader("X-GitHub-Api-Version", "2022-11-28");
    if (token) req.setHeader("Authorization", `Bearer ${token}`);
    req.on("response", (response) => {
      if (response.statusCode !== 200) {
        response.on("data", () => {});
        response.on("end", () =>
          reject(new Error(`HTTP ${response.statusCode} sur ${url}`)));
        response.on("error", reject);
        return;
      }
      let body = "";
      response.on("data", (c) => { body += c.toString("utf-8"); });
      response.on("end", () => {
        try { resolve(JSON.parse(body)); }
        catch (e) { reject(e); }
      });
      response.on("error", reject);
    });
    req.on("error", reject);
    req.end();
  });
}

async function resolveGithubAssetMap() {
  if (_ghAssetMap) return _ghAssetMap;
  const token = getGithubReadToken();
  if (!token) {
    // Pas de token (dev sans GH_READ_TOKEN, ou app-update.yml absent) →
    // on ne pourra pas atteindre le repo privé → map vide → fallback HF.
    _ghAssetMap = {};
    return _ghAssetMap;
  }
  const url = `https://api.github.com/repos/${GH_OWNER}/${GH_REPO}/releases/tags/${GH_RELEASE_TAG}`;
  try {
    const release = await ghApiJson(url, token);
    const map = {};
    for (const a of (release.assets || [])) {
      // a.url = URL API de l'asset (api.github.com/.../releases/assets/{id})
      if (a && a.name && a.url) map[a.name] = a.url;
    }
    _ghAssetMap = map;
    console.log(`[downloader] ${Object.keys(map).length} assets GitHub résolus`);
  } catch (e) {
    console.warn(`[downloader] résolution assets GitHub échouée (${e.message}) — fallback HF`);
    _ghAssetMap = {};
  }
  return _ghAssetMap;
}

// Récupère un header de réponse net (les valeurs net sont des tableaux de
// strings ; on prend la 1re occurrence).
function headerValue(headers, name) {
  const v = headers && headers[name.toLowerCase()];
  if (Array.isArray(v)) return v[0];
  return v;
}

// Une tentative de download via net.request. Reprend depuis le byte courant
// du fichier sur disque (Range). redirect:"follow" → Chromium suit les
// redirections ET drop l'Authorization sur cross-origin (auth GitHub→S3 OK).
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
    const safeReject = (err) => { if (!settled) { settled = true; reject(err); } };
    const safeResolve = () => { if (!settled) { settled = true; resolve(); } };

    const request = net.request({ method: "GET", url, redirect: "follow" });
    request.setHeader("User-Agent", USER_AGENT);
    if (startByte > 0) request.setHeader("Range", `bytes=${startByte}-`);
    // Auth GitHub privé : Bearer token + Accept octet-stream (sinon GitHub
    // renvoie le JSON de métadonnées au lieu du binaire). Chromium dropera
    // l'Authorization sur la redirection vers objects.githubusercontent.com.
    if (isGithubHost(url)) {
      const token = getGithubReadToken();
      if (token) {
        request.setHeader("Authorization", `Bearer ${token}`);
        request.setHeader("Accept", "application/octet-stream");
      }
    }

    let idleTimer = null;
    const armIdle = () => {
      if (idleTimer) clearTimeout(idleTimer);
      idleTimer = setTimeout(() => {
        try { request.abort(); } catch { /* déjà fini */ }
        safeReject(new Error(`Pas de données depuis ${IDLE_TIMEOUT_MS / 1000}s sur ${url}`));
      }, IDLE_TIMEOUT_MS);
    };
    const clearIdle = () => { if (idleTimer) { clearTimeout(idleTimer); idleTimer = null; } };

    request.on("response", (response) => {
      const status = response.statusCode;
      if (status !== 200 && status !== 206) {
        // Draine le corps puis rejette.
        response.on("data", () => {});
        response.on("end", () => {});
        clearIdle();
        return safeReject(new Error(`HTTP ${status} pour ${url}`));
      }
      // Si on a demandé un Range mais le serveur renvoie 200 (ignore Range),
      // on repart de zéro → réécrit tout le fichier.
      if (startByte > 0 && status === 200) startByte = 0;

      const clen = parseInt(headerValue(response.headers, "content-length") || "0", 10);
      const total = expectedBytes || (clen + startByte);
      let received = startByte;

      const out = fs.createWriteStream(destPath, { flags: startByte > 0 ? "a" : "w" });
      out.on("error", (err) => { clearIdle(); safeReject(err); });

      armIdle();
      response.on("data", (chunk) => {
        received += chunk.length;
        armIdle();
        // Backpressure : si le buffer disque est plein, on met la réponse
        // en pause jusqu'au drain (évite de tout charger en RAM sur le LLM
        // de 2 Go).
        const ok = out.write(chunk);
        if (!ok) {
          response.pause();
          out.once("drain", () => response.resume());
        }
        if (onProgress) onProgress(received, total);
      });
      response.on("end", () => {
        out.end(() => { clearIdle(); safeResolve(); });
      });
      response.on("error", (err) => { clearIdle(); out.destroy(); safeReject(err); });
    });
    request.on("error", (err) => { clearIdle(); safeReject(err); });
    request.on("abort", () => { clearIdle(); safeReject(new Error(`Requête annulée : ${url}`)); });

    armIdle();
    request.end();
  });
}

// Télécharge un fichier avec retries + reprise.
async function downloadOne(url, destPath, expectedBytes, onProgress) {
  await fsp.mkdir(path.dirname(destPath), { recursive: true });
  // Nettoyage initial : déjà complet → skip ; corrompu (trop gros) → reset.
  try {
    const stat = await fsp.stat(destPath);
    if (expectedBytes && stat.size === expectedBytes) {
      if (onProgress) onProgress(stat.size, expectedBytes);
      return;
    }
    if (expectedBytes && stat.size > expectedBytes) {
      await fsp.unlink(destPath);
    }
  } catch { /* absent, OK */ }

  let attempt = 0;
  let lastErr = null;
  while (attempt < MAX_RETRIES_PER_FILE) {
    attempt++;
    try {
      await downloadOneAttempt(url, destPath, expectedBytes, onProgress);
      return;
    } catch (err) {
      lastErr = err;
      console.warn(`[downloader] tentative ${attempt}/${MAX_RETRIES_PER_FILE} échouée pour ${url}: ${err.message}`);
      if (attempt < MAX_RETRIES_PER_FILE) {
        await new Promise((r) => setTimeout(r, RETRY_BACKOFF_MS * attempt));
      }
    }
  }
  throw new Error(`Échec après ${MAX_RETRIES_PER_FILE} tentatives : ${lastErr && lastErr.message}`);
}

// PRIMAIRE GitHub (via URL API d'asset, repo privé) → FALLBACK HuggingFace.
// `onSource(src)` est appelé avec "github" ou "huggingface" dès qu'on sait
// quelle source on utilise (pour l'afficher dans la fenêtre de progression
// — utile pour vérifier en entreprise que GitHub passe bien et qu'on ne
// retombe pas silencieusement sur HF).
async function downloadWithFallback(item, destPath, onProgress, onSource) {
  const fallback = item.urlFallback;
  if (item.ghAsset) {
    try {
      const map = await resolveGithubAssetMap();
      const apiUrl = map[item.ghAsset];
      if (apiUrl) {
        if (onSource) onSource("github");
        await downloadOne(apiUrl, destPath, item.bytes, onProgress);
        return;
      }
      console.warn(`[downloader] asset GitHub "${item.ghAsset}" absent de la release — fallback HF`);
    } catch (err) {
      if (!fallback) throw err;
      console.warn(
        `[downloader] GitHub échoué pour "${item.label}" (${err.message}). ` +
        `Bascule sur le fallback HuggingFace.`
      );
    }
    try { await fsp.unlink(destPath); } catch { /* ignore */ }
  }
  if (!fallback) throw new Error(`Aucune URL disponible pour "${item.label}"`);
  if (onSource) onSource("huggingface");
  await downloadOne(fallback, destPath, item.bytes, onProgress);
}

// Vérifie présence + taille exacte de TOUS les fichiers.
async function allPresent(destRoot) {
  for (const it of FULL_MANIFEST) {
    const p = path.join(destRoot, it.relPath);
    try {
      const st = await fsp.stat(p);
      if (it.bytes && st.size !== it.bytes) return false;
    } catch { return false; }
  }
  return true;
}

// Télécharge tous les fichiers manquants avec progression.
async function downloadAll(destRoot, onItem) {
  const items = FULL_MANIFEST;
  const totalBytes = items.reduce((a, b) => a + (b.bytes || 0), 0);
  let cumulative = 0;

  for (let i = 0; i < items.length; i++) {
    const it = items[i];
    const dest = path.join(destRoot, it.relPath);

    let lastReportedAt = 0;
    let currentSource = "résolution…";
    await downloadWithFallback(
      it,
      dest,
      (received) => {
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
            source: currentSource,
          });
        }
      },
      (src) => { currentSource = src; },
    );
    cumulative += it.bytes || 0;
    if (onItem) onItem({
      label: it.label,
      itemIndex: i,
      itemCount: items.length,
      itemReceivedBytes: it.bytes || 0,
      itemTotalBytes: it.bytes || 0,
      totalReceivedBytes: cumulative,
      totalBytes,
      source: currentSource,
    });
  }
}

module.exports = {
  downloadAll,
  allPresent,
  FULL_MANIFEST,
  // exportés pour le test unitaire (test_downloader.js)
  downloadWithFallback,
  downloadOne,
};
