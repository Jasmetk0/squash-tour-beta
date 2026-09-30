from __future__ import annotations

import pytest

from beta_engine.application.initial_world import InitialWorldState
from beta_engine.application.season_player_bootstrap_service import SeasonActivePlayer
from beta_engine.application.viewer_people_read_model import (
    resolve_viewer_countries,
    resolve_viewer_players,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.initial_pool import GeneratedPlayerAttributes
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.models import HiddenCareerTraits
from beta_engine.domain.players.sporting import (
    PlayerSportingRecord,
    PlayerSportingWeekState,
)
from beta_engine.domain.rankings.official import RankingWeek
from beta_engine.infrastructure.db.run_prospect_source_state import (
    RunProspectSourceSnapshot,
)


pytestmark = pytest.mark.pr_critical

WEEK = RankingWeek(season_index=1, week=5)


def _initial_player(player_id: str, name: str, country: str) -> SeasonActivePlayer:
    traits = HiddenCareerTraits(
        potential_ceiling=99,
        growth_curve="Standard",
        professionalism=0.5,
        ambition=0.5,
        travel_tolerance=0.5,
        schedule_aggression=0.5,
        injury_proneness=0.1,
        resilience=0.6,
    )
    return SeasonActivePlayer(
        player_id=player_id,
        name=name,
        nationality=country,
        country_code=country,
        birth_year=1975,
        birth_year_week=1,
        age_years_at_season_start=25,
        age_weeks_at_season_start=25 * 61,
        current_ability=70,
        potential_ability=80,
        potential_tier="A",
        career_stage="prime",
        season="2000/2001",
        active_status="active",
        play_style="attacking",
        archetype="Power Attacker",
        hidden_career_traits=traits,
        attributes=GeneratedPlayerAttributes(
            technique=70,
            movement=70,
            physical=70,
            mental=70,
            consistency=70,
            clutch=70,
            recovery=70,
        ),
        source_pool_player_id=player_id,
        source_generation_fingerprint=f"profile:{player_id}",
        source_generation="initial_pool",
        manual_override=False,
        locked_from_initial_pool=True,
        bootstrap_fingerprint="bootstrap",
        bootstrap_seed=1,
        bootstrap_id="bootstrap",
    )


def _world() -> InitialWorldState:
    return InitialWorldState(
        run_id="run",
        branch_id="branch",
        players=(
            _initial_player("P1", "Initial One", "CZE"),
            _initial_player("P2", "Initial Two", "EGY"),
        ),
        source_kind="production_initial_pool.v1",
        source_season="2000/2001",
        source_fingerprint="source",
        bootstrap_seed=1,
        bootstrap_fingerprint="bootstrap",
        adopted_by_command_id="adopt",
        audit_label="test",
        audit_reason="test",
        adoption_request_fingerprint="1" * 64,
    )


def _lifecycle() -> tuple[PlayerLifecycleWeekState, ...]:
    players = (
        PlayerLifecycleIdentity(
            player_id="P1",
            birth_year=1975,
            birth_year_week=1,
            tie_break_token="token:P1",
            tie_break_provenance="test",
            tour_entry_week=RankingWeek(season_index=0, week=1),
            age=26,
            status="active",
            origin="initial",
        ),
        PlayerLifecycleIdentity(
            player_id="P2",
            birth_year=1975,
            birth_year_week=1,
            tie_break_token="token:P2",
            tie_break_provenance="test",
            tour_entry_week=RankingWeek(season_index=0, week=1),
            age=26,
            status="retired",
            retirement_effective_week=RankingWeek(season_index=1, week=3),
            origin="initial",
        ),
        PlayerLifecycleIdentity(
            player_id="PROSPECT-1",
            birth_year=1986,
            birth_year_week=5,
            tie_break_token="token:PROSPECT-1",
            tie_break_provenance="test",
            tour_entry_week=None,
            age=15,
            status="active",
            origin="prospect",
        ),
    )
    return (
        PlayerLifecycleWeekState(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            players=tuple(sorted(players, key=lambda item: item.player_id)),
            source_initial_world_fingerprint=_world().fingerprint,
        ),
    )


def _sporting_record(player_id: str, value: int) -> PlayerSportingRecord:
    return PlayerSportingRecord(
        player_id=player_id,
        attributes=tuple((name, value) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=min(200, value + 25),
        potential_identity=f"potential:{player_id}",
        potential_provenance="test",
        development_timing="Standard",
        current_form=100,
        long_term_form_norm=100,
        match_sharpness=50,
        long_term_fatigue=5,
    )


def _sporting() -> tuple[PlayerSportingWeekState, ...]:
    return (
        PlayerSportingWeekState(
            run_id="run",
            branch_id="branch",
            week=WEEK,
            players=(
                _sporting_record("P1", 130),
                _sporting_record("PROSPECT-1", 110),
            ),
            completed_context_fingerprint="context",
            source_initial_world_fingerprint=_world().fingerprint,
            stage_provenance="test",
        ),
    )


def _prospects() -> RunProspectSourceSnapshot:
    records = (
        {
            "prospect_id": "PROSPECT-1",
            "display_name": "Future Star",
            "country_code": "USA",
        },
    )
    return RunProspectSourceSnapshot(
        schema_version="run_prospect_source_snapshot.v1",
        run_id="run",
        records=records,
        fingerprint="test-fingerprint",
    )


def test_viewer_players_projects_current_saved_roster_without_internal_provenance() -> None:
    players = resolve_viewer_players(
        initial_world=_world(),
        lifecycle_states=_lifecycle(),
        sporting_states=_sporting(),
        prospect_source=_prospects(),
        run_id="run",
        branch_id="branch",
    )

    assert players.schema_version == "viewer_players.v1"
    assert players.season_index == 1
    assert players.week == 5
    assert players.player_count == 3
    assert players.active_player_count == 2
    assert players.retired_player_count == 1

    by_id = {player.player_id: player for player in players.players}
    assert by_id["P1"].name == "Initial One"
    assert by_id["P1"].country_code == "CZE"
    assert by_id["P1"].current_ovr == 130
    assert by_id["P1"].identity_source == "initial_world"

    assert by_id["P2"].status == "retired"
    assert by_id["P2"].current_ovr is None

    assert by_id["PROSPECT-1"].name == "Future Star"
    assert by_id["PROSPECT-1"].country_code == "USA"
    assert by_id["PROSPECT-1"].current_ovr == 110
    assert by_id["PROSPECT-1"].identity_source == "run_prospect"

    rendered = str(players.model_dump(mode="json"))
    for forbidden in (
        "fingerprint",
        "seed",
        "provenance",
        "tie_break",
        "source_generation",
        "potential_identity",
    ):
        assert forbidden not in rendered


def test_viewer_players_fail_closed_when_active_player_has_no_sporting_state() -> None:
    sporting = _sporting()[0].model_copy(
        update={
            "players": (_sporting_record("P1", 130),),
        }
    )

    with pytest.raises(ValueError, match="PROSPECT-1.*sporting"):
        resolve_viewer_players(
            initial_world=_world(),
            lifecycle_states=_lifecycle(),
            sporting_states=(sporting,),
            prospect_source=_prospects(),
            run_id="run",
            branch_id="branch",
        )


def test_viewer_players_rejects_mismatched_public_week() -> None:
    sporting = _sporting()[0].model_copy(
        update={"week": RankingWeek(season_index=1, week=4)}
    )

    with pytest.raises(ValueError, match="public weeks differ"):
        resolve_viewer_players(
            initial_world=_world(),
            lifecycle_states=_lifecycle(),
            sporting_states=(sporting,),
            prospect_source=_prospects(),
            run_id="run",
            branch_id="branch",
        )


def test_viewer_countries_aggregates_current_player_projection() -> None:
    players = resolve_viewer_players(
        initial_world=_world(),
        lifecycle_states=_lifecycle(),
        sporting_states=_sporting(),
        prospect_source=_prospects(),
        run_id="run",
        branch_id="branch",
    )

    countries = resolve_viewer_countries(players)

    assert countries.schema_version == "viewer_countries.v1"
    assert countries.country_count == 3
    by_code = {country.country_code: country for country in countries.countries}

    assert by_code["CZE"].player_count == 1
    assert by_code["CZE"].average_current_ovr == 130
    assert by_code["CZE"].top_player_id == "P1"

    assert by_code["EGY"].retired_player_count == 1
    assert by_code["EGY"].average_current_ovr is None

    assert by_code["USA"].active_player_count == 1
    assert by_code["USA"].top_player_name == "Future Star"
