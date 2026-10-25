@echo off
cd /d "%~dp0"
echo Opening DraftMate AI at http://127.0.0.1:4174
echo Keep this window open while using the app. Press Ctrl+C to stop.
start "" "http://127.0.0.1:4174"
"%~dp0.venv\Scripts\python.exe" server.py
pause
