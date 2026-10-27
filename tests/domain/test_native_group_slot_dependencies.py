"""Scheduling/application boundary contracts; not real MatchEngine acceptance."""
from types import SimpleNamespace

import pytest

from beta_engine.application import calendar_native_groups as commands
from beta_engine.domain.tournaments import calendar_global_slots as slots
from beta_engine.domain.tournaments.group_standings_authority import (
    TournamentGroupStandingsTieCase,
    TournamentGroupStandingsUnresolvedTie,
)
from tests.domain.test_calendar_global_slot_contracts import authority

pytestmark = pytest.mark.pr_critical


def case():
    return TournamentGroupStandingsTieCase(group_index=1, player_ids=('A', 'B', 'C'),
        reason='exact-tie', source_match_results=(('match', 'a' * 64),))


@pytest.mark.parametrize('fork', [False, True])
@pytest.mark.parametrize('start', [3, 4, 5])
def test_tie_cannot_skip_its_playoff_frontier(monkeypatch, fork, start):
    group = SimpleNamespace(edition=SimpleNamespace(
        schema_version='calendar_tournament_edition.v3', edition_id='groups',
        week=authority('other').edition.week, start_slot=1,
        group_configuration=SimpleNamespace(format_kind='groups_knockout')),
        tournament_fingerprint=None, draw=SimpleNamespace(schedule=SimpleNamespace(
            match_day_count=3, matches=tuple(range(12)))))
    other = authority('other', start=start)
    original = slots.edition_plan
    def plan(a, matches, history):
        if a is group:
            raise TournamentGroupStandingsUnresolvedTie(case())
        return original(a, matches, history)
    monkeypatch.setattr(slots, 'edition_plan', plan)
    state = SimpleNamespace(week=group.edition.week, editions=(group, other))
    cp = SimpleNamespace(global_slots=(), history_global_slots=()) if fork else SimpleNamespace(events=())
    number, due, _ = slots.next_schedule(state, cp)
    assert number == min(7, start + 3)
    if number == 7:
        assert any(a is group and not ids for a, _, ids in due)
        with pytest.raises(TournamentGroupStandingsUnresolvedTie):
            slots.freeze_slot(state, cp, world=None, lifecycle=None, health=None, source=None, head='saved')
    group.edition.group_configuration.format_kind = 'groups'
    assert slots.next_schedule(state, cp)[0] == start + 3


def test_http_json_order_is_accepted_without_coercing_invalid_players(monkeypatch):
    group = SimpleNamespace(edition=SimpleNamespace(
        schema_version='calendar_tournament_edition.v3', edition_id='groups'), tournament_fingerprint=None)
    slot = slots.GlobalSlot.model_construct(scheduled=(SimpleNamespace(edition_id='groups'),),
                                            group_tie_decisions=())
    class Checkpoint:
        events = (slot,)
        tournaments = ()
        fingerprint = 'checkpoint'
        def model_copy(self, *, update):
            result = Checkpoint()
            result.events = update['events']
            return result
    class State:
        editions = ()
        def model_copy(self, *, update):
            return update
    payload = case().model_dump(mode='json')
    monkeypatch.setattr(commands, 'group_progress', lambda *_: {'tie_case': payload})
    command = SimpleNamespace(data={'case': payload, 'ordered_player_ids': ['C', 'B', 'A']},
        command_id='decision', operator_label='Admin', audit_reason='Reviewed case', action='resolve-group-tie')
    capture = {}
    commands.apply_group_tie(None, (None, None, None, None, Checkpoint()), State(), group,
                             command, persist=False, _successor_out=capture)
    assert capture['checkpoint'].events[0].group_tie_decisions[0].decision.ordered_player_ids == ('C', 'B', 'A')
    assert slot.group_tie_decisions == ()
    command.data['ordered_player_ids'] = ['C', 'C', 'A']
    with pytest.raises(ValueError):
        commands.apply_group_tie(None, (None, None, None, None, Checkpoint()), State(), group,
                                 command, persist=False)
