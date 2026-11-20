"""Measure the first Tour read after a restart on a retained Saved fixture.

Usage (one cold measurement per new process):

    python scripts/measure_cold_tour_read.py FIXTURE.sqlite FIXTURE.json OUT.json

``FIXTURE.json`` is the metadata written by the giant load runner next to its
``before-restart.sqlite`` (``sha256`` and ``expected_inspection``). The fixture
is copied to a fresh temporary directory first; the original file is never
opened for writing. The script starts the production app on that copy, issues
exactly one ``GET /admin/runs/run/branches/branch/calendar-tour`` without the
120-second client deadline (so a slow read is measured instead of aborted) and
compares the complete JSON response with ``expected_inspection``.
It reports wall time, response size, exact equality and the process peak RSS.
Set ``COLD_TOUR_READ_CHECKOUT`` to measure another checkout (for example the
base commit) with this same script.
"""

from __future__ import annotations

import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib import request

ROOT = Path(os.environ.get("COLD_TOUR_READ_CHECKOUT") or Path(__file__).resolve().parents[1]).resolve()
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

TOUR_PATH = "/admin/runs/run/branches/branch/calendar-tour"


def main(argv=None) -> int:
    fixture, metadata_path, output = map(Path, (argv or sys.argv[1:])[:3])
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="cold-tour-read-") as directory:
        database = Path(directory) / "fixture.sqlite"
        shutil.copyfile(fixture, database)
        digest = hashlib.sha256(database.read_bytes()).hexdigest()
        if digest != metadata["sha256"]:
            raise SystemExit(f"fixture digest {digest} differs from its metadata")
        from tests.api.test_saved_revision_history_api import ApiServer

        with ApiServer(database_url=f"sqlite:///{database}") as server:
            started = time.perf_counter()
            with request.urlopen(server.base_url + TOUR_PATH, timeout=3600) as response:
                status, raw = response.status, response.read()
            seconds = time.perf_counter() - started
    view = json.loads(raw)
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    result = {
        "repository_head": head,
        "fixture_sha256": digest,
        "status": status,
        "seconds": round(seconds, 3),
        "under_120_seconds": seconds < 120,
        "response_bytes": len(raw),
        "exact_expected_inspection": view == metadata["expected_inspection"],
        "saved_head_revision_id": view.get("saved_head_revision_id"),
        "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
        "python": sys.version.split()[0],
    }
    output.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if status == 200 and result["exact_expected_inspection"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
