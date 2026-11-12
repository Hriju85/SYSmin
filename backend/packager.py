import os
import sys
import io
import zipfile
import tarfile
from pathlib import Path
from typing import Optional


# VBScript & Batch Launchers for Windows
INSTALL_VBS = '''\
' ThrottlerOS Windows One-Click Installer
Option Explicit
Dim sh, fs, ret, pythonPath, pyVer

Set sh = CreateObject("WScript.Shell")
Set fs = CreateObject("Scripting.FileSystemObject")

On Error Resume Next
Set pyVer = sh.Exec("python --version")
If Err.Number <> 0 Then
    MsgBox "Python was not found on your system." & vbCrLf & vbCrLf & _
           "Please download and install Python 3.11 or newer from https://www.python.org" & vbCrLf & _
           "Ensure 'Add Python to PATH' is checked during installation.", vbCritical, "ThrottlerOS Setup"
    WScript.Quit 1
End If
On Error GoTo 0

' Install required dependencies
ret = sh.Run("cmd /c pip install -r requirements.txt", 1, True)
If ret = 0 Then
    MsgBox "ThrottlerOS installation successful!" & vbCrLf & vbCrLf & _
           "To start ThrottlerOS silently in the background, double-click 'run.vbs'." & vbCrLf & _
           "The dashboard will open at http://127.0.0.1:8742", vbInformation, "ThrottlerOS Setup"
Else
    MsgBox "Installation encountered warnings or errors." & vbCrLf & _
           "Try running install.bat in a terminal as Administrator.", vbExclamation, "ThrottlerOS Setup"
End If
'''

INSTALL_BAT = '''\
@echo off
title ThrottlerOS Installer
echo ====================================================
echo             ThrottlerOS Setup & Installer
echo ====================================================
echo.
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ is not found in PATH!
    echo Please download and install Python from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation.
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
    echo.
    echo [WARNING] Encountered issues installing packages.
)
echo.
pause
'''

RUN_VBS = '''\
' ThrottlerOS Silent Launcher (No console window)
Set sh = CreateObject("WScript.Shell")
sh.Run "pythonw -m backend.main --host 127.0.0.1 --port 8742", 0, False
'''

RUN_BAT = '''\
@echo off
title ThrottlerOS Server
echo Starting ThrottlerOS on http://127.0.0.1:8742...
python -m backend.main --host 127.0.0.1 --port 8742
pause
'''

README_TXT = '''\
====================================================
           ThrottlerOS v1.0.0 Stable
  Localhost Process Throttler & Priority Scheduler
====================================================

Quick Start (Windows):
1. Right-click install.vbs and choose Open (or run install.bat as Administrator).
2. Double-click run.vbs to launch silently in the background without a console window.
3. Open http://127.0.0.1:8742 in any browser.

Features:
- Non-destructive process freezing via kernel suspension (proc.suspend / proc.resume)
- Shortest-Job-First (SJF) priority task scheduling
- Segregated columns for user apps vs system background tasks
- 100% offline and loopback privacy (0 telemetry)

To stop ThrottlerOS:
End 'pythonw.exe' in Windows Task Manager, or close the console if started via run.bat.
'''

# Linux / macOS Shell Scripts
INSTALL_SH = '''\
#!/usr/bin/env bash
# ThrottlerOS Linux / macOS Installer
set -e

echo "===================================================="
echo "          ThrottlerOS Linux / macOS Setup"
echo "===================================================="

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.11 or newer."
    exit 1
fi

echo "Creating Python virtual environment (.venv)..."
python3 -m venv .venv

echo "Installing required dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

chmod +x run.sh

echo ""
echo "===================================================="
echo "[SUCCESS] Installation complete!"
echo "Run './run.sh' to start ThrottlerOS."
echo "Dashboard: http://127.0.0.1:8742"
echo "===================================================="
'''

RUN_SH = '''\
#!/usr/bin/env bash
# ThrottlerOS Runner
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f ".venv/bin/python3" ]; then
    PY=".venv/bin/python3"
else
    PY="python3"
fi

echo "Starting ThrottlerOS on http://127.0.0.1:8742..."
exec "$PY" -m backend.main --host 127.0.0.1 --port 8742 "$@"
'''

THROTTLEROS_SERVICE = '''\
[Unit]
Description=ThrottlerOS Localhost Process Throttler & Priority Scheduler
After=network.target

[Service]
Type=simple
User=%I
WorkingDirectory=/opt/throttleros
ExecStart=/opt/throttleros/.venv/bin/python3 -m backend.main --host 0.0.0.0 --port 8742
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
'''


def get_repo_root() -> Path:
    """Returns the root directory of the SYSmin repository."""
    backend_dir = Path(__file__).resolve().parent
    return backend_dir.parent


def get_core_files() -> list:
    """Gathers all core backend and frontend files to bundle."""
    root = get_repo_root()
    files = []

    # Backend Python files
    backend_files = [
        ("backend/__init__.py", root / "backend" / "__init__.py"),
        ("backend/main.py", root / "backend" / "main.py"),
        ("backend/process_manager.py", root / "backend" / "process_manager.py"),
        ("backend/sjf_scheduler.py", root / "backend" / "sjf_scheduler.py"),
        ("backend/packager.py", root / "backend" / "packager.py"),
        ("backend/requirements.txt", root / "backend" / "requirements.txt"),
    ]

    # Frontend files
    frontend_dir = root / "frontend"
    frontend_files = []
    if frontend_dir.exists():
        for f in frontend_dir.glob("*"):
            if f.is_file() and not f.name.startswith("."):
                frontend_files.append((f"frontend/{f.name}", f))

    for rel, path in backend_files + frontend_files:
        if path.exists():
            files.append((rel, path))

    return files


def generate_windows_zip(output_path: Optional[Path] = None) -> bytes:
    """Generates the ThrottlerOS-1.0.0-win64.zip package buffer or file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # Launcher and installer scripts
        z.writestr("install.vbs", INSTALL_VBS)
        z.writestr("install.bat", INSTALL_BAT)
        z.writestr("run.vbs", RUN_VBS)
        z.writestr("run.bat", RUN_BAT)
        z.writestr("README.txt", README_TXT)
        z.writestr("requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npsutil>=5.9.8\n")

        # Bundle core app files
        for rel_path, file_path in get_core_files():
            z.write(file_path, arcname=rel_path)

    data = buf.getvalue()
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
    return data


def generate_linux_package(output_path: Optional[Path] = None, archive_format: str = "tar.gz") -> bytes:
    """Generates the ThrottlerOS-1.0.0-linux package buffer or file."""
    if archive_format == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("install.sh", INSTALL_SH)
            z.writestr("run.sh", RUN_SH)
            z.writestr("throttleros.service", THROTTLEROS_SERVICE)
            z.writestr("README.md", README_TXT)
            z.writestr("requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npsutil>=5.9.8\n")
            for rel_path, file_path in get_core_files():
                z.write(file_path, arcname=rel_path)
        data = buf.getvalue()
    else:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            def add_str(name, content, mode=0o644):
                ti = tarfile.TarInfo(name=name)
                b = content.encode("utf-8")
                ti.size = len(b)
                ti.mode = mode
                tar.addfile(ti, io.BytesIO(b))

            add_str("install.sh", INSTALL_SH, mode=0o755)
            add_str("run.sh", RUN_SH, mode=0o755)
            add_str("throttleros.service", THROTTLEROS_SERVICE, mode=0o644)
            add_str("README.md", README_TXT, mode=0o644)
            add_str("requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npsutil>=5.9.8\n", mode=0o644)

            for rel_path, file_path in get_core_files():
                tar.add(str(file_path), arcname=rel_path)

        data = buf.getvalue()

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(data)
    return data


def generate_all_dist_packages(dist_dir: Optional[Path] = None):
    """Pre-generates distribution packages for Windows, Linux, and macOS."""
    if dist_dir is None:
        dist_dir = get_repo_root() / "dist_packages"

    dist_dir.mkdir(parents=True, exist_ok=True)
    generate_windows_zip(dist_dir / "ThrottlerOS-1.0.0-win64.zip")
    generate_linux_package(dist_dir / "ThrottlerOS-1.0.0-linux.tar.gz", "tar.gz")
    generate_linux_package(dist_dir / "ThrottlerOS-1.0.0-linux.zip", "zip")
    generate_linux_package(dist_dir / "ThrottlerOS-1.0.0-macos.tar.gz", "tar.gz")
    return dist_dir


if __name__ == "__main__":
    out = generate_all_dist_packages()
    print(f"Generated packages in {out}")
