"""Run one diagnostic gate command with a hard wall limit; keep its log; leave no process.

Diagnostic CI steps such as the Nov 27 #1936 "New optimization correctness gate"
used ``pytest ... 2>&1 | tee log``. When pytest printed its summary and then
never exited, the step waited for the six-hour job cap and blocked every
later diagnostic decision. This wrapper is meant only for such bounded
diagnostic steps (it changes no production timeout):

* the command runs in its own process group (POSIX session) with
  ``PYTHONUNBUFFERED=1`` unless set; its combined stdout/stderr is streamed
  line by line to the console and to ``--log``, flushed per line, so the log
  survives any outcome (with ``| tee`` pytest's block-buffered tail stayed in
  the hung process);
* after ``--limit-seconds`` the stacks are dumped with ``py-spy`` when it is
  installed, then the whole group gets SIGTERM, after ``--grace-seconds``
  SIGKILL, and the exit code is 124;
* when the command exits, every process still left in its group (for example
  a worker or helper that kept the pipe open) is reported and killed; a
  successful command that leaves processes behind fails with exit code 125;
* otherwise the command's own exit code is returned, so a failing gate fails
  the step and blocks every later step that is not ``if: always()``.

    python scripts/run_bounded_gate.py --limit-seconds 1800 --log out/new-tests.log -- \\
        python -m pytest -q tests/api/test_slot_worker_faults_http.py

The last log line is a ``BOUNDED_GATE {json}`` record of the outcome.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

TIMEOUT_EXIT = 124
LEFTOVER_EXIT = 125


def _group_pids(pgid):
    """Live (non-zombie) processes of process group ``pgid`` (Linux /proc)."""
    pids = []
    for entry in Path("/proc").iterdir() if Path("/proc").is_dir() else ():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
        except OSError:
            continue
        state, group = fields[0], int(fields[2])
        if group == pgid and state != "Z":
            pids.append(int(entry.name))
    return sorted(pids)


def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def _stop_group(pgid, grace):
    _signal_group(pgid, signal.SIGTERM)
    end = time.monotonic() + grace
    while _group_pids(pgid) and time.monotonic() < end:
        time.sleep(0.1)
    if _group_pids(pgid):
        _signal_group(pgid, signal.SIGKILL)
        end = time.monotonic() + grace
        while _group_pids(pgid) and time.monotonic() < end:
            time.sleep(0.1)


def run(command, *, limit, grace, log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        lock = threading.Lock()

        def emit(text):
            with lock:
                sys.stdout.write(text)
                sys.stdout.flush()
                log.write(text)
                log.flush()

        # Unbuffered Python output: a command that later hangs (or is stopped
        # at the limit) has already written everything it printed to the log.
        environment = {**os.environ, "PYTHONUNBUFFERED": os.environ.get("PYTHONUNBUFFERED", "1")}
        process = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environment,
            start_new_session=True, bufsize=1, text=True, errors="replace",
        )
        pgid = process.pid  # the new session's group id equals its leader's pid

        def pump():
            for line in process.stdout:
                emit(line)

        reader = threading.Thread(target=pump, daemon=True)
        reader.start()
        outcome = {"command": command, "limit_seconds": limit, "pid": process.pid}
        try:
            code = process.wait(timeout=limit)
            outcome["status"] = "exited"
        except subprocess.TimeoutExpired:
            code = None
            outcome["status"] = "limit_exceeded"
            spy = shutil.which("py-spy")
            if spy:
                for pid in _group_pids(pgid):
                    dump = subprocess.run([spy, "dump", "--pid", str(pid)], capture_output=True,
                                          text=True, timeout=60)
                    emit(f"BOUNDED_GATE stacks of pid {pid}:\n{dump.stdout}{dump.stderr}")
        leftovers = _group_pids(pgid)
        outcome["leftover_pids"] = leftovers
        if leftovers:
            _stop_group(pgid, grace)
        if code is None:
            code = process.wait(timeout=grace)
            exit_code = TIMEOUT_EXIT
        elif leftovers and code == 0:
            exit_code = LEFTOVER_EXIT
        else:
            exit_code = code
        reader.join(grace)  # every writer is gone: the pipe reaches EOF
        outcome.update(command_exit=code, exit=exit_code,
                       remaining_pids=_group_pids(pgid), reader_finished=not reader.is_alive(),
                       elapsed_seconds=round(time.monotonic() - started, 3))
        emit("BOUNDED_GATE " + json.dumps(outcome, sort_keys=True) + "\n")
    return exit_code


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit-seconds", type=float, required=True)
    parser.add_argument("--grace-seconds", type=float, default=15.0)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("missing command after --")
    if args.limit_seconds <= 0:
        parser.error("--limit-seconds must be positive")
    return run(command, limit=args.limit_seconds, grace=args.grace_seconds, log_path=args.log)


if __name__ == "__main__":
    raise SystemExit(main())
