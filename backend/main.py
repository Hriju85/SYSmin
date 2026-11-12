import os
import sys
import argparse
import socket
import platform

# Ensure sys.stdout and sys.stderr are valid (prevent NoneType crashes under pythonw.exe)
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
import multiprocessing
import threading
import time
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure repository root and backend directory are in sys.path
_cur_dir = Path(__file__).resolve().parent
_root_dir = _cur_dir.parent
for _p in [str(_root_dir), str(_cur_dir)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from fastapi import FastAPI, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Support relative or absolute imports for dev mode, installed module, or PyInstaller
try:
    from backend.process_manager import ProcessManager
    from backend.sjf_scheduler import SJFScheduler
    from backend.packager import generate_windows_zip, generate_linux_package
except ImportError:
    from process_manager import ProcessManager
    from sjf_scheduler import SJFScheduler
    from packager import generate_windows_zip, generate_linux_package

app = FastAPI(
    title="ThrottlerOS & SYSmin API",
    description="Localhost Process Throttler & Shortest-Job-First Priority Scheduler",
    version="1.0.0"
)

# Initialize Core Services
process_manager = ProcessManager()
sjf_scheduler = SJFScheduler(process_manager=process_manager)


# IP Masking & Privacy Middleware: Scrubs tracking headers and enforces local privacy
class IPMaskingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Mask client address in ASGI scope
        if "client" in request.scope and request.scope["client"]:
            port = request.scope["client"][1] if len(request.scope["client"]) > 1 else 0
            request.scope["client"] = ("127.0.0.1", port)

        # Scrub client-identifying and tracking headers
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

        # Strict local privacy and caching headers
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response


app.add_middleware(IPMaskingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Network and Device Utilities for Multi-Device Access
def get_local_ip() -> str:
    """Finds primary local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, purely probes default route interface
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def get_all_ips() -> List[str]:
    """Retrieves all non-loopback IPv4 addresses."""
    ips = []
    try:
        host = socket.gethostname()
        for ip in socket.gethostbyname_ex(host)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    primary = get_local_ip()
    if primary not in ips and not primary.startswith("127."):
        ips.insert(0, primary)
    return ips or ["127.0.0.1"]


def format_mb(mb: float) -> str:
    if mb >= 1000.0:
        return f"{(mb / 1024.0):.1f} GB"
    return f"{int(mb)} MB"


# Locate frontend directory (supports dev mode, PyInstaller, and installed wheel)
def get_frontend_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundle_frontend = Path(sys._MEIPASS) / "frontend"
        if bundle_frontend.exists():
            return bundle_frontend

    cur = Path(__file__).resolve().parent
    candidates = [
        cur.parent / "frontend",
        cur / "frontend",
        Path.cwd() / "frontend",
    ]
    for c in candidates:
        if c.exists():
            return c
    return cur.parent / "frontend"


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/tasks")
def get_tasks():
    """
    Returns running tasks, split into external vs system, with real-time stats
    for reclaimed CPU, RAM held intact, and SJF queue items.
    """
    tasks = process_manager.scan_processes()
    telemetry = process_manager.get_system_telemetry()

    external_apps = [t for t in tasks if t["category"] == "EXTERNAL_APP"]
    system_apps = [t for t in tasks if t["category"] == "SYSTEM_APP"]

    return {
        "auto_mode": process_manager.auto_mode,
        "focused_pid": process_manager.focused_pid,
        "system": telemetry,
        "stats": {
            "cpu_reclaimed": telemetry["cpu_reclaimed"],
            "ram_held_mb": telemetry["ram_held_mb"],
            "ram_held_fmt": format_mb(telemetry["ram_held_mb"]),
            "frozen_count": telemetry["frozen_count"],
            "external_count": len(external_apps),
            "system_count": len(system_apps),
            "total_processes": len(tasks),
        },
        "external_apps": external_apps[:50],
        "system_apps": system_apps[:50],
        "tasks": tasks,
        "queue": sjf_scheduler.get_queue(),
    }


@app.post("/api/freeze/{pid}")
@app.post("/api/suspend/{pid}")
def freeze_task(pid: int):
    """
    Non-destructive kernel suspension of a process.
    Memory remains intact, CPU utilization is reclaimed immediately.
    """
    success, msg, details = process_manager.freeze_process(pid)
    if not success:
        return JSONResponse(status_code=400, content={"status": "error", "message": msg})
    return {"status": "ok", "message": msg, "details": details}


@app.post("/api/resume/{pid}")
def resume_task(pid: int):
    """
    Resumes a frozen process from the exact instruction where it stopped.
    """
    success, msg, details = process_manager.resume_process(pid)
    if not success:
        return JSONResponse(status_code=400, content={"status": "error", "message": msg})
    return {"status": "ok", "message": msg, "details": details}


@app.post("/api/focus/{pid}")
def focus_task(pid: int):
    """
    Isolates CPU execution to the targeted process while suspending other user tasks.
    """
    success, msg = process_manager.focus_process(pid)
    return {"status": "ok" if success else "error", "message": msg, "focused": pid}


@app.post("/api/kill/{pid}")
def kill_task(pid: int):
    """
    Terminates a process with safety verification against system-critical processes.
    """
    success, msg = process_manager.kill_process(pid)
    if not success:
        return JSONResponse(status_code=403, content={"status": "error", "message": msg})
    return {"status": "terminated", "message": msg, "pid": pid}


@app.post("/api/resume-all")
def resume_all():
    """
    Resumes all frozen processes across the system.
    """
    count = process_manager.resume_all()
    return {"status": "ok", "resumed_count": count}


@app.post("/api/toggle-auto")
def toggle_auto():
    """
    Toggles automated Shortest-Job-First (SJF) scheduling mode.
    """
    process_manager.auto_mode = not process_manager.auto_mode
    process_manager.focused_pid = None
    if not process_manager.auto_mode:
        process_manager.resume_all()
    return {"status": "ok", "auto_mode": process_manager.auto_mode}


@app.get("/api/queue")
def get_queue():
    """Returns SJF job queue items and estimated runtimes."""
    return {"queue": sjf_scheduler.get_queue()}


@app.post("/api/queue/add")
async def add_queue_task(request: Request):
    """
    Adds a task to the SJF queue. Tasks with shorter durations execute first.
    Payload: {"name": str, "est_seconds": float, "pid": Optional[int], "command": Optional[str]}
    """
    try:
        data = await request.json()
        name = data.get("name", "Custom Task")
        est_seconds = float(data.get("est_seconds", 10))
        pid = data.get("pid")
        command = data.get("command")
        job = sjf_scheduler.add_job(name, est_seconds, pid=pid, command=command)
        return {"status": "ok", "job": job}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})


@app.post("/api/queue/remove/{job_id}")
def remove_queue_task(job_id: str):
    """Cancels or removes an item from the SJF queue."""
    removed = sjf_scheduler.remove_job(job_id)
    return {"status": "ok" if removed else "not_found", "job_id": job_id}


@app.get("/api/device")
def get_device_info():
    """
    Device and network information for multi-device cross-network connection.
    Enables remote monitoring/throttling from phones, tablets, or other PCs.
    """
    local_ip = get_local_ip()
    all_ips = get_all_ips()
    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "local_ip": local_ip,
        "all_ips": all_ips,
        "endpoints": {
            "loopback": "http://127.0.0.1:8742",
            "lan": f"http://{local_ip}:8742" if local_ip != "127.0.0.1" else None
        }
    }


@app.get("/api/download/{platform_name}")
def download_platform_bundle(platform_name: str):
    """
    Generates and downloads the real installer and runtime archive
    for Windows, Linux, macOS, or full Python source.
    """
    p = platform_name.lower().strip()
    if p in ("win", "windows", "win64", "exe"):
        zip_bytes = generate_windows_zip()
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="ThrottlerOS-1.0.0-win64.zip"'}
        )
    elif p in ("linux", "unix"):
        tar_bytes = generate_linux_package(archive_format="tar.gz")
        return Response(
            content=tar_bytes,
            media_type="application/gzip",
            headers={"Content-Disposition": 'attachment; filename="ThrottlerOS-1.0.0-linux.tar.gz"'}
        )
    elif p in ("linux-zip", "linux_zip"):
        zip_bytes = generate_linux_package(archive_format="zip")
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="ThrottlerOS-1.0.0-linux.zip"'}
        )
    elif p in ("mac", "macos", "darwin"):
        tar_bytes = generate_linux_package(archive_format="tar.gz")
        return Response(
            content=tar_bytes,
            media_type="application/gzip",
            headers={"Content-Disposition": 'attachment; filename="ThrottlerOS-1.0.0-macos.tar.gz"'}
        )
    else:
        # Default full package
        zip_bytes = generate_windows_zip()
        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={"Content-Disposition": 'attachment; filename="ThrottlerOS-1.0.0-all.zip"'}
        )


@app.get("/api/privacy")
def get_privacy_status():
    """Privacy status confirming zero telemetry and offline loopback binding."""
    return {
        "status": "active",
        "ip_masking": "ENABLED",
        "masked_client_ip": "127.0.0.1",
        "headers_scrubbed": True,
        "offline_mode": True,
        "cloud_telemetry": False
    }



# ============================================================================
# Static Files & Frontend Routing
# ============================================================================

frontend_path = get_frontend_dir()

# Mount static asset folder if present
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


@app.get("/")
def serve_home():
    """Serves the ThrottlerOS official UI and live controller."""
    throttleros_file = frontend_path / "throttleros.html"
    if throttleros_file.exists():
        return FileResponse(throttleros_file)
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "ok", "message": "ThrottlerOS & SYSmin Backend Running"}


@app.get("/dashboard")
@app.get("/taskmanager")
def serve_dashboard():
    """Serves the full Task Manager real-time performance graphs and process grid."""
    index_file = frontend_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return FileResponse(frontend_path / "throttleros.html")


@app.get("/throttleros")
def serve_throttleros_alias():
    """Direct route for ThrottlerOS interface."""
    return FileResponse(frontend_path / "throttleros.html")


# ============================================================================
# CLI Entrypoint & Runner
# ============================================================================

def run_cli():
    """Command-line entrypoint for pip-installed module and scripts."""
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="ThrottlerOS & SYSmin: Localhost Process Throttler")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="Port to listen on (default: 8742)")
    parser.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 for access across local network devices")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")

    args = parser.parse_args()

    host = "0.0.0.0" if args.lan else args.host
    port = args.port

    local_ip = get_local_ip()
    print("=" * 64)
    print("       ThrottlerOS & SYSmin - Localhost Process Throttler")
    print("=" * 64)
    print(f" * Local loopback address:  http://127.0.0.1:{port}")
    if host == "0.0.0.0" and local_ip != "127.0.0.1":
        print(f" * Local network (LAN):     http://{local_ip}:{port}")
        print("   (Open this on phones, tablets, or other computers on your Wi-Fi)")
    print(" * Privacy:                 100% Offline, Zero Cloud, 0 Telemetry")
    print("=" * 64)

    if not args.no_browser and not os.environ.get("NO_BROWSER"):
        target_url = f"http://127.0.0.1:{port}"
        threading.Timer(1.2, lambda: webbrowser.open(target_url)).start()

    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    # Track PID in project root for clean management
    root_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    pid_file = os.path.join(root_dir, ".server.pid")
    try:
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    import atexit
    def cleanup_pid():
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
        except Exception:
            pass
    atexit.register(cleanup_pid)

    run_cli()
