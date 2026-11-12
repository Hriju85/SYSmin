@echo off
title ThrottlerOS Server
cd /d "%~dp0"
echo Starting ThrottlerOS on http://127.0.0.1:8742...
python server.py --host 127.0.0.1 --port 8742 %*
pause
