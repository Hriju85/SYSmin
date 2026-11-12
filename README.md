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
├── website/                  # Official Public Website & Release Portal
│   ├── index.html            # Marketing landing page & in-browser downloader
│   ├── style.css             # Theme stylesheet & layout
│   ├── vercel.json           # Vercel Edge CDN configuration
│   └── README.md             # Website deployment guide
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

---

## 🌐 Official Website & Web Portal (`website/`)

SYSmin includes a modern, high-performance landing page and web release portal located in the [`website/`](./website) folder:

- **Live Demo & Downloads:** Visitors can select their operating system (Windows, Linux, macOS, Docker) and download releases with zero redirects.
- **Interactive Setup Guide:** Walks users through Step 1 (extracting), Step 2 (1-click `run.vbs` or `run.sh` launcher), and Step 3 (using the dashboard on port `8000`).
- **Zero-Dependency Edge Deployment:**
  - **Vercel:** Point your Vercel project's Root Directory to `website` for instant, global Edge CDN deployment.
  - **GitHub Pages:** Select branch `main` and folder `/website` under repository settings.
- **Local Preview:** Open [`website/index.html`](./website/index.html) directly in any browser or run:
  ```bash
  python -m http.server 8080 --directory website
  ```
