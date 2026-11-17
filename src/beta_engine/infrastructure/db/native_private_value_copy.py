"""Conservative exact-type accelerated copy for signed native sporting DTOs.

NOT an authority, cache, nor authorization to reuse mutable objects. Every
returned model/container is privately allocated; only *proven exact builtin*
immutable scalar values may retain identity. Unknown/custom classes, special
Pydantic deepcopy implementations and unusual containers defer to the normal
copy.deepcopy behavior with the SAME memo.

The call site must still authenticate physical Saved payload, source graph
and Run/Branch owner independently. This helper operates on already decoded
private values, and never touches Signed Saved raw bytes or fingerprints.
"""
from __future__ import annotations

from copy import deepcopy

from pydantic import BaseModel

from beta_engine.domain.rankings.official import FrozenInput

_SCALAR_TYPES = (type(None), str, int, bool, float, bytes)


class _TupleCycle(Exception):
    """A tuple cycle needs the standard copy.deepcopy cycle resolver."""


def private_copy(value, memo):
    """Copy trusted decoded values while preserving aliasing and isolation.

    The memo is caller-owned (including legacy private attribute hints).
    A fallback restarts with the *initial* memo to avoid leaking partial
    private copies in adversarial cyclic / custom-Pydantic cases.
    """
    seed = memo.copy()
    try:
        return _copy(value, memo, set())
    except _TupleCycle:
        memo.clear()
        memo.update(seed)
        return deepcopy(value, memo)


def _copy(value, memo, active_tuples):
    t = type(value)
    if t in _SCALAR_TYPES:
        return value
    key = id(value)
    if key in memo:
        return memo[key]

    if t is list:
        cloned = []
        memo[key] = cloned
        cloned.extend(_copy(item, memo, active_tuples) for item in value)
        return cloned

    if t is dict:
        if any(type(k) is not str for k in value):
            return deepcopy(value, memo)
        cloned = {}
        memo[key] = cloned
        for k, item in value.items():
            cloned[k] = _copy(item, memo, active_tuples)
        return cloned

    if t is tuple:
        # Complete scalar tuples are genuinely immutable and match
        # copy.deepcopy's identity-preserving result, including bool/int.
        if all(type(item) in _SCALAR_TYPES for item in value):
            return value
        if key in active_tuples:
            raise _TupleCycle()
        active_tuples.add(key)
        try:
            items = [_copy(item, memo, active_tuples) for item in value]
        finally:
            active_tuples.remove(key)
        cloned = value if all(x is y for x, y in zip(items, value)) else tuple(items)
        memo[key] = cloned
        return cloned

    # Only known FrozenInput subclass models inheriting the *unmodified*
    # Pydantic BaseModel deepcopy/copy contract, with no private/extra data.
    # The custom PlayerSportingRecord.__deepcopy__, private attrs, or any
    # unfamiliar model continue through the original standard path.
    if (
        isinstance(value, FrozenInput)
        and getattr(t, "__deepcopy__", None) is BaseModel.__deepcopy__
        and getattr(t, "__copy__", None) is BaseModel.__copy__
        and getattr(t, "__new__", None) is BaseModel.__new__
        and value.__pydantic_extra__ is None
        and value.__pydantic_private__ is None
        and type(value.__dict__) is dict
        and type(value.__pydantic_fields_set__) is set
    ):
        cloned = t.__new__(t)
        memo[key] = cloned
        object.__setattr__(cloned, "__dict__", _copy(value.__dict__, memo, active_tuples))
        object.__setattr__(
            cloned, "__pydantic_fields_set__", value.__pydantic_fields_set__.copy()
        )
        object.__setattr__(cloned, "__pydantic_extra__", None)
        object.__setattr__(cloned, "__pydantic_private__", None)
        return cloned

    return deepcopy(value, memo)
