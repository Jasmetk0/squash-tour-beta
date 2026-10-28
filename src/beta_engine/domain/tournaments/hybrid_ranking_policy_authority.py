"""Immutable explicit ranking configuration for one hybrid Tournament Edition."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentHybridRankingPolicyAuthority(FrozenInput):
    """Explicit phase-award policy; no numeric value is inferred by the engine."""

    schema_version: Literal["tournament_hybrid_ranking_policy_authority.v1"] = (
        "tournament_hybrid_ranking_policy_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    configured_by_command_id: str = Field(min_length=1, max_length=128)
    group_component_policy_id: Literal["played_group_match_win_only.v1"] = (
        "played_group_match_win_only.v1"
    )
    played_group_win_points: int = Field(ge=0)
    knockout_stage_points: tuple[tuple[str, int], ...] = Field(min_length=2)
    composition_policy_id: Literal[
        "single_tournament_sum_group_plus_knockout_no_double_count.v1"
    ] = "single_tournament_sum_group_plus_knockout_no_double_count.v1"

    @model_validator(mode="after")
    def validate_policy(self) -> TournamentHybridRankingPolicyAuthority:
        stages = dict(self.knockout_stage_points)
        if (
            len(stages) != len(self.knockout_stage_points)
            or tuple(sorted(stages.items())) != self.knockout_stage_points
            or any(not key.strip() or value < 0 for key, value in stages.items())
        ):
            raise ValueError("Hybrid ranking knockout stage table must be unique and sorted")
        if "champion" not in stages or "finalist" not in stages:
            raise ValueError(
                "Hybrid ranking knockout table requires champion and finalist values"
            )
        return self

    @property
    def fingerprint(self) -> str:
        return _hash(self.model_dump(mode="json"))


def hybrid_phase_point_components(*, policy, played_group_wins, knockout_reached_stage):
    """Shared pure composition for legacy and native single-Edition awards."""
    from beta_engine.domain.tournaments.point_award_authority import (
        TournamentPhasePointComponent,
    )

    components = [TournamentPhasePointComponent(
        component_id='group_played_wins', distribution_key='group:played_win',
        units=played_group_wins, points_per_unit=policy.played_group_win_points,
        points_awarded=played_group_wins * policy.played_group_win_points,
    )]
    if knockout_reached_stage is not None:
        table = dict(policy.knockout_stage_points)
        if knockout_reached_stage not in table:
            raise ValueError('Hybrid ranking policy lacks knockout stage values: ' + knockout_reached_stage)
        value = table[knockout_reached_stage]
        components.append(TournamentPhasePointComponent(
            component_id='knockout_finish', distribution_key='knockout:' + knockout_reached_stage,
            units=1, points_per_unit=value, points_awarded=value,
        ))
    return tuple(components)
