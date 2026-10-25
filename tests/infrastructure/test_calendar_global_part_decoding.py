"""Value-decoding reuse cannot authorize changed or mutated checkpoint inputs."""

from copy import deepcopy
from threading import Lock
from types import SimpleNamespace

import pytest

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.infrastructure.db import calendar_sporting_checkpoint as storage

pytestmark = pytest.mark.pr_critical


class Part(FrozenInput):
    values: dict[str, int]


def test_live_value_fingerprint_binds_complete_actual_bytes_and_scope():
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.native_fork_source_projection import (
        decoded_live_calendar_component, known_live_value_fingerprint,
        remember_live_value_fingerprint,
    )

    class FingerprintedPart(Part):
        @property
        def fingerprint(self):
            return canonical_hash(self.model_dump(mode='json'))

    repository = SimpleNamespace(_revision_validation_lock=Lock())
    fields = dict(run_id='run', branch_id='branch', kind='checkpoint')
    raw = '{"values":{"a":1}}'
    assert known_live_value_fingerprint(repository, raw=raw, **fields) is None
    value, fingerprint = decoded_live_calendar_component(repository, raw=raw,
        parse=FingerprintedPart.model_validate_json, _with_fingerprint=True, **fields)
    value.values['a'] = 999
    assert known_live_value_fingerprint(repository, raw=raw, **fields) == fingerprint
    for changed in ('{"values":{"a":2}}', '{"values":{"a":1},"changed":true}'):
        assert known_live_value_fingerprint(repository, raw=changed, **fields) is None
    for key in fields:
        assert known_live_value_fingerprint(repository, raw=raw,
            **{**fields, key: 'foreign'}) is None
    assert known_live_value_fingerprint(SimpleNamespace(_revision_validation_lock=Lock()), raw=raw, **fields) is None
    for number in range(40):
        remember_live_value_fingerprint(repository, raw=str(number), fingerprint=str(number), **fields)
    assert len(repository._live_value_fingerprints) == 32


def test_equal_parts_decode_once_but_changed_bytes_require_their_own_validation():
    calls = []
    cache = {}

    def parse(raw):
        calls.append(raw)
        return Part.model_validate_json(raw)

    first = storage._parsed_global_part({'values': {'a': 1}}, cache, parse)
    assert storage._parsed_global_part({'values': {'a': 1}}, cache, parse) == first
    assert len(calls) == 1
    changed = storage._parsed_global_part({'values': {'a': 2}}, cache, parse)
    assert changed.values == {'a': 2} and len(calls) == 2
    with pytest.raises(ValueError):
        storage._parsed_global_part({'values': {'a': 'invalid'}}, cache, parse)
    assert len(calls) == 3


def test_mutating_a_nested_cached_value_cannot_change_the_original_decoded_input():
    cache, calls = {}, []

    def parse(raw):
        calls.append(raw)
        return Part.model_validate_json(raw)

    original = {'values': {'a': 1}}
    first = storage._parsed_global_part(original, cache, parse)
    first.values['a'] = 999
    actual = storage._parsed_global_part(original, cache, parse)
    assert actual.values == {'a': 1} and len(calls) == 2


def test_retention_is_bounded_and_malformed_parts_are_rejected(monkeypatch):
    monkeypatch.setattr(storage, '_MAX_GLOBAL_PARTS', 2)
    cache = {}
    for value in range(4):
        storage._parsed_global_part({'values': {'a': value}}, cache, Part.model_validate_json)
    assert len(cache) == 2
    monkeypatch.setattr(storage, '_MAX_GLOBAL_PART_BYTES', 1)
    small_cache = {}
    assert storage._parsed_global_part({'values': {'a': 5}}, small_cache, Part.model_validate_json).values == {'a': 5}
    assert not small_cache
    with pytest.raises(TypeError, match='versioned object'):
        storage._parsed_global_part([], cache, Part.model_validate_json)
    with pytest.raises(TypeError, match='versioned object'):
        storage.parse_checkpoint_json('{"schema_version":"calendar_sporting_checkpoint.v13"}',
            _parsed_global_parts={})


def test_private_projection_memo_ends_with_the_pure_replay_even_on_failure():
    from beta_engine.domain.tournaments.calendar_global_slots import (
        _replay_fingerprint,
        global_replay_projection_scope,
    )

    value = Part(values={'a': 1})
    original = _replay_fingerprint(value)
    with pytest.raises(RuntimeError), global_replay_projection_scope():
        assert _replay_fingerprint(value) == original
        successor = value.model_copy(update={'values': {'a': 2}})
        assert _replay_fingerprint(successor) != original
        raise RuntimeError('injected replay failure')
    # Mutable containers are never trusted across a completed replay boundary.
    value.values['a'] = 3
    assert _replay_fingerprint(value) != original


def test_raw_math_proof_binds_actual_components_complete_histories_and_source_scope():
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.calendar_native_competition import (
        _raw_global_inputs,
        has_replayed_global_components,
    )

    # Only the private cache protocol is tested here. Real HTTP acceptance must
    # produce its proof through complete production sporting replay.
    payload = {'run': {'run_id': 'run', 'run_calendar': {'test_basis': 52}},
        'branch': {'branch_id': 'branch'}, 'content': {}}
    content = payload['content']
    for key, schema in (
        ('calendar_player_sporting_checkpoint', 'calendar_sporting_checkpoint.v13'),
        ('calendar_tour_authority', 'calendar_tour_authority.v5'),
    ):
        state = {'schema_version': schema, 'actual_value': 1}
        content[key] = {'state': state, 'fingerprint': canonical_hash(state)}
    for key in ('player_lifecycle', 'player_health_state'):
        states = [{'actual': 1}, {'actual': 2}]
        content[key] = {'states': states, 'fingerprint': canonical_hash(states)}
    identity = tuple(content[key]['fingerprint'] for key in (
        'calendar_player_sporting_checkpoint', 'calendar_tour_authority'))
    proofs = {'_prefixes': {'_global_replayed_values': {identity: _raw_global_inputs(payload)}}}
    assert has_replayed_global_components(payload, proofs)
    for target in ('world', 'calendar', 'calendar_origin', 'branch', 'history', 'checkpoint'):
        changed = deepcopy(payload)
        if target == 'world':
            changed['content']['initial_world'] = {'changed': True}
        elif target == 'calendar':
            changed['run']['run_calendar'] = {'test_basis': 80}
        elif target == 'calendar_origin':
            changed['run']['run_calendar_content_origin'] = {'forged': True}
        elif target == 'branch':
            changed['branch']['branch_id'] = 'foreign'
        elif target == 'checkpoint':
            part = changed['content']['calendar_player_sporting_checkpoint']
            part['state']['actual_value'] = 99
            part['fingerprint'] = canonical_hash(part['state'])
        else:
            part = changed['content']['player_health_state']
            part['states'].pop()
            part['fingerprint'] = canonical_hash(part['states'])
        assert not has_replayed_global_components(changed, proofs), target
    for malformed in (None, {}, {'states': [], 'fingerprint': 'forged'}):
        changed = deepcopy(payload)
        changed['content']['player_health_state'] = malformed
        with pytest.raises(ValueError, match='actual value fingerprint'):
            has_replayed_global_components(changed, proofs)


def test_routing_hint_and_origin_projection_follow_actual_bytes_and_detect_mutation():
    import json

    from beta_engine.infrastructure.db.calendar_global_slot_origins import (
        is_global_slot_row,
    )
    from beta_engine.infrastructure.db.calendar_tour import _origin_inputs

    repository = SimpleNamespace(_revision_validation_lock=Lock())
    row = SimpleNamespace(run_id='run', branch_id='branch', revision_id='source',
        payload_json=json.dumps({'content': {'calendar_tour_authority': {
            'state': {'schema_version': 'calendar_tour_authority.v5'}}}}))
    assert is_global_slot_row(row, repository=repository)
    row.payload_json = json.dumps({'content': {'unrelated': 'calendar_tour_authority.v5'}})
    assert not is_global_slot_row(row, repository=repository)
    row.payload_json = json.dumps({'run': {'run_id': 'run'}, 'branch': {'branch_id': 'branch'},
        'content': {'calendar_player_sporting_checkpoint': {'fingerprint': 'actual'},
            'initial_world': {'identity': 1}, 'player_lifecycle': {'states': []},
            'player_health_state': {'states': []}, 'irrelevant_large_content': 'unused'}})
    cache = {}
    first, _ = _origin_inputs(row, cache)
    assert 'irrelevant_large_content' not in first['content']
    first['content']['calendar_player_sporting_checkpoint']['fingerprint'] = 'forged'
    repaired, _ = _origin_inputs(row, cache)
    assert repaired['content']['calendar_player_sporting_checkpoint']['fingerprint'] == 'actual'
    health, _ = _origin_inputs(row, cache, with_health=True)
    assert all(key in health['content'] for key in ('initial_world', 'player_lifecycle', 'player_health_state'))


def test_authenticated_tour_decoding_returns_isolated_values_and_follows_actual_input():
    from beta_engine.infrastructure.db.native_fork_source_projection import (
        decoded_global_tour_source,
    )

    repo = SimpleNamespace(_revision_validation_lock=Lock())
    source = SimpleNamespace(run_id='run', branch_id='branch', payload={'values': [1]})
    calls = []

    def decode(record):
        calls.append(1)
        return deepcopy(record.payload)

    first = decoded_global_tour_source(repo, source, decode)
    first['values'].append(99)
    assert decoded_global_tour_source(repo, source, decode) == {'values': [1]}
    assert len(calls) == 1
    source.payload['values'].append(2)
    assert decoded_global_tour_source(repo, source, decode) == {'values': [1, 2]}
    source.branch_id = 'other'
    decoded_global_tour_source(repo, source, decode)
    assert len(calls) == 3


def test_oversized_tour_decoding_is_not_retained(monkeypatch):
    from beta_engine.infrastructure.db import (
        native_fork_source_projection as projection,
    )

    monkeypatch.setattr(projection, 'MAX_GLOBAL_TOUR_BYTES', 1)
    repo = SimpleNamespace(_revision_validation_lock=Lock())
    source = SimpleNamespace(run_id='run', branch_id='branch', payload={'values': [1]})
    calls = []
    for _ in range(2):
        projection.decoded_global_tour_source(repo, source, lambda value: calls.append(1) or value.payload)
    assert len(calls) == 2 and not hasattr(repo, '_global_tour_projection_cache')


def test_live_value_decoding_binds_actual_bytes_scope_and_kind_and_isolates_mutation():
    import json

    from beta_engine.infrastructure.db.native_fork_source_projection import decoded_live_calendar_component

    repo = SimpleNamespace(_revision_validation_lock=Lock())
    calls = []

    def parse(raw):
        calls.append(raw)
        return Part.model_validate_json(raw)

    args = dict(run_id='run', branch_id='branch', kind='sporting', raw=json.dumps({'values': {'a': 1}}), parse=parse)
    first = decoded_live_calendar_component(repo, **args)
    first.values['a'] = 999
    assert decoded_live_calendar_component(repo, **args).values == {'a': 1}
    assert len(calls) == 1
    for change in ({'run_id': 'other'}, {'branch_id': 'other'}, {'kind': 'tour'}, {'raw': '{"values":{"a":2}}'}):
        decoded_live_calendar_component(repo, **{**args, **change})
    assert len(calls) == 5
    with pytest.raises(ValueError):
        decoded_live_calendar_component(repo, **{**args, 'raw': '{"values":{"a":"invalid"}}'})
    assert len(calls) == 6


def test_live_value_retention_is_bounded_and_has_no_oversize_or_failed_entries(monkeypatch):
    import json

    from beta_engine.infrastructure.db import native_fork_source_projection as projection

    repo = SimpleNamespace(_revision_validation_lock=Lock())
    for i in range(8):
        projection.decoded_live_calendar_component(repo, run_id='run', branch_id='branch',
            kind='sporting', raw=json.dumps({'values': {'a': i}}), parse=Part.model_validate_json)
    assert len(repo._live_calendar_value_cache) == 4
    monkeypatch.setattr(projection, 'MAX_LIVE_COMPONENT_BYTES', 1)
    other = SimpleNamespace(_revision_validation_lock=Lock())
    for _ in range(2):
        projection.decoded_live_calendar_component(other, run_id='run', branch_id='branch',
            kind='sporting', raw='{"values":{"a":1}}', parse=Part.model_validate_json)
    assert not hasattr(other, '_live_calendar_value_cache')


def test_actual_value_fingerprint_reuse_ends_before_nested_mutation_can_escape():
    import json
    from beta_engine.domain.tournaments.calendar_global_slots import _replay_fingerprint, global_replay_projection_scope
    from beta_engine.infrastructure.db.native_fork_source_projection import decoded_live_calendar_component

    class HashedPart(Part):
        @property
        def fingerprint(self):
            return _replay_fingerprint(self)

    repo = SimpleNamespace(_revision_validation_lock=Lock())
    calls = []

    def parse(raw):
        calls.append(1)
        return HashedPart.model_validate_json(raw)

    args = dict(run_id='run', branch_id='branch', kind='sporting',
        raw=json.dumps({'values': {'a': 1}}), parse=parse, _with_fingerprint=True)
    with global_replay_projection_scope():
        first, expected = decoded_live_calendar_component(repo, **args)
        second, actual = decoded_live_calendar_component(repo, **args)
        assert first == second and expected == actual == second.fingerprint
    second.values['a'] = 99
    assert second.fingerprint != actual
    recovered, fingerprint = decoded_live_calendar_component(repo, **args)
    assert recovered.values == {'a': 1} and recovered.fingerprint == fingerprint == expected
    assert len(calls) == 1
