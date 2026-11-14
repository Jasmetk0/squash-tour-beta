"""Pause CPython's *cyclic* garbage collector during heavy native Saved operations.

A native Tour read or command decodes, validates and defensively copies millions of
short-lived acyclic JSON/Pydantic objects (whole Saved payloads and rally logs).
Allocation-triggered generational collections repeatedly traverse those young
objects and, as the heap grows, the long-lived ones. Measured on real long Runs
this was about a fifth of every read (see docs/NATIVE_LONG_RUN_SAVED_READ_PERFORMANCE.md).

Only *when* cycle collection runs changes. Reference counting still frees every
acyclic object immediately; no value, validation, ordering or result depends on it.

The pause is process-wide and reference counted across threads, so overlapping
operations could keep it active indefinitely. It is therefore bounded: whenever an
operation starts or ends while the collector has been paused continuously for more
than ``MAX_CONTINUOUS_PAUSE_SECONDS``, a full ``gc.collect()`` runs immediately and
the interval restarts. Cyclic garbage can thus survive at most that interval plus
the duration of the operations in flight. When the outermost operation ends, the
previous collector state is restored and automatic collection resumes.
"""

import gc
import time
from contextlib import contextmanager
from functools import wraps
from threading import Lock

MAX_CONTINUOUS_PAUSE_SECONDS = 30.0

_lock = Lock()
_active = 0
_restore = False
_paused_since = 0.0


def _collect_if_overdue_locked():
    global _paused_since
    now = time.monotonic()
    if now - _paused_since > MAX_CONTINUOUS_PAUSE_SECONDS:
        gc.collect()  # runs although automatic collection is disabled
        _paused_since = time.monotonic()


@contextmanager
def paused_cyclic_gc():
    global _active, _restore, _paused_since
    with _lock:
        if _active == 0:
            _restore = gc.isenabled()
            gc.disable()
            _paused_since = time.monotonic()
        else:
            _collect_if_overdue_locked()
        _active += 1
    try:
        yield
    finally:
        with _lock:
            _active -= 1
            if _active == 0:
                if _restore:
                    _restore = False
                    gc.enable()
            else:
                _collect_if_overdue_locked()


def with_paused_cyclic_gc(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with paused_cyclic_gc():
            return function(*args, **kwargs)
    return wrapper
