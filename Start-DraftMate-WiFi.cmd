@echo off
cd /d "%~dp0"
echo Starting DraftMate AI with Wi-Fi sharing.
echo This computer: http://127.0.0.1:4174
echo Anyone on this Wi-Fi can open the "Same Wi-Fi devices" link below and use your AI credits.
echo If Windows Firewall asks, allow Python on the network you are using.
echo Keep this window open. Press Ctrl+C to stop sharing.
echo.
start "" "http://127.0.0.1:4174"
"%~dp0.venv\Scripts\python.exe" server.py --lan
pause
