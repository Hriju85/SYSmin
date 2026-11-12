@echo off
title ThrottlerOS & SYSmin
cd /d "%~dp0"
echo ========================================================
echo  Starting ThrottlerOS & SYSmin on http://127.0.0.1:8742
echo ========================================================
python -m backend.main --host 127.0.0.1 --port 8742 %*
pause
