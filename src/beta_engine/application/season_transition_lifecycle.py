"""Ordinary Season Transition lifecycle staging for Week 61 -> next Season Week 1."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from beta_engine.application.season_transition_configuration import (
    validate_season_transition_configuration,
)
from beta_engine.domain.players.lifecycle import PlayerLifecycleWeekState
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.season_transition_configuration import (
    SeasonTransitionConfiguration,
)
from beta_engine.infrastructure.db.player_lifecycle_state import (
    advance_lifecycle_with_prospects,
    get_lifecycle,
    put_lifecycle,
)


class SeasonTransitionLifecycleStage(FrozenInput):
    schema_version: Literal["season_transition_lifecycle_stage.v1"] = (
        "season_transition_lifecycle_stage.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    configuration_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    target_state: PlayerLifecycleWeekState


def resolve_season_transition_lifecycle(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionLifecycleStage:
    """Calculate Week-1 lifecycle, including birth-week pre-Tour prospects.

    Prospect visibility is distinct from formal Tour entry. Target-week prospects are
    activated into canonical lifecycle with `tour_entry_week=None`; their incomplete
    sporting profile is allowed to remain outside the sporting snapshot until an
    operation actually requires simulation-valid sporting data.
    """

    configuration = validate_season_transition_configuration(session, configuration)
    predecessor = get_lifecycle(
        session,
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        week=configuration.completed_week,
    )
    if predecessor is None:
        raise ValueError("Season Transition predecessor lifecycle state is missing")

    target_state = advance_lifecycle_with_prospects(
        session,
        predecessor=predecessor,
        target=configuration.target_week,
    )
    if (
        target_state.week != configuration.target_week
        or target_state.predecessor_fingerprint != predecessor.fingerprint
    ):
        raise ValueError("Season Transition lifecycle candidate violates boundary lineage")

    return SeasonTransitionLifecycleStage(
        run_id=configuration.run_id,
        branch_id=configuration.branch_id,
        configuration_fingerprint=configuration.fingerprint,
        predecessor_lifecycle_fingerprint=predecessor.fingerprint,
        target_state=target_state,
    )


def stage_season_transition_lifecycle(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionLifecycleStage:
    """Persist the resolved lifecycle state inside a caller-owned Season transaction."""

    staged = resolve_season_transition_lifecycle(session, configuration)
    installed = put_lifecycle(session, staged.target_state)
    if installed.fingerprint != staged.target_state.fingerprint:
        raise ValueError("Season Transition lifecycle stage write could not be verified")
    return staged
