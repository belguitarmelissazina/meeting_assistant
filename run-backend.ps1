$root = "$env:LOCALAPPDATA\Programs\Meeting Assistant\resources"
$userAssets = "$env:APPDATA\Meeting Assistant\assets"
$log = "$env:TEMP\backend.log"

$env:BACKEND_PORT = "8000"
$env:BACKEND_HOST = "127.0.0.1"
$env:MODELS_DIR = "$userAssets\models"
$env:SHERPA_DIR = "$userAssets\sherpa-onnx-streaming-zipformer-fr-kroko"
$env:PRETRAINED_DIR = "$userAssets\pretrained_models"
$env:LLAMA_BIN_DIR = "$root\assets\bin\llama"
$env:MINILM_DIR = "$userAssets\models_hf\all-MiniLM-L6-v2"
$env:HF_HUB_OFFLINE = "1"
$env:TRANSFORMERS_OFFLINE = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "Backend log : $log" -ForegroundColor Cyan
Write-Host "Lance le backend... (Ctrl+C pour arrêter)`n" -ForegroundColor Cyan

& "$root\backend\backend.exe" server 2>&1 | Tee-Object -FilePath $log
