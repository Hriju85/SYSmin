@echo off
title ThrottlerOS Installer
cd /d "%~dp0"
echo ====================================================
echo             ThrottlerOS Setup & Installer
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
    echo [SUCCESS] ThrottlerOS installed successfully!
    echo Run 'run.vbs' for silent background execution.
    echo Run 'run.bat' for interactive console output.
    echo Dashboard: http://127.0.0.1:8742
    echo ====================================================
) else (
    echo [WARNING] Encountered issues installing packages.
)
echo.
pause
