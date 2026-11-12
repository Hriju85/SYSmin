# SYSmin (Local Process Controller & SJF Throttler)

A lightweight utility and process manager designed to monitor active system processes, provide real-time Task Manager telemetry graphs, and selectively throttle background tasks using Shortest-Job-First (SJF) scheduling to optimize CPU performance and reclaim system resources.

---

## 📂 Streamlined Project Structure

```text
SYSmin/
├── run.vbs                   # Unified Windows 1-Click Runner (runs EXE/source, stops, opens browser)
├── run.sh                    # Unified Linux/macOS Runner (start/stop/open browser)
├── requirements.txt          # Python dependencies with platform markers
│
├── backend/                  # Backend FastAPI Service
│   ├── main.py               # API endpoints, SJF daemon & static file serving
│   ├── requirements.txt      # Backend dependencies
│   ├── Dockerfile            # Backend container definition
│   ├── .dockerignore         # Docker ignore rules
│   └── README.md             # Backend setup & deployment guide
│
├── frontend/                 # Frontend Web UI (Vanilla HTML/CSS/JS)
│   ├── index.html            # Split-grid process monitor dashboard
│   ├── style.css             # Theme styles and responsive layout
│   ├── app.js                # Task polling, filtering, and API integration
│   ├── nginx.conf            # Nginx reverse proxy configuration
│   ├── Dockerfile            # Frontend container definition
│   ├── .dockerignore         # Docker ignore rules
│   └── README.md             # Frontend hosting & deployment guide
│
├── dist/                     # Standalone compiled binary (ProcessController)
├── scripts/                  # Network & Proxy helper scripts
│   ├── check_my_ip.ps1
│   ├── enable_system_proxy.ps1
│   └── disable_system_proxy.ps1
│
├── docker-compose.yml        # Multi-container deployment (Frontend + Backend)
├── ProcessController.spec    # PyInstaller specification for windowless executable
├── build.bat                 # Rebuild script for PyInstaller
├── LICENSE                   # Project license
└── README.md                 # Project documentation
```

---

## 🚀 Quick Start (One Running File Does It All)

### 🪟 Windows Users (`run.vbs`)
Double-click **`run.vbs`** to do everything:
1. **Auto-Detects Executable**: If `dist\ProcessController.exe` or `ProcessController.exe` is present, it launches the standalone executable completely silently.
2. **Auto-Detects Python Environment**: If the executable is not built, it automatically sets up `.venv` and installs `requirements.txt` on first launch, then runs `backend/main.py` hidden using `pythonw.exe`.
3. **Smart Lifecycle Management**:
   - If SYSmin is **not running**: starts the server, waits for port 8000, and opens `http://127.0.0.1:8000` in your default browser.
   - If SYSmin is **already running**: prompts you whether to open the dashboard in your browser or cleanly terminate the background server.

### 🐧 Linux & macOS Users (`run.sh`)
- **Start the app**:
  ```bash
  ./run.sh
  ```
- **Stop the app**:
  ```bash
  ./run.sh stop
  ```

---

## 📦 Building Standalone Executable (.exe)
To compile into a single, windowless `.exe`:
```cmd
build.bat
```
Output executable is saved to `dist/ProcessController.exe`.
