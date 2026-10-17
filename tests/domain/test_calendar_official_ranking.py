"""The full time semantics for versioned, read-only Official Ranking candidates."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.rankings.calendar_official import (
    CalendarDisciplinaryZero, CalendarOfficialRankingSnapshot,
    CalendarRankingPlayer, CalendarRankingResult, CalendarRankingWeek,
    calculate_calendar_official_ranking, load_calendar_official_ranking_candidate,
)
from beta_engine.domain.rankings.official import (
    OfficialRankingPlayer, OfficialRankingPolicy, OfficialRankingResult,
    RankingWeek, calculate_official_ranking,
)

pytestmark = pytest.mark.pr_critical
RUN, BRANCH = "run-a", "branch-a"
POLICY = OfficialRankingPolicy(policy_id="Best N", best_n=2)


def w(season: int, week: int) -> CalendarRankingWeek:
    return CalendarRankingWeek(season_index=season, week=week)


def p(name: str, *, entry: CalendarRankingWeek | None = None,
      retired: bool = False) -> CalendarRankingPlayer:
    return CalendarRankingPlayer(
        player_id=name, tie_break_token=name,
        tour_entry_week=entry or w(0, 1), retired=retired,
    )


def r(name: str, event: str, completed: CalendarRankingWeek,
      published: CalendarRankingWeek, *, pts: int = 100,
      duration: int | None = None, ranked: bool = True) -> CalendarRankingResult:
    return CalendarRankingResult(
        edition_id=event, player_id=name, source_fingerprint="f-" + event,
        completed_week=completed, first_publication_week=published,
        main_points=pts, validity_weeks=duration, ranked=ranked,
    )


def z(name: str, effective: CalendarRankingWeek, *,
      zero_id: str = "zero", duration: int = 2,
      branch: str = BRANCH) -> CalendarDisciplinaryZero:
    return CalendarDisciplinaryZero(
        zero_id=zero_id, run_id=RUN, branch_id=branch,
        player_id=name, source_fingerprint="discipline",
        effective_week=effective, duration_weeks=duration,
    )


def calc(calendar: RunCalendar, week: CalendarRankingWeek,
         players: tuple[CalendarRankingPlayer, ...] | None = None,
         results: tuple[CalendarRankingResult, ...] = (),
         previous: CalendarOfficialRankingSnapshot | None = None,
         zeros: tuple[CalendarDisciplinaryZero, ...] = (),
         policy: OfficialRankingPolicy = POLICY):
    return calculate_calendar_official_ranking(
        run_id=RUN, branch_id=BRANCH, run_calendar=calendar,
        week=week, policy=policy, players=players if players is not None else (p("a"),),
        results=results, previous=previous, disciplinary_zeros=zeros,
    )


@pytest.mark.parametrize("W", [52, 61, 80])
def test_W_expiry_across_season_and_exact_boundary(W):
    calendar = RunCalendar(W, 37 if W != 52 else 1, 2030, 3)
    facts = (r("a", "title", w(0, W-1), w(0, W)),)
    before = calc(calendar, w(1, W-1), results=facts)
    after = calc(calendar, w(1, W), results=facts)
    assert before.rows[0].points == 100
    assert before.rows[0].counted_results == facts
    assert after.rows[0].points == 0
    assert after.rows[0].counted_results == ()
    assert before.week.week == W-1
    assert after.run_calendar == calendar.to_metadata()
    assert before.fingerprint != after.fingerprint


@pytest.mark.parametrize("W", [52, 61, 80])
def test_previous_week_lineage_across_calendar_season_boundary(W):
    calendar = RunCalendar(W, 37 if W != 52 else 1, 2000, 3)
    # W to next season Week 1 is adjacent under the Run calendar.
    previous = calc(calendar, w(0, W))
    following = calc(calendar, w(1, 1), previous=previous)
    assert following.previous_fingerprint == previous.fingerprint
    assert following.rows[0].points == 0
    with pytest.raises(ValueError, match="preceding week"):
        calc(calendar, w(1, 2), previous=previous)


def test_W80_saves_week80_and_unambiguous_correction_and_bestN():
    calendar = RunCalendar(80, 37, 2030, 4)
    results = (
        r("a", "a1", w(0, 78), w(0, 79), pts=100),
        r("a", "a2", w(0, 79), w(0, 80), pts=90),
        r("a", "a3", w(0, 79), w(0, 80), pts=200),
    )
    last = calc(calendar, w(0, 80), results=results)
    assert last.rows[0].points == 300
    assert tuple(t.edition_id for t in last.rows[0].counted_results) == ("a3", "a1")
    assert last.week.week == 80
    assert CalendarOfficialRankingSnapshot.model_validate_json(last.model_dump_json()) == last
    reloaded = load_calendar_official_ranking_candidate(
        last.model_dump_json(), expected_fingerprint=last.fingerprint,
        run_id=RUN, branch_id=BRANCH, week=w(0, 80), run_calendar=calendar,
    )
    assert reloaded == last
    with pytest.raises(ValueError, match="fingerprint"):
        load_calendar_official_ranking_candidate(
            last.model_dump_json(), expected_fingerprint="0" * 64,
            run_id=RUN, branch_id=BRANCH, week=w(0, 80), run_calendar=calendar,
        )
    with pytest.raises(ValueError, match="scope/clock"):
        load_calendar_official_ranking_candidate(
            last.model_dump_json(), expected_fingerprint=last.fingerprint,
            run_id=RUN, branch_id="foreign", week=w(0, 80), run_calendar=calendar,
        )


def test_disciplinary_zero_reduces_bestN_and_expires_in_real_weeks():
    calendar = RunCalendar(52, 1, 2030, 3)
    facts = (
        r("a", "a1", w(0, 48), w(0, 49), pts=100),
        r("a", "a2", w(0, 49), w(0, 50), pts=80),
    )
    zeros = (z("a", w(0, 52)),)
    limited = calc(calendar, w(1, 1), results=facts, zeros=zeros)
    assert limited.rows[0].points == 100
    assert len(limited.rows[0].disciplinary_zeros) == 1
    assert len(limited.rows[0].counted_results) == 1
    restored = calc(calendar, w(1, 2), results=facts, zeros=zeros)
    assert restored.rows[0].points == 180
    assert not restored.rows[0].disciplinary_zeros


def test_tour_entry_is_next_week_only_and_retired_are_hidden():
    calendar = RunCalendar(80, 1, 2030, 2)
    players = (p("existing"), p("new", entry=w(0, 80)), p("retired", retired=True))
    first = calc(calendar, w(0, 80), players=players)
    assert [row.player_id for row in first.rows] == ["existing"]
    second = calc(calendar, w(1, 1), players=players)
    assert [row.player_id for row in second.rows] == ["existing", "new"]


def test_policy_inherits_actual_bestN_and_zero_points_rank_profile():
    clock = RunCalendar(52, 1, 2030, 3)
    players = (p("x"), p("y"))
    previous = calc(clock, w(0, 2), players=players)
    following = calc(clock, w(0, 3), players=tuple(reversed(players)), previous=previous)
    assert [row.player_id for row in following.rows] == ["x", "y"]
    assert following.previous_fingerprint == previous.fingerprint


def test_legacy_W61_official_results_and_policies_remain_semantically_identical():
    calendar = RunCalendar.fax_default()
    old_player = OfficialRankingPlayer(
        player_id="a", tie_break_token="a",
        tour_entry_week=RankingWeek(season_index=0, week=1),
    )
    legacy_result = OfficialRankingResult(
        edition_id="e", player_id="a", source_fingerprint="src",
        completed_week=RankingWeek(season_index=0, week=59),
        first_publication_week=RankingWeek(season_index=0, week=60),
        main_points=100,
    )
    old = calculate_official_ranking(
        run_id=RUN, branch_id=BRANCH, week=RankingWeek(season_index=1, week=59),
        policy=POLICY, players=(old_player,), results=(legacy_result,),
    )
    new = calc(
        calendar, w(1, 59),
        results=(r("a", "e", w(0, 59), w(0, 60)),),
    )
    assert [(row.player_id, row.points) for row in old.rows] == [
        (row.player_id, row.points) for row in new.rows
    ]
    assert len(old.rows[0].counted_results) == len(new.rows[0].counted_results)
    assert old.rows[0].counted_results[0].validity_weeks == 61
    assert new.rows[0].counted_results[0].validity_weeks is None
    assert old.schema_version == "official_ranking_calculation.v1"
    assert new.schema_version == "calendar_official_ranking_candidate.v1"
    assert "run_calendar" not in old.model_dump()
    assert new.fingerprint != old.fingerprint


@pytest.mark.parametrize("W", [52, 80])
def test_invalid_weeks_invalid_publishing_and_future_sources_fail_closed(W):
    calendar = RunCalendar(W, 1, 2000, 3)
    facts = (r("a", "e", w(0, W-1), w(0, W)),)
    with pytest.raises(ValueError, match="season_week"):
        calc(calendar, w(0, W+1))
    with pytest.raises(ValueError, match="season_index"):
        calc(calendar, w(3, 1))
    with pytest.raises(ValueError, match="season_week"):
        calc(calendar, w(1, 1), results=(r("a", "bad", w(0, W+1), w(1, 1)),))
    with pytest.raises(ValueError, match="publication"):
        calc(calendar, w(0, W), results=(r("a", "bad", w(0, W), w(0, W)),))
    with pytest.raises(ValueError, match="future"):
        calc(calendar, w(0, W-1), results=facts)
    with pytest.raises(ValueError, match="Future disciplinary zero"):
        calc(calendar, w(0, W-1), zeros=(z("a", w(0, W)),))
    with pytest.raises(ValueError, match="Future Tour entrant"):
        calc(calendar, w(0, 1), players=(p("late", entry=w(0, 2)),))


def test_unknown_id_duplicate_facts_and_foreign_zero_fail_closed():
    clock = RunCalendar(52, 1, 2000, 2)
    fact = r("a", "e", w(0, 1), w(0, 2))
    with pytest.raises(ValueError, match="Duplicate ranking player"):
        calc(clock, w(0, 3), players=(p("a"), p("a")))
    with pytest.raises(ValueError, match="Duplicate ranking tie-break"):
        calc(clock, w(0, 3), players=(p("a"), p("b").model_copy(update={"tie_break_token": "a"})))
    with pytest.raises(ValueError, match="One resolved result"):
        calc(clock, w(0, 3), results=(fact, fact))
    with pytest.raises(ValueError, match="Unknown ranking result"):
        calc(clock, w(0, 3), results=(r("someone", "e", w(0, 1), w(0, 2)),))
    with pytest.raises(ValueError, match="foreign scope"):
        calc(clock, w(0, 3), zeros=(z("a", w(0, 2), branch="other"),))
    with pytest.raises(ValueError, match="Duplicate disciplinary zero"):
        calc(clock, w(0, 3), zeros=(z("a", w(0, 2)), z("a", w(0, 2))))


def test_serialized_corruption_cannot_inject_ineligible_result_or_foreign_zero():
    clock = RunCalendar(80, 37, 2030, 3)
    candidate = calc(
        clock, w(1, 1), results=(r("a", "e", w(0, 79), w(0, 80)),),
        zeros=(z("a", w(0, 80)),),
    )
    raw = candidate.model_dump(mode="json")
    raw["rows"][0]["points"] = 3
    with pytest.raises(ValidationError, match="points"):
        CalendarOfficialRankingSnapshot.model_validate_json(json.dumps(raw))
    raw = candidate.model_dump(mode="json")
    raw["rows"][0]["counted_results"][0]["first_publication_week"]["week"] = 81
    with pytest.raises(ValidationError, match="season_week"):
        CalendarOfficialRankingSnapshot.model_validate_json(json.dumps(raw))
    raw = candidate.model_dump(mode="json")
    raw["rows"][0]["disciplinary_zeros"][0]["branch_id"] = "foreign"
    with pytest.raises(ValidationError, match="scope|ineligible"):
        CalendarOfficialRankingSnapshot.model_validate_json(json.dumps(raw))
    raw = candidate.model_dump(mode="json")
    raw["run_calendar"]["weeks_per_year"] = 52
    with pytest.raises(ValidationError, match="season_week"):
        CalendarOfficialRankingSnapshot.model_validate_json(json.dumps(raw))


def test_old_calendar_immutability_and_new_extension_remains_explicit():
    source = RunCalendar(52, 1, 2030, 2)
    candidate = calc(source, w(1, 1))
    with pytest.raises(ValueError, match="preceding week"):
        # The verified candidate has the OLD Saved clock identity; a different
        # horizon must not silently reinterpret its lineage.
        calc(source.extend_to(3), w(1, 2), previous=candidate)
    assert candidate.run_calendar == source.to_metadata()
    with pytest.raises(ValueError, match="versioned"):
        calc(RunCalendar.legacy_fax(), w(0, 1))


def test_fingerprint_and_rows_deterministic_under_input_order():
    clock = RunCalendar(80, 1, 2030, 2)
    players = (p("a"), p("b"))
    facts = (r("a", "A", w(0, 1), w(0, 2)), r("b", "B", w(0, 1), w(0, 2)))
    first = calc(clock, w(0, 3), players=players, results=facts)
    second = calc(clock, w(0, 3), players=tuple(reversed(players)), results=tuple(reversed(facts)))
    assert first.fingerprint == second.fingerprint
    assert first.model_dump_json() == second.model_dump_json()
