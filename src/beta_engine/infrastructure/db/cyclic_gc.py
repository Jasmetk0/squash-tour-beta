"""Pause CPython's *cyclic* garbage collector during one heavy native Saved operation.

A native Tour read or command decodes, validates and defensively copies millions of
short-lived acyclic JSON/Pydantic objects (whole Saved payloads and rally logs).
Allocation-triggered generational collections repeatedly traverse those young
objects and, as the heap grows, the long-lived ones. Measured on real long Runs
this was about a fifth of every read (see docs/NATIVE_LONG_RUN_SAVED_READ_PERFORMANCE.md).

Only *when* cycle collection runs changes. Reference counting still frees every
acyclic object immediately; any cyclic garbage is collected after the outermost
paused operation ends. No value, validation, ordering or result depends on it.
The pause is process-wide, so it is reference counted across threads and restores
the collector only if it was enabled when the first operation started.
"""

import gc
from contextlib import contextmanager
from functools import wraps
from threading import Lock

_lock = Lock()
_active = 0
_restore = False


@contextmanager
def paused_cyclic_gc():
    global _active, _restore
    with _lock:
        if _active == 0:
            _restore = gc.isenabled()
            gc.disable()
        _active += 1
    try:
        yield
    finally:
        with _lock:
            _active -= 1
            if _active == 0 and _restore:
                _restore = False
                gc.enable()


def with_paused_cyclic_gc(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        with paused_cyclic_gc():
            return function(*args, **kwargs)
    return wrapper
