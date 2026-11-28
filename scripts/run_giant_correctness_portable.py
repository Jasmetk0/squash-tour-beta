"""Run unchanged correctness tests with a Windows-only benchmark RSS adapter.

The adapter is installed in the test process and in fresh spawn/subprocess
interpreters via a temporary sitecustomize directory. No tracked candidate
file, production module or assertion is modified.
"""
from __future__ import annotations

import hashlib
import importlib.abc
import importlib.util
import os
from pathlib import Path
import sys
import tempfile

NAME = "scripts.benchmark_match_engine"
ROOT_ENV = "GIANT_DIAGNOSTIC_BENCH_ROOT"


class BenchmarkLoader(importlib.abc.Loader):
    def __init__(self, path, source):
        self.path, self.source = path, source

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        exec(compile(self.source, str(self.path), "exec"), module.__dict__)


class BenchmarkFinder(importlib.abc.MetaPathFinder):
    def __init__(self, path, source):
        self.path, self.source = path, source

    def find_spec(self, fullname, path=None, target=None):
        if fullname == NAME:
            return importlib.util.spec_from_file_location(
                fullname, self.path, loader=BenchmarkLoader(self.path, self.source)
            )
        return None


def install_benchmark_adapter(root):
    root = Path(root).resolve()
    path = root / "scripts" / "benchmark_match_engine.py"
    if NAME in sys.modules:
        raise RuntimeError("Benchmark already imported")
    raw = path.read_bytes()
    source = raw.decode("utf-8").replace("\r\n", "\n")
    old = "resource.getrusage(resource.RUSAGE_SELF).ru_maxrss"
    if source.count("import resource\n") != 1 or source.count(old) != 1 or source.count("resource.") != 2:
        raise RuntimeError("Pinned benchmark memory adapter no longer matches")
    source = source.replace("import resource\n", "from scripts.process_measurement import peak_rss_kib\n").replace(old, "peak_rss_kib()")
    sys.meta_path.insert(0, BenchmarkFinder(path, source))
    print("BENCHMARK_MEMORY_ADAPTER original_sha256="
          + hashlib.sha256(raw).hexdigest() + " adapted_sha256="
          + hashlib.sha256(source.encode("utf-8")).hexdigest(), flush=True)


def install_replay_cleanup(root):
    """Only the independent replay CLI needs to unlink a temporary DB immediately.

    Mirror the existing profile_native_week_ab.measurement_server teardown:
    stop the HTTP thread, verify it stopped, dispose the test-owned SQLAlchemy
    pool. Collect unreachable raw sqlite backup handles before Windows unlinks
    the temporary DB. Never suppress a cleanup error or change replay evidence.
    """
    if Path(sys.argv[0]).name != "verify_slot_worker_parity.py" or sys.argv[1:2] != ["replay"]:
        return
    name = "tests.api.test_saved_revision_history_api"
    replay_path = Path(root).resolve() / "tests" / "api" / "test_saved_revision_history_api.py"
    raw = replay_path.read_bytes()
    source = raw.decode("utf-8").replace("\r\n", "\n")
    old = "        self.thread.join(timeout=10)\n"
    if source.count(old) != 1 or name in sys.modules:
        raise RuntimeError("Pinned replay cleanup adapter no longer matches")
    source = source.replace(old, old +
        "        if self.thread.is_alive():\n"
        "            raise RuntimeError('Replay API server did not stop')\n"
        "        runtime = getattr(self.app.state, 'runtime', None)\n"
        "        if runtime is not None:\n"
        "            runtime.repository._engine.dispose()\n"
        "        import gc\n"
        "        gc.collect()\n"
        "        print('REPLAY_SQLITE_POOL_DISPOSED', flush=True)\n")
    class ReplayFinder(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == name:
                return importlib.util.spec_from_file_location(
                    fullname, replay_path, loader=BenchmarkLoader(replay_path, source)
                )
            return None
    sys.meta_path.insert(0, ReplayFinder())
    print("REPLAY_CLEANUP_ADAPTER original_sha256="
          + hashlib.sha256(raw).hexdigest() + " adapted_sha256="
          + hashlib.sha256(source.encode("utf-8")).hexdigest(), flush=True)


def main():
    root = Path.cwd().resolve()
    sys.path[:0] = [str(root), str(root / "src"), str(root / "tests" / "api")]
    if os.environ.get("BETA_ENGINE_NEW_RUN_SAVED_STORAGE") is not None:
        raise RuntimeError("Correctness tests must select their own storage mode")
    import pytest
    if sys.platform != "win32":
        return pytest.main(sys.argv[1:])

    # Spawned tests import crash_worker/slow_worker from the test modules,
    # which in turn import the benchmark. A parent-only sys.modules entry
    # does not survive spawn. Use a narrowly scoped import hook instead.
    with tempfile.TemporaryDirectory(prefix="giant-portable-import-") as temp:
        startup = Path(temp) / "sitecustomize.py"
        startup.write_text(
            "import os\n"
            "from run_giant_correctness_portable import install_benchmark_adapter, install_replay_cleanup\n"
            "install_benchmark_adapter(os.environ['GIANT_DIAGNOSTIC_BENCH_ROOT'])\n"
            "install_replay_cleanup(os.environ['GIANT_DIAGNOSTIC_BENCH_ROOT'])\n",
            encoding="utf-8",
        )
        previous = {key: os.environ.get(key) for key in ("PYTHONPATH", ROOT_ENV)}
        os.environ[ROOT_ENV] = str(root)
        entries = [temp, str(Path(__file__).resolve().parent), str(root), str(root / "src"),
                   str(root / "tests" / "api")]
        if previous["PYTHONPATH"]:
            entries.append(previous["PYTHONPATH"])
        os.environ["PYTHONPATH"] = os.pathsep.join(entries)
        install_benchmark_adapter(root)
        try:
            # Exercise the real fresh-interpreter import before running the tests.
            import subprocess
            subprocess.run([sys.executable, "-c",
                            "from scripts import benchmark_match_engine as b; "
                            "assert b.__spec__.loader.__class__.__name__ == 'BenchmarkLoader'; "
                            "assert b.peak_rss_kib() > 0"],
                           check=True, cwd=root, timeout=30)
            return pytest.main(sys.argv[1:])
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    raise SystemExit(main())
