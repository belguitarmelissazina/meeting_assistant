# Bench complet llama-server : 4 phases, du plus rentable au plus niche.
# Chaque phase log dans un fichier separe. Tu peux interrompre a tout moment
# avec Ctrl+C - les phases precedentes restent valables.
#
# Usage : .\run_bench.ps1
#
# Duree estimee : 45-60 min total.

$ErrorActionPreference = "Continue"
$ROOT = Split-Path -Parent $PSCommandPath
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$LOG_DIR = Join-Path $env:TEMP "bench_llamaserver_$STAMP"
New-Item -ItemType Directory -Path $LOG_DIR -Force | Out-Null

# Force Python stdout en UTF-8 pour eviter les UnicodeEncodeError quand
# le shell parent tourne en cp1252.
$env:PYTHONIOENCODING = "utf-8"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Bench llama-server - logs dans $LOG_DIR" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Etape 0 : pre-flight
Write-Host ""
Write-Host "[0/5] Pre-flight check..." -ForegroundColor Yellow
$exe = Join-Path $ROOT "bin\llama\llama-server.exe"
$model = Join-Path $ROOT "models\mistralai_Ministral-3-3B-Instruct-2512-Q4_K_M.gguf"
if (-not (Test-Path $exe)) {
    Write-Host "  [X] llama-server.exe introuvable : $exe" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $model)) {
    Write-Host "  [X] Modele introuvable : $model" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] binaires presents" -ForegroundColor Green

# Activer le venv si pas deja actif
if (-not $env:VIRTUAL_ENV) {
    $venvActivate = Join-Path $ROOT "meeting_assistant\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) {
        Write-Host "  [..] activation venv meeting_assistant"
        & $venvActivate
    }
}

# Etape 1 : smoke test (~2 min)
Write-Host ""
Write-Host "[1/5] Smoke test (1 config x 1 measure) - valide que tout part" -ForegroundColor Yellow
$smokeLog = Join-Path $LOG_DIR "01_smoke.log"
python _bench_llamaserver.py --only v0_baseline --measure 1 2>&1 | Tee-Object -FilePath $smokeLog
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "  [X] smoke test a echoue. Voir $smokeLog" -ForegroundColor Red
    Write-Host "  Stderr de llama-server :" -ForegroundColor Red
    $stderrFile = Join-Path $ROOT "_llama_bench_stderr.log"
    if (Test-Path $stderrFile) { Get-Content $stderrFile -Tail 30 }
    exit 1
}
Write-Host "  [OK] smoke test passe" -ForegroundColor Green

# Etape 2 : Tier 1 - leviers principaux (~15 min)
Write-Host ""
Write-Host "[2/5] Tier 1 : leviers principaux (cram, pin, batch, PLD)" -ForegroundColor Yellow
$tier1Log = Join-Path $LOG_DIR "02_tier1_leviers.log"
python _bench_llamaserver.py --only v0_baseline,v1_cram_only,v2_pin_only,v3_cram_pin,v4_cram_pin_batch,v5_cram_pin_batch_pld --warm 1 --measure 2 2>&1 | Tee-Object -FilePath $tier1Log
Write-Host "  [OK] Tier 1 termine - $tier1Log" -ForegroundColor Green

# Etape 3 : Tier 2-3 - Flash Attention + KV cache types (~10 min)
Write-Host ""
Write-Host "[3/5] Tier 2-3 : Flash Attention on/off + KV cache types" -ForegroundColor Yellow
$tier2Log = Join-Path $LOG_DIR "03_tier23_fa_kv.log"
python _bench_llamaserver.py --only v3_cram_pin,v6_no_flash_attn,v7_kv_f16,v8_kv_q4_0 --warm 1 --measure 2 2>&1 | Tee-Object -FilePath $tier2Log
Write-Host "  [OK] Tier 2-3 termine - $tier2Log" -ForegroundColor Green

# Etape 4 : Tier 4-5 - Memory residency + ctx size (~10 min)
Write-Host ""
Write-Host "[4/5] Tier 4-5 : memory (mlock, no-mmap) + ctx size" -ForegroundColor Yellow
$tier3Log = Join-Path $LOG_DIR "04_tier45_mem_ctx.log"
python _bench_llamaserver.py --only v3_cram_pin,v9_mlock,v10_no_mmap,v11_ctx_4096,v12_ctx_16384 --warm 1 --measure 2 2>&1 | Tee-Object -FilePath $tier3Log
Write-Host "  [OK] Tier 4-5 termine - $tier3Log" -ForegroundColor Green

# Etape 5 : Tier 6-8 - GBNF + ubatch + PLD sweeps (~15 min)
Write-Host ""
Write-Host "[5/5] Tier 6-8 : GBNF + ubatch sweep + PLD tuning" -ForegroundColor Yellow
$tier4Log = Join-Path $LOG_DIR "05_tier678_gbnf_ubatch_pld.log"
python _bench_llamaserver.py --only v4_cram_pin_batch,v13_gbnf_json,v14_ubatch_512,v15_ubatch_2048,v16_pld_dmax4,v17_pld_dmax16 --warm 1 --measure 2 2>&1 | Tee-Object -FilePath $tier4Log
Write-Host "  [OK] Tier 6-8 termine - $tier4Log" -ForegroundColor Green

# Consolidation
$finalLog = Join-Path $LOG_DIR "00_FINAL.log"
$header = "=== BENCH RECAP - " + (Get-Date) + " ==="
$header | Out-File -FilePath $finalLog -Encoding utf8
"" | Out-File -FilePath $finalLog -Append -Encoding utf8
$pattern = "config|baseline|cram|pin|batch|pld|Gagnant|FAILED|kv_|mlock|no_mmap|ctx_|gbnf|ubatch|====|----"
Get-Content $tier1Log, $tier2Log, $tier3Log, $tier4Log | Select-String -Pattern $pattern | Out-File -FilePath $finalLog -Append -Encoding utf8

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " BENCH TERMINE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Logs detailles : $LOG_DIR"
Write-Host " Recap final    : $finalLog"
Write-Host ""
Write-Host " Le tableau final de chaque phase est dans les logs 02-05." -ForegroundColor Green
Write-Host " Cherche 'Gagnant :' a la fin de chacun." -ForegroundColor Green
