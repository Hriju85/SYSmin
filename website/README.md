# ThrottlerOS

> **Localhost Process Throttler & Shortest-Job-First (SJF) Priority Scheduler**  
> *Reclaim Your PC Performance. Zero Cloud. 100% Offline.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)

This folder contains the complete, standalone website and dedicated process controller backend for **ThrottlerOS**.

---

## 📂 Standalone Folder Contents

```text
ThrottlerOS/
├── index.html              # The official ThrottlerOS web interface
├── server.py               # Dedicated FastAPI backend & process controller
├── main.py                 # Runner alias (python main.py)
├── process_manager.py      # Cross-platform kernel suspension & process classification
├── sjf_scheduler.py        # Shortest-Job-First priority queue engine
├── packager.py             # Package builder for platform distributions
├── requirements.txt        # Backend dependencies (fastapi, uvicorn, psutil)
│
├── downloads/              # Pre-bundled platform installers
│   ├── ThrottlerOS-1.0.0-win64.zip
│   ├── ThrottlerOS-1.0.0-linux.tar.gz
│   ├── ThrottlerOS-1.0.0-linux.zip
│   └── ThrottlerOS-1.0.0-macos.tar.gz
│
├── install.vbs             # Windows elevated 1-click installer
├── run.vbs                 # Windows silent background launcher (no console window)
├── install.bat             # Windows CMD installer
├── run.bat                 # Windows CMD runner
├── install.sh              # Linux / macOS shell installer
├── run.sh                  # Linux / macOS launcher
├── throttleros.service     # Linux systemd background service unit
└── README.md               # Documentation
```

---

## 🚀 How to Run on Different Devices

### 1. Windows (10 / 11)
- **Install**: Double-click `install.vbs` (or run `install.bat` as Administrator).
- **Run Silently**: Double-click `run.vbs`. It starts in the background with no console window.
- **Run Interactively**: Double-click `run.bat`.
- Open **`http://127.0.0.1:8742`** in your browser.

### 2. Linux & Raspberry Pi
- **Install**:
  ```bash
  ./install.sh
  ```
- **Run**:
  ```bash
  ./run.sh
  ```
- **Background Daemon (Systemd)**:
  ```bash
  sudo cp throttleros.service /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl enable --now throttleros
  ```

### 3. macOS
- Setup and run:
  ```bash
  ./install.sh
  ./run.sh
  ```
- Open `http://127.0.0.1:8742` in Safari or Chrome.

### 4. Cross-Device Control (Phone, Tablet, or Another PC via Wi-Fi)
To monitor and freeze processes remotely from another device on your local network:
```bash
python server.py --lan --port 8742
```
Or on Linux/macOS:
```bash
./run.sh --lan
```
The server outputs your local network IP (e.g. `http://192.168.1.15:8742`). Open this URL in your mobile browser to control the host computer!

---

## ⚡ Features on the Web Page

1. **Live App Window**:
   - **External Apps vs System Background**: Clear separation so user apps can be throttled without risking system stability.
   - **Freeze & Resume**: Calls `proc.suspend()` to reclaim CPU cycles while keeping memory and open documents intact in RAM.
   - **Real-Time Telemetry**: Reclaimed CPU %, RAM held intact, and frozen process counter.
   - **SJF Queue**: Priority execution of short heavy jobs first to minimize task latency.
2. **Download Section**:
   - Platform selector for Windows, Linux, macOS, and Python.
   - Downloads real `.zip` and `.tar.gz` packages bundled directly with installers.
3. **100% Offline & Loopback Privacy**:
   - Zero telemetry, no external accounts, zero tracking.

---

## 📡 API Reference

- `GET /` — Serves `index.html` (ThrottlerOS web interface)
- `GET /api/tasks` — List processes, CPU reclaimed, RAM held, and SJF queue
- `POST /api/freeze/{pid}` — Non-destructively freezes (suspends) process PID
- `POST /api/resume/{pid}` — Resumes a frozen process PID
- `POST /api/focus/{pid}` — Focuses CPU on target PID, suspends others
- `POST /api/kill/{pid}` — Terminates process safely
- `POST /api/resume-all` — Resumes all suspended processes
- `POST /api/toggle-auto` — Toggles auto SJF scheduling mode
- `GET /api/queue` — Returns active SJF queue items
- `POST /api/queue/add` — Adds task to SJF queue
- `POST /api/queue/remove/{id}` — Removes task from SJF queue
- `GET /api/device` — Returns host info and LAN access URLs
- `GET /api/download/{platform}` — Serves package for `windows`, `linux`, `macos`, or `source`
- `GET /api/privacy` — Privacy middleware status
