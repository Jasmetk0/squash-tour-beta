"""Versioned calibration for hidden rally control and pressure development."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RallyCalibrationProfile(BaseModel):
    """Frozen numeric inputs for the first hidden-control pre-alpha model."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["rally_calibration_profile.v1"] = (
        "rally_calibration_profile.v1"
    )
    calibration_version: Literal["pre_alpha_control_v1"] = "pre_alpha_control_v1"
    cohort_profile: Literal["elite_men"] = "elite_men"
    maximum_control_segments: Literal[24] = 24
    opening_terminal_probability: float = Field(default=0.075, ge=0, le=1)
    base_segment_closure_probability: float = Field(default=0.14, ge=0, le=1)
    early_closure_growth_per_segment: float = Field(default=0.012, ge=0, le=1)
    late_closure_starts_after_segment: int = Field(default=10, ge=1, le=23)
    late_closure_growth_per_segment: float = Field(default=0.045, ge=0, le=1)
    fast_segment_shot_cdf: tuple[float, float, float, float] = (
        0.12,
        0.60,
        0.89,
        0.975,
    )
    balanced_segment_shot_cdf: tuple[float, float, float, float] = (
        0.10,
        0.54,
        0.86,
        0.97,
    )
    patient_segment_shot_cdf: tuple[float, float, float, float] = (
        0.06,
        0.38,
        0.76,
        0.94,
    )
    fast_seconds_per_shot_range: tuple[float, float] = (0.72, 0.98)
    balanced_seconds_per_shot_range: tuple[float, float] = (0.94, 1.24)
    patient_seconds_per_shot_range: tuple[float, float] = (1.14, 1.48)
    opening_elapsed_seconds_range: tuple[float, float] = (1.05, 1.70)
    serve_fault_elapsed_seconds_range: tuple[float, float] = (0.48, 0.82)
    terminal_elapsed_seconds_range: tuple[float, float] = (0.45, 0.85)
    stay_transition_weight: float = Field(default=0.58, gt=0)
    local_transition_weight: float = Field(default=0.185, gt=0)
    significant_break_weight: float = Field(default=0.022, gt=0)
    direct_reversal_weight: float = Field(default=0.0015, gt=0)
    transition_direction_log_weight: float = Field(default=0.38, ge=0, le=1)
    final_control_logit_weight: float = Field(default=0.42, ge=0, le=2)
    mean_control_logit_weight: float = Field(default=0.18, ge=0, le=2)
    pressure_workload_per_control_step: float = Field(default=0.075, ge=0, le=0.25)
    controlled_workload_relief_per_step: float = Field(default=0.035, ge=0, le=0.25)
    low_reserve_effort_change_probability: float = Field(default=0.42, ge=0, le=1)
    strong_pressure_effort_change_probability: float = Field(default=0.28, ge=0, le=1)
    tactical_effort_change_probability: float = Field(default=0.035, ge=0, le=1)

    @model_validator(mode="after")
    def validate_closure_profile(self) -> RallyCalibrationProfile:
        if (
            self.late_closure_growth_per_segment
            <= self.early_closure_growth_per_segment
        ):
            raise ValueError("late closure growth must exceed early closure growth")
        if not (
            self.stay_transition_weight
            > self.local_transition_weight
            > self.significant_break_weight
            > self.direct_reversal_weight
        ):
            raise ValueError("control transition weights must preserve local inertia")
        for shot_cdf in (
            self.fast_segment_shot_cdf,
            self.balanced_segment_shot_cdf,
            self.patient_segment_shot_cdf,
        ):
            if not (0 < shot_cdf[0] < shot_cdf[1] < shot_cdf[2] < shot_cdf[3] < 1):
                raise ValueError("segment shot CDF must be strictly increasing")
        for duration_range in (
            self.fast_seconds_per_shot_range,
            self.balanced_seconds_per_shot_range,
            self.patient_seconds_per_shot_range,
            self.opening_elapsed_seconds_range,
            self.serve_fault_elapsed_seconds_range,
            self.terminal_elapsed_seconds_range,
        ):
            if not 0 < duration_range[0] < duration_range[1]:
                raise ValueError("rally duration range must be positive and ordered")
        return self
