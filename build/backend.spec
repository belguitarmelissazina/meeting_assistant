# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Meeting Assistant backend.

Build (run from the project root with the venv active):
    pyinstaller build/backend.spec --noconfirm --clean

Output: dist/backend/backend.exe (one-folder mode).
"""
from pathlib import Path
import importlib.util

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

PROJECT_ROOT = Path(SPECPATH).parent  # SPECPATH is set by PyInstaller


# ── Heavy ML deps that PyInstaller doesn't pick up correctly on its own.
# `collect_all` returns (datas, binaries, hiddenimports) for a top-level package.
def _collect(pkg: str):
    try:
        if importlib.util.find_spec(pkg) is None:
            return [], [], []
        return collect_all(pkg)
    except Exception:
        return [], [], []


datas, binaries, hiddenimports = [], [], []
for pkg in (
    "sherpa_onnx",
    "sounddevice",
    "pyaudiowpatch",
    "sentence_transformers",
    "wespeakerruntime",
    "imageio_ffmpeg",
    "onnxruntime",
    "scipy",
    "sklearn",
    "transformers",
    "tokenizers",
    "huggingface_hub",
    "docx",  # python-docx
    "silero_vad",  # le sous-package .data (modèle ONNX + jit) doit être collecté
    "msal",            # auth Microsoft Graph (calendrier)
    "msal_extensions",  # cache de jetons chiffré (DPAPI) + portalocker
):
    d, b, h = _collect(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# Uvicorn protocol/lifespan modules are loaded by string at runtime — must be
# explicitly declared as hidden imports or the frozen exe boots and then 500s
# on the first request.
hiddenimports += [
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.wsproto_impl",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.loops.uvloop",
    "uvicorn.logging",
]

# Project source modules invoked via `runpy.run_module` (in run_app.py) are
# discovered statically from this list — runpy lookups don't trigger import
# graph traversal.
hiddenimports += [
    "backend",
    "backend.main",
    "backend.job_logger",
    "backend.resource_monitor",
    "backend.graph_calendar",  # importé paresseusement par les endpoints /api/calendar
    "audio_capture",
    "audio_capture.recorder",
    "audio_capture.live_processor",
    "audio_capture.live_llm",
    "diar_pipeline",
    "diar_pipeline.run",
    "diar_pipeline.audio",
    "diar_pipeline.vad",
    "diar_pipeline.embeddings",
    "diar_pipeline.clustering",
    "diar_pipeline.segments",
    "diar_pipeline.transcription",
    "diar_pipeline.refinement",
    "diar_pipeline.tracking",
    "normalize_transcript",
    "meeting_minutes_pipeline",
]

# Ship the project source + top-level scripts. The bulky model files
# (models/, sherpa-onnx-.../, pretrained_models/, bin/llama/) are NOT bundled
# inside the exe — they ship as electron-builder `extraResources` so the same
# 32 MB exe doesn't need rebuilding when models change.
datas += [
    (str(PROJECT_ROOT / "backend"),                "backend"),
    (str(PROJECT_ROOT / "audio_capture"),          "audio_capture"),
    (str(PROJECT_ROOT / "diar_pipeline"),          "diar_pipeline"),
    (str(PROJECT_ROOT / "normalize_transcript.py"), "."),
    (str(PROJECT_ROOT / "meeting_minutes_pipeline.py"), "."),
]


a = Analysis(
    [str(PROJECT_ROOT / "backend" / "run_app.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "tkinter",
        "notebook",
        "IPython",
        "jupyter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # keep console for log visibility; flip to False for prod
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="backend",
)
