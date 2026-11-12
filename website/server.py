#!/usr/bin/env python3
"""
ThrottlerOS Dedicated Website & Process Control Backend
Serves the ThrottlerOS official web interface and provides real-time
process monitoring, non-destructive freezing, SJF queue automation,
and multi-device downloadable packages.
"""

import os
import sys
import argparse
import socket
import platform
import multiprocessing
import threading
import webbrowser
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Response, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Ensure local directory is in path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from process_manager import ProcessManager
from sjf_scheduler import SJFScheduler
import packager

app = FastAPI(
    title="ThrottlerOS",
    description="Localhost Process Throttler & Priority Scheduler",
    version="1.0.0"
)

# Core Services
process_manager = ProcessManager()
sjf_scheduler = SJFScheduler(process_manager=process_manager)


# IP Masking & Local Privacy Middleware
class IPMaskingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if "client" in request.scope and request.scope["client"]:
            port = request.scope["client"][1] if len(request.scope["client"]) > 1 else 0
            request.scope["client"] = ("127.0.0.1", port)

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
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response


app.add_middleware(IPMaskingMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Multi-Device IP discovery
def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.254.254.254', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def get_all_ips() -> List[str]:
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


# ============================================================================
# API Routes
# ============================================================================

@app.get("/api/tasks")
def get_tasks():
    """
    Returns running processes separated into external apps and system background,
    with real-time stats for CPU reclaimed, RAM held intact, and frozen count.
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
    """Freezes (suspends) a process non-destructively."""
    success, msg, details = process_manager.freeze_process(pid)
    if not success:
        return JSONResponse(status_code=400, content={"status": "error", "message": msg})
    return {"status": "ok", "message": msg, "details": details}


@app.post("/api/resume/{pid}")
def resume_task(pid: int):
    """Resumes a suspended process from the exact instruction where it was stopped."""
    success, msg, details = process_manager.resume_process(pid)
    if not success:
        return JSONResponse(status_code=400, content={"status": "error", "message": msg})
    return {"status": "ok", "message": msg, "details": details}


@app.post("/api/focus/{pid}")
def focus_task(pid: int):
    """Isolates CPU to target process and suspends other background tasks."""
    success, msg = process_manager.focus_process(pid)
    return {"status": "ok" if success else "error", "message": msg, "focused": pid}


@app.post("/api/kill/{pid}")
def kill_task(pid: int):
    """Terminates a process with safety checks."""
    success, msg = process_manager.kill_process(pid)
    if not success:
        return JSONResponse(status_code=403, content={"status": "error", "message": msg})
    return {"status": "terminated", "message": msg, "pid": pid}


@app.post("/api/resume-all")
def resume_all():
    """Resumes all currently suspended processes."""
    count = process_manager.resume_all()
    return {"status": "ok", "resumed_count": count}


@app.post("/api/toggle-auto")
def toggle_auto():
    """Toggles automated Shortest-Job-First scheduling mode."""
    process_manager.auto_mode = not process_manager.auto_mode
    process_manager.focused_pid = None
    if not process_manager.auto_mode:
        process_manager.resume_all()
    return {"status": "ok", "auto_mode": process_manager.auto_mode}


@app.get("/api/queue")
def get_queue():
    """Returns SJF queue items."""
    return {"queue": sjf_scheduler.get_queue()}


@app.post("/api/queue/add")
async def add_queue_task(request: Request):
    """Adds a task to the SJF queue sorted shortest-first."""
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
    """Removes an item from the SJF queue."""
    removed = sjf_scheduler.remove_job(job_id)
    return {"status": "ok" if removed else "not_found", "job_id": job_id}


@app.get("/api/device")
def get_device_info():
    """Returns host platform, hostname, local IP, and multi-device LAN URLs."""
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
    """Serves ready-to-run packages for Windows, Linux, macOS, or full Python module."""
    downloads_dir = BASE_DIR / "downloads"
    p = platform_name.lower().strip()

    if p in ("win", "windows", "win64", "exe"):
        target_file = downloads_dir / "ThrottlerOS-1.0.0-win64.zip"
        if not target_file.exists():
            packager.build_standalone_packages(BASE_DIR)
        return FileResponse(
            path=str(target_file),
            media_type="application/zip",
            filename="ThrottlerOS-1.0.0-win64.zip"
        )
    elif p in ("linux", "unix"):
        target_file = downloads_dir / "ThrottlerOS-1.0.0-linux.tar.gz"
        if not target_file.exists():
            packager.build_standalone_packages(BASE_DIR)
        return FileResponse(
            path=str(target_file),
            media_type="application/gzip",
            filename="ThrottlerOS-1.0.0-linux.tar.gz"
        )
    elif p in ("mac", "macos", "darwin"):
        target_file = downloads_dir / "ThrottlerOS-1.0.0-macos.tar.gz"
        if not target_file.exists():
            packager.build_standalone_packages(BASE_DIR)
        return FileResponse(
            path=str(target_file),
            media_type="application/gzip",
            filename="ThrottlerOS-1.0.0-macos.tar.gz"
        )
    else:
        target_file = downloads_dir / "ThrottlerOS-1.0.0-win64.zip"
        if not target_file.exists():
            packager.build_standalone_packages(BASE_DIR)
        return FileResponse(
            path=str(target_file),
            media_type="application/zip",
            filename="ThrottlerOS-1.0.0-all.zip"
        )


@app.get("/api/privacy")
def get_privacy_status():
    """Privacy confirmation endpoint."""
    return {
        "status": "active",
        "ip_masking": "ENABLED",
        "masked_client_ip": "127.0.0.1",
        "offline_mode": True,
        "telemetry": False
    }


# ============================================================================
# Website Serving
# ============================================================================

index_file = BASE_DIR / "index.html"

# Serve static downloads folder if requested directly
downloads_path = BASE_DIR / "downloads"
if downloads_path.exists():
    app.mount("/downloads", StaticFiles(directory=str(downloads_path)), name="downloads")


@app.get("/")
def serve_website():
    """Serves the ThrottlerOS official website."""
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"status": "ok", "message": "ThrottlerOS backend running"}


# ============================================================================
# CLI Entrypoint
# ============================================================================

def run_server():
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="ThrottlerOS: Localhost Process Throttler & Priority Scheduler")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8742)), help="Port to listen on (default: 8742)")
    parser.add_argument("--lan", action="store_true", help="Bind to 0.0.0.0 for access across local network devices")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open web browser")

    args = parser.parse_args()

    host = "0.0.0.0" if args.lan else args.host
    port = args.port
    local_ip = get_local_ip()

    print("=" * 64)
    print("       ThrottlerOS - Localhost Process Throttler")
    print("=" * 64)
    print(f" * Localhost URL:      http://127.0.0.1:{port}")
    if host == "0.0.0.0" and local_ip != "127.0.0.1":
        print(f" * LAN Access (Wi-Fi): http://{local_ip}:{port}")
        print("   (Open this URL on phones, tablets, or other PCs on your network)")
    print(" * Privacy:            100% Offline, Zero Cloud Telemetry")
    print("=" * 64)

    if not args.no_browser and not os.environ.get("NO_BROWSER"):
        target_url = f"http://127.0.0.1:{port}"
        threading.Timer(1.2, lambda: webbrowser.open(target_url)).start()

    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    run_server()
