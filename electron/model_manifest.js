"use strict";

// Modèles téléchargés au premier lancement depuis HuggingFace.
// Tous stockés sous `app.getPath('userData')/assets/` côté utilisateur
// (zone writable, pas besoin d'élévation admin).
//
// Total ~2.3 GB pour la version FR :
//   - Mistral 3B Q4_K_M ........... 2.15 GB
//   - Sherpa Zipformer FR (4 fich) .. 67 MB
//   - WeSpeaker ResNet34 ............ 26 MB
//   - MiniLM all-MiniLM-L6-v2 ....... 80 MB (multi-fichiers, listés via API)
//
// Les URLs HF /resolve/main/ sont stables et n'exigent pas d'auth pour
// les repos publics (cas de tous les modèles ci-dessous).

const hfUrl = (repo, file) =>
  `https://huggingface.co/${repo}/resolve/main/${file}`;
const hfApiTree = (repo) =>
  `https://huggingface.co/api/models/${repo}/tree/main`;

// Manifeste statique : fichiers connus à l'avance (taille fixe vérifiable).
const STATIC_MANIFEST = [
  {
    label: "LLM Mistral 3B Instruct (Q4_K_M)",
    url: hfUrl(
      "bartowski/mistralai_Ministral-3-3B-Instruct-2512-GGUF",
      "mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
    ),
    relPath: "models/mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf",
    bytes: 2146498528,
  },
  {
    label: "ASR Zipformer FR — encoder",
    url: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "encoder.onnx"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/encoder.onnx",
    bytes: 70092599,
  },
  {
    label: "ASR Zipformer FR — decoder",
    url: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "decoder.onnx"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/decoder.onnx",
    bytes: 617488,
  },
  {
    label: "ASR Zipformer FR — joiner",
    url: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "joiner.onnx"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/joiner.onnx",
    bytes: 336817,
  },
  {
    label: "ASR Zipformer FR — tokens",
    url: hfUrl(
      "csukuangfj/sherpa-onnx-streaming-zipformer-fr-kroko-2025-08-06",
      "tokens.txt"
    ),
    relPath: "sherpa-onnx-streaming-zipformer-fr-kroko/tokens.txt",
    bytes: 5415,
  },
  {
    label: "WeSpeaker ResNet34 (embeddings locuteurs)",
    url: hfUrl(
      "Wespeaker/wespeaker-voxceleb-resnet34-LM",
      "voxceleb_resnet34_LM.onnx"
    ),
    relPath: "pretrained_models/resnet34/voxceleb_resnet34_LM.onnx",
    bytes: 26530309,
  },
];

// MiniLM est multi-fichiers. On énumère dynamiquement via l'API HF pour
// éviter de hardcoder une liste qui peut bouger entre versions du modèle.
const MINILM_REPO = "sentence-transformers/all-MiniLM-L6-v2";
const MINILM_REL_DIR = "models_hf/all-MiniLM-L6-v2";

module.exports = {
  STATIC_MANIFEST,
  MINILM_REPO,
  MINILM_REL_DIR,
  hfUrl,
  hfApiTree,
};
