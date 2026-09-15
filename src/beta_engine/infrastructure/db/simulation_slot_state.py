"""Saved Revision projection for authoritative slot/match/effect history."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import delete, select

from beta_engine.infrastructure.db.models import (
    SimulationEventGroupModel,
    SimulationSlotModel,
)

COMPONENT_KEY = "simulation_slot_match_state"


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


def _component(slots, groups):
    _validate_semantics(slots, groups)
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
    if slots or groups:
        payload["content"][COMPONENT_KEY] = _component(slots, groups)


def _load(payload, *, run_id, branch_id):
    component = payload.get("content", {}).get(COMPONENT_KEY)
    if component is None:
        return None
    if set(component) != {"fingerprint", "slots", "groups"}:
        raise ValueError("Invalid Saved Revision simulation-slot component")
    calculated = _component(
        [SimulationSlotModel(**value) for value in component["slots"]],
        [SimulationEventGroupModel(**value) for value in component["groups"]],
    )
    if calculated["fingerprint"] != component["fingerprint"]:
        raise ValueError("Saved simulation-slot component fingerprint mismatch")
    if any(
        (value["run_id"], value["branch_id"]) != (run_id, branch_id)
        for kind in ("slots", "groups")
        for value in component[kind]
    ):
        raise ValueError("Saved simulation-slot component scope mismatch")
    return component


def restore_saved_simulation_slots(
    session, *, current_payload, target_payload, run_id, branch_id
):
    expected = _load(current_payload, run_id=run_id, branch_id=branch_id)
    target = _load(target_payload, run_id=run_id, branch_id=branch_id)
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
    live = _component(live_slots, live_groups) if live_slots or live_groups else None
    if (live or {}).get("fingerprint") != (expected or {}).get("fingerprint"):
        raise ValueError("Live simulation-slot state differs from saved head")
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
    session.flush()
