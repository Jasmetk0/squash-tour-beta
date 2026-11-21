#!/usr/bin/env python3
"""One cold first Tour read after a restart, on Linux or Windows (diagnostic).

    python scripts/bounded_cold_read.py CHECKOUT FIXTURE.sqlite FIXTURE.json OUT.json

The fixture is copied to a fresh temporary directory (the original is never
opened for writing) and its SHA-256 is checked against ``FIXTURE.json``. The
production app of CHECKOUT is started in this new process (real uvicorn HTTP,
real SQLite) and exactly one ``GET .../calendar-tour`` is issued without the
120-second client deadline, so a slow read is measured instead of aborted. The
complete JSON response is compared with ``expected_inspection``. Reports wall
time, whether it is under 120 s, exact equality, the Saved revision count and
the process peak resident memory (Linux ``ru_maxrss``, Windows
``PeakWorkingSetSize``) sampled before and after the read.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import request


def peak_mib():
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]

        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        process = ctypes.windll.kernel32.GetCurrentProcess()
        ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb)
        return counters.PeakWorkingSetSize / 2**20
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def main(argv):
    checkout, fixture, metadata_path, output = (Path(a) for a in argv[:4])
    checkout = checkout.resolve()
    sys.path[:0] = [str(checkout / "src"), str(checkout)]
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="bounded-cold-read-", ignore_cleanup_errors=True) as directory:
        database = Path(directory) / "fixture.sqlite"
        shutil.copyfile(fixture, database)
        digest = hashlib.sha256(database.read_bytes()).hexdigest()
        if digest != metadata["sha256"]:
            raise SystemExit(f"fixture digest {digest} differs from its metadata")
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
            revisions = connection.execute(
                "SELECT COUNT(*) FROM branch_saved_revisions WHERE run_id='run'").fetchone()[0]
        from tests.api.test_saved_revision_history_api import ApiServer

        before = peak_mib()
        with ApiServer(database_url=f"sqlite:///{database}") as server:
            started = time.perf_counter()
            with request.urlopen(server.base_url + "/admin/runs/run/branches/branch/calendar-tour",
                                 timeout=7200) as response:
                status, raw = response.status, response.read()
            seconds = time.perf_counter() - started
        after = peak_mib()
    view = json.loads(raw)
    head = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    result = {
        "checkout_head": head, "fixture_sha256": digest, "revisions": revisions,
        "status": status, "seconds": round(seconds, 2), "under_120_seconds": seconds < 120,
        "exact_expected_inspection": view == metadata["expected_inspection"],
        "peak_rss_mib_before_read": round(before, 1), "peak_rss_mib": round(after, 1),
        "python": sys.version.split()[0], "platform": platform.platform(),
    }
    output.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if status == 200 and result["exact_expected_inspection"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
