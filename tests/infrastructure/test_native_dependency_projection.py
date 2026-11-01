"""Dependency hints discard sporting payloads, never validate Saved history."""

import json
from threading import Lock
from types import SimpleNamespace

import pytest

from beta_engine.infrastructure.db import native_fork_runtime_state as storage

pytestmark = pytest.mark.pr_critical


def reference_result(raw):
    content = json.loads(raw).get('content', {})
    baseline = content.get('native_fork_baseline', {}).get('state')
    branches = {baseline.get('selected_source_branch_id')} if isinstance(baseline, dict) else set()
    if 'calendar_tour_authority' in content:
        branches.add('branch')
    return tuple(branches)


def actual_result(raw):
    row = (None, None, 'branch', None, None, None, None, None, None, raw)
    return storage._dependency_references(None, row, 'unused-without-repository')


def test_reference_walk_never_materializes_large_unrelated_components(monkeypatch):
    raw = json.dumps({'content': {
        'initial_world': {'players': [{'attributes': list(range(57))}] * 1000},
        'calendar_player_sporting_checkpoint': {'state': {'events': [{'rallies': list(range(1000))}] * 100}},
        'calendar_tour_authority': {'state': {'receipts': [{'unneeded': 'x' * 1000}] * 100}},
        'native_fork_baseline': {'state': {'selected_source_branch_id': 'original', 'unneeded': [0] * 10000}},
    }})

    def full_decode_forbidden(*args, **kwargs):
        pytest.fail('Dependency hints redundantly decoded the complete Saved payload')

    monkeypatch.setattr(storage.json, 'loads', full_decode_forbidden)
    assert set(actual_result(raw)) == {'branch', 'original'}
    projected = storage._dependency_content(raw)
    assert projected == {'calendar_tour_authority': {},
                         'native_fork_baseline': {'state': {'selected_source_branch_id': 'original'}}}


@pytest.mark.parametrize('raw', [
    '{}', '{"content":{}}', '{"content":{"native_fork_baseline":{"state":{}}}}',
    '{"content":{"calendar_tour_authority":{}}}',
    '{"content":{"calendar_tour_authority":null}}',
    '{"content":{"calendar_tour_authority":false}}',
    '{"content":{"calendar_tour_authority":[1]}}',
    '{"content":{"native_fork_baseline":{"state":null}}}',
    '{"content":{"native_fork_baseline":{"state":1}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":null}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":true}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":1}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":-0.0}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":"source"}}}}',
    '{"content":{"calendar_tour_authority":{}},"content":{}}',
    '{"content":{},"content":{"calendar_tour_authority":{}}}',
    '{"content":false,"content":{"calendar_tour_authority":{}}}',
    '{"content":{"calendar_tour_authority":{}},"content":false}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":"old"},"state":{}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":[],"selected_source_branch_id":"last"}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":"old","selected_source_branch_id":[]}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":"old"}}},"\\u0063ontent":{}}',
    '{"unused":[true,1,-0.0,NaN,Infinity,-Infinity],"content":{}}',
    '{"unused":"\\ud800","content":{}}',
    '{"content":null}', '{"content":[]}', '[]', 'null',
    '{"content":{"native_fork_baseline":null}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":[]}}}}',
    '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":{}}}}}',
    '{"content":{},"unused":[01]}', '{"content":{},"unused":1e}',
    '{"content":{},"unused":"\\q"}', '{"content":{},"unused":[1,]}',
    '{"content":{}} trailing',
])
def test_projection_preserves_original_reference_values_and_rejections(raw):
    try:
        expected = reference_result(raw)
    except (TypeError, ValueError, AttributeError):
        with pytest.raises(ValueError, match='malformed JSON dependency data'):
            actual_result(raw)
    else:
        actual = actual_result(raw)
        assert actual == expected
        assert tuple(type(value) for value in actual) == tuple(type(value) for value in expected)
        # Python equality alone would conflate opposite signs of zero.
        assert json.dumps(actual) == json.dumps(expected)


def test_unknown_raw_type_and_unsupported_shapes_take_the_original_parser(monkeypatch):
    class Raw(str):
        pass

    original = json.loads
    calls = []

    def observed(raw):
        calls.append(raw)
        return original(raw)

    monkeypatch.setattr(storage.json, 'loads', observed)
    raw = Raw('{"content":{"calendar_tour_authority":{}}}')
    assert actual_result(raw) == ('branch',)
    unsupported = '{"content":{"native_fork_baseline":{"state":{"selected_source_branch_id":true}}}}'
    assert actual_result(unsupported) == (True,)
    assert calls == [raw, unsupported]


def test_projection_uses_existing_compact_hint_budget_and_strict_fallback(monkeypatch):
    monkeypatch.setattr(storage, '_MAX_DEPENDENCY_REFERENCE_HINTS', 1)
    repository = SimpleNamespace(_revision_validation_lock=Lock())
    for index, branch in enumerate(('short', 'other', 'x' * 1025)):
        raw = json.dumps({'content': {'native_fork_baseline': {'state': {'selected_source_branch_id': branch}}}})
        row = (None, None, 'branch', None, None, None, None, None, None, raw)
        assert storage._dependency_references(repository, row, str(index)) == (branch,)
        assert len(repository._native_dependency_reference_hints) == 1
    assert repository._native_dependency_reference_hints == {'1': ('other',)}
