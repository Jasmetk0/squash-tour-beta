"""Pure deterministic annual and weekly 15-year-old intake volume policy."""

from __future__ import annotations

import hashlib
import math

from pydantic import BaseModel, ConfigDict, Field, model_validator

from beta_engine.domain.calendar import parse_season_start_year
from beta_engine.domain.calendar.season_labels import long_season_label_from_start_year
from beta_engine.domain.calendar.season_weeks import TOTAL_SEASON_WEEKS

BASE_ANNUAL_INTAKE_TARGET = 200
SEASON_GROWTH_RATE = 0.015
SEASON_VARIATION_MIN = 0.90
SEASON_VARIATION_MAX = 1.10
WEEK_WEIGHT_MIN = 0.55
WEEK_WEIGHT_MAX = 1.55
WEEKS_PER_SEASON = TOTAL_SEASON_WEEKS


class IntakeVolumePolicyConfig(BaseModel):
    """Configuration for deterministic intake cohort volume planning."""

    model_config = ConfigDict(extra="forbid")

    base_annual_intake_target: int = Field(default=BASE_ANNUAL_INTAKE_TARGET, ge=0)
    season_growth_rate: float = Field(default=SEASON_GROWTH_RATE, ge=0.0)
    season_variation_min: float = Field(default=SEASON_VARIATION_MIN, gt=0.0)
    season_variation_max: float = Field(default=SEASON_VARIATION_MAX, gt=0.0)
    week_weight_min: float = Field(default=WEEK_WEIGHT_MIN, gt=0.0)
    week_weight_max: float = Field(default=WEEK_WEIGHT_MAX, gt=0.0)
    policy_version: str = "v1"

    @model_validator(mode="after")
    def validate_ranges(self) -> "IntakeVolumePolicyConfig":
        if self.season_variation_max < self.season_variation_min:
            raise ValueError("season_variation_max must be greater than or equal to season_variation_min")
        if self.week_weight_max < self.week_weight_min:
            raise ValueError("week_weight_max must be greater than or equal to week_weight_min")
        return self


class WeeklyIntakeVolume(BaseModel):
    """Read-only target volume for a single season week."""

    model_config = ConfigDict(extra="forbid")

    season: str
    season_start_year: int
    season_week: int = Field(ge=1, le=WEEKS_PER_SEASON)
    target_intake_count: int = Field(ge=0)
    week_weight: float = Field(gt=0.0)


class SeasonIntakeVolumePlan(BaseModel):
    """Read-only annual intake target and weighted weekly allocation plan."""

    model_config = ConfigDict(extra="forbid")

    world_id: str
    season: str
    season_start_year: int
    season_index: int
    base_annual_intake_target: int
    season_growth_rate: float
    season_variation_multiplier: float
    annual_target: int
    total_weekly_target: int
    weeks: list[WeeklyIntakeVolume]


class IntakeVolumePolicy:
    """Plans intake cohort slot counts without generating or persisting players."""

    def plan_season(
        self,
        *,
        world_id: str,
        season: str | int,
        config: IntakeVolumePolicyConfig | None = None,
    ) -> SeasonIntakeVolumePlan:
        policy_config = config or IntakeVolumePolicyConfig()
        season_start_year = parse_season_start_year(season) if isinstance(season, str) else season
        if not isinstance(season_start_year, int):
            raise ValueError("season_start_year must be an integer")
        season_label = long_season_label_from_start_year(season_start_year)
        season_index = season_start_year - 2000
        variation = self._mapped_float(
            f"intake-volume|{policy_config.policy_version}|{world_id}|{season_label}|season-variation",
            policy_config.season_variation_min,
            policy_config.season_variation_max,
        )
        grown_base = policy_config.base_annual_intake_target * ((1 + policy_config.season_growth_rate) ** season_index)
        annual_target = round(grown_base * variation)
        weights = [
            self._mapped_float(
                f"intake-volume|{policy_config.policy_version}|{world_id}|{season_label}|week|{season_week}",
                policy_config.week_weight_min,
                policy_config.week_weight_max,
            )
            for season_week in range(1, WEEKS_PER_SEASON + 1)
        ]
        targets = self._allocate_weighted(annual_target=annual_target, weights=weights)
        weeks = [
            WeeklyIntakeVolume(
                season=season_label,
                season_start_year=season_start_year,
                season_week=index + 1,
                target_intake_count=targets[index],
                week_weight=weights[index],
            )
            for index in range(WEEKS_PER_SEASON)
        ]
        return SeasonIntakeVolumePlan(
            world_id=world_id,
            season=season_label,
            season_start_year=season_start_year,
            season_index=season_index,
            base_annual_intake_target=policy_config.base_annual_intake_target,
            season_growth_rate=policy_config.season_growth_rate,
            season_variation_multiplier=variation,
            annual_target=annual_target,
            total_weekly_target=sum(targets),
            weeks=weeks,
        )

    def weekly_target(
        self,
        *,
        world_id: str,
        season: str | int,
        season_week: int,
        config: IntakeVolumePolicyConfig | None = None,
    ) -> int:
        if season_week < 1 or season_week > WEEKS_PER_SEASON:
            raise ValueError(f"season_week must be between 1 and {WEEKS_PER_SEASON}")
        return self.plan_season(world_id=world_id, season=season, config=config).weeks[season_week - 1].target_intake_count

    @staticmethod
    def _mapped_float(key: str, lower: float, upper: float) -> float:
        digest = hashlib.blake2b(key.encode("utf-8"), digest_size=8).digest()
        unit = int.from_bytes(digest, byteorder="big", signed=False) / ((1 << 64) - 1)
        return lower + (upper - lower) * unit

    @staticmethod
    def _allocate_weighted(*, annual_target: int, weights: list[float]) -> list[int]:
        if annual_target == 0:
            return [0 for _ in weights]
        total_weight = sum(weights)
        raw = [annual_target * weight / total_weight for weight in weights]
        targets = [math.floor(value) for value in raw]
        remainder = annual_target - sum(targets)
        order = sorted(range(len(raw)), key=lambda index: (-(raw[index] - math.floor(raw[index])), index + 1))
        for index in order[:remainder]:
            targets[index] += 1
        return targets
