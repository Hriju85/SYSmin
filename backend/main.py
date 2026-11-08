import os
import sys
import multiprocessing
import threading
import time
import webbrowser
from typing import List
import psutil
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

app = FastAPI()

# IP Masking & Privacy Middleware: Scrubs client IP and tracking headers
class IPMaskingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Mask client address in ASGI scope
        if "client" in request.scope and request.scope["client"]:
            port = request.scope["client"][1] if len(request.scope["client"]) > 1 else 0
            request.scope["client"] = ("127.0.0.1", port)
        
        # Scrub client-identifying headers from incoming request headers
        scrub_headers = {
            b"x-forwarded-for", b"x-real-ip", b"cf-connecting-ip",
            b"true-client-ip", b"x-client-ip", b"client-ip", b"forwarded"
        }
        filtered_headers = [
            (k, v) for (k, v) in request.scope.get("headers", [])
            if k.lower() not in scrub_headers
        ]
        filtered_headers.append((b"x-forwarded-for", b"127.0.0.1"))
        filtered_headers.append((b"x-real-ip", b"127.0.0.1"))
        request.scope["headers"] = filtered_headers

        response = await call_next(request)
        
        # Enforce strict privacy headers on all responses
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response

app.add_middleware(IPMaskingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Initialize CPU counter baseline
psutil.cpu_percent()

SYSTEM_WHITELIST = {
    "system", "registry", "smss.exe", "csrss.exe", "wininit.exe", "services.exe",
    "lsass.exe", "svchost.exe", "explorer.exe", "dwm.exe", "python.exe", "conhost.exe"
}

STATE = {
    "auto_mode": False,
    "focused_pid": None,
    "suspended_pids": set(),
}

def scan_processes() -> List[dict]:
    procs = []
    my_pid = os.getpid()
    
    for p in psutil.process_iter(['pid', 'name', 'memory_info', 'exe', 'username']):
        try:
            info = p.info
            name = (info.get('name') or '').lower()
            pid = info['pid']

            if pid <= 0 or pid == my_pid:
                continue

            exe_path = (info.get('exe') or '').lower()
            system_prefixes = (
                r"c:\windows\system32",
                r"c:\windows\syswow64",
                r"c:\windows\winsxs",
                r"c:\windows\\",
                r"c:\windows",
            )

            if not exe_path or any(exe_path.startswith(prefix) for prefix in system_prefixes) or name in SYSTEM_WHITELIST:
                category = "SYSTEM_APP"
            else:
                category = "EXTERNAL_APP"

            rss_mb = round(info['memory_info'].rss / (1024 * 1024), 1) if info.get('memory_info') else 0
            is_protected = name in SYSTEM_WHITELIST or pid <= 4

            procs.append({
                "pid": pid,
                "name": info['name'] or f"Process ({pid})",
                "memory_mb": rss_mb,
                "status": "SUSPENDED" if pid in STATE["suspended_pids"] else "RUNNING",
                "is_big": rss_mb > 350,
                "category": category,
                "is_protected": is_protected
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sorted(procs, key=lambda x: x["memory_mb"])

# Background Scheduler Thread: Executes big tasks 1-by-1 in SJF order
def scheduler_daemon():
    while True:
        time.sleep(2.0)
        if not STATE["auto_mode"] or STATE["focused_pid"] is not None:
            continue

        procs = scan_processes()
        big_tasks = [p for p in procs if p["is_big"] and not p.get("is_protected")]
        if not big_tasks:
            continue

        active_candidate = big_tasks[0]["pid"]

        for task in big_tasks:
            pid = task["pid"]
            try:
                proc = psutil.Process(pid)
                if pid == active_candidate:
                    if pid in STATE["suspended_pids"]:
                        proc.resume()
                        STATE["suspended_pids"].discard(pid)
                else:
                    if pid not in STATE["suspended_pids"]:
                        proc.suspend()
                        STATE["suspended_pids"].add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                STATE["suspended_pids"].discard(pid)

threading.Thread(target=scheduler_daemon, daemon=True).start()

# API Routes
@app.get("/api/tasks")
def get_tasks():
    tasks = scan_processes()
    vm = psutil.virtual_memory()
    external_count = sum(1 for t in tasks if t.get("category") == "EXTERNAL_APP")
    system_count = len(tasks) - external_count

    return {
        "auto_mode": STATE["auto_mode"],
        "focused_pid": STATE["focused_pid"],
        "system": {
            "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
            "ram_percent": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / (1024**3), 2),
            "ram_total_gb": round(vm.total / (1024**3), 2),
            "total_processes": len(tasks),
            "external_count": external_count,
            "system_count": system_count,
            "cpu_cores": psutil.cpu_count(logical=True),
        },
        "tasks": tasks
    }

@app.post("/api/focus/{pid}")
def focus_task(pid: int):
    STATE["focused_pid"] = pid
    STATE["auto_mode"] = False
    
    for p in scan_processes():
        target_pid = p["pid"]
        if p.get("is_protected") or target_pid <= 4:
            continue
        try:
            proc = psutil.Process(target_pid)
            if target_pid == pid:
                proc.resume()
                STATE["suspended_pids"].discard(target_pid)
            else:
                proc.suspend()
                STATE["suspended_pids"].add(target_pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return {"status": "ok", "focused": pid}

@app.post("/api/kill/{pid}")
def kill_task(pid: int):
    my_pid = os.getpid()
    if pid <= 4 or pid == my_pid:
        return JSONResponse(
            status_code=403,
            content={"status": "error", "message": "Protected system process cannot be terminated."}
        )

    try:
        proc = psutil.Process(pid)
        proc_name = (proc.name() or "").lower()
        if proc_name in SYSTEM_WHITELIST:
            return JSONResponse(
                status_code=403,
                content={"status": "error", "message": "Protected system process cannot be terminated."}
            )

        if pid in STATE["suspended_pids"]:
            STATE["suspended_pids"].discard(pid)
        if STATE["focused_pid"] == pid:
            STATE["focused_pid"] = None

        proc.terminate()
        try:
            proc.wait(timeout=0.5)
        except psutil.TimeoutExpired:
            proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return {"status": "terminated", "pid": pid}

@app.post("/api/resume-all")
def resume_all():
    STATE["focused_pid"] = None
    STATE["auto_mode"] = False
    for pid in list(STATE["suspended_pids"]):
        try:
            psutil.Process(pid).resume()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    STATE["suspended_pids"].clear()
    return {"status": "ok"}

@app.post("/api/toggle-auto")
def toggle_auto():
    STATE["auto_mode"] = not STATE["auto_mode"]
    STATE["focused_pid"] = None
    if not STATE["auto_mode"]:
        resume_all()
    return {"auto_mode": STATE["auto_mode"]}

@app.get("/api/privacy")
def get_privacy_status():
    return {
        "status": "active",
        "ip_masking": "ENABLED",
        "masked_client_ip": "127.0.0.1",
        "headers_scrubbed": True,
        "proxy_configured": bool(os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY"))
    }

# Locate frontend directory (supports dev mode and PyInstaller frozen bundle)
def get_frontend_dir() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_frontend = os.path.join(sys._MEIPASS, "frontend")
        if os.path.exists(bundle_frontend):
            return bundle_frontend
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(backend_dir, "..", "frontend")),
        os.path.abspath(os.path.join(backend_dir, "frontend")),
        os.path.abspath(os.path.join(os.getcwd(), "frontend")),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return os.path.abspath(os.path.join(backend_dir, "..", "frontend"))

frontend_dir = get_frontend_dir()
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    @app.get("/")
    def serve_index():
        return {"status": "ok", "message": "Process Controller API is running. Frontend directory not found."}

if __name__ == "__main__":
    multiprocessing.freeze_support()
    import uvicorn
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:8000")).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")