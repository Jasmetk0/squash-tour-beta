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


@pytest.mark.parametrize("W,offset", [(52, 1), (61, 37), (80, 37)])
def test_old_calendar_immutability_and_new_extension_remains_explicit(W, offset):
    source = RunCalendar(W, offset, 2030, 2)
    original = calc(source, w(1, 1))
    original_json = original.model_dump_json()
    original_hash = original.fingerprint
    extended_calendar = source.extend_to(3)

    # A strict horizon extension permits the *next* week but creates a new
    # candidate. The predecessor keeps its exact original bytes and clock.
    successor = calc(extended_calendar, w(1, 2), previous=original)
    assert successor.previous_fingerprint == original_hash
    assert successor.run_calendar == extended_calendar.to_metadata()
    assert successor.week == w(1, 2)
    assert original.run_calendar == source.to_metadata()
    assert original.model_dump_json() == original_json
    assert original.fingerprint == original_hash
    assert CalendarOfficialRankingSnapshot.model_validate_json(original_json) == original

    # New candidates may not shorten a predecessor's recorded horizon, even
    # when the calendar week itself would still fall inside that shorter Run.
    with pytest.raises(ValueError, match="preceding week"):
        calc(source, w(1, 3), previous=successor)

    # Neither a different W, season offset nor starting year is an extension.
    for rebased in (
        RunCalendar(W + 1, offset, 2030, 3),
        RunCalendar(W, 2 if offset == 1 else 1, 2030, 3),
        RunCalendar(W, offset, 2031, 3),
    ):
        with pytest.raises(ValueError, match="preceding week"):
            calc(rebased, w(1, 2), previous=original)

    with pytest.raises(ValueError, match="preceding week"):
        calc(extended_calendar, w(1, 3), previous=original)
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


@pytest.mark.parametrize("W", [52, 61, 80])
def test_final_week_completed_edition_first_publishes_next_season(W):
    clock = RunCalendar(W, 37 if W != 52 else 1, 2030, 3)
    end = r("a", "final-week", w(0, W), w(1, 1), pts=150)
    before = calc(clock, w(0, W), results=())
    after = calc(clock, w(1, 1), results=(end,), previous=before)
    assert before.rows[0].points == 0
    assert after.rows[0].points == 150
    assert after.rows[0].counted_results == (end,)
    assert after.previous_fingerprint == before.fingerprint


def test_multi_player_W61_ranking_bestN_and_disciplinary_zero_match_legacy():
    """Differential test of exact ranking rows, Best N, previous rank tie and zeros."""
    from beta_engine.domain.rankings.official import (
        DisciplinaryZero, OfficialRankingPlayer,
        OfficialRankingResult, RankingWeek, calculate_official_ranking,
    )
    clock = RunCalendar.fax_default()
    policy = OfficialRankingPolicy(policy_id="best-two", best_n=2)
    players = (p("a"), p("b"), p("c"))
    result_data = (
        ("a", "a1", 1, 2, 100), ("a", "a2", 3, 4, 75),
        ("b", "b1", 1, 2, 100), ("b", "b2", 3, 4, 75),
        ("c", "c1", 1, 2, 100),
    )
    facts = tuple(
        r(name, event, w(0, completed), w(0, published), pts=pts)
        for name, event, completed, published, pts in result_data
    )
    old_facts = tuple(OfficialRankingResult(
        edition_id=event, player_id=name, source_fingerprint="f-"+event,
        completed_week=RankingWeek(season_index=0, week=completed),
        first_publication_week=RankingWeek(season_index=0, week=published),
        main_points=pts,
    ) for name, event, completed, published, pts in result_data)
    zeros = (z("a", w(0, 3), duration=5),)
    old_zeros = (DisciplinaryZero(
        zero_id="zero", run_id=RUN, branch_id=BRANCH, player_id="a",
        source_fingerprint="discipline",
        effective_week=RankingWeek(season_index=0, week=3), duration_weeks=5,
    ),)
    new = calc(clock, w(0, 5), players=players, results=facts, zeros=zeros, policy=policy)
    old = calculate_official_ranking(
        run_id=RUN, branch_id=BRANCH,
        week=RankingWeek(season_index=0, week=5), policy=policy,
        players=tuple(OfficialRankingPlayer(
            player_id=player.player_id,
            tie_break_token=player.tie_break_token,
            tour_entry_week=RankingWeek(season_index=0, week=1),
        ) for player in players),
        results=old_facts, disciplinary_zeros=old_zeros,
    )
    view = lambda snapshot: [
        (row.rank, row.player_id, row.points,
         tuple(result.edition_id for result in row.counted_results),
         tuple(zero.zero_id for zero in row.disciplinary_zeros))
        for row in snapshot.rows
    ]
    assert view(new) == view(old)
