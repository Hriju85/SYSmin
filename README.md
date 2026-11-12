# ThrottlerOS & SYSmin

> **Localhost Process Throttler & Shortest-Job-First (SJF) Priority Scheduler**  
> *Reclaim Your PC Performance. Zero Cloud. 100% Offline.*

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Platforms](https://img.shields.io/badge/Platforms-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

ThrottlerOS (SYSmin) is a lightweight process manager and scheduler designed to eliminate CPU contention and resource thrashing. It freezes resource-hungry background applications non-destructively, queues heavy jobs in Shortest-Job-First (SJF) order, provides real-time Task Manager telemetry graphs, and runs completely locally from loopback (`127.0.0.1:8742`) with zero telemetry.

---

## ⚡ Core Features

- **Non-Destructive Freezing**: Pauses apps immediately using OS kernel suspension (`NtSuspendProcess` on Windows, `SIGSTOP` on POSIX/Linux/macOS). Memory, open sockets, and unsaved work stay preserved in RAM. When resumed, apps continue seamlessly from the exact instruction where they were paused.
- **Shortest-Job-First (SJF) Automation**: Queues heavy tasks and processes shortest-first. Short jobs complete early instead of waiting behind long operations, significantly decreasing average latency.
- **Dual-Column Process Segregation**: Clear division between external user applications and system background processes. Protected OS processes are locked to prevent accidental freezing.
- **Multi-Device & LAN Support**: Run on a PC, server, or Raspberry Pi, and connect from a phone, tablet, or secondary computer over the local network using `--lan`.
- **Zero Cloud & Strict Privacy**: Binds to loopback by default, strips client identifiers with IP masking middleware, and operates with no internet connection required.
- **Dual Web Interface**:
  - **ThrottlerOS Controller (`/`)**: Streamlined control with real-time CPU reclaimed, RAM held intact, freeze/resume actions, and SJF queue.
  - **Task Manager Dashboard (`/dashboard`)**: Full 60-second real-time CPU & RAM canvas utilization charts, multi-column sorting, and search filtering.

---

## 📂 Project Structure

```text
SYSmin/
├── pyproject.toml              # Modern Python package configuration
├── setup.py                    # Setup script for pip install
├── requirements.txt            # Root dependencies (fastapi, uvicorn, psutil)
├── Dockerfile                  # Cross-platform container definition (pid: host)
├── docker-compose.yml          # Container orchestration
│
├── backend/                    # Core Backend Services
│   ├── main.py                 # FastAPI application, routing, and CLI runner
│   ├── process_manager.py      # Cross-platform process monitoring, suspension, and classification
│   ├── sjf_scheduler.py        # Shortest-Job-First queue engine & auto-scheduler
│   ├── packager.py             # Generates pre-bundled download packages (.zip / .tar.gz)
│   └── requirements.txt        # Backend dependencies
│
├── frontend/                   # Frontend Web Applications
│   ├── throttleros.html        # Official ThrottlerOS landing & live interactive UI
│   ├── index.html              # Advanced Task Manager real-time telemetry dashboard
│   ├── style.css               # Task Manager dashboard styles
│   ├── app.js                  # Task Manager dashboard state & polling
│   └── nginx.conf              # Optional Nginx configuration
│
├── dist_packages/              # Pre-generated distribution packages
│   ├── ThrottlerOS-1.0.0-win64.zip
│   ├── ThrottlerOS-1.0.0-linux.tar.gz
│   ├── ThrottlerOS-1.0.0-linux.zip
│   └── ThrottlerOS-1.0.0-macos.tar.gz
│
├── scripts/                    # Platform Launchers & Service Installers
│   ├── install.sh              # Linux / macOS 1-click virtualenv installer
│   ├── run.sh                  # Linux / macOS launcher
│   ├── install.bat             # Windows CMD installer
│   ├── run.bat                 # Windows interactive runner
│   ├── throttleros.service     # Linux systemd service unit
│   └── check_my_ip.ps1         # IP diagnostic script
│
├── install.vbs                 # Windows elevated 1-click installer
├── run.vbs                     # Windows silent background runner (no console window)
└── README.md                   # Documentation
```

---

## 🚀 Running on Different Devices

### 1. Windows (10 / 11 64-bit)
1. **One-Click Installation**: Double-click `install.vbs` (or run `scripts\install.bat` as Administrator).
2. **Silent Background Execution**: Double-click `run.vbs`. It starts the server silently without opening a terminal window.
3. Open **`http://127.0.0.1:8742`** in your browser.

### 2. Linux & Raspberry Pi
1. Run the installer script:
   ```bash
   ./scripts/install.sh
   ```
2. Start the application:
   ```bash
   ./scripts/run.sh
   ```
3. *(Optional)* Install as a background **systemd** service:
   ```bash
   sudo cp scripts/throttleros.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now throttleros
   ```

### 3. macOS
1. Setup and run:
   ```bash
   ./scripts/install.sh
   ./scripts/run.sh
   ```
2. Open `http://127.0.0.1:8742` in Safari or Chrome.

### 4. Cross-Device Control (Phone, Tablet, or Laptop via LAN)
To manage and throttle processes from another device on your local Wi-Fi or home network:
```bash
# Start with the --lan flag:
python -m backend.main --lan --port 8742
```
The server will output your local IP (e.g. `http://192.168.1.15:8742`). Open this link on your smartphone or other computer to monitor and control tasks remotely!

### 5. Install as a Python Module (`pip install`)
You can install and run the tool on any device with Python 3.10+:
```bash
pip install .
throttleros --port 8742
```

### 6. Docker (Containerized with Host Process Access)
To run in Docker while retaining visibility over host processes:
```bash
docker compose up --build
```

---

## 📡 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/tasks` | Returns running processes, CPU reclaimed, RAM held, and SJF queue |
| `POST` | `/api/freeze/{pid}` | Non-destructively freezes (suspends) process PID |
| `POST` | `/api/resume/{pid}` | Resumes a suspended process PID |
| `POST` | `/api/focus/{pid}` | Focuses CPU on target PID; suspends other user apps |
| `POST` | `/api/kill/{pid}` | Terminates a process (protected system tasks blocked) |
| `POST` | `/api/resume-all` | Resumes all suspended processes across the system |
| `POST` | `/api/toggle-auto` | Toggles automated SJF scheduling mode |
| `GET` | `/api/queue` | Returns SJF priority task queue |
| `POST` | `/api/queue/add` | Adds a job to the SJF queue (`name`, `est_seconds`, `pid`) |
| `POST` | `/api/queue/remove/{id}` | Cancels/removes an item from the SJF queue |
| `GET` | `/api/device` | Returns device OS, hostname, local IP, and LAN endpoints |
| `GET` | `/api/download/{platform}` | Downloads bundle for `windows`, `linux`, `macos`, or `source` |
| `GET` | `/api/privacy` | Privacy middleware and IP masking status |

---

## 🔒 Privacy & Security

ThrottlerOS enforces complete offline privacy:
- Does not ping external analytics or cloud services.
- Uses `IPMaskingMiddleware` to scrub identifying headers (`X-Forwarded-For`, `CF-Connecting-IP`, etc.).
- Critical OS components (`csrss.exe`, `explorer.exe`, `systemd`, `init`, PID &le; 4) are whitelisted and locked from termination or suspension.

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.
