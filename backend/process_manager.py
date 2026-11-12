import os
import sys
import platform
import socket
from typing import List, Dict, Set, Optional, Tuple
import psutil

# Platform identification
IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MACOS = sys.platform == "darwin"

# Common system processes that must never be frozen or killed
SYSTEM_WHITELIST_COMMON = {
    "system", "registry", "init", "systemd", "kernel_task", "launchd"
}

WINDOWS_SYSTEM_WHITELIST = {
    "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe",
    "svchost.exe", "explorer.exe", "dwm.exe", "conhost.exe", "taskhostw.exe",
    "sihost.exe", "runtimebroker.exe", "securityhealthservice.exe",
    "msmpeng.exe", "spoolsv.exe", "fontdrvhost.exe", "winlogon.exe"
}

LINUX_SYSTEM_WHITELIST = {
    "kthreadd", "kworker", "ksoftirqd", "migration", "rcu_sched", "rcu_bh",
    "watchdog", "systemd-journald", "systemd-udevd", "systemd-resolved",
    "systemd-logind", "dbus-daemon", "polkitd", "sshd", "cron", "crond",
    "networkmanager", "pipewire", "wireplumber", "pulseaudio", "xorg",
    "xwayland", "wayland", "gdm", "lightdm", "sddm", "dockerd", "containerd"
}

MACOS_SYSTEM_WHITELIST = {
    "windowserver", "syslogd", "logd", "diskarbitrationd", "opendirectoryd",
    "mds", "mds_stores", "coreaudiod", "fseventsd", "powerd"
}


class ProcessManager:
    """
    Cross-platform process monitoring, classification, and non-destructive
    freezing (suspend/resume) controller supporting Windows, Linux, and macOS.
    """

    def __init__(self):
        self.suspended_pids: Set[int] = set()
        self.frozen_meta: Dict[int, dict] = {}
        self.focused_pid: Optional[int] = None
        self.auto_mode: bool = False
        self._my_pid = os.getpid()

        # Prime psutil CPU monitoring
        try:
            psutil.cpu_percent(interval=None)
        except Exception:
            pass

    def get_whitelist(self) -> Set[str]:
        wl = set(SYSTEM_WHITELIST_COMMON)
        if IS_WINDOWS:
            wl.update(WINDOWS_SYSTEM_WHITELIST)
        elif IS_LINUX:
            wl.update(LINUX_SYSTEM_WHITELIST)
        elif IS_MACOS:
            wl.update(MACOS_SYSTEM_WHITELIST)
        return wl

    def is_system_process(self, pid: int, name: str, exe_path: str, username: Optional[str]) -> bool:
        """
        Classifies a process as SYSTEM_APP vs EXTERNAL_APP across Windows, Linux, and macOS.
        """
        name_lower = (name or "").lower()
        exe_lower = (exe_path or "").lower()
        whitelist = self.get_whitelist()

        # PIDs reserved for OS kernel / init
        if pid <= 4:
            return True

        if name_lower in whitelist:
            return True

        # Windows classification
        if IS_WINDOWS:
            windows_prefixes = (
                r"c:\windows\system32",
                r"c:\windows\syswow64",
                r"c:\windows\winsxs",
                r"c:\windows\\",
                r"c:\windows",
            )
            if not exe_lower:
                return True
            if any(exe_lower.startswith(p) for p in windows_prefixes):
                return True
            return False

        # Linux classification
        elif IS_LINUX:
            # Kernel threads typically have no exe or are child of PID 2 (kthreadd)
            if not exe_path:
                return True
            linux_sys_prefixes = (
                "/usr/lib/systemd",
                "/lib/systemd",
                "/usr/sbin",
                "/sbin",
                "/usr/libexec",
            )
            if any(exe_lower.startswith(p) for p in linux_sys_prefixes):
                return True
            # Root or system daemons
            if username in {"root", "systemd-resolve", "systemd-network", "messagebus", "syslog"}:
                # If running from user directory, count as external, otherwise system
                if not exe_lower.startswith(("/home/", "/root/", "/opt/")):
                    return True
            return False

        # macOS classification
        elif IS_MACOS:
            if not exe_path:
                return True
            macos_sys_prefixes = (
                "/system/",
                "/usr/libexec/",
                "/usr/sbin/",
            )
            if any(exe_lower.startswith(p) for p in macos_sys_prefixes):
                return True
            if username in {"_windowserver", "root", "_mdnsresponder", "_coreaudiod"}:
                return True
            return False

        # Generic fallback
        if not exe_path:
            return True
        return False

    def is_protected_process(self, pid: int, name: str) -> bool:
        """
        Determines whether a process is strictly protected from being frozen or terminated.
        """
        if pid <= 4 or pid == self._my_pid:
            return True
        name_lower = (name or "").lower()
        whitelist = self.get_whitelist()
        return name_lower in whitelist

    def scan_processes(self) -> List[dict]:
        """
        Scans all running processes and categorizes them with memory, CPU,
        suspension state, and protection flags.
        """
        procs = []
        my_pid = self._my_pid

        # Re-check live status of suspended PIDs
        active_suspended = set()
        for spid in list(self.suspended_pids):
            try:
                proc = psutil.Process(spid)
                # On Unix, stopped process reports STATUS_STOPPED
                # On Windows, status may still be running while threads are suspended
                if proc.is_running():
                    active_suspended.add(spid)
                else:
                    self.frozen_meta.pop(spid, None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.frozen_meta.pop(spid, None)
        self.suspended_pids = active_suspended

        for p in psutil.process_iter(['pid', 'name', 'memory_info', 'exe', 'username', 'cpu_percent']):
            try:
                info = p.info
                pid = info['pid']
                if pid <= 0 or pid == my_pid:
                    continue

                name = info.get('name') or f"Process-{pid}"
                exe_path = info.get('exe') or ""
                username = info.get('username') or ""

                is_system = self.is_system_process(pid, name, exe_path, username)
                category = "SYSTEM_APP" if is_system else "EXTERNAL_APP"
                is_protected = self.is_protected_process(pid, name)

                mem_info = info.get('memory_info')
                rss_mb = round(mem_info.rss / (1024 * 1024), 1) if mem_info else 0.0

                is_frozen = pid in self.suspended_pids
                status = "SUSPENDED" if is_frozen else "RUNNING"

                # Estimated CPU usage
                if is_frozen:
                    cpu_pct = 0.0
                else:
                    raw_cpu = info.get('cpu_percent') or 0.0
                    cpu_pct = round(raw_cpu, 1)

                procs.append({
                    "pid": pid,
                    "name": name,
                    "exe": exe_path,
                    "user": username,
                    "memory_mb": rss_mb,
                    "cpu_percent": cpu_pct,
                    "status": status,
                    "is_frozen": is_frozen,
                    "is_big": rss_mb > 350 or cpu_pct > 15.0,
                    "category": category,
                    "is_protected": is_protected
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        # Sort: external apps first, then descending by memory usage
        return sorted(procs, key=lambda x: (x["category"] == "SYSTEM_APP", -x["memory_mb"]))

    def freeze_process(self, pid: int) -> Tuple[bool, str, dict]:
        """
        Freezes (suspends) a process non-destructively using OS kernel suspension.
        Memory, open handles, and sockets remain intact in RAM.
        """
        if pid <= 4 or pid == self._my_pid:
            return False, "Cannot freeze critical system process or self", {}

        try:
            proc = psutil.Process(pid)
            name = proc.name() or f"Process-{pid}"

            if self.is_protected_process(pid, name):
                return False, f"Process '{name}' (PID {pid}) is a protected system service", {}

            # Record baseline stats before suspension
            try:
                mem_mb = round(proc.memory_info().rss / (1024 * 1024), 1)
            except Exception:
                mem_mb = 0.0

            try:
                prev_cpu = round(proc.cpu_percent(interval=None) or 2.5, 1)
            except Exception:
                prev_cpu = 2.5

            # Kernel-level suspension (NtSuspendProcess on Win, SIGSTOP on POSIX)
            proc.suspend()

            self.suspended_pids.add(pid)
            self.frozen_meta[pid] = {
                "name": name,
                "memory_mb": mem_mb,
                "saved_cpu": max(prev_cpu, 1.2),
            }

            return True, f"Process '{name}' (PID {pid}) suspended non-destructively", {
                "pid": pid,
                "name": name,
                "memory_mb": mem_mb,
                "status": "SUSPENDED"
            }

        except psutil.NoSuchProcess:
            self.suspended_pids.discard(pid)
            self.frozen_meta.pop(pid, None)
            return False, f"Process with PID {pid} no longer exists", {}
        except psutil.AccessDenied:
            return False, f"Access denied suspending PID {pid}. Administrator or root privileges required.", {}
        except Exception as e:
            return False, f"Failed to suspend PID {pid}: {str(e)}", {}

    def resume_process(self, pid: int) -> Tuple[bool, str, dict]:
        """
        Resumes a suspended process from the exact instruction where it stopped.
        """
        try:
            proc = psutil.Process(pid)
            name = proc.name() or f"Process-{pid}"

            proc.resume()
            self.suspended_pids.discard(pid)
            self.frozen_meta.pop(pid, None)

            if self.focused_pid == pid:
                self.focused_pid = None

            return True, f"Process '{name}' (PID {pid}) resumed", {
                "pid": pid,
                "name": name,
                "status": "RUNNING"
            }

        except psutil.NoSuchProcess:
            self.suspended_pids.discard(pid)
            self.frozen_meta.pop(pid, None)
            return False, f"Process with PID {pid} no longer exists", {}
        except psutil.AccessDenied:
            return False, f"Access denied resuming PID {pid}.", {}
        except Exception as e:
            return False, f"Failed to resume PID {pid}: {str(e)}", {}

    def focus_process(self, pid: int) -> Tuple[bool, str]:
        """
        Isolates execution: resumes target PID and suspends all other non-protected external tasks.
        """
        self.focused_pid = pid
        self.auto_mode = False

        procs = self.scan_processes()
        target_found = False

        for p in procs:
            t_pid = p["pid"]
            if p["is_protected"] or t_pid <= 4:
                continue

            try:
                proc = psutil.Process(t_pid)
                if t_pid == pid:
                    target_found = True
                    proc.resume()
                    self.suspended_pids.discard(t_pid)
                    self.frozen_meta.pop(t_pid, None)
                elif p["category"] == "EXTERNAL_APP":
                    proc.suspend()
                    self.suspended_pids.add(t_pid)
                    self.frozen_meta[t_pid] = {
                        "name": p["name"],
                        "memory_mb": p["memory_mb"],
                        "saved_cpu": max(p.get("cpu_percent", 0.0), 1.5)
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return True, f"Focused CPU resources on PID {pid}"

    def kill_process(self, pid: int) -> Tuple[bool, str]:
        """
        Terminates a process safely with system protection checks.
        """
        if pid <= 4 or pid == self._my_pid:
            return False, "Protected system process cannot be terminated."

        try:
            proc = psutil.Process(pid)
            name = proc.name() or f"Process-{pid}"
            if self.is_protected_process(pid, name):
                return False, f"Protected system process '{name}' cannot be terminated."

            self.suspended_pids.discard(pid)
            self.frozen_meta.pop(pid, None)
            if self.focused_pid == pid:
                self.focused_pid = None

            # First attempt polite termination
            proc.terminate()
            try:
                proc.wait(timeout=0.6)
            except psutil.TimeoutExpired:
                proc.kill()

            return True, f"Process '{name}' (PID {pid}) terminated."

        except psutil.NoSuchProcess:
            return True, f"Process {pid} already stopped."
        except psutil.AccessDenied:
            return False, f"Access denied terminating PID {pid}."
        except Exception as e:
            return False, f"Failed to terminate PID {pid}: {str(e)}"

    def resume_all(self) -> int:
        """
        Resumes all currently suspended processes and clears focus/auto state.
        """
        self.focused_pid = None
        self.auto_mode = False
        resumed_count = 0

        for pid in list(self.suspended_pids):
            try:
                psutil.Process(pid).resume()
                resumed_count += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        self.suspended_pids.clear()
        self.frozen_meta.clear()
        return resumed_count

    def get_system_telemetry(self) -> dict:
        """
        Gathers system-wide telemetry including CPU reclaimed and RAM held by frozen tasks.
        """
        vm = psutil.virtual_memory()
        cpu_cur = round(psutil.cpu_percent(interval=None), 1)

        # Calculate reclaimed CPU and held RAM
        ram_held_mb = 0.0
        cpu_reclaimed = 0.0
        for pid in list(self.suspended_pids):
            meta = self.frozen_meta.get(pid)
            if meta:
                ram_held_mb += meta.get("memory_mb", 0.0)
                cpu_reclaimed += meta.get("saved_cpu", 1.5)
            else:
                try:
                    p = psutil.Process(pid)
                    mem = p.memory_info().rss / (1024 * 1024)
                    ram_held_mb += mem
                    cpu_reclaimed += 2.0
                except Exception:
                    pass

        return {
            "cpu_percent": cpu_cur,
            "ram_percent": round(vm.percent, 1),
            "ram_used_gb": round(vm.used / (1024**3), 2),
            "ram_total_gb": round(vm.total / (1024**3), 2),
            "cpu_cores": psutil.cpu_count(logical=True) or 4,
            "cpu_reclaimed": round(cpu_reclaimed, 1),
            "ram_held_mb": round(ram_held_mb, 1),
            "frozen_count": len(self.suspended_pids),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "machine": platform.machine(),
                "node": platform.node(),
            }
        }

