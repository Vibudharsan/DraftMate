@echo off
cd /d "%~dp0"
set "PY=%~dp0runtime\python.exe"
if not exist "%PY%" set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo DraftMate's Python was not found. Download the full Windows release zip from
  echo   https://github.com/Vibudharsan/draftmate/releases/latest
  echo and extract it before running this file.
  pause
  exit /b 1
)
echo Starting DraftMate AI with Wi-Fi sharing.
echo This computer: http://127.0.0.1:4174
echo Anyone on this Wi-Fi can open the "Same Wi-Fi devices" link below and use your AI credits.
echo If Windows Firewall asks, allow Python on the network you are using.
echo Keep this window open. Press Ctrl+C to stop sharing.
echo.
start "" "http://127.0.0.1:4174"
"%PY%" server.py --lan
pause
