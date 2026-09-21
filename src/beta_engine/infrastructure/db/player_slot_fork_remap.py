from __future__ import annotations

import json
from dataclasses import dataclass

from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)
from beta_engine.domain.simulation_slots import WeekSimulationSchedule, fingerprint
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.player_sporting_state import (
    PLAYER_SPORTING_COMPONENT_KEY,
    _component as sporting_component,
    load_saved_sporting_bundle,
)
from beta_engine.infrastructure.db.simulation_slot_fork_remap import (
    RemappedSimulationSlotCore,
    SimulationSlotForkRemapUnsupportedError,
    remap_completed_simulation_slot_core,
)
from beta_engine.infrastructure.db.simulation_slot_state import (
    COMPONENT_KEY as SIMULATION_SLOT_COMPONENT_KEY,
    _component as simulation_component,
    _load as load_saved_simulation_slots,
)


@dataclass(frozen=True)
class CoupledPlayerSlotForkRemap:
    sporting_component: dict
    simulation_component: dict
    result_fingerprints: dict[str, str]
    match_effect_fingerprints: dict[str, str]
    terminal_checkpoint_fingerprints: dict[str, str]


def remap_coupled_player_slot_history(
    payload,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    v1_source_fingerprint_map: dict[str, str],
) -> CoupledPlayerSlotForkRemap | None:
    """Remap sporting + completed Slot core in canonical week order.

    Each target sporting state becomes the opening authority for that week's target
    Simulation Slot ledger. The rebuilt ledger then provides the evidence needed to
    rebuild that week's completed sporting context and therefore the next sporting state.
    """
    source_bundle = load_saved_sporting_bundle(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    source_slot_component = load_saved_simulation_slots(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source_bundle is None or source_slot_component is None:
        return None

    auxiliary = set(source_slot_component) - {
        "fingerprint",
        "slots",
        "groups",
        "authorities",
        "schedules",
    }
    nonempty_auxiliary = {
        key for key in auxiliary if source_slot_component.get(key)
    }
    if nonempty_auxiliary:
        raise SimulationSlotForkRemapUnsupportedError(
            "Coupled player/Slot fork does not yet support auxiliary authorities: "
            + ", ".join(sorted(nonempty_auxiliary))
        )

    source_schedules = [
        WeekSimulationScheduleModel(**value)
        for value in source_slot_component.get("schedules", [])
    ]
    target_schedules: list[WeekSimulationScheduleModel] = []
    for row in source_schedules:
        schedule = WeekSimulationSchedule.model_validate_json(row.payload_json)
        if (
            schedule.run_id,
            schedule.branch_id,
            schedule.week.ordinal,
            schedule.fingerprint,
        ) != (
            run_id,
            source_branch_id,
            row.week_ordinal,
            row.schedule_fingerprint,
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Saved Week Simulation Schedule identity is corrupt"
            )
        target_schedule = WeekSimulationSchedule.model_validate_json(
            schedule.model_copy(update={"branch_id": target_branch_id}).model_dump_json()
        )
        target_request_fingerprint = fingerprint(
            {
                "request_id": row.request_id,
                "schedule": target_schedule.model_dump(mode="json"),
            }
        )
        target_schedules.append(
            WeekSimulationScheduleModel(
                run_id=run_id,
                branch_id=target_branch_id,
                week_ordinal=row.week_ordinal,
                request_id=row.request_id,
                request_fingerprint=target_request_fingerprint,
                schedule_fingerprint=target_schedule.fingerprint,
                payload_json=target_schedule.model_dump_json(),
            )
        )

    source_authorities = [
        AdoptedTournamentAuthorityModel(**value)
        for value in source_slot_component.get("authorities", [])
    ]
    target_authorities: list[AdoptedTournamentAuthorityModel] = []
    if source_authorities:
        from beta_engine.application.authoritative_run_simulation_driver import (
            AuthoritativeRunSimulationDriver,
        )

        for row in source_authorities:
            items = AuthoritativeRunSimulationDriver._decode_adopted_authority(
                row.package_json
            )
            if any(item.draw_authority_fingerprint is not None for item in items):
                raise SimulationSlotForkRemapUnsupportedError(
                    "Adopted Tournament authority references Draw evidence without a target mapping"
                )
            week = next(
                (
                    state.week
                    for state in source_bundle[0]
                    if state.week.ordinal == row.week_ordinal
                ),
                None,
            )
            if week is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Adopted Tournament authority week has no saved sporting state"
                )
            source_fingerprint = (
                AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
                    run_id,
                    source_branch_id,
                    week,
                    items,
                )
            )
            if source_fingerprint != row.authority_fingerprint:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Saved Adopted Tournament authority fingerprint is corrupt"
                )
            target_fingerprint = (
                AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
                    run_id,
                    target_branch_id,
                    week,
                    items,
                )
            )
            target_authorities.append(
                AdoptedTournamentAuthorityModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    week_ordinal=row.week_ordinal,
                    event_id=row.event_id,
                    authority_fingerprint=target_fingerprint,
                    package_json=row.package_json,
                )
            )

    source_states, source_contexts = source_bundle
    context_by_week = {
        context.completed_week.ordinal: context for context in source_contexts
    }
    slots_by_week: dict[int, list[SimulationSlotModel]] = {}
    groups_by_week: dict[int, list[SimulationEventGroupModel]] = {}
    for value in source_slot_component["slots"]:
        row = SimulationSlotModel(**value)
        slots_by_week.setdefault(row.week_ordinal, []).append(row)
    for value in source_slot_component["groups"]:
        row = SimulationEventGroupModel(**value)
        groups_by_week.setdefault(row.week_ordinal, []).append(row)

    target_states: list[PlayerSportingWeekState] = []
    target_contexts: list[CompletedWeekSportingContext] = []
    target_slot_components: list[dict] = []
    all_results: dict[str, str] = {}
    all_effects: dict[str, str] = {}
    all_terminals: dict[str, str] = {}
    remapped_context_by_week: dict[int, CompletedWeekSportingContext] = {}

    previous_target: PlayerSportingWeekState | None = None
    for source_state in source_states:
        updates = {
            "branch_id": target_branch_id,
            "predecessor_fingerprint": (
                previous_target.fingerprint if previous_target is not None else None
            ),
        }
        if source_state.week.ordinal != 0:
            predecessor_context = remapped_context_by_week.get(
                source_state.week.ordinal - 1
            )
            if predecessor_context is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting state requires a prior completed context that has not been remapped"
                )
            updates["completed_context_fingerprint"] = predecessor_context.fingerprint

        target_state = PlayerSportingWeekState.model_validate_json(
            source_state.model_copy(update=updates).model_dump_json()
        )
        target_states.append(target_state)
        previous_target = target_state

        week_ordinal = source_state.week.ordinal
        week_slots = sorted(
            slots_by_week.get(week_ordinal, []),
            key=lambda row: row.slot_ordinal,
        )
        week_groups = sorted(
            groups_by_week.get(week_ordinal, []),
            key=lambda row: (row.slot_id, row.group_id),
        )
        week_remap: RemappedSimulationSlotCore | None = None
        if week_slots or week_groups:
            if not week_slots:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Saved Simulation Slot groups exist without their week slots"
                )
            source_week_component = simulation_component(
                week_slots,
                week_groups,
                include_commands=False,
                include_authorities=False,
                include_schedules=False,
                include_entry_fields=False,
                include_wild_card_authorities=False,
                include_draw_inputs=False,
                include_draw_authorities=False,
                include_draw_process_authorities=False,
                include_draw_revisions=False,
            )
            week_remap = remap_completed_simulation_slot_core(
                {"content": {SIMULATION_SLOT_COMPONENT_KEY: source_week_component}},
                run_id=run_id,
                source_branch_id=source_branch_id,
                target_branch_id=target_branch_id,
                opening_sporting_fingerprint_map={
                    source_state.fingerprint: target_state.fingerprint
                },
            )
            assert week_remap is not None
            target_slot_components.append(week_remap.component)
            all_results.update(week_remap.results)
            all_effects.update(week_remap.match_effects)
            all_terminals.update(week_remap.terminal_checkpoints)

        source_context = context_by_week.get(week_ordinal)
        if source_context is None:
            continue

        if source_context.schema_version == "completed_week_sporting_context.v1":
            try:
                mapped_sources = tuple(
                    sorted(
                        v1_source_fingerprint_map[value]
                        for value in source_context.source_fingerprints
                    )
                )
            except KeyError as exc:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v1 context references evidence without a target mapping"
                ) from exc
            context_updates = {
                "branch_id": target_branch_id,
                "source_fingerprints": mapped_sources,
            }
        else:
            if week_remap is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v2 context requires a remapped Simulation Slot week"
                )
            if source_context.terminal_sporting_fingerprint is None:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v2 context is missing terminal checkpoint evidence"
                )
            try:
                context_updates = {
                    "branch_id": target_branch_id,
                    "source_fingerprints": tuple(
                        sorted(
                            week_remap.results[value]
                            for value in source_context.source_fingerprints
                        )
                    ),
                    "terminal_sporting_fingerprint": week_remap.terminal_checkpoints[
                        source_context.terminal_sporting_fingerprint
                    ],
                    "match_effect_fingerprints": tuple(
                        sorted(
                            week_remap.match_effects[value]
                            for value in source_context.match_effect_fingerprints
                        )
                    ),
                }
            except KeyError as exc:
                raise SimulationSlotForkRemapUnsupportedError(
                    "Sporting v2 context references Slot evidence without a target mapping"
                ) from exc

        target_context = CompletedWeekSportingContext.model_validate_json(
            source_context.model_copy(update=context_updates).model_dump_json()
        )
        target_contexts.append(target_context)
        remapped_context_by_week[week_ordinal] = target_context

    if set(slots_by_week) - {state.week.ordinal for state in source_states}:
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation Slot history contains a week without a saved sporting opening state"
        )

    target_slots = [
        SimulationSlotModel(**value)
        for component in target_slot_components
        for value in component["slots"]
    ]
    target_groups = [
        SimulationEventGroupModel(**value)
        for component in target_slot_components
        for value in component["groups"]
    ]
    merged_simulation_component = simulation_component(
        target_slots,
        target_groups,
        authorities=target_authorities,
        include_commands=False,
        include_authorities="authorities" in source_slot_component,
        schedules=target_schedules,
        include_schedules="schedules" in source_slot_component,
        include_entry_fields=False,
        include_wild_card_authorities=False,
        include_draw_inputs=False,
        include_draw_authorities=False,
        include_draw_process_authorities=False,
        include_draw_revisions=False,
    )

    return CoupledPlayerSlotForkRemap(
        sporting_component=sporting_component(
            tuple(target_states),
            tuple(target_contexts),
        ),
        simulation_component=merged_simulation_component,
        result_fingerprints=all_results,
        match_effect_fingerprints=all_effects,
        terminal_checkpoint_fingerprints=all_terminals,
    )
