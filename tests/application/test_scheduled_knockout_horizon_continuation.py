"""Real Q/Main records retain their original clocks through Run extension.

This exercises the component consumer, not a native Tour execution/Save route.
The separate Saved-source HTTP test verifies actual immutable source recovery.
"""
import pytest

from beta_engine.application.scheduled_knockout_results import (
    complete_scheduled_knockout_result, scheduled_knockout_ranking_results,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_continuation_match import CalendarContinuationMatch
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRoundPosition
from beta_engine.domain.tournaments.scheduled_knockout_feeders import scheduled_knockout_progress
from tests.application.test_scheduled_knockout_feeders import plan, play_scheduled

pytestmark = pytest.mark.pr_critical


def at_runtime(position, clock):
    return KnockoutRoundPosition(week=RunWeekPosition(calendar=clock,
        season_index=position.week.season_index, week=position.week.week), slot=position.slot)


@pytest.fixture(scope='module')
def continued():
    return play_scheduled(plan(), extend_after_qualification_to=3)


def test_real_main_consumes_saved_q_after_extension_without_rewriting_inputs(continued):
    p, matches, positions, batches = continued
    frozen_plan = p.model_dump_json()
    frozen_matches = tuple(m.model_dump_json() for m in matches)
    assert len(matches) == 43
    assert {m.week.calendar.season_count for m in batches[0][1] + batches[1][1]} == {2}
    assert {m.week.calendar.season_count for _, rows in batches[2:] for m in rows} == {3}
    # New Main records have genuine input anchors for the extended clock.
    assert tuple(CalendarContinuationMatch.model_validate_json(raw)
                 for raw in frozen_matches) == matches
    current = at_runtime(p.schedule.main[-1], p.calendar.extend_to(3))
    progress, due = scheduled_knockout_progress(plan=p, matches=matches,
        positions=positions, current=current)
    assert progress.champion_player_id and not due
    winners = {pid for _, pid in progress.qualification_winners}
    assert len(winners) == 4
    assert winners <= {pid for m in batches[2][1]
                      for pid in (m.result.player_a_id, m.result.player_b_id)}
    reversed_progress = scheduled_knockout_progress(plan=p, matches=tuple(reversed(matches)),
        positions=positions, current=current)
    assert reversed_progress == (progress, due)
    assert p.model_dump_json() == frozen_plan
    assert tuple(m.model_dump_json() for m in matches) == frozen_matches


def test_partial_frozen_slot_can_continue_on_a_longer_run(continued):
    p, _, positions, batches = continued
    first_round = batches[0][1]
    accepted = first_round[:4]
    progress, due = scheduled_knockout_progress(plan=p, matches=accepted,
        positions={m.match_id: positions[m.match_id] for m in accepted},
        current=at_runtime(p.schedule.qualification[0], p.calendar.extend_to(3)))
    assert len(progress.accepted_match_ids) == 4
    assert {m.match_id for m in due} == {m.match_id for m in first_round[4:]}
    assert all(m.seed == p.match_seed(m.match_id) for m in due)


def test_horizon_extension_alone_preserves_actual_sporting_outcomes(continued):
    _, extended_matches, _, _ = continued
    _, original_matches, _, _ = play_scheduled(plan())
    def sporting_facts(records):
        # New records bind the extended clock in their input/result hashes.
        # Compare actual scores and physical effects, retaining the physical
        # checkpoint hash while allowing those two provenance hashes to differ.
        return tuple((m.match_id, m.seed, m.result.winner_player_id,
                      m.result.sets, tuple(e.model_dump(exclude={
                          'input_fingerprint', 'result_fingerprint'})
                          for e in m.effects)) for m in records)
    assert sporting_facts(extended_matches) == sporting_facts(original_matches)


def test_completed_result_keeps_actual_play_clock_on_later_extensions(continued):
    p, matches, positions, _ = continued
    result, rows = scheduled_knockout_ranking_results(plan=p, matches=matches,
        positions=positions, runtime_calendar=p.calendar.extend_to(3))
    assert result.completed_week.calendar.season_count == 3
    assert result.source_plan_fingerprint == p.fingerprint
    assert len(rows) == len({r.player_id for r in rows}) == 44
    assert all(r.validity_weeks == 52 and r.first_publication_week.week == 7 for r in rows)
    frozen_result = result.model_dump_json()
    later_result, later_rows = scheduled_knockout_ranking_results(plan=p, matches=matches,
        positions=positions, runtime_calendar=p.calendar.extend_to(4))
    assert later_result.model_dump_json() == frozen_result
    assert later_rows == rows
    with pytest.raises(ValueError, match='exceeds the consuming Run horizon'):
        complete_scheduled_knockout_result(plan=p, matches=matches, positions=positions)


@pytest.mark.parametrize('clock', [
    RunCalendar(52, 1, 2025, 1),  # smaller horizon
    RunCalendar(61, 1, 2025, 3),  # a different annual scale
    RunCalendar(52, 2, 2025, 3),  # shifted season
    RunCalendar(52, 1, 2026, 3),  # shifted civil year
])
def test_extension_cannot_rebase_the_frozen_tournament(continued, clock):
    p, _, _, _ = continued
    with pytest.raises(ValueError, match='only extend'):
        scheduled_knockout_progress(plan=p, matches=(), positions={},
            current=at_runtime(p.schedule.qualification[0], clock))


@pytest.mark.parametrize('damage', ['record_clock', 'slot_clock', 'slot_number', 'mixed_round', 'shrinking_round'])
def test_changed_clock_or_round_evidence_is_rejected(continued, damage):
    p, accepted, original_positions, _ = continued
    matches = list(accepted)
    positions = dict(original_positions)
    first = matches[0]
    clock = p.calendar.extend_to(3)
    expected = 'frozen round schedule'
    if damage == 'record_clock':
        matches[0] = first.model_copy(update={'week': at_runtime(positions[first.match_id], clock).week})
    elif damage == 'slot_clock':
        positions[first.match_id] = at_runtime(positions[first.match_id], clock)
    elif damage == 'slot_number':
        positions[first.match_id] = positions[first.match_id].model_copy(update={'slot': 99})
    else:
        # Deliberately corrupt clock evidence. The feeder rejects the inconsistency
        # before the independent MatchEngine input-anchor validation runs.
        targets = [first] if damage == 'mixed_round' else [m for m in matches if m.week.week == 5]
        for m in targets:
            positions[m.match_id] = at_runtime(positions[m.match_id], p.calendar.extend_to(4))
            index = matches.index(m)
            matches[index] = m.model_copy(update={'week': positions[m.match_id].week})
        clock = p.calendar.extend_to(4)
        expected = 'different Run clocks' if damage == 'mixed_round' else 'cannot shrink'
    with pytest.raises(ValueError, match=expected):
        scheduled_knockout_progress(plan=p, matches=tuple(matches), positions=positions,
            current=at_runtime(p.schedule.main[-1], clock))
