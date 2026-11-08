# Backend - Process Controller API

FastAPI backend service for system process discovery, Shortest-Job-First (SJF) scheduling, memory inspection, and task management.

---

## 📁 Files
- **`main.py`**: FastAPI application with API endpoints (`/api/tasks`, `/api/kill/{pid}`, `/api/focus/{pid}`, etc.) and static file serving.
- **`requirements.txt`**: Minimal Python dependencies required for the backend service.
- **`Dockerfile`**: Container definition based on `python:3.11-slim`.

---

## 🚀 Running & Deployment

### 1. Direct Python Run
```bash
# Navigate to backend or project root
pip install -r requirements.txt
python main.py
```
API will be live at `http://127.0.0.1:8000` with Swagger docs at `http://127.0.0.1:8000/docs`.

### 2. Production with Gunicorn / Uvicorn Workers
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

### 3. Docker Deployment
```bash
docker build -t process-controller-backend .
docker run -p 8000:8000 process-controller-backend
```

> **Note on Containerized Process Monitoring:** psutil queries processes of the host/container. To monitor host processes inside a Linux Docker container, launch the container with `--pid=host`.

