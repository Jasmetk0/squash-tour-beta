"""Projection from canonical Run-owned evidence into the single Finals Race kernel."""

import hashlib
from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_package_run_adapter import RunCalendarProjection
from beta_engine.application.finals_race_projection import (
    build_canonical_world_tour_finals_race_snapshot,
    project_canonical_world_tour_finals_race_input,
)
from beta_engine.domain.finals import WorldTourFinalsRaceConfiguration
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.domain.tournaments.models import CalendarEvent, SeasonCalendar


def fp(char: str) -> str:
    return char * 64


def calendar_projection() -> RunCalendarProjection:
    events = [
        CalendarEvent(
            event_id="E1",
            season="2000/2001",
            season_week=4,
            template_id="TPL-1",
            event_name="Diamond One",
            category="DIAMOND",
            tour_level="WORLD_TOUR",
            host_country="CZE",
            region="EUROPE",
            main_draw_size=4,
        ),
        CalendarEvent(
            event_id="E2",
            season="2000/2001",
            season_week=7,
            template_id="TPL-2",
            event_name="Diamond Two",
            category="DIAMOND",
            tour_level="WORLD_TOUR",
            host_country="CZE",
            region="EUROPE",
            main_draw_size=4,
        ),
        CalendarEvent(
            event_id="ELITE",
            season="2000/2001",
            season_week=5,
            template_id="TPL-3",
            event_name="Elite",
            category="ELITE",
            tour_level="ELITE_TOUR",
            host_country="CZE",
            region="EUROPE",
            main_draw_size=4,
        ),
        CalendarEvent(
            event_id="FINALS",
            season="2000/2001",
            season_week=20,
            template_id="FINALS-TPL",
            event_name="World Tour Finals",
            category="FINALS",
            tour_level="WORLD_TOUR",
            host_country="CZE",
            region="EUROPE",
            main_draw_size=8,
        ),
    ]
    return RunCalendarProjection(
        package_id="calendar-2000-2001",
        run_id="run",
        branch_id="branch",
        run_package_state_fingerprint=fp("9"),
        season="2000/2001",
        calendar=SeasonCalendar(season="2000/2001", events=events),
        provenance=(),
    )


def configuration(calendar: RunCalendarProjection) -> WorldTourFinalsRaceConfiguration:
    return WorldTourFinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        target_season_index=0,
        finals_event_id="FINALS",
        eligible_categories=("DIAMOND",),
        best_n=2,
        cutoff_week=RankingWeek(season_index=0, week=10),
        cutoff_official_ranking_fingerprint=fp("a"),
        cutoff_transition_fingerprint=fp("b"),
        calendar_content_fingerprint=calendar.content_fingerprint,
        adopted_by_command_id="config-race",
    )


def cutoff_publication():
    return SimpleNamespace(
        run_id="run",
        branch_id="branch",
        week=RankingWeek(season_index=0, week=10),
        fingerprint=fp("a"),
        policy=SimpleNamespace(policy_id="official", best_n=15),
        rows=(
            # Official ranking order is deliberately p1 before p2.
            SimpleNamespace(rank=1, player_id="p1"),
            SimpleNamespace(rank=2, player_id="p2"),
        ),
    )


def transition():
    return SimpleNamespace(
        run_id="run",
        branch_id="branch",
        target_week=RankingWeek(season_index=0, week=10),
        fingerprint=fp("b"),
        policy=SimpleNamespace(policy_id="official", best_n=15),
        players=(
            SimpleNamespace(player_id="p1", tie_break_token="token-b"),
            SimpleNamespace(player_id="p2", tie_break_token="token-a"),
            # Deliberately absent from Official Ranking rows: the ranking is only
            # the cutoff boundary and must not become a Race eligibility filter.
            SimpleNamespace(player_id="p3", tie_break_token="token-c"),
        ),
    )


def source(
    *,
    edition_id: str,
    event_id: str,
    completed_week: int,
    publication_week: int,
    points: dict[str, int],
    marker: str,
    canonical: bool = True,
):
    result_fp = fp(marker)
    awards_fp = fp(marker.upper())
    binding = SimpleNamespace(
        run_id="run",
        branch_id="branch",
        edition_id=edition_id,
        event_id=event_id,
        completed_week=RankingWeek(season_index=0, week=completed_week),
        first_publication_week=RankingWeek(
            season_index=0, week=publication_week
        ),
        expected_result_fingerprint=result_fp,
        expected_award_fingerprint=awards_fp,
    )
    if not canonical:
        return SimpleNamespace(
            binding=binding,
            canonical_result=None,
            canonical_awards=None,
        )
    return SimpleNamespace(
        binding=binding,
        canonical_result=SimpleNamespace(
            run_id="run",
            branch_id="branch",
            event_id=event_id,
            completed_week=binding.completed_week,
            fingerprint=result_fp,
        ),
        canonical_awards=SimpleNamespace(
            run_id="run",
            branch_id="branch",
            event_id=event_id,
            completed_week=binding.completed_week,
            fingerprint=awards_fp,
            awards=tuple(
                SimpleNamespace(
                    player_id=player_id,
                    race_points_awarded=value,
                    award_fingerprint=hashlib.sha256(
                        f"{edition_id}:{player_id}".encode()
                    ).hexdigest(),
                )
                for index, (player_id, value) in enumerate(sorted(points.items()))
            ),
        ),
    )


@pytest.mark.pr_critical
def test_projection_uses_canonical_race_points_and_never_official_ranking_order():
    calendar = calendar_projection()
    race = build_canonical_world_tour_finals_race_snapshot(
        configuration=configuration(calendar),
        calendar=calendar,
        cutoff_publication=cutoff_publication(),
        transition_authority=transition(),
        tournament_sources=(
            source(
                edition_id="edition-1",
                event_id="E1",
                completed_week=4,
                publication_week=5,
                points={"p1": 500, "p2": 500},
                marker="d",
            ),
            source(
                edition_id="edition-2",
                event_id="E2",
                completed_week=7,
                publication_week=8,
                points={"p1": 300, "p2": 300},
                marker="g",
            ),
            # Ineligible category is ignored.
            source(
                edition_id="elite-edition",
                event_id="ELITE",
                completed_week=5,
                publication_week=6,
                points={"p1": 9000},
                marker="j",
            ),
            # Eligible category published after cutoff is ignored.
            source(
                edition_id="late-edition",
                event_id="E2",
                completed_week=7,
                publication_week=11,
                points={"p1": 9000},
                marker="m",
            ),
        ),
    )

    # Both players have exactly the same result profile. The stored Race token
    # decides the tie, even though the Official Ranking had p1 ahead of p2.
    assert [(row.rank, row.player_id, row.race_points) for row in race.rows] == [
        (1, "p2", 800),
        (2, "p1", 800),
        (3, "p3", 0),
    ]
    assert all(
        [result.race_points for result in row.counted_results] == [500, 300]
        for row in race.rows[:2]
    )
    assert race.rows[2].counted_results == ()
    assert race.eligible_result_count == 4
    assert race.eligibility_fingerprint == configuration(
        calendar
    ).eligibility_fingerprint


@pytest.mark.pr_critical
def test_projection_fails_closed_for_legacy_only_eligible_source():
    calendar = calendar_projection()
    with pytest.raises(
        ValueError,
        match="requires canonical result and point-award authority",
    ):
        project_canonical_world_tour_finals_race_input(
            configuration=configuration(calendar),
            calendar=calendar,
            cutoff_publication=cutoff_publication(),
            transition_authority=transition(),
            tournament_sources=(
                source(
                    edition_id="edition-1",
                    event_id="E1",
                    completed_week=4,
                    publication_week=5,
                    points={"p1": 500},
                    marker="d",
                    canonical=False,
                ),
            ),
        )


@pytest.mark.pr_critical
def test_projection_binds_exact_calendar_publication_and_transition():
    calendar = calendar_projection()
    config = configuration(calendar)

    bad_publication = cutoff_publication()
    bad_publication.fingerprint = fp("f")
    with pytest.raises(ValueError, match="publication identity mismatch"):
        project_canonical_world_tour_finals_race_input(
            configuration=config,
            calendar=calendar,
            cutoff_publication=bad_publication,
            transition_authority=transition(),
            tournament_sources=(),
        )

    bad_transition = transition()
    bad_transition.fingerprint = fp("f")
    with pytest.raises(ValueError, match="transition authority mismatch"):
        project_canonical_world_tour_finals_race_input(
            configuration=config,
            calendar=calendar,
            cutoff_publication=cutoff_publication(),
            transition_authority=bad_transition,
            tournament_sources=(),
        )

    missing_finals = config.model_copy(update={"finals_event_id": "MISSING"})
    with pytest.raises(ValueError, match="Finals Edition absent"):
        project_canonical_world_tour_finals_race_input(
            configuration=missing_finals,
            calendar=calendar,
            cutoff_publication=cutoff_publication(),
            transition_authority=transition(),
            tournament_sources=(),
        )
