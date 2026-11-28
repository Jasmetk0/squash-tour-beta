"""Run the original MatchEngine tests on Windows with a memory-only adapter.

The original benchmark is loaded from the selected engine checkout in memory.
No production file or test is edited, and no assertion is disabled.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import sys


def main():
    root = Path.cwd().resolve()
    sys.path[:0] = [str(root), str(root / "src"), str(root / "tests" / "api")]
    if os.environ.get("BETA_ENGINE_NEW_RUN_SAVED_STORAGE") is not None:
        raise RuntimeError("Correctness tests must select their own storage mode")
    if sys.platform == "win32":
        path = root / "scripts" / "benchmark_match_engine.py"
        name = "scripts.benchmark_match_engine"
        if name in sys.modules:
            raise RuntimeError("Benchmark already imported")
        raw = path.read_bytes()
        source = raw.decode("utf-8").replace("\r\n", "\n")
        old = "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss"
        if source.count("import resource\n") != 1 or source.count(old) != 1 or source.count("resource.") != 2:
            raise RuntimeError("Pinned benchmark memory adapter no longer matches")
        source = source.replace("import resource\n", "from scripts.process_measurement import peak_rss_kib\n").replace(old, "peak_rss_kib()")
        package = importlib.import_module("scripts")
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None:
            raise RuntimeError("Could not load benchmark")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            exec(compile(source, str(path), "exec"), module.__dict__)
        except BaseException:
            sys.modules.pop(name, None)
            raise
        setattr(package, "benchmark_match_engine", module)
        print("BENCHMARK_MEMORY_ADAPTER original_sha256="
              + hashlib.sha256(raw).hexdigest() + " adapted_sha256="
              + hashlib.sha256(source.encode("utf-8")).hexdigest(), flush=True)

    import pytest
    return pytest.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
