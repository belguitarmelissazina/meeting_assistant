# Building the Meeting Assistant desktop installer

This document describes how to package the project as a Windows Electron
desktop app (NSIS installer).

## Architecture (recap)

```
Meeting Assistant Setup.exe  (NSIS, ~3 GB)
└── Installed app folder
    ├── Meeting Assistant.exe                  (Electron shell)
    └── resources/
        ├── app.asar                           (main.js, preload.js)
        ├── backend/backend.exe + DLLs         (PyInstaller --onedir)
        ├── webapp-out/                        (Next.js static export)
        └── assets/
            ├── models/                        (Mistral GGUF, ~2 GB)
            ├── sherpa-onnx-streaming-zipformer-fr-kroko/
            ├── pretrained_models/
            ├── bin/llama/                     (llama-server.exe + ggml DLLs)
            └── hf_cache/                      (sentence-transformers cache)
```

Runtime: Electron spawns `backend.exe server` on launch, polls
`http://127.0.0.1:8000/api/health`, then opens a `BrowserWindow` loading
`webapp-out/index.html`.

## One-time prerequisites

- Windows 10/11, x64
- Python 3.10+ with the project venv already set up at `meeting_assistant/`
  (or wherever you keep it). Activate it before running PyInstaller.
- Node.js 20+ and npm
- The full project assets present locally:
  - `models/mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf`
  - `sherpa-onnx-streaming-zipformer-fr-kroko/`
  - `pretrained_models/resnet34/voxceleb_resnet34_LM.onnx`
  - `bin/llama/llama-server.exe` (+ all `ggml-*.dll`)

## Build steps

All commands assume the project root is the current directory.

### 1. Install build-time Python dependencies

```bash
# Activate your venv first
pip install -r requirements-build.txt
```

### 2. Pre-warm the HuggingFace cache (once, or whenever HF model changes)

```bash
python scripts/prepare_assets.py
```

This writes `~80 MB` to `assets/hf_cache/` (sentence-transformers
`all-MiniLM-L6-v2`). Without this step the packaged app will fail offline
with a HuggingFace download error the first time it builds a meeting
report.

### 3. Build the Python backend with PyInstaller

```bash
pyinstaller build/backend.spec --noconfirm --clean
```

Output: `dist/backend/backend.exe` (one-folder, ~500 MB including
sherpa-onnx, sentence-transformers, scipy, etc.).

Smoke-test it before going further:

```bash
# Set the env vars Electron would normally set
export MODELS_DIR=$(pwd)/models
export SHERPA_DIR=$(pwd)/sherpa-onnx-streaming-zipformer-fr-kroko
export PRETRAINED_DIR=$(pwd)/pretrained_models
export LLAMA_BIN_DIR=$(pwd)/bin/llama
export HF_HOME=$(pwd)/assets/hf_cache

dist/backend/backend.exe server
# In another shell:
curl http://127.0.0.1:8000/api/health   # → {"ok": true, ...}
```

### 4. Build the Next.js frontend (static export)

```bash
cd webapp
npm install        # first time only
npm run build      # produces webapp/out/
cd ..
```

The export is fully static — there is no `next start` server in production.
All fetches go to `window.electronAPI.backendUrl` (set by `electron/preload.js`).

### 5. Install Electron + electron-builder

```bash
cd electron
npm install        # first time only
```

### 6. Produce the installer

```bash
cd electron
npm run dist
```

Or, to do everything in one shot from a clean state:

```bash
cd electron
npm run release   # = build:assets + build:python + build:webapp + dist
```

Output: `release/Meeting Assistant-Setup-0.1.0.exe` (~2.5–2.9 GB, mostly
the Mistral GGUF).

## Development workflow (no installer)

You don't need to rebuild the installer to iterate. Two options:

```bash
# Option A — Electron loads the static export from disk
cd webapp && npm run build && cd ..
cd electron && npm run dev

# Option B — Electron loads `next dev` for hot reload
cd webapp && npm run dev    # in one shell
cd electron && npm run dev:hot   # in another
```

In both cases Electron spawns the backend via `python -m backend.run_app
server` (your venv must be on PATH or `PYTHON_BIN` env var set).

## Troubleshooting

### Backend exits immediately after launch

Run `dist/backend/backend.exe server` directly in a console — PyInstaller
hidden-import failures show up as `ModuleNotFoundError`. Add the missing
module to `hiddenimports` in `build/backend.spec` and rebuild.

### Recording fails with `pyaudiowpatch` not found

`pyaudiowpatch` ships a native DLL that PyInstaller sometimes misses.
Force-collect it: it is already in `hiddenimports`, so check that the venv
has `pyaudiowpatch` installed (`pip show pyaudiowpatch`).

### Installer SmartScreen warning ("Unknown publisher")

Expected until you sign the installer with an Authenticode certificate.
Set `CSC_LINK` and `CSC_KEY_PASSWORD` env vars before `npm run dist` and
electron-builder will sign both `Meeting Assistant.exe` and the installer.

### "Modèle introuvable: ..." at runtime

The packaged app couldn't find `mistralai_Ministral-...gguf`. Check that
the file exists under
`<install dir>/resources/assets/models/`. If not, the
`extraResources` glob in `electron/package.json` didn't match — likely
because you ran `npm run dist` before the model was in place.
