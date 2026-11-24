"""Portable process memory and machine description for measurement scripts.

The pre-alpha performance reference is a modest Windows PC (Master 31.41:
Windows, four CPU cores, 8 GB RAM, SSD). The measurement scripts must
therefore run unchanged on Windows as well as on Linux and macOS, without
new dependencies.

* ``memory_kib()`` returns ``{"VmRSS": current, "VmHWM": peak}`` in KiB for
  this process: Linux ``/proc/self/status``; Windows ``WorkingSetSize`` and
  ``PeakWorkingSetSize`` from ``K32GetProcessMemoryInfo``; other systems
  only the peak (``ru_maxrss``). The key names are the historical Linux
  ones so existing reports stay comparable.
* ``peak_rss_kib()`` is the process peak alone.
* ``machine()`` describes the hardware and OS a number was measured on
  (CPU model and logical cores, total physical memory, OS, Python).

Measurement only: nothing here changes engine behaviour or any threshold.
"""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path


def _windows_counters():
    import ctypes
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

    counters = Counters()
    counters.cb = ctypes.sizeof(Counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE  # the pseudo handle -1, not a 32-bit int
    query = kernel32.K32GetProcessMemoryInfo
    query.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    query.restype = wintypes.BOOL
    if not query(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise OSError(ctypes.get_last_error(), "K32GetProcessMemoryInfo failed")
    return counters


def memory_kib():
    """Current and peak resident memory of this process, in KiB."""
    if sys.platform == "win32":
        counters = _windows_counters()
        return {"VmRSS": counters.WorkingSetSize // 1024, "VmHWM": counters.PeakWorkingSetSize // 1024}
    status = Path("/proc/self/status")
    if status.exists():
        values = {}
        for line in status.read_text().splitlines():
            key, _, rest = line.partition(":")
            if key in ("VmRSS", "VmHWM"):
                values[key] = int(rest.split()[0])
        if values:
            return values
    return {"VmHWM": peak_rss_kib()}


def peak_rss_kib():
    """Peak resident memory of this process, in KiB."""
    if sys.platform == "win32":
        return _windows_counters().PeakWorkingSetSize // 1024
    status = Path("/proc/self/status")
    if status.exists():
        # VmHWM belongs to this process's own memory; Linux ru_maxrss also keeps
        # the parent's peak across fork+exec (e.g. a multiprocessing spawn child).
        for line in status.read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    import resource

    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak // 1024 if sys.platform == "darwin" else peak  # macOS reports bytes


def _total_memory_bytes():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Status(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        status = Status()
        status.dwLength = ctypes.sizeof(Status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None
        return status.ullTotalPhys
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def _cpu_model():
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                return str(winreg.QueryValueEx(key, "ProcessorNameString")[0]).strip()
        except OSError:
            return platform.processor() or None
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    return platform.processor() or None


def machine():
    """The hardware and OS a measurement ran on (no user or host identifiers)."""
    total = _total_memory_bytes()
    return {
        "os": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "cpu_model": _cpu_model(),
        "logical_cpus": os.cpu_count(),
        "total_memory_mib": round(total / 2**20) if total else None,
        "python": sys.version.split()[0],
        "memory_metric": "Windows working set" if sys.platform == "win32" else "resident set size",
    }
