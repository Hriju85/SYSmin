import io
import zipfile
import tarfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

INSTALL_VBS = '''\
' ThrottlerOS Windows One-Click Installer
Option Explicit
Dim sh, ret

Set sh = CreateObject("WScript.Shell")

On Error Resume Next
sh.Exec("python --version")
If Err.Number <> 0 Then
    MsgBox "Python was not found on your system." & vbCrLf & vbCrLf & _
           "Please download and install Python 3.10 or newer from https://www.python.org" & vbCrLf & _
           "Ensure 'Add Python to PATH' is checked during installation.", vbCritical, "ThrottlerOS Setup"
    WScript.Quit 1
End If
On Error GoTo 0

ret = sh.Run("cmd /c pip install -r requirements.txt", 1, True)
If ret = 0 Then
    MsgBox "ThrottlerOS installation successful!" & vbCrLf & vbCrLf & _
           "To start ThrottlerOS silently in the background, double-click 'run.vbs'." & vbCrLf & _
           "The dashboard will open at http://127.0.0.1:8742", vbInformation, "ThrottlerOS Setup"
Else
    MsgBox "Installation encountered warnings or errors." & vbCrLf & _
           "Try running install.bat as Administrator.", vbExclamation, "ThrottlerOS Setup"
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
'''

RUN_VBS = '''\
' ThrottlerOS Silent Launcher (No console window)
Set sh = CreateObject("WScript.Shell")
sh.Run "pythonw server.py --host 127.0.0.1 --port 8742", 0, False
'''

RUN_BAT = '''\
@echo off
title ThrottlerOS Server
echo Starting ThrottlerOS on http://127.0.0.1:8742...
python server.py --host 127.0.0.1 --port 8742
pause
'''

INSTALL_SH = '''\
#!/usr/bin/env bash
# ThrottlerOS Linux / macOS Installer
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "===================================================="
echo "          ThrottlerOS Linux / macOS Setup"
echo "===================================================="

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10 or newer."
    exit 1
fi

echo "Setting up Python virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

echo "Installing required dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

chmod +x run.sh
chmod +x install.sh

echo ""
echo "===================================================="
echo "[SUCCESS] Installation complete!"
echo "Run './run.sh' to start ThrottlerOS."
echo "Run './run.sh --lan' to allow access from other devices."
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
elif command -v python3 &>/dev/null; then
    PY="python3"
else
    echo "[ERROR] Python 3 not found."
    exit 1
fi

echo "Starting ThrottlerOS on http://127.0.0.1:8742..."
exec "$PY" server.py --host 127.0.0.1 --port 8742 "$@"
'''

THROTTLEROS_SERVICE = '''\
[Unit]
Description=ThrottlerOS Localhost Process Throttler & Priority Scheduler
After=network.target

[Service]
Type=simple
User=%I
WorkingDirectory=/opt/throttleros
ExecStart=/opt/throttleros/.venv/bin/python3 server.py --host 0.0.0.0 --port 8742 --no-browser
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
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

Quick Start (Linux / macOS):
1. Run ./install.sh
2. Run ./run.sh (or ./run.sh --lan for network access)
3. Open http://127.0.0.1:8742

Features:
- Non-destructive process freezing via kernel suspension (proc.suspend / proc.resume)
- Shortest-Job-First (SJF) priority task scheduling
- Segregated columns for user apps vs system background tasks
- 100% offline and loopback privacy (0 telemetry)
'''


def get_core_files(root: Path) -> list:
    core_names = [
        "index.html",
        "server.py",
        "main.py",
        "process_manager.py",
        "sjf_scheduler.py",
    ]
    files = []
    for name in core_names:
        p = root / name
        if p.exists():
            files.append((name, p))
    return files


def build_standalone_packages(root: Path = BASE_DIR):
    downloads_dir = root / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    core = get_core_files(root)

    # 1. Windows Zip
    win_zip_path = downloads_dir / "ThrottlerOS-1.0.0-win64.zip"
    with zipfile.ZipFile(win_zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("install.vbs", INSTALL_VBS)
        z.writestr("install.bat", INSTALL_BAT)
        z.writestr("run.vbs", RUN_VBS)
        z.writestr("run.bat", RUN_BAT)
        z.writestr("README.txt", README_TXT)
        z.writestr("requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npsutil>=5.9.8\n")
        for rel_name, file_path in core:
            z.write(file_path, arcname=rel_name)

    # 2. Linux tar.gz
    linux_tar_path = downloads_dir / "ThrottlerOS-1.0.0-linux.tar.gz"
    with tarfile.open(linux_tar_path, mode="w:gz") as tar:
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

        for rel_name, file_path in core:
            tar.add(str(file_path), arcname=rel_name)

    # 3. Linux zip
    linux_zip_path = downloads_dir / "ThrottlerOS-1.0.0-linux.zip"
    with zipfile.ZipFile(linux_zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("install.sh", INSTALL_SH)
        z.writestr("run.sh", RUN_SH)
        z.writestr("throttleros.service", THROTTLEROS_SERVICE)
        z.writestr("README.md", README_TXT)
        z.writestr("requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npsutil>=5.9.8\n")
        for rel_name, file_path in core:
            z.write(file_path, arcname=rel_name)

    # 4. macOS tar.gz
    macos_tar_path = downloads_dir / "ThrottlerOS-1.0.0-macos.tar.gz"
    with tarfile.open(macos_tar_path, mode="w:gz") as tar:
        def add_str_mac(name, content, mode=0o644):
            ti = tarfile.TarInfo(name=name)
            b = content.encode("utf-8")
            ti.size = len(b)
            ti.mode = mode
            tar.addfile(ti, io.BytesIO(b))

        add_str_mac("install.sh", INSTALL_SH, mode=0o755)
        add_str_mac("run.sh", RUN_SH, mode=0o755)
        add_str_mac("README.md", README_TXT, mode=0o644)
        add_str_mac("requirements.txt", "fastapi>=0.110.0\nuvicorn>=0.28.0\npsutil>=5.9.8\n", mode=0o644)

        for rel_name, file_path in core:
            tar.add(str(file_path), arcname=rel_name)

    return downloads_dir


if __name__ == "__main__":
    out = build_standalone_packages()
    print(f"Generated standalone packages in: {out}")
