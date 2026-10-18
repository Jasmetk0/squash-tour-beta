"""Freeze the native v1 checkpoint contract before adding explicit v2 history."""
import json
from types import SimpleNamespace
import pytest

from beta_engine.domain.players.calendar_sporting_checkpoint import CalendarSportingCheckpoint, build_calendar_sporting_checkpoint
from beta_engine.infrastructure.db.calendar_standalone_match_state import _parse_calendar_match
from tests.domain.test_calendar_canonical_match import canonical_bracket

pytestmark = pytest.mark.pr_critical


def initial():
    raw = canonical_bracket().model_dump(mode='json')
    raw['schema_version'] = 'calendar_opening_knockout.v5'
    knockout = _parse_calendar_match(json.dumps(raw))
    world = SimpleNamespace(schema_version='initial_world_state.v2', run_id=knockout.run_id,
        branch_id=knockout.branch_id, run_calendar=knockout.week.calendar,
        players=knockout.canonical_source.players, fingerprint=knockout.source_initial_world_fingerprint)
    return build_calendar_sporting_checkpoint(world, knockout, lambda p: p.player)


def test_v1_json_and_hash_match_the_pre_continuation_implementation_exactly():
    state = initial()
    assert state.fingerprint == '78945f8c29bcec8c9ace3a26f52aeb02c1729e41697dd80d3ad8b872535b8762'
    assert 'continuations' not in state.model_dump(mode='json')
    assert CalendarSportingCheckpoint.model_validate_json(state.model_dump_json()).fingerprint == state.fingerprint


@pytest.mark.parametrize('damage', ['explicit_empty_ledger', 'fake_v2'])
def test_neither_historical_v1_nor_empty_v2_can_silently_claim_continued_state(damage):
    raw = initial().model_dump(mode='json')
    if damage == 'explicit_empty_ledger': raw['continuations'] = []
    else: raw.update(schema_version='calendar_sporting_checkpoint.v2', phase='opening_week_continued')
    with pytest.raises(ValueError): CalendarSportingCheckpoint.model_validate_json(json.dumps(raw))
