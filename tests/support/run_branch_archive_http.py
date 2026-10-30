"""A truly fresh installation process with no inherited Python/authority caches."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from tests.api.test_saved_revision_history_api import _free_port, _request


class ColdApiServer:
    def __init__(self, *, database_url, directory):
        self.database_url, self.directory = database_url, Path(directory)
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"

    def __enter__(self):
        root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(root / "src")
        self.log = (self.directory / f"api-{self.port}.log").open("wb")
        code = (
            "import sys,uvicorn; from beta_engine.main import create_app; "
            "uvicorn.run(create_app(database_url=sys.argv[1]),host='127.0.0.1',port=int(sys.argv[2]),log_level='error')"
        )
        self.process = subprocess.Popen(
            [sys.executable, "-c", code, self.database_url, str(self.port)],
            cwd=self.directory,
            env=env,
            stdout=self.log,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                break
            try:
                if _request("GET", self.base_url + "/health")[0] == 200:
                    return self
            except OSError:
                time.sleep(0.05)
        self.__exit__(None, None, None)
        raise AssertionError(
            "Independent target API did not start; inspect its local log"
        )

    def __exit__(self, *_):
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)
            raise AssertionError(
                "Independent target API did not shut down cleanly"
            ) from None
        finally:
            self.log.close()
