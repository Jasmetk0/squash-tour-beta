"""Projection from Run-owned Calendar/tournament evidence into canonical Finals Race."""

from types import SimpleNamespace

import pytest

from beta_engine.application.calendar_package_run_adapter import RunCalendarProjection
from beta_engine.application.finals_race_projection import (
    project_canonical_finals_race_snapshot,
)
from beta_engine.domain.finals import FinalsRaceConfiguration
from beta_engine.domain.rankings.official import OfficialRankingPlayer, RankingWeek
from beta_engine.domain.tournaments.models import CalendarEvent, SeasonCalendar


def fp(char: str) -> str:
    return char * 64


def calendar_projection() -> RunCalendarProjection:
    event = CalendarEvent(
        event_id="EVT-1",
        season="2000/2001",
        season_week=4,
        template_id="TPL-1",
        event_name="Event 1",
        category="DIAMOND",
        tour_level="WORLD_TOUR",
        host_country="CZE",
        region="EUROPE",
        main_draw_size=4,
    )
    return RunCalendarProjection(
        package_id="calendar-2000-2001",
        run_id="run",
        branch_id="branch",
        run_package_state_fingerprint=fp("a"),
        season="2000/2001",
        calendar=SeasonCalendar(season="2000/2001", events=[event]),
        provenance=(),
    )


def configuration(projection: RunCalendarProjection) -> FinalsRaceConfiguration:
    return FinalsRaceConfiguration(
        run_id="run",
        branch_id="branch",
        season_index=0,
        best_n_results=2,
        eligible_categories=("DIAMOND",),
        cutoff_ranking_week=RankingWeek(season_index=0, week=10),
        cutoff_ranking_snapshot_fingerprint=fp("b"),
        cutoff_transition_fingerprint=fp("c"),
        calendar_content_fingerprint=projection.content_fingerprint,
        adopted_by_command_id="race-config",
    )


def transition():
    return SimpleNamespace(
        run_id="run",
        branch_id="branch",
        target_week=RankingWeek(season_index=0, week=10),
        fingerprint=fp("c"),
        players=(
            OfficialRankingPlayer(
                player_id="p1",
                tie_break_token="token-1",
                tour_entry_week=RankingWeek(season_index=0, week=1),
                retired=False,
            ),
        ),
    )


def source(*, canonical: bool):
    award = SimpleNamespace(player_id="p1", race_points_awarded=500)
    canonical_awards = (
        SimpleNamespace(
            run_id="run",
            branch_id="branch",
            event_id="EVT-1",
            completed_week=RankingWeek(season_index=0, week=4),
            fingerprint=fp("d"),
            awards=(award,),
        )
        if canonical
        else None
    )
    return SimpleNamespace(
        binding=SimpleNamespace(
            run_id="run",
            branch_id="branch",
            event_id="EVT-1",
            completed_week=RankingWeek(season_index=0, week=4),
            first_publication_week=RankingWeek(season_index=0, week=5),
            expected_award_fingerprint=fp("d"),
        ),
        canonical_awards=canonical_awards,
        canonical_result=(SimpleNamespace() if canonical else None),
        fingerprint=fp("e"),
    )


@pytest.mark.pr_critical
def test_projection_uses_frozen_calendar_and_canonical_point_awards_only():
    projection = calendar_projection()
    snapshot = project_canonical_finals_race_snapshot(
        configuration=configuration(projection),
        calendar=projection,
        tournament_sources=(source(canonical=True),),
        transition_authority=transition(),
    )
    assert snapshot.source_event_ids == ("EVT-1",)
    assert [(row.player_id, row.race_points) for row in snapshot.rows] == [
        ("p1", 500)
    ]


@pytest.mark.pr_critical
def test_projection_rejects_legacy_only_eligible_tournament_source():
    projection = calendar_projection()
    with pytest.raises(
        ValueError,
        match="requires canonical point-award authority",
    ):
        project_canonical_finals_race_snapshot(
            configuration=configuration(projection),
            calendar=projection,
            tournament_sources=(source(canonical=False),),
            transition_authority=transition(),
        )
