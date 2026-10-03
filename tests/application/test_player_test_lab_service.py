"""Player Test Lab V1 shared-development-kernel coverage."""

import pytest

from beta_engine.application.player_test_lab_service import (
    PlayerLabRequest,
    PlayerLabScenario,
    PlayerLabVariant,
    PlayerTestLabService,
)
from beta_engine.domain.players.attribute_catalog import CANONICAL_PLAYER_ATTRIBUTES
from beta_engine.domain.players.health import PlayerHealthProfile, PlayerHealthRecord
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import RankingWeek


def _player() -> PlayerSportingRecord:
    return PlayerSportingRecord(
        player_id="P-LAB",
        attributes=tuple((name, 100) for name in CANONICAL_PLAYER_ATTRIBUTES),
        potential_ovr=160,
        potential_identity="potential:P-LAB",
        potential_provenance="test",
        development_timing="Standard",
        current_form=100,
        long_term_form_norm=100,
        match_sharpness=80,
        long_term_fatigue=20,
    )


def _scenario(*, variants, start_week=None) -> PlayerLabScenario:
    return PlayerLabScenario(
        scenario_id="test-player-lab",
        player=_player(),
        birth_year=1980,
        birth_year_week=1,
        start_week=start_week or RankingWeek(season_index=0, week=1),
        variants=variants,
    )


@pytest.mark.pr_critical
def test_player_lab_uses_shared_kernels_and_keeps_run_boundary_isolated():
    service = PlayerTestLabService()
    scenario = _scenario(
        variants=(
            PlayerLabVariant(
                variant_id="active",
                display_name="Active",
                competitive_match_counts=(1, 1, 1, 1),
            ),
            PlayerLabVariant(
                variant_id="idle",
                display_name="Idle",
                competitive_match_counts=(0, 0, 0, 0),
            ),
        )
    )

    first = service.run(PlayerLabRequest(scenario=scenario))
    second = service.run(PlayerLabRequest(scenario=scenario))

    assert first == second
    assert first.scenario_fingerprint == scenario.fingerprint
    assert first.compatibility.production_kernels == (
        "weekly_player_development_update",
        "between_week_state_update",
    )
    assert first.compatibility.run_mutation_performed is False
    assert first.compatibility.run_live_link is False
    assert first.compatibility.health_supported is True
    assert first.compatibility.training_load_supported is False
    assert first.compatibility.career_ai_supported is False
    assert first.diagnostics.variant_count == 2
    assert first.diagnostics.duration_weeks == 4

    by_variant = {item.variant_id: item for item in first.variants}
    assert by_variant["active"].final_player.match_sharpness == 80
    assert by_variant["idle"].final_player.match_sharpness == 72
    assert len(by_variant["active"].snapshots) == 4
    assert by_variant["active"].snapshots[-1].week == RankingWeek(
        season_index=0, week=5
    )


@pytest.mark.pr_critical
def test_player_lab_projects_explicit_health_timeline_without_inventing_numeric_effect():
    service = PlayerTestLabService()
    start = RankingWeek(season_index=0, week=1)
    active = PlayerHealthProfile(
        player_id="P-LAB",
        records=(
            PlayerHealthRecord(
                record_id="ankle",
                kind="Injury",
                condition_key="ankle",
                lifecycle="Active",
                severity=40,
                affected_domains=("movement",),
                onset_week=start,
                recovery_window_min_weeks=1,
                recovery_window_max_weeks=4,
                provenance="test",
            ),
        ),
    )
    recovering = PlayerHealthProfile(
        player_id="P-LAB",
        records=(
            active.records[0].model_copy(
                update={"lifecycle": "Recovering", "severity": 20}
            ),
        ),
    )
    recovered = PlayerHealthProfile(
        player_id="P-LAB",
        records=(
            active.records[0].model_copy(
                update={
                    "lifecycle": "Recovered",
                    "severity": 0,
                    "recovered_week": RankingWeek(season_index=0, week=3),
                }
            ),
        ),
    )
    scenario = _scenario(
        variants=(
            PlayerLabVariant(
                variant_id="health",
                display_name="Health",
                competitive_match_counts=(0, 0),
                health_timeline=(active, recovering, recovered),
            ),
        )
    )

    result = service.run(PlayerLabRequest(scenario=scenario))
    variant = result.variants[0]

    assert result.compatibility.health_supported is True
    assert variant.initial_health_projection.highest_current_severity == 40
    assert variant.initial_health_projection.affected_domains == ("movement",)
    assert variant.initial_health_projection.numeric_effect_applied is False
    assert variant.initial_health_projection.numeric_calibration_required is True
    assert variant.snapshots[0].health_projection.highest_current_severity == 20
    assert variant.snapshots[0].health_projection.numeric_effect_applied is False
    assert variant.snapshots[1].health_projection.highest_current_severity == 0
    assert variant.snapshots[1].health_projection.current_records == ()
    assert variant.snapshots[1].health_projection.numeric_calibration_required is False
    assert (
        variant.snapshots[1].health_projection_fingerprint
        == variant.snapshots[1].health_projection.fingerprint
    )


@pytest.mark.pr_critical
def test_player_lab_variant_label_does_not_change_sporting_rng():
    service = PlayerTestLabService()
    scenario = _scenario(
        variants=(
            PlayerLabVariant(
                variant_id="a",
                display_name="Label A",
                competitive_match_counts=(0, 1, 0),
            ),
            PlayerLabVariant(
                variant_id="b",
                display_name="Completely different label",
                competitive_match_counts=(0, 1, 0),
            ),
        )
    )

    result = service.run(PlayerLabRequest(scenario=scenario))

    assert result.variants[0].final_state_fingerprint == result.variants[1].final_state_fingerprint
    assert result.variants[0].final_player == result.variants[1].final_player
    assert result.diagnostics.distinct_final_state_count == 1


@pytest.mark.pr_critical
def test_player_lab_can_cross_season_boundary_without_run_persistence():
    service = PlayerTestLabService()
    scenario = _scenario(
        start_week=RankingWeek(season_index=0, week=61),
        variants=(
            PlayerLabVariant(
                variant_id="baseline",
                display_name="Baseline",
                competitive_match_counts=(0,),
            ),
        ),
    )

    result = service.run(PlayerLabRequest(scenario=scenario))

    assert result.variants[0].snapshots[0].week == RankingWeek(
        season_index=1, week=1
    )
    assert result.variants[0].snapshots[0].age >= 20


def test_player_lab_rejects_misaligned_variant_horizons():
    with pytest.raises(ValueError, match="same number of weeks"):
        _scenario(
            variants=(
                PlayerLabVariant(
                    variant_id="a",
                    display_name="A",
                    competitive_match_counts=(0,),
                ),
                PlayerLabVariant(
                    variant_id="b",
                    display_name="B",
                    competitive_match_counts=(0, 0),
                ),
            )
        )
