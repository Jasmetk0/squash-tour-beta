"""Ordinary Season Transition Health V1 staging for Week 61 -> next Season Week 1."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from beta_engine.application.season_transition_configuration import (
    validate_season_transition_configuration,
)
from beta_engine.application.season_transition_lifecycle import (
    resolve_season_transition_lifecycle,
)
from beta_engine.domain.players.health import (
    PlayerHealthWeekState,
    carry_health_state_forward,
)
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.season_transition_configuration import (
    SeasonTransitionConfiguration,
)
from beta_engine.infrastructure.db.player_health_state import get_health, put_health


class SeasonTransitionHealthStage(FrozenInput):
    schema_version: Literal["season_transition_health_stage.v1"] = (
        "season_transition_health_stage.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_health_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_state: PlayerHealthWeekState


def resolve_season_transition_health(
    session,
    configuration: SeasonTransitionConfiguration,
    *,
    target_lifecycle: PlayerLifecycleWeekState | None = None,
) -> SeasonTransitionHealthStage:
    """Calculate cross-season health carry-forward without stochastic policy."""

    configuration = validate_season_transition_configuration(session, configuration)
    predecessor = get_health(
        session,
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.completed_week,
    )
    if predecessor is None:
        raise ValueError("Season Transition predecessor health state is missing")

    if target_lifecycle is None:
        target_lifecycle = resolve_season_transition_lifecycle(
            session, configuration
        ).target_state
    if (
        target_lifecycle.run_id,
        target_lifecycle.branch_id,
        target_lifecycle.week,
    ) != (
        configuration.run_id,
        configuration.branch_id,
        configuration.target_week,
    ):
        raise ValueError("Season Transition target lifecycle scope differs from Health")

    target_state = carry_health_state_forward(
        predecessor,
        target=configuration.target_week,
        target_player_ids=tuple(
            player.player_id for player in target_lifecycle.players
        ),
    )
    return SeasonTransitionHealthStage(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        configuration_fingerprint=configuration.fingerprint,
        predecessor_health_fingerprint=predecessor.fingerprint,
        target_state=target_state,
    )


def stage_season_transition_health(
    session,
    configuration: SeasonTransitionConfiguration,
    *,
    target_lifecycle: PlayerLifecycleWeekState,
) -> SeasonTransitionHealthStage:
    """Persist Health V1 target state inside the caller-owned Season transaction."""

    staged = resolve_season_transition_health(
        session,
        configuration,
        target_lifecycle=target_lifecycle,
    )
    installed = put_health(session, staged.target_state)
    if installed.fingerprint != staged.target_state.fingerprint:
        raise ValueError("Season Transition health stage write could not be verified")
    return staged
