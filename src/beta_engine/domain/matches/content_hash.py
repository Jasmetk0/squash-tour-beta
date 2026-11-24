"""Compute a freshly created event's content hash once, from its validated value.

Rally, stamina-transition and timeline events used to hash an unvalidated
``model_construct`` draft in ``create`` and then hash the validated model again
in their validator, comparing the two. ``create`` now validates once with only
that final hash comparison deferred for exactly the instance being created
(every other validator check still runs), and then stores the hash computed
from the VALIDATED model. Whenever the original sequence succeeded the two
hashes were equal, so the created event is byte-identical; the stored hash is
always the hash its validator recomputes. Any instance not created through this
path (loading stored data, model_validate, direct construction) is validated in
full, exactly as before.
"""

from __future__ import annotations

from contextvars import ContextVar

_deferred: ContextVar[list | None] = ContextVar("deferred_event_hash_check", default=None)


def create_with_validated_hash(cls, values: dict, hash_field: str, compute_hash):
    """``cls(**values, hash_field=compute_hash(validated))`` with one validation."""
    marker = [cls, False]
    token = _deferred.set(marker)
    try:
        draft = cls(**values, **{hash_field: "0" * 64})
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
