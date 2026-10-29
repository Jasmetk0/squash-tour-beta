"""Bounded value cache for decoding already authenticated original Saved inputs.

This is never a physical-row validation proof. Callers still authenticate owners,
ancestry and actual dependencies before decoding. Each lookup hashes the complete
current payload; a declared Saved hash cannot authorize reuse. Repository-local
retention and defensive copies isolate databases, requests and mutable model data.
"""

import hashlib
from copy import deepcopy
from types import SimpleNamespace
from typing import NamedTuple

from beta_engine.domain.run_revisions import canonical_json

MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_SOURCES = 2
MAX_GLOBAL_TOUR_BYTES = 64 * 1024 * 1024
MAX_LIVE_COMPONENT_BYTES = 64 * 1024 * 1024


class _GlobalTourValue(NamedTuple):
    # A complete-payload adapter, not a second retained checkpoint. Its private
    # references are resolved under the cache lock, then copied outside it.
    checkpoint_key: tuple
    other: tuple


def _value_identity(run_id, branch_id, payload):
    serialized = canonical_json(payload).encode('utf-8')
    return len(serialized), (run_id, branch_id, hashlib.sha256(serialized).digest())


def _global_cache(repository):
    cache = getattr(repository, '_global_tour_projection_cache', None)
    if cache is None:
        cache = repository._global_tour_projection_cache = {}
    return cache


def _trim_global_cache(cache):
    # Keep the most recently used whole DTO, plus reusable components. A second
    # full history's evidence/Tour tail can dwarf the checkpoint itself; readers
    # of an older/other complete payload may always take the strict miss path.
    adapters = [key for key, entry in cache.items() if isinstance(entry[1], _GlobalTourValue)]
    for key in adapters[:-1]:
        cache.pop(key)
    while len(cache) > 4 or sum(entry[0] for entry in cache.values()) > MAX_GLOBAL_TOUR_BYTES:
        oldest = next(iter(cache))
        cache.pop(oldest)
        # An adapter never keeps an evicted checkpoint alive out of budget.
        for key, entry in list(cache.items()):
            if isinstance(entry[1], _GlobalTourValue) and entry[1].checkpoint_key == oldest:
                cache.pop(key)


def _global_component(source):
    content = source.payload.get('content', {})
    if not isinstance(content, dict):
        return None
    cp = content.get('calendar_player_sporting_checkpoint')
    tour = content.get('calendar_tour_authority')
    if (isinstance(cp, dict) and isinstance(cp.get('state'), dict)
        and cp['state'].get('schema_version') == 'calendar_sporting_checkpoint.v13'
        and isinstance(tour, dict) and isinstance(tour.get('state'), dict)
        and tour['state'].get('schema_version') == 'calendar_tour_authority.v5'):
        return cp
    return None


def _checked_checkpoint(value, component, run_id, branch_id):
    if (value.schema_version, value.run_id, value.branch_id, value.fingerprint) != (
        'calendar_sporting_checkpoint.v13', run_id, branch_id, component['fingerprint'],
    ):
        raise ValueError('Prevalidated Saved sporting scope/hash changed')
    return value


def _decoded_global_source(repository, source, component, decode, *, _identity=None, retain_miss=True):
    """Retain the full DTO contract through one shared checkpoint value.

    Both keys bind complete actual content and Run/Branch. The adapter is useful
    only while its checkpoint is resident; a miss uses the original decoder.
    The unchanged byte budget charges the checkpoint once and the remainder of
    the COMPLETE payload once. This is input-byte accounting, not a heap limit.
    """
    size, key = _identity or _value_identity(source.run_id, source.branch_id, source.payload)
    if size > MAX_GLOBAL_TOUR_BYTES:
        return decode(source)
    with repository._revision_validation_lock:
        cache = _global_cache(repository)
        entry = cache.get(key)
        if entry is not None and isinstance(entry[1], _GlobalTourValue):
            adapter = entry[1]
            checkpoint = cache.get(adapter.checkpoint_key)
            if checkpoint is not None:
                cache[adapter.checkpoint_key] = cache.pop(adapter.checkpoint_key)
                cache[key] = cache.pop(key)
                # Take private references while locked, then copy outside it.
                value = (adapter.other[0], checkpoint[1], adapter.other[1])
                hints = {**checkpoint[2], **entry[2]}
            else:
                value = None
        else:
            value = None
    if value is not None:
        return _copy_decoded_value(value, hints)[0]

    result = decode(source)
    if not retain_miss:
        return result
    if not isinstance(result, tuple) or len(result) != 3:
        return result
    checkpoint = _checked_checkpoint(result[1], component, source.run_id, source.branch_id)
    cp_size, cp_key = _value_identity(source.run_id, source.branch_id,
        {'calendar_player_sporting_checkpoint': component})
    if cp_size > MAX_GLOBAL_TOUR_BYTES:
        return result
    # Reuse the one private retained component, without copying it back out just
    # to prime another entry. Never retain a caller's model by reference.
    with repository._revision_validation_lock:
        known = cache.get(cp_key)
    cp_entry = known
    if cp_entry is None:
        retained, hints = _copy_decoded_value(checkpoint)
        cp_entry = (cp_size, retained, hints)
    other, hints = _copy_decoded_value((result[0], result[2]))
    with repository._revision_validation_lock:
        # Concurrent equivalent readers may have installed the same value.
        # Whichever copy wins has identical complete content; no HEAD pointer
        # or source authority is retained, so commit ordering is irrelevant.
        cache[cp_key] = cache.pop(cp_key, cp_entry)
        cache.pop(key, None)
        cache[key] = (max(0, size - cp_size), _GlobalTourValue(cp_key, other), hints)
        _trim_global_cache(cache)
    return result


def _copy_decoded_value(value, attribute_hints=None):
    from beta_engine.domain.players.sporting import _SPORTING_ATTRIBUTE_COPY_MEMO_KEY

    memo = {_SPORTING_ATTRIBUTE_COPY_MEMO_KEY: dict(attribute_hints or {})}
    result = deepcopy(value, memo)
    return result, memo[_SPORTING_ATTRIBUTE_COPY_MEMO_KEY]


def known_live_value_fingerprint(repository, *, run_id, branch_id, kind, raw):
    """Decode result for these complete actual bytes, never source authority."""
    if repository is None:
        return None
    key = (run_id, branch_id, kind, hashlib.sha256(raw.encode('utf-8')).digest())
    with repository._revision_validation_lock:
        return getattr(repository, '_live_value_fingerprints', {}).get(key)


def remember_live_value_fingerprint(repository, *, run_id, branch_id, kind, raw, fingerprint):
    if repository is None:
        return
    key = (run_id, branch_id, kind, hashlib.sha256(raw.encode('utf-8')).digest())
    with repository._revision_validation_lock:
        cache = getattr(repository, '_live_value_fingerprints', None)
        if cache is None:
            cache = repository._live_value_fingerprints = {}
        cache.pop(key, None)
        cache[key] = fingerprint
        while len(cache) > 32:
            cache.pop(next(iter(cache)))


def decoded_original_source(repository, source, decode):
    return _decoded_value(repository, source, decode,
        cache_name='_native_source_projection_cache', byte_limit=MAX_SOURCE_BYTES,
        entry_limit=MAX_SOURCES)


def decoded_global_tour_source(repository, source, decode, *, _retain_miss=True):
    """Larger bounded DTO decoding for an already authenticated native Tour."""
    component = _global_component(source) if repository is not None else None
    if component is not None:
        with repository._revision_validation_lock:
            has_adapter = any(isinstance(entry[1], _GlobalTourValue)
                and key[:2] == (source.run_id, source.branch_id)
                for key, entry in getattr(repository, '_global_tour_projection_cache', {}).items())
        if not _retain_miss and not has_adapter:
            result = decode(source)
        else:
            result = _decoded_global_source(repository, source, component, decode,
                retain_miss=_retain_miss)
    else:
        result = _decoded_value(repository, source, decode,
            cache_name='_global_tour_projection_cache', byte_limit=MAX_GLOBAL_TOUR_BYTES,
            entry_limit=4)
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


def remember_committed_global_sources(repository, source, captured):
    """Called ONLY after successful Save transaction exit and append proof.

    An oversize full payload still hands off a fitting checkpoint. No complete
    DTO is promised in that case, matching the original oversize fallback.
    """
    component = _global_component(source)
    if component is None:
        decoded_global_tour_source(repository, source, lambda _source: captured)
        return
    # The whole-payload path now also installs the component. Avoid a second
    # handoff which would return another isolated copy of that same checkpoint.
    identity = _value_identity(source.run_id, source.branch_id, source.payload)
    size, _ = identity
    if size <= MAX_GLOBAL_TOUR_BYTES:
        _decoded_global_source(repository, source, component, lambda _source: captured,
            _identity=identity)
    else:
        decoded_global_checkpoint_component(repository, component,
            run_id=source.run_id, branch_id=source.branch_id,
            decode=lambda _component: captured[1])


def decoded_global_checkpoint_component(repository, component, *, run_id, branch_id, decode):
    """Strict v13 decode data bound to the complete actual component.

    Tour-only Saves need not decode an unchanged 1,000-player checkpoint again.
    This shares the existing 64 MiB budget and defensive copies. The caller's
    full physical Saved, ownership, dependency and math gates stay mandatory.
    """
    def checked(source):
        value = decode(source.payload['calendar_player_sporting_checkpoint'])
        return _checked_checkpoint(value, component, run_id, branch_id)

    source = SimpleNamespace(run_id=run_id, branch_id=branch_id,
        payload={'calendar_player_sporting_checkpoint': component})
    value = _decoded_value(repository, source, checked,
        cache_name='_global_tour_projection_cache', byte_limit=MAX_GLOBAL_TOUR_BYTES,
        entry_limit=4)
    # checked() bound the strict decode to this entire component. Every hit
    # rehashes that full envelope and returns a defensive private copy.
    from beta_engine.domain.tournaments.calendar_global_slots import _prime_private_fingerprint
    _prime_private_fingerprint(value, component['fingerprint'])
    return value


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
        value, _ = _copy_decoded_value(known[1], known[3] if len(known) > 3 else None)
        fingerprint = known[2] if len(known) > 2 else None
        if _with_fingerprint:
            fingerprint = fingerprint or value.fingerprint
            from beta_engine.domain.tournaments.calendar_global_slots import _prime_private_fingerprint
            _prime_private_fingerprint(value, fingerprint)
            return value, fingerprint
        return value
    value = parse(raw)
    fingerprint = value.fingerprint if _with_fingerprint else None
    if fingerprint is not None:
        remember_live_value_fingerprint(repository, run_id=run_id, branch_id=branch_id,
            kind=kind, raw=raw, fingerprint=fingerprint)
    retained, attribute_hints = _copy_decoded_value(value)
    with repository._revision_validation_lock:
        cache[key] = (size, retained, fingerprint, attribute_hints)
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
        return _copy_decoded_value(entry[1], entry[2] if len(entry) > 2 else None)[0]
    result = decode(source)
    retained, attribute_hints = _copy_decoded_value(result)
    with repository._revision_validation_lock:
        cache[key] = (size, retained, attribute_hints)
        if cache_name == '_global_tour_projection_cache':
            _trim_global_cache(cache)
        else:
            while len(cache) > entry_limit or sum(item[0] for item in cache.values()) > byte_limit:
                cache.pop(next(iter(cache)))
    return result
