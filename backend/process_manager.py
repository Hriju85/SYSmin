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

# Common system and runtime processes that must never be frozen or killed
SYSTEM_WHITELIST_COMMON = {
    "system", "registry", "init", "systemd", "kernel_task", "launchd",
    "python", "python3", "python.exe", "python3.exe"
}

# Web browsers - must never be frozen or killed (they run the web dashboard!)
BROWSER_WHITELIST = {
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe",
    "vivaldi.exe", "arc.exe", "chromium.exe", "chrome", "msedge",
    "firefox", "brave", "opera", "vivaldi", "arc", "chromium",
    "safari", "webkit"
}

# Windows system, desktop manager, input, audio, and shell processes
WINDOWS_SYSTEM_WHITELIST = {
    "smss.exe", "csrss.exe", "wininit.exe", "services.exe", "lsass.exe",
    "svchost.exe", "explorer.exe", "dwm.exe", "conhost.exe", "taskhostw.exe",
    "sihost.exe", "runtimebroker.exe", "securityhealthservice.exe",
    "msmpeng.exe", "spoolsv.exe", "fontdrvhost.exe", "winlogon.exe",
    "ctfmon.exe", "shellexperiencehost.exe", "startmenuexperiencehost.exe",
    "searchhost.exe", "audiodg.exe", "windowsterminal.exe", "cmd.exe",
    "powershell.exe", "pwsh.exe", "code.exe"
}

# Linux system, desktop compositors, audio, and shell daemons
LINUX_SYSTEM_WHITELIST = {
    "kthreadd", "kworker", "ksoftirqd", "migration", "rcu_sched", "rcu_bh",
    "watchdog", "systemd-journald", "systemd-udevd", "systemd-resolved",
    "systemd-logind", "dbus-daemon", "polkitd", "sshd", "cron", "crond",
    "networkmanager", "pipewire", "wireplumber", "pulseaudio", "xorg",
    "xwayland", "wayland", "gdm", "lightdm", "sddm", "dockerd", "containerd",
    "gnome-shell", "kwin", "kwin_wayland", "kwin_x11", "mutter", "xfwm4",
    "mate-session", "plasmashell", "bash", "zsh", "sh", "konsole",
    "gnome-terminal", "alacritty", "kitty", "code"
}

# macOS system, UI server, and window services
MACOS_SYSTEM_WHITELIST = {
    "windowserver", "syslogd", "logd", "diskarbitrationd", "opendirectoryd",
    "mds", "mds_stores", "coreaudiod", "fseventsd", "powerd", "finder",
    "dock", "terminal", "iterm2", "code"
}


class ProcessManager:
    """
    Cross-platform process monitoring, classification, and non-destructive
    freezing (suspend/resume) controller supporting Windows, Linux, and macOS.
    """

    def __init__(self):
        self.suspended_pids: Set[int] = set()
        self.throttled_pids: Set[int] = set()
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
        wl.update(BROWSER_WHITELIST)
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
                is_throttled = pid in self.throttled_pids
                is_focused = pid == self.focused_pid

                if is_frozen:
                    status = "SUSPENDED"
                elif is_focused:
                    status = "FOCUSED"
                elif is_throttled:
                    status = "THROTTLED"
                else:
                    status = "RUNNING"

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
                    "is_throttled": is_throttled,
                    "is_focused": is_focused,
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

    @staticmethod
    def _set_process_priority(proc: psutil.Process, level: str) -> bool:
        """
        Safely configures CPU scheduling priority across Windows, Linux, and macOS.
        level: 'high', 'below_normal', 'low', or 'normal'
        """
        try:
            if IS_WINDOWS:
                priority_map = {
                    "high": getattr(psutil, "HIGH_PRIORITY_CLASS", 0x00000080),
                    "above_normal": getattr(psutil, "ABOVE_NORMAL_PRIORITY_CLASS", 0x00008000),
                    "normal": getattr(psutil, "NORMAL_PRIORITY_CLASS", 0x00000020),
                    "below_normal": getattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS", 0x00004000),
                    "low": getattr(psutil, "IDLE_PRIORITY_CLASS", 0x00000040),
                }
                val = priority_map.get(level, getattr(psutil, "NORMAL_PRIORITY_CLASS", 0x00000020))
                proc.nice(val)
                return True
            else:
                # POSIX nice levels (-20 to 19, 0 is default)
                if level == "high":
                    try:
                        proc.nice(-5)
                    except (psutil.AccessDenied, PermissionError):
                        try:
                            proc.nice(0)
                        except Exception:
                            pass
                elif level in ("below_normal", "low"):
                    try:
                        proc.nice(10)
                    except Exception:
                        pass
                else:
                    try:
                        proc.nice(0)
                    except Exception:
                        pass
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
            return False
        except Exception:
            return False

    def _restore_priorities(self):
        """
        Restores focused and throttled processes back to normal CPU scheduling priority.
        """
        if self.focused_pid:
            try:
                proc = psutil.Process(self.focused_pid)
                self._set_process_priority(proc, "normal")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            self.focused_pid = None

        for t_pid in list(self.throttled_pids):
            try:
                proc = psutil.Process(t_pid)
                self._set_process_priority(proc, "normal")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        self.throttled_pids.clear()

    def focus_process(self, pid: int) -> Tuple[bool, str]:
        """
        Prioritizes CPU execution for the targeted process without freezing the OS.
        Elevates target PID to HIGH priority and throttles heavy background tasks
        to BELOW_NORMAL priority. Never suspends browsers, compositors, or input threads.
        Clicking Focus on an already-focused PID cleanly toggles/unfocuses it.
        """
        # Toggle: if already focused on this PID, unfocus and restore normal priorities
        if self.focused_pid == pid:
            self.resume_all()
            return True, f"Unfocused PID {pid}. Restored all background tasks to normal priority."

        if pid <= 4 or pid == self._my_pid:
            return False, "Cannot focus system-critical process or self."

        try:
            target_proc = psutil.Process(pid)
            target_name = target_proc.name() or f"Process-{pid}"
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False, f"Process with PID {pid} is no longer accessible."

        if self.is_protected_process(pid, target_name):
            return False, f"Process '{target_name}' (PID {pid}) is a protected system service."

        # Reset any prior focus or throttle state
        self._restore_priorities()

        # If target process was suspended, resume it
        if pid in self.suspended_pids:
            self.resume_process(pid)

        # Elevate target process CPU priority
        self._set_process_priority(target_proc, "high")
        self.focused_pid = pid
        self.auto_mode = False

        # Throttle heavy background external tasks
        procs = self.scan_processes()
        throttled_count = 0

        for p in procs:
            t_pid = p["pid"]
            if t_pid == pid or p["is_protected"] or t_pid <= 4 or t_pid == self._my_pid:
                continue

            # Throttle only heavy non-protected external tasks
            if p["category"] == "EXTERNAL_APP" and p["is_big"]:
                try:
                    bg_proc = psutil.Process(t_pid)
                    if self._set_process_priority(bg_proc, "below_normal"):
                        self.throttled_pids.add(t_pid)
                        throttled_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

        return True, f"Focused on '{target_name}' (PID {pid}). Prioritized CPU resources and throttled {throttled_count} heavy background tasks."

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
        Resumes all currently suspended processes, restores throttled priorities,
        and clears focus/auto state.
        """
        self.focused_pid = None
        self.auto_mode = False
        self._restore_priorities()

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

