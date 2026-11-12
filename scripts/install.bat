@echo off
title ThrottlerOS & SYSmin Installer
cd /d "%~dp0\.."

echo ====================================================
echo             ThrottlerOS & SYSmin Setup
echo ====================================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.10+ is not found in PATH!
    echo Please install Python from https://www.python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo Installing dependencies (fastapi, uvicorn, psutil)...
pip install -r requirements.txt
if %errorlevel% equ 0 (
    echo.
    echo ====================================================
    echo [SUCCESS] Setup completed successfully!
    echo Run 'run.vbs' for background execution without a console.
    echo Run 'scripts\run.bat' for interactive console output.
    echo URL: http://127.0.0.1:8742
    echo ====================================================
) else (
    echo [WARNING] There was an issue installing dependencies.
)
echo.
pause
