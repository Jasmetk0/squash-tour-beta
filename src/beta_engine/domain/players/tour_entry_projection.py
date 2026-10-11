"""Pure Tour-entry overlay for immutable lifecycle week snapshots."""

from __future__ import annotations

from collections.abc import Iterable

from beta_engine.domain.calendar.season_weeks import (
    age_at_calendar_position,
    season_week_to_calendar_position,
)
from beta_engine.domain.players.lifecycle import (
    PlayerLifecycleIdentity,
    PlayerLifecycleWeekState,
)
from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger


def _age_at_trigger(
    player: PlayerLifecycleIdentity,
    trigger: PlayerTourEntryTrigger,
) -> int:
    position = season_week_to_calendar_position(
        2000 + trigger.trigger_week.season_index,
        trigger.trigger_week.week,
    )
    return age_at_calendar_position(
        birth_year=player.birth_year,
        birth_year_week=player.birth_year_week,
        calendar_year=position.calendar_year,
        year_week=position.year_week,
    )


def project_lifecycle_tour_entries(
    state: PlayerLifecycleWeekState,
    triggers: Iterable[PlayerTourEntryTrigger],
) -> PlayerLifecycleWeekState:
    """Overlay all Tour-entry triggers effective by this snapshot week.

    PlayerLifecycleWeekState remains immutable historical week-boundary truth.
    This projection never mutates the stored predecessor and never changes age,
    retirement or predecessor lineage. It only derives the career-status field that
    became effective through an append-only Tour-entry trigger at or before
    state.week.

    Future trigger history is intentionally ignored so an old week can still be read
    from a Branch that later accumulated additional Tour entrants.
    """

    canonical = tuple(
        sorted(
            triggers,
            key=lambda item: (
                item.trigger_week.ordinal,
                item.decision_slot_ordinal,
                item.player_id,
            ),
        )
    )
    if len({item.player_id for item in canonical}) != len(canonical):
        raise ValueError("Tour-entry projection requires at most one trigger per player")
    if any(
        (item.run_id, item.branch_id) != (state.run_id, state.branch_id)
        for item in canonical
    ):
        raise ValueError("Tour-entry trigger scope differs from lifecycle state")

    effective = tuple(
        item for item in canonical if item.trigger_week.ordinal <= state.week.ordinal
    )
    if not effective:
        return state

    by_id = {player.player_id: player for player in state.players}
    updates: dict[str, PlayerLifecycleIdentity] = {}
    for trigger in effective:
        player = by_id.get(trigger.player_id)
        if player is None:
            raise ValueError(
                "Effective Tour-entry trigger references player absent from lifecycle"
            )
        if _age_at_trigger(player, trigger) < 15:
            raise ValueError("Tour-entry trigger predates the player's 15th birthday")
        if (
            player.retirement_effective_week is not None
            and trigger.trigger_week.ordinal
            >= player.retirement_effective_week.ordinal
        ):
            raise ValueError("Tour-entry trigger is not valid at or after retirement")
        if player.tour_entry_week is not None:
            if player.tour_entry_week != trigger.trigger_week:
                raise ValueError(
                    "Lifecycle Tour-entry week conflicts with canonical trigger history"
                )
            continue
        updates[player.player_id] = player.model_copy(
            update={"tour_entry_week": trigger.trigger_week}
        )

    if not updates:
        return state
    return state.model_copy(
        update={
            "players": tuple(
                updates.get(player.player_id, player) for player in state.players
            )
        }
    )
