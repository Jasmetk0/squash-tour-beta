"""Private memo of PURE values computed during one verification replay.

A native replay validates week after week of the same immutable (frozen)
models. Values that are a pure function of such a model -- its canonical
fingerprint -- or of an identical prefix of inputs are recomputed for every
later week, which makes a replay quadratic in the number of weeks.

This memo is active only inside ``replay_value_scope`` (entered by the global
replay projection scope). Entries are keyed by object identity and keep the
object alive, so an identity can never be reused by a different object. It is
never a validation proof, never crosses a replay and is never persisted.
Outside the scope every caller computes its value freshly, exactly as before.
"""

from contextlib import contextmanager
from contextvars import ContextVar

MAX_IDENTITY_VALUES = 16384

_memo = ContextVar("native_replay_value_memo", default=None)


@contextmanager
def replay_value_scope():
    token = _memo.set({"identity": {}}) if _memo.get() is None else None
    try:
        yield
    finally:
        if token is not None:
            _memo.reset(token)


def active_memo():
    """The private memo dict of the active replay scope, or None."""
    return _memo.get()


def identity_value(value, name, compute):
    """``compute()``, memoized per (object identity, name) inside the scope."""
    memo = _memo.get()
    if memo is None:
        return compute()
    values = memo["identity"]
    key = (id(value), name)
    known = values.get(key)
    if known is not None and known[0] is value:
        return known[1]
    result = compute()
    values[key] = (value, result)
    while len(values) > MAX_IDENTITY_VALUES:
        values.pop(next(iter(values)))
    return result


def already_checked(name, objects):
    """True if the pure check ``name`` already PASSED for these exact objects."""
    memo = _memo.get()
    if memo is None:
        return False
    known = memo.setdefault("checked", {}).get((name, tuple(id(o) for o in objects)))
    return known is not None and len(known) == len(objects) and all(a is b for a, b in zip(known, objects))


def remember_checked(name, objects):
    """Record that the pure check ``name`` passed; keeps the objects alive."""
    memo = _memo.get()
    if memo is None:
        return
    checked = memo.setdefault("checked", {})
    checked[(name, tuple(id(o) for o in objects))] = tuple(objects)
    while len(checked) > MAX_IDENTITY_VALUES:
        checked.pop(next(iter(checked)))
