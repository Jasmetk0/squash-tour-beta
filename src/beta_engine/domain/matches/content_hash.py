"""Compute a freshly created event's content hash once, from its validated value.

The public event factories hash an unvalidated draft, then validate it with
that hash. The engine's typed internal factories instead validate a fresh
event, then hash the validated value. Only that fresh instance defers its
hash comparison. Persisted events are validated with their original hash.
"""

from __future__ import annotations

from contextvars import ContextVar

_deferred: ContextVar[list | None] = ContextVar("deferred_event_hash_check", default=None)
_PLACEHOLDER_HASH = "0" * 64


def create_with_input_hash(cls, values: dict, hash_field: str, compute_hash):
    """Keep the public factory's pre-validation hash contract."""
    draft = cls.model_construct(**values, **{hash_field: _PLACEHOLDER_HASH})
    return cls(**values, **{hash_field: compute_hash(draft)})


def create_with_validated_hash(cls, values: dict, hash_field: str, compute_hash):
    """``cls(**values, hash_field=compute_hash(validated))`` with one validation."""
    marker = [cls, False]
    token = _deferred.set(marker)
    try:
        draft = cls(**values, **{hash_field: _PLACEHOLDER_HASH})
    finally:
        _deferred.reset(token)
    if not marker[1]:
        raise RuntimeError(f"{cls.__name__} validator did not run")
    return draft.model_copy(update={hash_field: compute_hash(draft)})


def hash_check_deferred(instance) -> bool:
    """True once, for the outermost instance that ``create`` is validating."""
    marker = _deferred.get()
    if marker is None or marker[1] or type(instance) is not marker[0]:
        return False
    marker[1] = True
    return True
