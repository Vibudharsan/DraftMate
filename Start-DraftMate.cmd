@echo off
cd /d "%~dp0"
set "PY=%~dp0runtime\python.exe"
if not exist "%PY%" set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo DraftMate's Python was not found. Download the full Windows release zip from
  echo   https://github.com/Vibudharsan/DraftMate/releases/latest
  echo and extract it before running this file.
  pause
  exit /b 1
)
echo Opening DraftMate AI at http://127.0.0.1:4174
echo Keep this window open while using the app. Press Ctrl+C to stop.
start "" "http://127.0.0.1:4174"
"%PY%" server.py
pause
