"use strict";

// Modèles téléchargés au premier lancement.
// Tous stockés sous `app.getPath('userData')/assets/` côté utilisateur
// (zone writable, pas besoin d'élévation admin).
//
// Total ~2.3 GB pour la version FR.
//
// SOURCE PRIMAIRE : GitHub Releases (repo PUBLIC `meeting-assistant-models`)
// → URLs whitelist par défaut dans 99 % des SI entreprise (devs en ont
//   besoin partout). Évite le filtrage des plateformes IA (huggingface.co
//   est souvent bloqué chez les grands comptes type RTE, EDF, BNP, etc.).
//
// SOURCE DE REPLI : HuggingFace
// → utilisée automatiquement si GitHub renvoie une erreur (404, 5xx,
//   timeout). Défense en profondeur : si on supprime accidentellement
//   un asset GitHub ou si GitHub est en panne, l'app continue de
//   fonctionner pour les nouveaux installs.
//
// AVANTAGE : aucune dépendance à l'API HF (qui peut changer, rate-limiter
// ou être bloquée à la couche DPI même quand huggingface.co est accessible
// en HTTPS classique). Manifeste 100 % statique, pas d'appel /api/models.

// ── GitHub Releases (source primaire) ────────────────────────────────────
// Repo PRIVÉ — le même que celui des installeurs de l'app. Pourquoi :
// (1) on évite de redistribuer publiquement des modèles tiers (les licences
// HF ne couvrent pas forcément la rediffusion en miroir public) ;
// (2) on réutilise le READ token déjà embarqué dans l'app via app-update.yml ;
// (3) pas de nouveau repo à gérer.
//
// IMPORTANT — repo PRIVÉ : l'URL navigateur
//   github.com/OWNER/REPO/releases/download/TAG/FILE
// NE marche PAS avec un token Bearer (elle exige un cookie de session web) →
// renvoie 404. Pour un repo privé il faut passer par l'API REST :
//   1. GET api.github.com/repos/OWNER/REPO/releases/tags/TAG  (liste assets)
//   2. pour chaque asset → son `url` API (api.github.com/.../assets/{id})
//   3. GET cette url avec `Accept: application/octet-stream` + Bearer token
//      → 302 vers une URL S3 signée → binaire.
// C'est downloader.js qui fait cette résolution (resolveGithubAssetMap).
// Le manifest ne stocke donc QUE le NOM de l'asset (`ghAsset`), pas l'URL.
const GH_OWNER = "belguitarmelissazina";
const GH_REPO = "meeting-assistant-releases";
const GH_RELEASE_TAG = "assets-v1";

// ── HuggingFace (fallback) ───────────────────────────────────────────────
const hfUrl = (repo, file) =>
  `https://huggingface.co/${repo}/resolve/main/${file}`;
// Conservé en export pour rétro-compat éventuelle (plus utilisé en interne :
// MiniLM est maintenant listé statiquement, plus d'appel API).
const hfApiTree = (repo) =>
  `https://huggingface.co/api/models/${repo}/tree/main`;

// Chaque entrée a :
//   - ghAsset    : NOM de l'asset sur la release GitHub (résolu en URL API
//                  au runtime par downloader.js — repo privé oblige)
//   - urlFallback: URL directe HuggingFace (repos publics, pas d'auth)
//   - bytes      : taille exacte attendue (vérif intégrité + reprise partielle)
const STATIC_MANIFEST = [
  {
    label: "LLM Mistral 3B Instruct (Q4_K_M)",
    ghAsset: "mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
    urlFallback: hfUrl(
      "bartowski/mistralai_Ministral-3-3B-Instruct-2512-GGUF",
      "mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
    ),
    relPath: "models/mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
    bytes: 2146498528,
  },
  {
    label: "ASR Zipformer FR — encoder",
    ghAsset: "sherpa-encoder.onnx",
    urlFallback: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "encoder.onnx"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/encoder.onnx",
    bytes: 70092599,
  },
  {
    label: "ASR Zipformer FR — decoder",
    ghAsset: "sherpa-decoder.onnx",
    urlFallback: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "decoder.onnx"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/decoder.onnx",
    bytes: 617488,
  },
  {
    label: "ASR Zipformer FR — joiner",
    ghAsset: "sherpa-joiner.onnx",
    urlFallback: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "joiner.onnx"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/joiner.onnx",
    bytes: 336817,
  },
  {
    label: "ASR Zipformer FR — tokens",
    ghAsset: "sherpa-tokens.txt",
    urlFallback: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "tokens.txt"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/tokens.txt",
    bytes: 5415,
  },
  {
    label: "WeSpeaker ResNet34 (embeddings locuteurs)",
    ghAsset: "voxceleb_resnet34_LM.onnx",
    urlFallback: hfUrl(
      "Wespeaker/wespeaker-voxceleb-resnet34-LM",
      "voxceleb_resnet34_LM.onnx"
    ),
    relPath: "pretrained_models/resnet34/voxceleb_resnet34_LM.onnx",
    bytes: 26530309,
  },
];

// MiniLM (sentence-transformers/all-MiniLM-L6-v2) : 10 fichiers nécessaires
// pour l'init de SentenceTransformer en inférence Python. Liste statique
// (avant on l'énumérait via l'API HF, ce qui ajoutait une dépendance réseau
// inutile et un appel souvent bloqué par les firewalls qui filtrent /api/).
const MINILM_REPO = "sentence-transformers/all-MiniLM-L6-v2";
const MINILM_REL_DIR = "models_hf/all-MiniLM-L6-v2";

// Préfixe `minilm-` pour le nom d'asset GitHub (évite la collision avec
// d'autres fichiers du même nom — config.json existe dans plein de modèles).
// Le `/` du sous-chemin devient `_` car les noms d'assets GitHub ne peuvent
// pas contenir de slash.
const ghMinilmAsset = (subpath) => `minilm-${subpath.replace(/\//g, "_")}`;

const MINILM_FILES = [
  { subpath: "config.json", bytes: 612 },
  { subpath: "config_sentence_transformers.json", bytes: 116 },
  { subpath: "modules.json", bytes: 349 },
  { subpath: "sentence_bert_config.json", bytes: 53 },
  { subpath: "special_tokens_map.json", bytes: 112 },
  { subpath: "tokenizer.json", bytes: 466247 },
  { subpath: "tokenizer_config.json", bytes: 350 },
  { subpath: "vocab.txt", bytes: 231508 },
  { subpath: "model.safetensors", bytes: 90868376 },
  { subpath: "1_Pooling/config.json", bytes: 190 },
].map((f) => ({
  label: `MiniLM — ${f.subpath}`,
  ghAsset: ghMinilmAsset(f.subpath),
  urlFallback: hfUrl(MINILM_REPO, f.subpath),
  relPath: `${MINILM_REL_DIR}/${f.subpath}`,
  bytes: f.bytes,
}));

// Manifeste complet = STATIC_MANIFEST + MINILM_FILES, tout statique, prêt
// pour vérification de présence ou téléchargement.
const FULL_MANIFEST = [...STATIC_MANIFEST, ...MINILM_FILES];

module.exports = {
  STATIC_MANIFEST,
  MINILM_FILES,
  FULL_MANIFEST,
  MINILM_REPO,
  MINILM_REL_DIR,
  hfUrl,
  hfApiTree,
  GH_OWNER,
  GH_REPO,
  GH_RELEASE_TAG,
};
