"""The bounded diagnostic gate wrapper: exit code, retained log, no process left.

Real subprocesses (no mocks). Each case reproduces one way a ``pytest | tee``
diagnostic step could fail to end: a failing command, a command that never
exits after printing its summary, and a command that exits while a
descendant keeps the output pipe open.
"""

from __future__ import annotations

import json
import os
import sys
import time

import pytest

from scripts import run_bounded_gate as gate

pytestmark = [
    pytest.mark.pr_critical,
    pytest.mark.skipif(not os.path.isdir("/proc"), reason="POSIX process groups and /proc"),
]

PY = sys.executable


def _record(log):
    last = log.read_text().splitlines()[-1]
    assert last.startswith("BOUNDED_GATE ")
    return json.loads(last.removeprefix("BOUNDED_GATE "))


def _alive(pid):
    try:
        with open(f"/proc/{pid}/stat") as stat:
            return stat.read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def test_a_failing_command_keeps_its_exit_code_and_its_log(tmp_path):
    log = tmp_path / "gate.log"
    code = gate.main(["--limit-seconds", "60", "--log", str(log), "--",
                      PY, "-c", "print('FAILED x - assert (2 == 1)'); raise SystemExit(1)"])
    assert code == 1
    assert "FAILED x - assert (2 == 1)" in log.read_text()
    record = _record(log)
    assert record["status"] == "exited" and record["exit"] == 1 and record["remaining_pids"] == []


def test_a_command_that_never_exits_after_its_summary_is_stopped_at_the_limit(tmp_path):
    log, pid_file = tmp_path / "gate.log", tmp_path / "child.pid"
    script = (
        "import subprocess, sys, time\n"
        f"child = subprocess.Popen(['sleep', '600'])\n"  # a descendant holding the pipe
        f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
        "print('1 failed in 3.21s', flush=True)\n"
        "time.sleep(600)\n"                              # the summary was printed, no exit
    )
    started = time.monotonic()
    code = gate.main(["--limit-seconds", "3", "--grace-seconds", "5", "--log", str(log), "--",
                      PY, "-c", script])
    assert code == gate.TIMEOUT_EXIT
    assert time.monotonic() - started < 30
    assert "1 failed in 3.21s" in log.read_text()
    record = _record(log)
    assert record["status"] == "limit_exceeded" and record["remaining_pids"] == []
    assert record["reader_finished"]
    assert not _alive(int(pid_file.read_text()))


def test_a_successful_command_that_leaves_a_process_behind_fails_and_is_cleaned(tmp_path):
    log, pid_file = tmp_path / "gate.log", tmp_path / "child.pid"
    script = (
        "import subprocess\n"
        "child = subprocess.Popen(['sleep', '600'])\n"
        f"open({str(pid_file)!r}, 'w').write(str(child.pid))\n"
        "print('9 passed', flush=True)\n"
    )
    started = time.monotonic()
    code = gate.main(["--limit-seconds", "60", "--grace-seconds", "5", "--log", str(log), "--",
                      PY, "-c", script])
    assert code == gate.LEFTOVER_EXIT
    assert time.monotonic() - started < 30  # ``| tee`` would wait 600 s for the descendant
    record = _record(log)
    assert record["command_exit"] == 0 and record["leftover_pids"] and record["remaining_pids"] == []
    assert not _alive(int(pid_file.read_text()))
