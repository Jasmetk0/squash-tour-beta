"""Optional SQLite fetch accounting for the native simulation profiling CLIs."""

import sqlite3
from collections import Counter
from threading import Lock

from sqlalchemy import event


def measure_fetches(engine):
    """Count fetched text/blob UTF-8 bytes without changing or retaining results.

    Scalars and wire/protocol overhead are excluded. Timing includes the same
    instrumentation in both compared runs. No query is added to production work.
    """
    totals = Counter()
    lock = Lock()

    def record(rows):
        count = 0
        for row in rows:
            for value in row:
                if isinstance(value, str):
                    count += len(value.encode("utf-8"))
                elif isinstance(value, bytes):
                    count += len(value)
        with lock:
            totals["rows"] += len(rows)
            totals["text_blob_bytes"] += count

    class Cursor(sqlite3.Cursor):
        def fetchone(self):
            row = super().fetchone()
            if row is not None:
                record([row])
            return row

        def fetchmany(self, size=None):
            rows = super().fetchmany() if size is None else super().fetchmany(size)
            record(rows)
            return rows

        def fetchall(self):
            rows = super().fetchall()
            record(rows)
            return rows

    class Connection(sqlite3.Connection):
        def cursor(self, factory=Cursor):
            return super().cursor(factory)

    def connect(dialect, record, args, kwargs):
        kwargs["factory"] = Connection

    event.listen(engine, "do_connect", connect)
    return totals


def measure_calls(owner, attribute):
    """Observe production calls without changing their inputs/results/errors."""
    import functools
    import time

    original = getattr(owner, attribute)
    totals = {"calls": 0, "wall_seconds": 0.0, "thread_cpu_seconds": 0.0}
    lock = Lock()

    @functools.wraps(original)
    def measured(*args, **kwargs):
        start, cpu = time.perf_counter(), time.thread_time()
        try:
            return original(*args, **kwargs)
        finally:
            with lock:
                totals["calls"] += 1
                totals["wall_seconds"] += time.perf_counter() - start
                totals["thread_cpu_seconds"] += time.thread_time() - cpu

    setattr(owner, attribute, measured)
    return totals
