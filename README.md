# SYSmin (Local Process Controller & SJF Throttler)

A lightweight Windows utility and process manager designed to monitor active system processes, provide real-time Task Manager telemetry graphs, and selectively throttle background tasks using Shortest-Job-First (SJF) scheduling to optimize CPU performance and reclaim system resources.

---

## 📂 Project Structure

```text
processidentifer/
├── backend/                  # Backend FastAPI Service
│   ├── main.py               # API endpoints & static serving
│   ├── requirements.txt      # Backend Python dependencies
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
├── dist/                     # Standalone Windows executable output
├── docker-compose.yml        # Multi-container deployment (Frontend + Backend)
├── ProcessController.spec    # PyInstaller specification for Windows bundle
├── build.bat                 # Rebuild script for PyInstaller
├── run.vbs                   # Silent VBS launcher for Python source
├── run_exe_silent.vbs        # Silent VBS launcher for Windows executable
├── requirements.txt          # Root Python dependencies
└── README.md                 # Project documentation
```

---

## 🚀 Deployment Options

### 1. Docker Compose (Full Stack)
To run both the backend and frontend in containerized environments:
```bash
docker compose up --build
```
- Frontend UI: `http://localhost:3000`
- Backend API: `http://localhost:8000`

### 2. Standalone Windows Executable (.exe)
The project is packaged into a single Windows executable bundling Python, dependencies, and frontend:
- **Direct run**: Double-click `dist\ProcessController.exe`.
- **Silent background run**: Double-click `run_exe_silent.vbs`.
- **Rebuilding the executable**: Run `build.bat` or:
  ```powershell
  .\.venv\Scripts\pyinstaller.exe --clean ProcessController.spec
  ```

### 3. Decoupled Cloud / Server Deployment
- **Backend**: Can be deployed independently (e.g., on Render, Fly.io, Railway, AWS ECS, or any Linux VPS) using `backend/Dockerfile` or `pip install -r backend/requirements.txt && python backend/main.py`.
- **Frontend**: Can be deployed to any static host (Vercel, Netlify, Cloudflare Pages, S3, or Nginx) using `frontend/`. Point the frontend to the backend by setting `window.API_BASE_URL` in `frontend/index.html`.

---

## 💻 Local Development Mode

Run directly from source:
```powershell
.\.venv\Scripts\python.exe backend\main.py
```
Or launch silently without a console window:
```cmd
wscript run_exe_silent.vbs
```
>>>>>>> fe0480d (Initial commit: Process Controller & SJF Task Throttler with real-time Task Manager graphs, IP masking, and modular frontend/backend architecture)
