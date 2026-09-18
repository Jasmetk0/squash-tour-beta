"""Saved Revision projection for authoritative slot/match/effect history."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select

from beta_engine.infrastructure.db.models import (
    AdoptedTournamentAuthorityModel,
    AuthoritativeSimulationCommandModel,
    SimulationEventGroupModel,
    SimulationSlotModel,
    WeekSimulationScheduleModel,
    TournamentEntryFieldVersionModel,
)

COMPONENT_KEY = "simulation_slot_match_state"


def _validate_entry_field_rows(rows):
    from beta_engine.infrastructure.db.tournament_entry_field import (
        TournamentEntryFieldStore,
    )

    by_event = {}
    for row in rows:
        by_event.setdefault(row.event_id, []).append(row)
    for event_rows in by_event.values():
        ordered = sorted(event_rows, key=lambda row: row.sequence)
        if [row.sequence for row in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError("Tournament Entry Field version sequence has a gap")
        previous = None
        for index, row in enumerate(ordered):
            field, _ = TournamentEntryFieldStore._load_row(row)
            if index == 0:
                if field.mode != "initial" or row.predecessor_fingerprint is not None:
                    raise ValueError(
                        "First Tournament Entry Field version must be initial"
                    )
            else:
                if field.mode != "pre_draw_repair" or previous is None:
                    raise ValueError(
                        "Later Tournament Entry Field versions must be pre-draw repairs"
                    )
                if row.predecessor_fingerprint != previous.fingerprint:
                    raise ValueError(
                        "Tournament Entry Field predecessor chain is corrupt"
                    )
            previous = field


def _validate_semantics(slots, groups):
    from beta_engine.application.authoritative_slot_matches import (
        AuthoritativeSlotMatchExecutor,
    )

    slot_keys = [(row.week_ordinal, row.slot_id) for row in slots]
    ordinal_keys = [(row.week_ordinal, row.slot_ordinal) for row in slots]
    if len(slot_keys) != len(set(slot_keys)) or len(ordinal_keys) != len(
        set(ordinal_keys)
    ):
        raise ValueError("Simulation slots require unique IDs and global ordinals")
    by_week = {}
    for row in slots:
        by_week.setdefault(row.week_ordinal, []).append(row)
    for week_slots in by_week.values():
        ordered = sorted(week_slots, key=lambda item: item.slot_ordinal)
        if [item.slot_ordinal for item in ordered] != list(range(1, len(ordered) + 1)):
            raise ValueError(
                "Simulation Slot ordinals must be canonical and contiguous"
            )
        predecessor = None
        for row in ordered:
            plan = AuthoritativeSlotMatchExecutor._load_plan(row)
            start = AuthoritativeSlotMatchExecutor._load_slot_start(row)
            terminal = AuthoritativeSlotMatchExecutor._load_checkpoint(row)
            if (
                plan.run_id,
                plan.branch_id,
                plan.week.ordinal,
                plan.slot_id,
                plan.ordinal,
            ) != (
                row.run_id,
                row.branch_id,
                row.week_ordinal,
                row.slot_id,
                row.slot_ordinal,
            ):
                raise ValueError("Simulation Slot plan scope is corrupt")
            if start.predecessor_checkpoint_fingerprint != predecessor:
                raise ValueError(
                    "Simulation Slot predecessor checkpoint chain is corrupt"
                )
            slot_groups = sorted(
                (
                    group
                    for group in groups
                    if (group.week_ordinal, group.slot_id)
                    == (row.week_ordinal, row.slot_id)
                ),
                key=lambda item: item.group_id,
            )
            group_ids = {group.group_id for group in slot_groups}
            if not group_ids <= set(plan.group_ids) or (
                row.status == "complete" and group_ids != set(plan.group_ids)
            ):
                raise ValueError(
                    "Simulation Slot status and planned group universe differ"
                )
            effects = []
            for group in slot_groups:
                loaded = AuthoritativeSlotMatchExecutor._load_group(group)
                effects.extend(loaded.effects)
            players = {player.player_id: player for player in start.players}
            for effect in sorted(
                effects, key=lambda item: (item.player_id, item.group_id)
            ):
                player = players[effect.player_id]
                if (
                    player.current_form,
                    player.match_sharpness,
                    player.long_term_fatigue,
                ) != (
                    effect.form_before,
                    effect.sharpness_before,
                    effect.fatigue_before,
                ):
                    raise ValueError(
                        "Simulation Slot effects do not rebuild from frozen input"
                    )
                players[effect.player_id] = player.model_copy(
                    update={
                        "current_form": effect.form_after,
                        "match_sharpness": effect.sharpness_after,
                        "long_term_fatigue": effect.fatigue_after,
                    }
                )
            rebuilt = start.model_copy(
                update={
                    "applied_effect_fingerprints": tuple(
                        sorted(effect.fingerprint for effect in effects)
                    ),
                    "players": tuple(
                        players[player_id] for player_id in sorted(players)
                    ),
                }
            )
            if rebuilt != terminal:
                raise ValueError(
                    "Simulation Slot terminal checkpoint is not rebuildable"
                )
            predecessor = terminal.fingerprint
    known = set(slot_keys)
    if any((group.week_ordinal, group.slot_id) not in known for group in groups):
        raise ValueError("Simulation event group has no planned slot")


def _component(
    slots,
    groups,
    commands=(),
    authorities=(),
    *,
    include_commands=True,
    include_authorities=True,
    schedules=(),
    include_schedules=True,
    entry_fields=(),
    include_entry_fields=True,
):
    _validate_semantics(slots, groups)
    _validate_entry_field_rows(entry_fields)
    body = {
        "slots": [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "slot_id": row.slot_id,
                "slot_ordinal": row.slot_ordinal,
                "plan_fingerprint": row.plan_fingerprint,
                "slot_start_fingerprint": row.slot_start_fingerprint,
                "status": row.status,
                "payload_json": row.payload_json,
                "slot_start_checkpoint_json": row.slot_start_checkpoint_json,
                "terminal_checkpoint_json": row.terminal_checkpoint_json,
            }
            for row in slots
        ],
        "groups": [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "slot_id": row.slot_id,
                "group_id": row.group_id,
                "command_fingerprint": row.command_fingerprint,
                "match_id": row.match_id,
                "match_input_fingerprint": row.match_input_fingerprint,
                "result_fingerprint": row.result_fingerprint,
                "payload_json": row.payload_json,
            }
            for row in groups
        ],
    }
    if include_commands:
        body["commands"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "status": row.status,
                "result_json": row.result_json,
            }
            for row in commands
        ]
    if include_authorities:
        body["authorities"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "week_ordinal": row.week_ordinal,
                "event_id": row.event_id,
                "authority_fingerprint": row.authority_fingerprint,
                "package_json": row.package_json,
            }
            for row in authorities
        ]
    if include_entry_fields:
        body["entry_fields"] = [
            {
                "run_id": row.run_id,
                "branch_id": row.branch_id,
                "event_id": row.event_id,
                "sequence": row.sequence,
                "command_id": row.command_id,
                "request_fingerprint": row.request_fingerprint,
                "field_fingerprint": row.field_fingerprint,
                "predecessor_fingerprint": row.predecessor_fingerprint,
                "ranking_authority_fingerprint": row.ranking_authority_fingerprint,
                "applications_fingerprint": row.applications_fingerprint,
                "applications_json": row.applications_json,
                "payload_json": row.payload_json,
            }
            for row in entry_fields
        ]
    if include_schedules:
        body["schedules"] = [
            {
                "run_id": r.run_id,
                "branch_id": r.branch_id,
                "week_ordinal": r.week_ordinal,
                "request_id": r.request_id,
                "request_fingerprint": r.request_fingerprint,
                "schedule_fingerprint": r.schedule_fingerprint,
                "payload_json": r.payload_json,
            }
            for r in schedules
        ]
    return {
        "fingerprint": hashlib.sha256(
            json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        **body,
    }


def capture_saved_simulation_slots(session, payload, *, run_id, branch_id):
    slots = session.scalars(
        select(SimulationSlotModel)
        .where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
        .order_by(SimulationSlotModel.week_ordinal, SimulationSlotModel.slot_ordinal)
    ).all()
    groups = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
        .order_by(
            SimulationEventGroupModel.week_ordinal,
            SimulationEventGroupModel.slot_id,
            SimulationEventGroupModel.group_id,
        )
    ).all()
    commands = session.scalars(
        select(AuthoritativeSimulationCommandModel)
        .where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
        .order_by(AuthoritativeSimulationCommandModel.command_id)
    ).all()
    authorities = session.scalars(
        select(AdoptedTournamentAuthorityModel)
        .where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
        .order_by(AdoptedTournamentAuthorityModel.week_ordinal)
    ).all()
    schedules = session.scalars(
        select(WeekSimulationScheduleModel)
        .where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
        .order_by(WeekSimulationScheduleModel.week_ordinal)
    ).all()
    entry_fields = session.scalars(
        select(TournamentEntryFieldVersionModel)
        .where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentEntryFieldVersionModel.event_id,
            TournamentEntryFieldVersionModel.sequence,
        )
    ).all()
    if entry_fields:
        from beta_engine.infrastructure.db.tournament_entry_field import (
            TournamentEntryFieldStore,
        )

        store = TournamentEntryFieldStore(session)
        for event_id in sorted({row.event_id for row in entry_fields}):
            store.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
    if slots or groups or commands or authorities or schedules or entry_fields:
        payload["content"][COMPONENT_KEY] = _component(
            slots,
            groups,
            commands,
            authorities,
            schedules=schedules,
            entry_fields=entry_fields,
            include_entry_fields=bool(entry_fields),
        )


def _load(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        return None
    required = {"fingerprint", "slots", "groups"}
    optional = {"commands", "authorities", "schedules", "entry_fields"}
    if not required <= set(component) or set(component) - required - optional:
        raise ValueError("Invalid Saved Revision simulation-slot component")
    calculated = _component(
        [SimulationSlotModel(**value) for value in component["slots"]],
        [SimulationEventGroupModel(**value) for value in component["groups"]],
        [
            AuthoritativeSimulationCommandModel(**value)
            for value in component.get("commands", [])
        ],
        [
            AdoptedTournamentAuthorityModel(**value)
            for value in component.get("authorities", [])
        ],
        include_commands="commands" in component,
        include_authorities="authorities" in component,
        schedules=[
            WeekSimulationScheduleModel(**value)
            for value in component.get("schedules", [])
        ],
        include_schedules="schedules" in component,
        entry_fields=[
            TournamentEntryFieldVersionModel(**value)
            for value in component.get("entry_fields", [])
        ],
        include_entry_fields="entry_fields" in component,
    )
    if calculated["fingerprint"] != component["fingerprint"]:
        raise ValueError("Saved simulation-slot component fingerprint mismatch")
    if any(
        (value["run_id"], value["branch_id"]) != (run_id, branch_id)
        for kind in (
            set(component)
            & {"slots", "groups", "commands", "authorities", "schedules", "entry_fields"}
        )
        for value in component[kind]
    ):
        raise ValueError("Saved simulation-slot component scope mismatch")
    return component


def _validate_saved_entry_fields_against_live_ranking_authority(
    session, component, *, run_id: str, branch_id: str
) -> None:
    values = (component or {}).get("entry_fields", [])
    if not values:
        return

    from beta_engine.infrastructure.db.tournament_entry_field import (
        TournamentEntryFieldStore,
    )
    from beta_engine.infrastructure.db.tournament_ranking_snapshot_authority import (
        TournamentRankingSnapshotAuthorityStore,
    )

    rows = [TournamentEntryFieldVersionModel(**value) for value in values]
    by_event: dict[str, list[TournamentEntryFieldVersionModel]] = {}
    for row in rows:
        by_event.setdefault(row.event_id, []).append(row)

    ranking_store = TournamentRankingSnapshotAuthorityStore(session)
    for event_id, event_rows in sorted(by_event.items()):
        authority = ranking_store.get(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
        )
        if authority is None:
            raise ValueError(
                "Saved Tournament Entry Field references missing Tournament "
                "Ranking Snapshot authority"
            )
        TournamentEntryFieldStore.validate_rows(
            event_rows,
            authority=authority,
        )


def restore_saved_simulation_slots(
    session, *, current_payload, target_payload, run_id, branch_id
):
    expected = _load(current_payload, run_id=run_id, branch_id=branch_id)
    target = _load(target_payload, run_id=run_id, branch_id=branch_id)
    _validate_saved_entry_fields_against_live_ranking_authority(
        session,
        target,
        run_id=run_id,
        branch_id=branch_id,
    )
    live_slots = session.scalars(
        select(SimulationSlotModel)
        .where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
        .order_by(SimulationSlotModel.week_ordinal, SimulationSlotModel.slot_ordinal)
    ).all()
    live_groups = session.scalars(
        select(SimulationEventGroupModel)
        .where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
        .order_by(
            SimulationEventGroupModel.week_ordinal,
            SimulationEventGroupModel.slot_id,
            SimulationEventGroupModel.group_id,
        )
    ).all()
    live_commands = session.scalars(
        select(AuthoritativeSimulationCommandModel)
        .where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
        .order_by(AuthoritativeSimulationCommandModel.command_id)
    ).all()
    live_authorities = session.scalars(
        select(AdoptedTournamentAuthorityModel)
        .where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
        .order_by(AdoptedTournamentAuthorityModel.week_ordinal)
    ).all()
    live_schedules = session.scalars(
        select(WeekSimulationScheduleModel)
        .where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
        .order_by(WeekSimulationScheduleModel.week_ordinal)
    ).all()
    live_entry_fields = session.scalars(
        select(TournamentEntryFieldVersionModel)
        .where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
        .order_by(
            TournamentEntryFieldVersionModel.event_id,
            TournamentEntryFieldVersionModel.sequence,
        )
    ).all()
    if live_entry_fields:
        from beta_engine.infrastructure.db.tournament_entry_field import (
            TournamentEntryFieldStore,
        )

        store = TournamentEntryFieldStore(session)
        for event_id in sorted({row.event_id for row in live_entry_fields}):
            store.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
    live = (
        _component(
            live_slots,
            live_groups,
            live_commands,
            live_authorities,
            schedules=live_schedules,
            entry_fields=live_entry_fields,
            include_entry_fields=(
                bool(live_entry_fields)
                or bool(expected is not None and "entry_fields" in expected)
            ),
        )
        if live_slots
        or live_groups
        or live_commands
        or live_authorities
        or live_schedules
        or live_entry_fields
        else None
    )
    if (live or {}).get("fingerprint") != (expected or {}).get("fingerprint"):
        raise ValueError("Live simulation-slot state differs from saved head")
    session.execute(
        delete(TournamentEntryFieldVersionModel).where(
            TournamentEntryFieldVersionModel.run_id == run_id,
            TournamentEntryFieldVersionModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(WeekSimulationScheduleModel).where(
            WeekSimulationScheduleModel.run_id == run_id,
            WeekSimulationScheduleModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(AdoptedTournamentAuthorityModel).where(
            AdoptedTournamentAuthorityModel.run_id == run_id,
            AdoptedTournamentAuthorityModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(AuthoritativeSimulationCommandModel).where(
            AuthoritativeSimulationCommandModel.run_id == run_id,
            AuthoritativeSimulationCommandModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(SimulationEventGroupModel).where(
            SimulationEventGroupModel.run_id == run_id,
            SimulationEventGroupModel.branch_id == branch_id,
        )
    )
    session.execute(
        delete(SimulationSlotModel).where(
            SimulationSlotModel.run_id == run_id,
            SimulationSlotModel.branch_id == branch_id,
        )
    )
    for value in (target or {}).get("slots", []):
        session.add(SimulationSlotModel(**value))
    for value in (target or {}).get("groups", []):
        session.add(SimulationEventGroupModel(**value))
    for value in (target or {}).get("commands", []):
        session.add(AuthoritativeSimulationCommandModel(**value))
    for value in (target or {}).get("authorities", []):
        session.add(AdoptedTournamentAuthorityModel(**value))
    for value in (target or {}).get("schedules", []):
        session.add(WeekSimulationScheduleModel(**value))
    for value in (target or {}).get("entry_fields", []):
        session.add(TournamentEntryFieldVersionModel(**value))
    session.flush()
    target_entry_fields = (target or {}).get("entry_fields", [])
    if target_entry_fields:
        from beta_engine.infrastructure.db.tournament_entry_field import (
            TournamentEntryFieldStore,
        )

        store = TournamentEntryFieldStore(session)
        for event_id in sorted({value["event_id"] for value in target_entry_fields}):
            store.history(run_id=run_id, branch_id=branch_id, event_id=event_id)
