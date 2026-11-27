"""Compute a freshly created event's content hash once, from its validated value.

The public event factories hash an unvalidated draft, then validate it with
that hash. The engine's typed internal factories instead validate a fresh
event, then hash the validated value. Only that fresh instance defers its
hash comparison. Persisted events are validated with their original hash.

Inside one ``MatchEngine`` call (``engine_event_scope``) the same fresh instance
is validated again when its log is assembled: pydantic re-runs the event's
``after`` validator for every model instance placed in the log. Every
structural check of that second run still executes; only the hash comparison
is skipped, and only when the instance is the exact object the factory hashed,
it was never re-validated since, and none of its fields was reassigned. That
comparison would re-serialize the identical value and hash the identical
bytes. Everything else (stored data, ``model_validate``, copies, public
factories, events created outside an engine call) keeps the full check.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_deferred: ContextVar[list | None] = ContextVar("deferred_event_hash_check", default=None)
# id(instance) -> (instance, its field values when hashed) for one engine call.
_hashed_in_scope: ContextVar[dict[int, tuple[object, tuple]] | None] = ContextVar(
    "engine_hashed_events", default=None
)
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
    event = draft.model_copy(update={hash_field: compute_hash(draft)})
    hashed = _hashed_in_scope.get()
    if hashed is not None:
        hashed[id(event)] = (event, tuple(event.__dict__.values()))
    return event


def hash_check_deferred(instance) -> bool:
    """True once, for the outermost instance that ``create`` is validating."""
    marker = _deferred.get()
    if marker is None or marker[1] or type(instance) is not marker[0]:
        return False
    marker[1] = True
    return True


@contextmanager
def engine_event_scope() -> Iterator[None]:
    """Remember the events hashed by the engine factories during one engine call."""
    token = _hashed_in_scope.set({})
    try:
        yield
    finally:
        _hashed_in_scope.reset(token)


def hash_verified_in_scope(instance) -> bool:
    """True once, when ``instance`` is unchanged since its factory hashed it.

    Consumed on the first re-validation, so any later validation of the same
    object (and every copy or reload) recomputes and compares the hash.
    """
    hashed = _hashed_in_scope.get()
    if not hashed:
        return False
    entry = hashed.pop(id(instance), None)
    if entry is None or entry[0] is not instance:
        return False
    current = tuple(instance.__dict__.values())
    recorded = entry[1]
    return len(current) == len(recorded) and all(
        now is then for now, then in zip(current, recorded, strict=True)
    )
