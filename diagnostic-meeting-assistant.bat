@echo off
chcp 65001 >nul
title Diagnostic Meeting Assistant

set "ROOT=%LOCALAPPDATA%\Programs\Meeting Assistant\resources"
set "USERASSETS=%APPDATA%\Meeting Assistant\assets"
set "LOG=%USERPROFILE%\Desktop\meeting-assistant-diagnostic.log"
if not exist "%USERPROFILE%\Desktop" set "LOG=%TEMP%\meeting-assistant-diagnostic.log"

echo ============================================================ > "%LOG%"
echo Diagnostic Meeting Assistant - %DATE% %TIME% >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo. >> "%LOG%"

echo [1/4] Verification fichiers installes... >> "%LOG%"
if exist "%ROOT%\backend\backend.exe" (echo   OK : backend.exe trouve >> "%LOG%") else (echo   MANQUANT : backend.exe >> "%LOG%")
if exist "%ROOT%\assets\bin\llama\llama-server.exe" (echo   OK : llama-server.exe trouve >> "%LOG%") else (echo   MANQUANT : llama-server.exe >> "%LOG%")
echo. >> "%LOG%"

echo [2/4] Verification modeles telecharges... >> "%LOG%"
if exist "%USERASSETS%\models" (echo   OK : dossier models present >> "%LOG%") else (echo   MANQUANT : dossier models >> "%LOG%")
if exist "%USERASSETS%\sherpa-onnx-streaming-zipformer-fr-kroko" (echo   OK : sherpa present >> "%LOG%") else (echo   MANQUANT : sherpa >> "%LOG%")
if exist "%USERASSETS%\pretrained_models" (echo   OK : pretrained_models present >> "%LOG%") else (echo   MANQUANT : pretrained_models >> "%LOG%")
if exist "%USERASSETS%\models_hf\all-MiniLM-L6-v2" (echo   OK : MiniLM present >> "%LOG%") else (echo   MANQUANT : MiniLM >> "%LOG%")
echo. >> "%LOG%"

echo [3/4] Verification port 8000... >> "%LOG%"
netstat -ano | findstr ":8000 " >> "%LOG%" 2>&1
if errorlevel 1 echo   OK : port 8000 libre >> "%LOG%"
echo. >> "%LOG%"

echo [4/4] Lancement du backend (60s)... >> "%LOG%"
echo. >> "%LOG%"

set "BACKEND_PORT=8000"
set "BACKEND_HOST=127.0.0.1"
set "MODELS_DIR=%USERASSETS%\models"
set "SHERPA_DIR=%USERASSETS%\sherpa-onnx-streaming-zipformer-fr-kroko"
set "PRETRAINED_DIR=%USERASSETS%\pretrained_models"
set "LLAMA_BIN_DIR=%ROOT%\assets\bin\llama"
set "MINILM_DIR=%USERASSETS%\models_hf\all-MiniLM-L6-v2"
set "HF_HUB_OFFLINE=1"
set "TRANSFORMERS_OFFLINE=1"
set "PYTHONIOENCODING=utf-8"

echo === Sortie de backend.exe === >> "%LOG%"
echo. >> "%LOG%"
"%ROOT%\backend\backend.exe" server >> "%LOG%" 2>&1

echo.
echo ============================================================
echo  Diagnostic termine.
echo  Le rapport est sauvegarde dans :
echo  %LOG%
echo.
echo  Merci d'envoyer ce fichier par mail.
echo ============================================================
echo.
pause
