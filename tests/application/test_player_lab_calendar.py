"""Versioned calendar replay, production-kernel oracle and immutable v1 bytes."""

from types import SimpleNamespace

import pytest

from beta_engine.application.historical_lab_source import HistoricalLabPlayer
from beta_engine.application.player_test_lab_service import (
    PlayerLabRequest,
    PlayerLabScenarioV2,
    PlayerLabVariant,
    PlayerTestLabService,
)
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_health import CalendarHealthProfile
from beta_engine.domain.players.calendar_sporting_week import develop_and_recover
from tests.application.test_player_test_lab_service import _player

pytestmark = pytest.mark.pr_critical


def scenario(clock, season=1, week=None, duration=2):
    week = RunWeekPosition(
        calendar=clock, season_index=season, week=week or clock.weeks_per_year
    )
    player = _player()
    health = CalendarHealthProfile(player_id=player.player_id)
    birth_year, birth_week = clock.start_year - 20, clock.weeks_per_year
    snapshot = HistoricalLabPlayer(
        run_id="run",
        selected_branch_id="fork",
        owner_branch_id="owner",
        saved_revision_id="old",
        saved_revision_content_hash="a" * 64,
        week=week,
        sporting_fingerprint="b" * 64,
        profile_fingerprint="c" * 64,
        biography={
            "name": "Player",
            "birth_year": birth_year,
            "birth_year_week": birth_week,
        },
        player=player,
        health=health,
        health_source_week=week.model_dump(mode="json"),
        health_fingerprint="d" * 64,
    )
    return PlayerLabScenarioV2(
        scenario_id="calendar",
        player=player,
        birth_year=birth_year,
        birth_year_week=birth_week,
        start_week=week,
        initial_health=health,
        source_snapshot=snapshot,
        variants=(
            PlayerLabVariant(
                variant_id="active",
                display_name="Active",
                competitive_match_counts=(1,) * duration,
            ),
        ),
    )


@pytest.mark.parametrize("width,offset", [(52, 35), (61, 37), (80, 80)])
def test_calendar_scenario_uses_actual_year_season_boundary_and_production_formula(
    width, offset
):
    draft = scenario(RunCalendar(width, offset, 2070, 5))
    request = PlayerLabRequest(scenario=draft)
    service = PlayerTestLabService()
    result = service.run(request)
    assert result == service.run(
        PlayerLabRequest.model_validate_json(request.model_dump_json())
    )
    snapshots = result.variants[0].snapshots
    assert (snapshots[0].week.season_index, snapshots[0].week.week) == (2, 1)
    assert snapshots[0].week.calendar.start_year == 2070
    assert snapshots[0].age == (22 if offset == width else 21)
    if offset == width:
        assert snapshots[1].age == 22
    _, expected = develop_and_recover(
        SimpleNamespace(
            players=(draft.player,),
            week=draft.start_week,
            fingerprint=result.variants[0].initial_state_fingerprint,
        ),
        SimpleNamespace(
            players=(
                SimpleNamespace(
                    player_id=draft.player.player_id,
                    birth_year=draft.birth_year,
                    birth_year_week=draft.birth_year_week,
                ),
            )
        ),
        completed_week=draft.start_week,
        seed=draft.seed,
        policy=draft.development_policy,
        counts=((draft.player.player_id, 1),),
    )
    assert snapshots[0].ovr == expected[0].ovr
    assert snapshots[0].current_form == expected[0].current_form
    assert snapshots[0].long_term_fatigue == expected[0].long_term_fatigue


def test_year_rollover_and_performance_limit_are_distinct_from_run_horizon():
    draft = scenario(RunCalendar(80, 80, 2200, 120), season=70, week=1)
    result = PlayerTestLabService().run(PlayerLabRequest(scenario=draft))
    assert result.variants[0].snapshots[0].week.calendar_position.calendar_year == 2271
    assert result.variants[0].snapshots[0].age == 90
    with pytest.raises(ValueError, match="execution budget"):
        scenario(RunCalendar(80, 1, 2200, 120), duration=62)
    with pytest.raises(ValueError, match="horizon"):
        scenario(RunCalendar(52, 1, 2030, 2), season=1)
    with pytest.raises(ValueError, match="birthday"):
        PlayerLabScenarioV2.model_validate_json(
            draft.model_copy(update={"birth_year_week": 81}).model_dump_json()
        )


@pytest.mark.parametrize(
    "index,scenario_hash,result_hash",
    [
        (
            0,
            "a7e102ef7f959a908a3e90c5bddbd27ab8ad8c7756bd1f6c4f3a8e9c522f20b2",
            "db1021545841d30d0d69c8cdfd44f260e025d18edf85b9d30ef63dfccb5c5c22",
        ),
        (
            1,
            "186817f8cf8b0b65ff6ee0a772ae14682fc4f31b1a6acaff068a4fcbde628d02",
            "9479d16edabbe8ab2527880b000a298dbfa88bb54f2971c22e6f6f8671f77962",
        ),
    ],
)
def test_v1_saved_scenario_and_result_bytes_match_owner_merged_405b569c(
    index, scenario_hash, result_hash
):
    from beta_engine.domain.run_packages import canonical_hash

    service = PlayerTestLabService()
    draft = service.list_built_in_scenarios()[index].scenario
    assert draft.fingerprint == scenario_hash
    result = service.run(PlayerLabRequest(scenario=draft))
    assert canonical_hash(result.model_dump(mode="json")) == result_hash


def test_calendar_health_dates_roundtrip_without_healing_or_match_penalty_invention():
    from beta_engine.application.historical_lab_source import match_projection
    from beta_engine.domain.players.calendar_health import CalendarHealthRecord

    draft = scenario(RunCalendar(80, 80, 2030, 4), season=1)
    injury = CalendarHealthProfile(
        player_id=draft.player.player_id,
        records=(
            CalendarHealthRecord(
                record_id="injury",
                kind="Injury",
                condition_key="ankle",
                lifecycle="Active",
                severity=20,
                affected_domains=("movement",),
                onset_week=draft.start_week,
                recovery_window_min_weeks=2,
                recovery_window_max_weeks=5,
                provenance="explicit Health test",
            ),
        ),
    )
    draft = draft.model_copy(update={"initial_health": injury})
    request = PlayerLabRequest.model_validate_json(
        PlayerLabRequest(scenario=draft).model_dump_json()
    )
    assert request.scenario.initial_health.records[0].onset_week == draft.start_week
    result = PlayerTestLabService().run(request)
    assert all(
        s.health_projection.highest_current_severity == 20
        for s in result.variants[0].snapshots
    )
    copied = draft.source_snapshot.model_copy(
        update={
            "health": injury,
            "biography": {**draft.source_snapshot.biography, "status": "active"},
        }
    )
    with pytest.raises(ValueError, match="unsupported numeric"):
        match_projection(copied)
