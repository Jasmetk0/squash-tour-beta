"""Ordinary Season Transition lifecycle staging for Week 61 -> next Season Week 1."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from sqlalchemy import select

from beta_engine.application.season_transition_configuration import (
    validate_season_transition_configuration,
)
from beta_engine.domain.calendar.season_weeks import season_week_to_calendar_position
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleWeekState,
    advance_lifecycle,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.season_transition_configuration import (
    SeasonTransitionConfiguration,
)
from beta_engine.infrastructure.db.models import RunProspectModel
from beta_engine.infrastructure.db.player_lifecycle_state import (
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


def _target_prospect_ids(
    session,
    configuration: SeasonTransitionConfiguration,
) -> tuple[str, ...]:
    position = season_week_to_calendar_position(
        2000 + configuration.target_week.season_index,
        configuration.target_week.week,
    )
    return tuple(
        session.scalars(
            select(RunProspectModel.prospect_id)
            .where(
                RunProspectModel.run_id == configuration.run_id,
                RunProspectModel.season_start_year
                == 2000 + configuration.target_week.season_index,
                RunProspectModel.season_week == configuration.target_week.week,
                RunProspectModel.calendar_year == position.calendar_year,
                RunProspectModel.year_week == position.year_week,
            )
            .order_by(RunProspectModel.prospect_id)
        )
    )


def resolve_season_transition_lifecycle(
    session,
    configuration: SeasonTransitionConfiguration,
) -> SeasonTransitionLifecycleStage:
    """Calculate existing-player Week-1 lifecycle without persisting it.

    Prospect/Tour-entry activation remains a separate fail-closed Season Transition
    step. This kernel must never silently omit a Run-scoped prospect that belongs to
    the opening week.
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

    prospect_ids = _target_prospect_ids(session, configuration)
    if prospect_ids:
        raise ValueError(
            "Season Transition target week has unbridged Run prospects: "
            + ", ".join(prospect_ids)
        )

    target_state = advance_lifecycle(predecessor, configuration.target_week)
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
