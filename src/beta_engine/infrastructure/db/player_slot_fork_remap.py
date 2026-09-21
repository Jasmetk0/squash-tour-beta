from __future__ import annotations

import json
from dataclasses import dataclass

from beta_engine.domain.players.sporting import (
    CompletedWeekSportingContext,
    PlayerSportingWeekState,
)
from beta_engine.domain.simulation_slots import WeekSimulationSchedule, fingerprint
from beta_engine.domain.tournaments.draw_authority import (
    TournamentDrawAuthority,
    TournamentDrawAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_input_authority import (
    TournamentDrawInputAuthority,
    TournamentDrawInputAuthorityBuilder,
)
from beta_engine.domain.tournaments.draw_process_authority import (
    TournamentDrawProcessAuthority,
    TournamentDrawProcessAuthorityBuilder,
)
from beta_engine.domain.tournaments.entry_field import (
    TournamentEntryApplication,
    TournamentEntryField,
    TournamentEntryFieldResolver,
)
from beta_engine.domain.tournaments.ranking_snapshot_authority import (
    TournamentRankingSnapshotAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
    TournamentWildCardAuthorityBuilder,
)
from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    TournamentDrawAuthorityModel,
    TournamentDrawInputAuthorityModel,
    TournamentDrawProcessAuthorityModel,
    TournamentEntryFieldVersionModel,
    TournamentWildCardAuthorityModel,
    WeekSimulationScheduleModel,
)
from beta_engine.infrastructure.db.tournament_entry_field import (
    TournamentEntryFieldStore,
    _applications_fingerprint,
    _applications_json,
    _request_fingerprint as entry_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_authority import (
    TournamentDrawAuthorityStore,
    _request_fingerprint as draw_authority_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_input_authority import (
    TournamentDrawInputAuthorityStore,
    _request_fingerprint as draw_input_request_fingerprint,
)
from beta_engine.infrastructure.db.tournament_draw_process_authority import (
    TournamentDrawProcessAuthorityStore,
    _fingerprint as draw_process_request_fingerprint,
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
    tournament_ranking_authority_map: dict[
        str, TournamentRankingSnapshotAuthority
    ] | None = None,
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

    tournament_ranking_authority_map = tournament_ranking_authority_map or {}

    auxiliary = set(source_slot_component) - {
        "fingerprint",
        "slots",
        "groups",
        "authorities",
        "schedules",
        "entry_fields",
        "wild_card_authorities",
        "draw_inputs",
        "draw_authorities",
        "draw_process_authorities",
    }
    nonempty_auxiliary = {
        key for key in auxiliary if source_slot_component.get(key)
    }
    if nonempty_auxiliary:
        raise SimulationSlotForkRemapUnsupportedError(
            "Coupled player/Slot fork does not yet support auxiliary authorities: "
            + ", ".join(sorted(nonempty_auxiliary))
        )

    source_entry_rows = [
        TournamentEntryFieldVersionModel(**value)
        for value in source_slot_component.get("entry_fields", [])
    ]
    source_wc_rows = [
        TournamentWildCardAuthorityModel(**value)
        for value in source_slot_component.get("wild_card_authorities", [])
    ]
    source_draw_input_rows = [
        TournamentDrawInputAuthorityModel(**value)
        for value in source_slot_component.get("draw_inputs", [])
    ]
    source_draw_rows = [
        TournamentDrawAuthorityModel(**value)
        for value in source_slot_component.get("draw_authorities", [])
    ]
    source_draw_process_rows = [
        TournamentDrawProcessAuthorityModel(**value)
        for value in source_slot_component.get("draw_process_authorities", [])
    ]

    target_entry_rows: list[TournamentEntryFieldVersionModel] = []
    target_wc_rows: list[TournamentWildCardAuthorityModel] = []
    target_draw_input_rows: list[TournamentDrawInputAuthorityModel] = []
    target_draw_rows: list[TournamentDrawAuthorityModel] = []
    target_draw_process_rows: list[TournamentDrawProcessAuthorityModel] = []
    target_fields_by_event: dict[str, tuple[TournamentEntryField, ...]] = {}
    target_wc_by_event: dict[str, TournamentWildCardAuthority] = {}
    target_draw_input_by_event: dict[str, TournamentDrawInputAuthority] = {}
    target_draw_by_event: dict[str, TournamentDrawAuthority] = {}

    source_entries_by_event: dict[str, list[TournamentEntryFieldVersionModel]] = {}
    for row in source_entry_rows:
        source_entries_by_event.setdefault(row.event_id, []).append(row)

    for event_id, rows in source_entries_by_event.items():
        ordered = tuple(sorted(rows, key=lambda row: row.sequence))
        source_authority_fingerprint = ordered[0].ranking_authority_fingerprint
        target_authority = tournament_ranking_authority_map.get(
            source_authority_fingerprint
        )
        if target_authority is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Entry Field references ranking authority without a target mapping"
            )
        source_authority = None
        source_fields: tuple[TournamentEntryField, ...] = ()
        # Reconstruct source authority from the frozen field contract: every row must
        # point at the same source authority fingerprint, which is already mapped.
        if any(
            row.ranking_authority_fingerprint != source_authority_fingerprint
            for row in ordered
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Entry Field history changes ranking authority mid-lineage"
            )

        target_fields: list[TournamentEntryField] = []
        previous_target: TournamentEntryField | None = None
        for row in ordered:
            source_field, source_apps = TournamentEntryFieldStore._load_row(row)
            target_apps = tuple(
                TournamentEntryApplication.model_validate_json(
                    app.model_copy(update={"branch_id": target_branch_id}).model_dump_json()
                )
                for app in source_apps
            )
            apps_fp = _applications_fingerprint(target_apps)
            if row.sequence == 1:
                target_field = TournamentEntryFieldResolver.build_initial(
                    authority=target_authority,
                    applications=target_apps,
                    capacity=source_field.capacity,
                )
                request_fp = entry_request_fingerprint(
                    {
                        "mode": "initial",
                        "run_id": run_id,
                        "branch_id": target_branch_id,
                        "event_id": event_id,
                        "authority_fingerprint": target_authority.fingerprint,
                        "applications_fingerprint": apps_fp,
                        "capacity": source_field.capacity.model_dump(mode="json"),
                    }
                )
            else:
                if previous_target is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Tournament Entry Field repair has no target predecessor"
                    )
                source_previous = TournamentEntryFieldStore._load_row(
                    ordered[row.sequence - 2]
                )[0]
                newly_withdrawn = tuple(
                    sorted(
                        set(source_field.withdrawn_player_ids)
                        - set(source_previous.withdrawn_player_ids)
                    )
                )
                target_field = TournamentEntryFieldResolver.repair_pre_draw(
                    authority=target_authority,
                    applications=target_apps,
                    previous=previous_target,
                    withdrawn_player_ids=newly_withdrawn,
                )
                request_fp = entry_request_fingerprint(
                    {
                        "mode": "pre_draw_repair",
                        "run_id": run_id,
                        "branch_id": target_branch_id,
                        "event_id": event_id,
                        "authority_fingerprint": target_authority.fingerprint,
                        "applications_fingerprint": apps_fp,
                        "predecessor_fingerprint": previous_target.fingerprint,
                        "withdrawn_player_ids": newly_withdrawn,
                    }
                )
            target_entry_rows.append(
                TournamentEntryFieldVersionModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    event_id=event_id,
                    sequence=row.sequence,
                    command_id=row.command_id,
                    request_fingerprint=request_fp,
                    field_fingerprint=target_field.fingerprint,
                    predecessor_fingerprint=(
                        previous_target.fingerprint
                        if previous_target is not None
                        else None
                    ),
                    ranking_authority_fingerprint=target_authority.fingerprint,
                    applications_fingerprint=apps_fp,
                    applications_json=_applications_json(target_apps),
                    payload_json=target_field.model_dump_json(),
                )
            )
            target_fields.append(target_field)
            previous_target = target_field
        target_fields_by_event[event_id] = tuple(target_fields)

    for row in source_wc_rows:
        source_authority = TournamentWildCardAuthority.model_validate_json(
            row.payload_json
        )
        fields = target_fields_by_event.get(row.event_id)
        if not fields or row.field_sequence != len(fields):
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament WC authority has no matching target terminal Entry Field"
            )
        target_field = fields[-1]
        target_authority = TournamentWildCardAuthorityBuilder.build(
            field=target_field,
            field_sequence=row.field_sequence,
            command_id=row.command_id,
            original_wild_card_player_ids=source_authority.original_wild_card_player_ids,
            reserve_wild_card_player_ids=source_authority.reserve_wild_card_player_ids,
            unavailable_player_ids=source_authority.unavailable_player_ids,
            decision_week=source_authority.decision_week,
            decision_slot_ordinal=source_authority.decision_slot_ordinal,
            selection_policy_id=source_authority.selection_policy_id,
            operator_label=source_authority.operator_label,
            audit_reason=source_authority.audit_reason,
        )
        request = {
            "entry_field_fingerprint": target_field.fingerprint,
            "field_sequence": row.field_sequence,
            "original_wild_card_player_ids": list(
                source_authority.original_wild_card_player_ids
            ),
            "reserve_wild_card_player_ids": list(
                source_authority.reserve_wild_card_player_ids
            ),
            "unavailable_player_ids": sorted(
                set(source_authority.unavailable_player_ids)
            ),
        }
        if source_authority.decision_week is not None:
            request["decision_week"] = source_authority.decision_week.model_dump(
                mode="json"
            )
            request["decision_slot_ordinal"] = (
                source_authority.decision_slot_ordinal
            )
        if source_authority.selection_policy_id is not None:
            request["selection_policy_id"] = source_authority.selection_policy_id
            request["operator_label"] = source_authority.operator_label
            request["audit_reason"] = source_authority.audit_reason
        target_wc_rows.append(
            TournamentWildCardAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=fingerprint(request),
                authority_fingerprint=target_authority.fingerprint,
                entry_field_fingerprint=target_field.fingerprint,
                field_sequence=row.field_sequence,
                payload_json=target_authority.model_dump_json(),
            )
        )
        target_wc_by_event[row.event_id] = target_authority

    for row in source_draw_input_rows:
        source_draw_input = TournamentDrawInputAuthority.model_validate_json(
            row.payload_json
        )
        fields = target_fields_by_event.get(row.event_id)
        target_ranking_authority = tournament_ranking_authority_map.get(
            source_draw_input.tournament_ranking_authority_fingerprint
        )
        if not fields or target_ranking_authority is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw Input has no mapped ranking/Entry Field dependencies"
            )
        target_field = fields[-1]
        target_wc = target_wc_by_event.get(row.event_id)
        target_draw_input = TournamentDrawInputAuthorityBuilder.build(
            authority=target_ranking_authority,
            field=target_field,
            field_sequence=row.field_sequence,
            command_id=row.command_id,
            draw_seed=source_draw_input.draw_seed,
            main_seed_count=source_draw_input.main_seed_count,
            qualification_seed_count=source_draw_input.qualification_seed_count,
            schema_version=source_draw_input.schema_version,
            wild_card_authority=target_wc,
        )
        request = TournamentDrawInputAuthorityStore._request(
            ranking_authority_fingerprint=target_ranking_authority.fingerprint,
            entry_field_fingerprint=target_field.fingerprint,
            field_sequence=row.field_sequence,
            draw_seed=source_draw_input.draw_seed,
            main_seed_count=target_draw_input.main_seed_count,
            qualification_seed_count=target_draw_input.qualification_seed_count,
            wild_card_authority_fingerprint=(
                target_draw_input.wild_card_authority_fingerprint
            ),
        )
        target_draw_input_rows.append(
            TournamentDrawInputAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=draw_input_request_fingerprint(request),
                authority_fingerprint=target_draw_input.fingerprint,
                ranking_authority_fingerprint=target_ranking_authority.fingerprint,
                entry_field_fingerprint=target_field.fingerprint,
                field_sequence=row.field_sequence,
                payload_json=target_draw_input.model_dump_json(),
            )
        )
        target_draw_input_by_event[row.event_id] = target_draw_input

    for row in source_draw_rows:
        source_draw = TournamentDrawAuthority.model_validate_json(row.payload_json)
        target_draw_input = target_draw_input_by_event.get(row.event_id)
        if target_draw_input is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw authority has no mapped Draw Input dependency"
            )
        if (
            source_draw.draw_input_fingerprint != row.draw_input_fingerprint
            or source_draw.fingerprint != row.authority_fingerprint
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Saved Tournament Draw authority identity is corrupt"
            )
        target_draw = TournamentDrawAuthorityBuilder.build(
            draw_input=target_draw_input,
            command_id=row.command_id,
            algorithm_version=source_draw.algorithm_version,
        )
        request = TournamentDrawAuthorityStore._request(
            draw_input_fingerprint=target_draw_input.fingerprint
        )
        target_draw_rows.append(
            TournamentDrawAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=draw_authority_request_fingerprint(request),
                authority_fingerprint=target_draw.fingerprint,
                draw_input_fingerprint=target_draw_input.fingerprint,
                payload_json=target_draw.model_dump_json(),
            )
        )
        target_draw_by_event[row.event_id] = target_draw

    for row in source_draw_process_rows:
        source_process = TournamentDrawProcessAuthority.model_validate_json(
            row.payload_json
        )
        target_draw = target_draw_by_event.get(row.event_id)
        if target_draw is None:
            raise SimulationSlotForkRemapUnsupportedError(
                "Tournament Draw process authority has no mapped Draw dependency"
            )
        if (
            source_process.draw_authority_fingerprint
            != row.draw_authority_fingerprint
            or source_process.fingerprint != row.authority_fingerprint
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Saved Tournament Draw process authority identity is corrupt"
            )
        target_process = TournamentDrawProcessAuthorityBuilder.build(
            draw=target_draw,
            command_id=row.command_id,
            main_process_window_count=source_process.main.process_window_count,
            qualification_process_window_count=(
                source_process.qualification.process_window_count
                if source_process.qualification is not None
                else None
            ),
        )
        request = TournamentDrawProcessAuthorityStore._request(
            draw_authority_fingerprint=target_draw.fingerprint,
            main_process_window_count=source_process.main.process_window_count,
            qualification_process_window_count=(
                source_process.qualification.process_window_count
                if source_process.qualification is not None
                else None
            ),
        )
        target_draw_process_rows.append(
            TournamentDrawProcessAuthorityModel(
                run_id=run_id,
                branch_id=target_branch_id,
                event_id=row.event_id,
                command_id=row.command_id,
                request_fingerprint=draw_process_request_fingerprint(request),
                authority_fingerprint=target_process.fingerprint,
                draw_authority_fingerprint=target_draw.fingerprint,
                payload_json=target_process.model_dump_json(),
            )
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

            target_items = []
            for item in items:
                if item.draw_authority_fingerprint is None:
                    target_items.append(item)
                    continue
                mapped_draw_fingerprint = target_draw_fingerprint_map.get(
                    item.draw_authority_fingerprint
                )
                if mapped_draw_fingerprint is None:
                    raise SimulationSlotForkRemapUnsupportedError(
                        "Adopted Tournament authority references Draw evidence without a target mapping"
                    )
                target_items.append(
                    item.model_copy(
                        update={
                            "draw_authority_fingerprint": mapped_draw_fingerprint
                        }
                    )
                )
            target_items = tuple(target_items)
            target_fingerprint = (
                AuthoritativeRunSimulationDriver._tournament_authority_fingerprint(
                    run_id,
                    target_branch_id,
                    week,
                    target_items,
                )
            )
            target_authorities.append(
                AdoptedTournamentAuthorityModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    week_ordinal=row.week_ordinal,
                    event_id=row.event_id,
                    authority_fingerprint=target_fingerprint,
                    package_json=AuthoritativeRunSimulationDriver._encode_adopted_authority(
                        target_items
                    ),
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
        entry_fields=target_entry_rows,
        include_entry_fields="entry_fields" in source_slot_component,
        wild_card_authorities=target_wc_rows,
        include_wild_card_authorities="wild_card_authorities" in source_slot_component,
        draw_inputs=target_draw_input_rows,
        include_draw_inputs="draw_inputs" in source_slot_component,
        draw_authorities=target_draw_rows,
        include_draw_authorities="draw_authorities" in source_slot_component,
        draw_process_authorities=target_draw_process_rows,
        include_draw_process_authorities=(
            "draw_process_authorities" in source_slot_component
        ),
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
