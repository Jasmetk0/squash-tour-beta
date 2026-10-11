from __future__ import annotations

import pytest
from pydantic import ValidationError

from beta_engine.domain.players.intake_volume_policy import IntakeVolumePolicy, IntakeVolumePolicyConfig


def test_intake_volume_policy_annual_target_growth_band() -> None:
    policy = IntakeVolumePolicy()
    base = policy.plan_season(world_id="official_fax_world", season="2000/2001")
    later = policy.plan_season(world_id="official_fax_world", season="2010/2011")

    assert base.season_index == 0
    assert later.season_index == 10
    grown_base = 200 * ((1 + 0.015) ** later.season_index)
    assert later.annual_target > 200 * ((1 + 0.015) ** base.season_index) * 0.90
    assert grown_base * 0.90 <= later.annual_target <= grown_base * 1.10


def test_intake_volume_policy_is_deterministic_and_world_or_season_sensitive() -> None:
    policy = IntakeVolumePolicy()
    first = policy.plan_season(world_id="official_fax_world", season="2000/2001")
    second = policy.plan_season(world_id="official_fax_world", season="2000/2001")
    different_world = policy.plan_season(world_id="alternate_world", season="2000/2001")
    different_season = policy.plan_season(world_id="official_fax_world", season="2001/2002")

    assert first == second
    assert [week.week_weight for week in first.weeks] != [week.week_weight for week in different_world.weeks]
    assert first.season_variation_multiplier != different_season.season_variation_multiplier


def test_intake_volume_policy_weekly_sum_matches_annual_target() -> None:
    plan = IntakeVolumePolicy().plan_season(world_id="official_fax_world", season="2000/2001")

    assert sum(week.target_intake_count for week in plan.weeks) == plan.annual_target
    assert plan.total_weekly_target == plan.annual_target
    assert len(plan.weeks) == 61


def test_intake_volume_policy_weekly_targets_vary_for_default_target() -> None:
    plan = IntakeVolumePolicy().plan_season(
        world_id="official_fax_world",
        season="2000/2001",
        config=IntakeVolumePolicyConfig(base_annual_intake_target=200),
    )

    assert len({week.target_intake_count for week in plan.weeks}) > 1


def test_intake_volume_policy_bounds() -> None:
    plan = IntakeVolumePolicy().plan_season(world_id="official_fax_world", season="2000/2001")

    assert 0.90 <= plan.season_variation_multiplier <= 1.10
    assert all(0.55 <= week.week_weight <= 1.55 for week in plan.weeks)


def test_intake_volume_policy_validation() -> None:
    policy = IntakeVolumePolicy()
    with pytest.raises(ValueError, match="season_week"):
        policy.weekly_target(world_id="official_fax_world", season="2000/2001", season_week=0)
    with pytest.raises(ValidationError):
        IntakeVolumePolicyConfig(base_annual_intake_target=-1)
    with pytest.raises(ValidationError):
        IntakeVolumePolicyConfig(season_variation_min=1.2, season_variation_max=1.1)
    with pytest.raises(ValidationError):
        IntakeVolumePolicyConfig(week_weight_min=1.2, week_weight_max=1.1)


def test_intake_volume_policy_zero_target_allocates_zero_weeks() -> None:
    plan = IntakeVolumePolicy().plan_season(
        world_id="official_fax_world",
        season="2000/2001",
        config=IntakeVolumePolicyConfig(base_annual_intake_target=0),
    )

    assert plan.annual_target == 0
    assert plan.total_weekly_target == 0
    assert all(week.target_intake_count == 0 for week in plan.weeks)
