@echo off
title ThrottlerOS & SYSmin Server
cd /d "%~dp0\.."
echo Starting ThrottlerOS & SYSmin on http://127.0.0.1:8742...
python -m backend.main --host 127.0.0.1 --port 8742 %*
pause

