"use strict";

// Test harness pour downloader.js (net.request proxy-aware).
// Lance une mini-app Electron, attend app.ready, puis télécharge quelques
// petits fichiers RÉELS (les plus légers du manifest) pour valider :
//   1. Le download GitHub privé fonctionne (auth Bearer + redirect S3)
//   2. La vérification de taille exacte passe
//   3. Le fallback HuggingFace marche si on force une URL GitHub bidon
//
// Usage :
//   cd electron
//   node load-env-and-test.js   (wrapper qui charge .env puis lance ceci)
//   OU : $env:GH_READ_TOKEN="..." ; npx electron test_downloader.js
//
// On NE télécharge PAS le Ministral 2 Go — juste les petits fichiers
// (sherpa-tokens 5 Ko, minilm-config 600 o, etc.) pour valider la
// mécanique réseau sans saturer.

const { app } = require("electron");
const path = require("path");
const os = require("os");
const fs = require("fs");

// Charge electron/.env pour récupérer GH_READ_TOKEN (le token READ embarqué).
function loadEnv() {
  const envPath = path.join(__dirname, ".env");
  if (!fs.existsSync(envPath)) {
    console.log("[test] pas de .env trouvé — le download GitHub privé échouera (401) et testera le fallback HF.");
    return;
  }
  for (const line of fs.readFileSync(envPath, "utf-8").split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith("#") || !t.includes("=")) continue;
    const i = t.indexOf("=");
    const k = t.slice(0, i).trim();
    const v = t.slice(i + 1).trim().replace(/^['"]|['"]$/g, "");
    if (k && !(k in process.env)) process.env[k] = v;
  }
}

app.whenReady().then(async () => {
  loadEnv();
  const { downloadWithFallback, FULL_MANIFEST } = require("./downloader");
  const tmpRoot = path.join(os.tmpdir(), "ma-dl-test-" + Date.now());
  fs.mkdirSync(tmpRoot, { recursive: true });
  console.log("[test] dossier temp :", tmpRoot);
  console.log("[test] GH_READ_TOKEN présent :", !!(process.env.GH_READ_TOKEN || "").trim());

  // On prend les 5 plus PETITS fichiers du manifest (pour aller vite).
  const smallest = [...FULL_MANIFEST]
    .sort((a, b) => (a.bytes || 0) - (b.bytes || 0))
    .slice(0, 5);

  let okCount = 0;
  let failCount = 0;

  for (const item of smallest) {
    const dest = path.join(tmpRoot, item.relPath);
    process.stdout.write(`[test] ↓ ${item.label} (${item.bytes} o)… `);
    try {
      await downloadWithFallback(item, dest, () => {});
      const size = fs.statSync(dest).size;
      if (item.bytes && size !== item.bytes) {
        console.log(`❌ TAILLE INCORRECTE : ${size} ≠ ${item.bytes}`);
        failCount++;
      } else {
        console.log(`✓ OK (${size} o)`);
        okCount++;
      }
    } catch (e) {
      console.log(`❌ ÉCHEC : ${e.message}`);
      failCount++;
    }
  }

  // Test du FALLBACK : asset GitHub volontairement inexistant → doit
  // basculer sur HF.
  console.log("\n[test] --- Test du fallback HuggingFace (asset GitHub bidon) ---");
  const fbItem = {
    ...smallest[0],
    label: smallest[0].label + " (fallback test)",
    ghAsset: "CE_FICHIER_NEXISTE_PAS.bin",
    // urlFallback reste le vrai HF
  };
  const fbDest = path.join(tmpRoot, "fallback-test.bin");
  try {
    await downloadWithFallback(fbItem, fbDest, () => {});
    const size = fs.statSync(fbDest).size;
    console.log(`[test] ✓ Fallback HF OK (${size} o récupérés malgré l'URL GitHub cassée)`);
    okCount++;
  } catch (e) {
    console.log(`[test] ❌ Fallback HF a échoué : ${e.message}`);
    failCount++;
  }

  console.log(`\n[test] ===== RÉSULTAT : ${okCount} OK, ${failCount} échec(s) =====`);

  // Cleanup
  try { fs.rmSync(tmpRoot, { recursive: true, force: true }); } catch { /* ignore */ }

  app.exit(failCount === 0 ? 0 : 1);
});
