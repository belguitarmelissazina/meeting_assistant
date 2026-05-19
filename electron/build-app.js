"use strict";
/**
 * Build / publication de l'app.
 *
 * Séparation stricte des 2 jetons (tous les deux dans electron/.env, GITIGNORÉ) :
 *  - GH_READ_TOKEN (Contents read-only)  → injecté dans config.publish.token
 *    → gravé dans app-update.yml → l'app l'utilise pour TÉLÉCHARGER les MAJ
 *    du repo privé. electron-builder ne fait AUCUN appel API ici (publish:
 *    "never"), donc ce jeton read-only ne sert jamais à publier.
 *  - GH_TOKEN (Contents read+write)      → utilisé UNIQUEMENT ici, côté build,
 *    pour créer la release GitHub + uploader les fichiers via l'API REST.
 *    JAMAIS embarqué dans l'app.
 *
 * Usage (via npm) :
 *   node build-app.js            → installeur local (pas de publication)
 *   node build-app.js --publish  → build + crée la release GitHub + upload
 */
require("dotenv").config(); // charge electron/.env

const fs = require("fs");
const path = require("path");
const { build, Platform } = require("electron-builder");

const OWNER = "belguitarmelissazina";
const REPO = "meeting-assistant-releases";

const doPublish = process.argv.includes("--publish");
const readToken = (process.env.GH_READ_TOKEN || "").trim();
const writeToken = (process.env.GH_TOKEN || "").trim();

if (!readToken) {
  console.error("[build] GH_READ_TOKEN manquant dans electron/.env (jeton READ-only).");
  process.exit(1);
}
if (doPublish && !writeToken) {
  console.error("[build] GH_TOKEN manquant dans electron/.env (jeton WRITE, requis pour --publish).");
  process.exit(1);
}

const version = require("./package.json").version;
const tag = `v${version}`;
const releaseDir = path.resolve(process.cwd(), "..", "release");

const GH_HEADERS = {
  Authorization: `Bearer ${writeToken}`,
  Accept: "application/vnd.github+json",
  "X-GitHub-Api-Version": "2022-11-28",
  "User-Agent": "meeting-assistant-build",
};

async function ghJson(url, init) {
  const r = await fetch(url, init);
  const text = await r.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    /* réponse non-JSON */
  }
  return { ok: r.ok, status: r.status, data, text };
}

async function getOrCreateRelease() {
  // Existe déjà ? (re-publication de la même version)
  let res = await ghJson(
    `https://api.github.com/repos/${OWNER}/${REPO}/releases/tags/${tag}`,
    { headers: GH_HEADERS }
  );
  if (res.ok && res.data) return res.data;

  // Création
  res = await ghJson(
    `https://api.github.com/repos/${OWNER}/${REPO}/releases`,
    {
      method: "POST",
      headers: { ...GH_HEADERS, "Content-Type": "application/json" },
      body: JSON.stringify({
        tag_name: tag,
        name: tag,
        draft: false,
        prerelease: false,
      }),
    }
  );
  if (!res.ok) {
    throw new Error(
      `Création release échouée (HTTP ${res.status}). ` +
        `Vérifie que le jeton WRITE (GH_TOKEN) a bien Contents: Read and write ` +
        `sur ${OWNER}/${REPO}. Réponse: ${res.text}`
    );
  }
  return res.data;
}

async function uploadAsset(release, filePath) {
  const name = path.basename(filePath);

  // Supprime un asset homonyme existant (re-publication idempotente).
  const existing = (release.assets || []).find((a) => a.name === name);
  if (existing) {
    await fetch(
      `https://api.github.com/repos/${OWNER}/${REPO}/releases/assets/${existing.id}`,
      { method: "DELETE", headers: GH_HEADERS }
    );
  }

  const body = fs.readFileSync(filePath);
  const r = await fetch(
    `https://uploads.github.com/repos/${OWNER}/${REPO}/releases/${release.id}/assets?name=${encodeURIComponent(name)}`,
    {
      method: "POST",
      headers: { ...GH_HEADERS, "Content-Type": "application/octet-stream" },
      body,
    }
  );
  if (!r.ok) {
    throw new Error(`Upload de ${name} échoué (HTTP ${r.status}): ${await r.text()}`);
  }
  console.log(`[publish] uploadé: ${name}`);
}

async function publishToGitHub() {
  const wanted = fs
    .readdirSync(releaseDir)
    .filter(
      (f) =>
        f === "latest.yml" ||
        f.endsWith(".exe") ||
        f.endsWith(".exe.blockmap")
    );
  if (wanted.length === 0) {
    throw new Error(`Aucun artefact trouvé dans ${releaseDir}`);
  }
  console.log(`[publish] release ${tag} sur ${OWNER}/${REPO} …`);
  const release = await getOrCreateRelease();
  for (const f of wanted) {
    await uploadAsset(release, path.join(releaseDir, f));
  }
  console.log(`[publish] OK — release ${tag} publiée.`);
}

// 1) Build local : electron-builder ne contacte JAMAIS GitHub (publish:never).
//    config.publish.token = jeton READ → gravé dans app-update.yml.
build({
  targets: Platform.WINDOWS.createTarget("nsis"),
  publish: "never",
  config: {
    publish: {
      provider: "github",
      owner: OWNER,
      repo: REPO,
      private: true,
      releaseType: "release",
      token: readToken,
    },
  },
})
  .then(async () => {
    console.log("[build] OK");
    if (doPublish) {
      // 2) Publication via API GitHub avec le jeton WRITE (jamais embarqué).
      await publishToGitHub();
    }
  })
  .catch((e) => {
    console.error("[build] échec:", e && (e.stack || e.message || e));
    process.exit(1);
  });
