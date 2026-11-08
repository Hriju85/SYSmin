@echo off
echo Building ProcessController standalone executable...
.\.venv\Scripts\pyinstaller.exe --clean ProcessController.spec
echo.
echo Build complete! The executable is located at dist\ProcessController.exe
pause
