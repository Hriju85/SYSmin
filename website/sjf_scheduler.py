import time
import threading
import uuid
from typing import List, Dict, Optional, Any


class SJFScheduler:
    """
    Shortest-Job-First (SJF) Task Scheduler and Queue Engine.
    Minimizes average wait time by executing or prioritizing tasks
    with the shortest estimated run duration first.
    """

    def __init__(self, process_manager=None):
        self.process_manager = process_manager
        self.lock = threading.Lock()
        self.jobs: List[Dict[str, Any]] = []
        self._seed_default_jobs()
        self._running = True
        self._worker_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._worker_thread.start()

    def _seed_default_jobs(self):
        """Seeds initial illustrative SJF jobs matching ThrottlerOS UI specs."""
        self.jobs = [
            {
                "id": "job-1",
                "name": "unzip logs",
                "est_seconds": 4,
                "status": "running",
                "progress": 45,
                "created_at": time.time(),
                "started_at": time.time(),
            },
            {
                "id": "job-2",
                "name": "reindex photos",
                "est_seconds": 38,
                "status": "queued",
                "progress": 0,
                "created_at": time.time(),
                "started_at": None,
            },
            {
                "id": "job-3",
                "name": "export video",
                "est_seconds": 220,
                "status": "queued",
                "progress": 0,
                "created_at": time.time(),
                "started_at": None,
            }
        ]

    def add_job(self, name: str, est_seconds: float, pid: Optional[int] = None, command: Optional[str] = None) -> Dict[str, Any]:
        """
        Adds a new job to the queue and re-sorts by shortest estimated duration.
        """
        with self.lock:
            job = {
                "id": f"job-{uuid.uuid4().hex[:6]}",
                "name": name,
                "est_seconds": max(1.0, float(est_seconds)),
                "pid": pid,
                "command": command,
                "status": "queued",
                "progress": 0,
                "created_at": time.time(),
                "started_at": None
            }
            self.jobs.append(job)
            self._sort_queue_locked()
            return job

    def remove_job(self, job_id: str) -> bool:
        """Removes or cancels a job from the queue."""
        with self.lock:
            initial_len = len(self.jobs)
            self.jobs = [j for j in self.jobs if j["id"] != job_id]
            return len(self.jobs) < initial_len

    def get_queue(self) -> List[Dict[str, Any]]:
        """Returns the current list of jobs with human-friendly formatted duration."""
        with self.lock:
            result = []
            for j in self.jobs:
                item = dict(j)
                sec = int(item["est_seconds"])
                if sec < 60:
                    item["formatted_duration"] = f"{sec} s"
                else:
                    mins = sec // 60
                    rem_sec = sec % 60
                    item["formatted_duration"] = f"{mins} min {rem_sec} s" if rem_sec else f"{mins} min"
                result.append(item)
            return result

    def _sort_queue_locked(self):
        """
        SJF Algorithm: Sorts non-running queued jobs shortest-first.
        Running jobs remain at the top.
        """
        running = [j for j in self.jobs if j["status"] == "running"]
        queued = [j for j in self.jobs if j["status"] == "queued"]
        completed = [j for j in self.jobs if j["status"] == "completed"]

        queued.sort(key=lambda j: j["est_seconds"])
        self.jobs = running + queued + completed

    def _scheduler_loop(self):
        """
        Continuous background thread that drives SJF queue execution and
        coordinates with ProcessManager when auto_mode is enabled.
        """
        while self._running:
            time.sleep(1.0)

            # 1. Update queue progress
            with self.lock:
                running_jobs = [j for j in self.jobs if j["status"] == "running"]
                if not running_jobs:
                    queued_jobs = [j for j in self.jobs if j["status"] == "queued"]
                    if queued_jobs:
                        # Pick shortest job to run
                        queued_jobs.sort(key=lambda j: j["est_seconds"])
                        next_job = queued_jobs[0]
                        next_job["status"] = "running"
                        next_job["started_at"] = time.time()
                else:
                    active = running_jobs[0]
                    elapsed = time.time() - (active.get("started_at") or time.time())
                    total = active["est_seconds"]
                    active["progress"] = min(100, int((elapsed / max(total, 0.1)) * 100))

                    if elapsed >= total:
                        active["status"] = "completed"
                        active["progress"] = 100
                        # Auto-clean completed after a short delay
                        self.jobs = [j for j in self.jobs if j["status"] != "completed"]

                        # Start next queued job
                        queued_jobs = [j for j in self.jobs if j["status"] == "queued"]
                        if queued_jobs:
                            queued_jobs.sort(key=lambda j: j["est_seconds"])
                            next_job = queued_jobs[0]
                            next_job["status"] = "running"
                            next_job["started_at"] = time.time()

            # 2. Automated OS Task Throttling if auto_mode is ON
            if self.process_manager and self.process_manager.auto_mode and self.process_manager.focused_pid is None:
                try:
                    procs = self.process_manager.scan_processes()
                    heavy_tasks = [p for p in procs if p["is_big"] and not p["is_protected"]]
                    if heavy_tasks:
                        # In auto SJF, execute smallest heavy task first, suspend remainder
                        heavy_tasks.sort(key=lambda x: x["memory_mb"])
                        favored_pid = heavy_tasks[0]["pid"]

                        for task in heavy_tasks:
                            t_pid = task["pid"]
                            if t_pid == favored_pid:
                                if t_pid in self.process_manager.suspended_pids:
                                    self.process_manager.resume_process(t_pid)
                            else:
                                if t_pid not in self.process_manager.suspended_pids:
                                    self.process_manager.freeze_process(t_pid)
                except Exception:
                    pass

