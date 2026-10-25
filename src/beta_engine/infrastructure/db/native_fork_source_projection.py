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
MAX_GLOBAL_TOUR_BYTES = 64 * 1024 * 1024
MAX_LIVE_COMPONENT_BYTES = 64 * 1024 * 1024


def decoded_original_source(repository, source, decode):
    return _decoded_value(repository, source, decode,
        cache_name='_native_source_projection_cache', byte_limit=MAX_SOURCE_BYTES,
        entry_limit=MAX_SOURCES)


def decoded_global_tour_source(repository, source, decode):
    """Larger bounded DTO decoding for an already authenticated native Tour."""
    result = _decoded_value(repository, source, decode,
        cache_name='_global_tour_projection_cache', byte_limit=MAX_GLOBAL_TOUR_BYTES,
        entry_limit=2)
    if isinstance(result, tuple) and len(result) == 3:
        from beta_engine.domain.tournaments.calendar_global_slots import _prime_private_fingerprint

        for value, key, schema in (
            (result[1], 'calendar_player_sporting_checkpoint', 'calendar_sporting_checkpoint.v13'),
            (result[2], 'calendar_tour_authority', 'calendar_tour_authority.v5'),
        ):
            if getattr(value, 'schema_version', None) == schema:
                # decode checked this actual component's value/hash after the
                # complete physical Saved gate; cache hits bind its full bytes.
                _prime_private_fingerprint(value, source.payload['content'][key]['fingerprint'])
    return result


def decoded_live_calendar_component(repository, *, run_id, branch_id, kind, raw, parse, _with_fingerprint=False):
    """Bounded value decoding only; callers still verify every live authority.

    Hash the complete actual SQLite JSON, not its declared fingerprint. Reusing
    strict parsing does not authenticate a Working state, sporting results or
    sources; the ordinary current-row and full live replay gates still run.
    Defensive copies keep mutable nested model data isolated across requests.
    """
    if repository is None:
        value = parse(raw)
        return (value, value.fingerprint) if _with_fingerprint else value
    actual = raw.encode('utf-8')
    size = len(actual)
    if size > MAX_LIVE_COMPONENT_BYTES:
        value = parse(raw)
        return (value, value.fingerprint) if _with_fingerprint else value
    key = (run_id, branch_id, kind, hashlib.sha256(actual).digest())
    with repository._revision_validation_lock:
        cache = getattr(repository, '_live_calendar_value_cache', None)
        if cache is None:
            cache = repository._live_calendar_value_cache = {}
        known = cache.pop(key, None)
        if known is not None:
            cache[key] = known
    if known is not None:
        value = deepcopy(known[1])
        fingerprint = known[2] if len(known) > 2 else None
        if _with_fingerprint:
            fingerprint = fingerprint or value.fingerprint
            from beta_engine.domain.tournaments.calendar_global_slots import _prime_private_fingerprint
            _prime_private_fingerprint(value, fingerprint)
            return value, fingerprint
        return value
    value = parse(raw)
    fingerprint = value.fingerprint if _with_fingerprint else None
    retained = deepcopy(value)
    with repository._revision_validation_lock:
        cache[key] = (size, retained, fingerprint)
        while len(cache) > 4 or sum(item[0] for item in cache.values()) > MAX_LIVE_COMPONENT_BYTES:
            cache.pop(next(iter(cache)))
    return (value, fingerprint) if _with_fingerprint else value


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
