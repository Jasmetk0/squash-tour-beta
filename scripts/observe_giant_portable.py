"""Portable observer for the pinned giant load harness; no sporting changes."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
import time
from urllib import request
from urllib.parse import urlsplit

def main():
    engine, harness, output = map(lambda s: Path(s).resolve(), sys.argv[1:4])
    args = sys.argv[4:]
    output.mkdir(parents=True, exist_ok=True)
    sys.path[:0] = [str(engine), str(engine / "src"), str(engine / "tests" / "api")]
    os.environ["PYTHONPATH"] = os.pathsep.join(sys.path[:3])
    os.chdir(engine)
    from scripts.process_measurement import machine, memory_kib, peak_rss_kib

    # Only replace the two Linux-only RSS observations in the historical harness.
    # Refuse a changed source instead of silently adapting unknown sporting logic.
    original_source = harness.read_bytes()
    source = original_source.decode("utf-8")
    old = "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss"
    if source.count("import resource\n") != 1 or source.count(old) != 2:
        raise RuntimeError("Pinned harness RSS adapter no longer matches")
    source = source.replace("import resource\n", "from scripts.process_measurement import peak_rss_kib\n").replace(old, "peak_rss_kib()")
    adapted = output / "portable_harness.py"
    adapted.write_text(source, encoding="utf-8", newline="\n")
    (output / "machine.json").write_text(json.dumps({
        **machine(), "harness_sha256": hashlib.sha256(original_source).hexdigest(),
        "adapted_sha256": hashlib.sha256(adapted.read_bytes()).hexdigest(),
        "memory_scope": "main process only; excludes worker children",
        "workers": os.environ.get("BETA_ENGINE_MATCH_WORKERS", "0"),
        "linux_io_available": Path("/proc/self/io").is_file(),
    }, indent=2), encoding="utf-8")

    original = request.urlopen
    started = time.perf_counter()
    sequence = 0
    def counters():
        mem = memory_kib()
        io = {}
        try:
            for line in Path("/proc/self/io").read_text().splitlines():
                k, _, v = line.partition(":")
                if k in ("rchar", "wchar", "read_bytes", "write_bytes"):
                    io[k] = int(v)
        except OSError:
            pass
        return time.process_time(), mem, io

    with (output / "http-requests.jsonl").open("x", encoding="utf-8", buffering=1) as stream:
        def observed(req, *a, **kw):
            nonlocal sequence
            sequence += 1
            before_cpu, before_mem, before_io = counters()
            t0 = time.perf_counter()
            status = error = None
            try:
                response = original(req, *a, **kw)
                status = getattr(response, "status", None)
                return response
            except BaseException as exc:
                status = getattr(exc, "code", None)
                error = type(exc).__name__
                raise
            finally:
                wall = time.perf_counter() - t0
                try:
                    cpu, mem, io = counters()
                    url = req.full_url if hasattr(req, "full_url") else str(req)
                    row = {
                        "request_index": sequence,
                        "endpoint": urlsplit(url).path,
                        "method": req.get_method() if hasattr(req, "get_method") else "GET",
                        "http_status": status, "error_type": error,
                        "wall_to_headers_s": wall,
                        "elapsed_since_wrapper_s": time.perf_counter() - started,
                        "process_cpu_s": cpu - before_cpu,
                        "rss_before_kib": before_mem.get("VmRSS"),
                        "rss_after_kib": mem.get("VmRSS"),
                        "hwm_after_kib": mem.get("VmHWM"),
                        **{k + "_delta": io[k] - before_io[k] if k in io and k in before_io else None
                           for k in ("rchar", "wchar", "read_bytes", "write_bytes")},
                    }
                    stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                except Exception as exc:
                    print("REQUEST_TELEMETRY_ERROR", type(exc).__name__, file=sys.stderr)
        request.urlopen = observed
        try:
            sys.argv = [str(adapted), "--output-dir", str(output), *args]
            runpy.run_path(str(adapted), run_name="__main__")
        finally:
            request.urlopen = original

if __name__ == "__main__":
    main()
