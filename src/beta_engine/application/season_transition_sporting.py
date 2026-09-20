"""Ordinary Season Transition sporting staging for Week 61 -> next Season Week 1."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from beta_engine.application.season_transition_configuration import (
    validate_season_transition_configuration,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.season_transition_configuration import (
    SeasonTransitionConfiguration,
    policy_fingerprint,
)
from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)
from beta_engine.infrastructure.db.models import CompletedWeekSportingContextModel
from beta_engine.infrastructure.db.player_lifecycle_state import get_lifecycle
from beta_engine.infrastructure.db.player_sporting_state import (
    get_completed_context,
    get_sporting,
    preflight_completed_context_from_authoritative_matches,
    put_completed_context,
    put_sporting,
    stage_sporting_transition,
)


class SeasonTransitionSportingStage(FrozenInput):
    schema_version: Literal["season_transition_sporting_stage.v1"] = (
        "season_transition_sporting_stage.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_sporting_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_context: CompletedWeekSportingContext
    target_state: PlayerSportingWeekState
    applied_outgoing_development_policy_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )
    effective_target_development_policy_fingerprint: str = Field(
        pattern=r"^[0-9a-f]{64}$"
    )


def _completed_context(
    session,
    *,
    configuration: SeasonTransitionConfiguration,
    sporting: PlayerSportingWeekState,
) -> CompletedWeekSportingContext:
    key = (
        configuration.run_id,
        configuration.branch_id,
        configuration.completed_week.ordinal,
    )
    row = session.get(CompletedWeekSportingContextModel, key)
    if row is not None:
        return get_completed_context(
            session,
            run_id=configuration.run_id,
            branch_id=configuration.branch_id,
            completed_week=configuration.completed_week,
        )
    return preflight_completed_context_from_authoritative_matches(
        session,
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        completed_week=configuration.completed_week,
        player_ids=tuple(player.player_id for player in sporting.players),
    )


def resolve_season_transition_sporting(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionSportingStage:
    """Calculate the ordinary cross-season sporting candidate without persistence."""

    configuration = validate_season_transition_configuration(session, configuration)
    predecessor = get_sporting(
        session,
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.completed_week,
    )
    lifecycle = get_lifecycle(
        session,
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.completed_week,
    )
    if predecessor is None:
        raise ValueError("Season Transition predecessor sporting state is missing")
    if lifecycle is None:
        raise ValueError("Season Transition predecessor lifecycle state is missing")

    context = _completed_context(
        session,
        configuration=configuration,
        sporting=predecessor,
    )
    terminal_players = None
    if context.terminal_sporting_fingerprint:
        from beta_engine.application.authoritative_slot_matches import (
            AuthoritativeSlotMatchExecutor,
        )

        terminal = AuthoritativeSlotMatchExecutor(session).terminal_checkpoint(
            run_id=configuration.run_id,
            branch_id=configuration.branch_id,
            week=configuration.completed_week,
        )
        if (
            terminal is None
            or terminal.fingerprint != context.terminal_sporting_fingerprint
        ):
            raise ValueError("Season Transition terminal sporting head mismatch")
        terminal_players = terminal.players

    target_state = stage_sporting_transition(
        predecessor=predecessor,
        context=context,
        lifecycle=lifecycle,
        target=configuration.target_week,
        target_effective_development_policy=configuration.target_development_policy,
        terminal_players=terminal_players,
    )

    applied = target_state.applied_development_policy_fingerprint
    effective = policy_fingerprint(target_state.effective_development_policy)
    if (
        target_state.week != configuration.target_week
        or target_state.predecessor_fingerprint
        != configuration.predecessor_sporting_fingerprint
        or applied != configuration.outgoing_development_policy_fingerprint
        or effective
        != policy_fingerprint(configuration.target_development_policy)
    ):
        raise ValueError(
            "Season Transition sporting candidate violates outgoing/incoming policy boundary"
        )

    return SeasonTransitionSportingStage(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        configuration_fingerprint=configuration.fingerprint,
        predecessor_sporting_fingerprint=predecessor.fingerprint,
        completed_context=context,
        target_state=target_state,
        applied_outgoing_development_policy_fingerprint=applied,
        effective_target_development_policy_fingerprint=effective,
    )


def stage_season_transition_sporting(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionSportingStage:
    """Persist the resolved sporting pieces inside a caller-owned Season transaction."""

    staged = resolve_season_transition_sporting(session, configuration)
    put_completed_context(session, staged.completed_context)
    installed = put_sporting(session, staged.target_state)
    if installed.fingerprint != staged.target_state.fingerprint:
        raise ValueError("Season Transition sporting stage write could not be verified")
    return staged
