"""Bounded value cache for decoding already authenticated original Saved inputs.

This is never a physical-row validation proof. Callers still authenticate owners,
ancestry and actual dependencies before decoding. Each lookup hashes the complete
current payload; a declared Saved hash cannot authorize reuse. Repository-local
retention and defensive copies isolate databases, requests and mutable model data.
"""

import hashlib
from copy import deepcopy

from beta_engine.domain.run_revisions import canonical_json

MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_SOURCES = 2
MAX_GLOBAL_TOUR_BYTES = 32 * 1024 * 1024


def decoded_original_source(repository, source, decode):
    return _decoded_value(repository, source, decode,
        cache_name='_native_source_projection_cache', byte_limit=MAX_SOURCE_BYTES,
        entry_limit=MAX_SOURCES)


def decoded_global_tour_source(repository, source, decode):
    """Larger bounded DTO decoding for an already authenticated native Tour."""
    return _decoded_value(repository, source, decode,
        cache_name='_global_tour_projection_cache', byte_limit=MAX_GLOBAL_TOUR_BYTES,
        entry_limit=2)


def _decoded_value(repository, source, decode, *, cache_name, byte_limit, entry_limit):
    if repository is None:
        return decode(source)
    serialized = canonical_json(source.payload).encode("utf-8")
    size = len(serialized)
    if size > byte_limit:
        return decode(source)
    key = (source.run_id, source.branch_id, hashlib.sha256(serialized).digest())
    with repository._revision_validation_lock:
        cache = getattr(repository, cache_name, None)
        if cache is None:
            cache = {}
            setattr(repository, cache_name, cache)
        entry = cache.pop(key, None)
        if entry is not None:
            cache[key] = entry
    if entry is not None:
        return deepcopy(entry[1])
    result = decode(source)
    retained = deepcopy(result)
    with repository._revision_validation_lock:
        cache[key] = (size, retained)
        while (
            len(cache) > entry_limit
            or sum(item[0] for item in cache.values()) > byte_limit
        ):
            cache.pop(next(iter(cache)))
    return result
