from __future__ import annotations

from dataclasses import dataclass

from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.simulation_slots import (
    AuthoritativeMatchInput,
    MatchSportingEffectsPolicy,
    PlayerMatchSportingEffect,
    PlayerSportingCheckpoint,
    SimulationSlotPlan,
    fingerprint,
)


class SimulationSlotForkRemapUnsupportedError(ValueError):
    pass


@dataclass(frozen=True)
class SimulationSlotSportingFingerprintMaps:
    terminal_checkpoints: dict[str, str]
    match_effects: dict[str, str]


def remap_match_effect(
    effect: PlayerMatchSportingEffect,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    pre_match_sporting_fingerprint_map: dict[str, str],
    match_input_fingerprint_map: dict[str, str],
    authoritative_result_fingerprint_map: dict[str, str],
) -> PlayerMatchSportingEffect:
    if (effect.run_id, effect.branch_id) != (run_id, source_branch_id):
        raise SimulationSlotForkRemapUnsupportedError(
            "Match sporting effect scope does not match source Branch"
        )
    try:
        target = effect.model_copy(
            update={
                "branch_id": target_branch_id,
                "pre_match_sporting_fingerprint": pre_match_sporting_fingerprint_map[
                    effect.pre_match_sporting_fingerprint
                ],
                "match_input_fingerprint": match_input_fingerprint_map[
                    effect.match_input_fingerprint
                ],
                "authoritative_result_fingerprint": authoritative_result_fingerprint_map[
                    effect.authoritative_result_fingerprint
                ],
            }
        )
    except KeyError as exc:
        raise SimulationSlotForkRemapUnsupportedError(
            "Match sporting effect references evidence without a target fork mapping"
        ) from exc
    return PlayerMatchSportingEffect.model_validate_json(target.model_dump_json())


def remap_sporting_checkpoint(
    checkpoint: PlayerSportingCheckpoint,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    opening_week_fingerprint_map: dict[str, str],
    slot_start_fingerprint_map: dict[str, str],
    predecessor_checkpoint_fingerprint_map: dict[str, str],
    match_effect_fingerprint_map: dict[str, str],
) -> PlayerSportingCheckpoint:
    if (checkpoint.run_id, checkpoint.branch_id) != (run_id, source_branch_id):
        raise SimulationSlotForkRemapUnsupportedError(
            "Sporting checkpoint scope does not match source Branch"
        )
    try:
        opening = opening_week_fingerprint_map[checkpoint.opening_week_fingerprint]
        slot_start = slot_start_fingerprint_map[checkpoint.slot_start_fingerprint]
        predecessor = (
            None
            if checkpoint.predecessor_checkpoint_fingerprint is None
            else predecessor_checkpoint_fingerprint_map[
                checkpoint.predecessor_checkpoint_fingerprint
            ]
        )
        effects = tuple(
            sorted(
                match_effect_fingerprint_map[value]
                for value in checkpoint.applied_effect_fingerprints
            )
        )
    except KeyError as exc:
        raise SimulationSlotForkRemapUnsupportedError(
            "Sporting checkpoint references evidence without a target fork mapping"
        ) from exc

    target = checkpoint.model_copy(
        update={
            "branch_id": target_branch_id,
            "opening_week_fingerprint": opening,
            "slot_start_fingerprint": slot_start,
            "predecessor_checkpoint_fingerprint": predecessor,
            "applied_effect_fingerprints": effects,
        }
    )
    return PlayerSportingCheckpoint.model_validate_json(target.model_dump_json())


@dataclass(frozen=True)
class RemappedCompetitiveGroup:
    payload_json: str
    match_input_fingerprint: str
    result_fingerprint: str
    effect_fingerprint_map: dict[str, str]


def remap_slot_plan(
    plan: SimulationSlotPlan,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    slot_start_fingerprint_map: dict[str, str],
) -> SimulationSlotPlan:
    if (plan.run_id, plan.branch_id) != (run_id, source_branch_id):
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation Slot plan scope does not match source Branch"
        )
    try:
        target_start = slot_start_fingerprint_map[plan.slot_start_fingerprint]
    except KeyError as exc:
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation Slot plan references slot-start evidence without a target fork mapping"
        ) from exc
    target = plan.model_copy(
        update={
            "branch_id": target_branch_id,
            "slot_start_fingerprint": target_start,
        }
    )
    return SimulationSlotPlan.model_validate_json(target.model_dump_json())


def remap_competitive_group_payload(
    payload_json: str,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    slot_start_fingerprint_map: dict[str, str],
) -> RemappedCompetitiveGroup:
    import json

    payload = json.loads(payload_json)
    if payload.get("schema_version") == "authoritative_walkover_group.v1":
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation Slot core group remap does not yet support walkover groups"
        )

    protected = AuthoritativeMatchInput.model_validate_json(
        json.dumps(payload["authoritative_input"])
    )
    if (protected.run_id, protected.branch_id) != (run_id, source_branch_id):
        raise SimulationSlotForkRemapUnsupportedError(
            "Authoritative match input scope does not match source Branch"
        )
    try:
        target_slot_start = slot_start_fingerprint_map[
            protected.slot_start_fingerprint
        ]
    except KeyError as exc:
        raise SimulationSlotForkRemapUnsupportedError(
            "Authoritative match input references slot-start evidence without a target fork mapping"
        ) from exc

    target_projections = tuple(
        projection.model_copy(
            update={"source_sporting_fingerprint": target_slot_start}
        )
        for projection in protected.player_projections
    )
    target_input = AuthoritativeMatchInput.model_validate_json(
        protected.model_copy(
            update={
                "branch_id": target_branch_id,
                "slot_start_fingerprint": target_slot_start,
                "player_projections": target_projections,
            }
        ).model_dump_json()
    )

    result = MatchResult.model_validate(payload["result"])
    target_result_fingerprint = fingerprint(
        {
            "input": target_input.fingerprint,
            "result": result.model_dump(mode="json"),
        }
    )
    policy = MatchSportingEffectsPolicy.model_validate_json(
        json.dumps(payload["effects_policy"])
    )
    source_effects = tuple(
        PlayerMatchSportingEffect.model_validate_json(json.dumps(value))
        for value in payload["effects"]
    )
    effect_map: dict[str, str] = {}
    target_effects = []
    for source_effect in source_effects:
        target_effect = remap_match_effect(
            source_effect,
            run_id=run_id,
            source_branch_id=source_branch_id,
            target_branch_id=target_branch_id,
            pre_match_sporting_fingerprint_map={
                protected.slot_start_fingerprint: target_slot_start
            },
            match_input_fingerprint_map={
                protected.fingerprint: target_input.fingerprint
            },
            authoritative_result_fingerprint_map={
                payload["result_fingerprint"]: target_result_fingerprint
            },
        )
        if (
            target_effect.policy_id != policy.policy_id
            or target_effect.policy_fingerprint != policy.fingerprint
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Remapped match effect policy differs from frozen group policy"
            )
        effect_map[source_effect.fingerprint] = target_effect.fingerprint
        target_effects.append(target_effect)

    target_payload = {
        "authoritative_input": target_input.model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
        "result_fingerprint": target_result_fingerprint,
        "effects": [effect.model_dump(mode="json") for effect in target_effects],
        "effects_policy": policy.model_dump(mode="json"),
    }
    return RemappedCompetitiveGroup(
        payload_json=json.dumps(
            target_payload, sort_keys=True, separators=(",", ":")
        ),
        match_input_fingerprint=target_input.fingerprint,
        result_fingerprint=target_result_fingerprint,
        effect_fingerprint_map=effect_map,
    )


@dataclass(frozen=True)
class RemappedSimulationSlotCore:
    component: dict
    match_inputs: dict[str, str]
    results: dict[str, str]
    match_effects: dict[str, str]
    terminal_checkpoints: dict[str, str]
    slot_starts: dict[str, str]


def remap_completed_simulation_slot_core(
    payload,
    *,
    run_id: str,
    source_branch_id: str,
    target_branch_id: str,
    opening_sporting_fingerprint_map: dict[str, str],
) -> RemappedSimulationSlotCore | None:
    """Rebuild a completed slots+groups Saved Revision core in canonical order.

    Non-empty auxiliary Simulation Slot authorities stay fail-closed until their
    individual identity trees have dedicated remappers.
    """
    import json

    from beta_engine.application.authoritative_slot_matches import (
        MATCH_ENGINE_VERSION,
    )
    from beta_engine.infrastructure.db.models import (
        SimulationEventGroupModel,
        SimulationSlotModel,
    )
    from beta_engine.infrastructure.db.simulation_slot_state import (
        COMPONENT_KEY,
        _component,
        _load,
    )

    source = _load(
        payload,
        run_id=run_id,
        branch_id=source_branch_id,
    )
    if source is None:
        return None

    auxiliary = set(source) - {"fingerprint", "slots", "groups"}
    nonempty_auxiliary = {
        key for key in auxiliary if source.get(key)
    }
    if nonempty_auxiliary:
        raise SimulationSlotForkRemapUnsupportedError(
            "Simulation Slot Branch fork core has unsupported auxiliary authorities: "
            + ", ".join(sorted(nonempty_auxiliary))
        )

    source_slots = sorted(
        (SimulationSlotModel(**value) for value in source["slots"]),
        key=lambda row: (row.week_ordinal, row.slot_ordinal),
    )
    source_groups = [
        SimulationEventGroupModel(**value) for value in source["groups"]
    ]
    groups_by_slot: dict[tuple[int, str], list[SimulationEventGroupModel]] = {}
    for group in source_groups:
        groups_by_slot.setdefault(
            (group.week_ordinal, group.slot_id), []
        ).append(group)

    slot_start_map: dict[str, str] = {}
    checkpoint_map: dict[str, str] = {}
    input_map: dict[str, str] = {}
    result_map: dict[str, str] = {}
    effect_map: dict[str, str] = {}
    target_slots: list[SimulationSlotModel] = []
    target_groups: list[SimulationEventGroupModel] = []

    for source_slot in source_slots:
        if source_slot.status != "complete":
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation Slot Branch fork core currently requires completed slots"
            )
        source_plan = SimulationSlotPlan.model_validate_json(
            source_slot.payload_json
        )
        source_start = PlayerSportingCheckpoint.model_validate_json(
            source_slot.slot_start_checkpoint_json
        )
        source_terminal = PlayerSportingCheckpoint.model_validate_json(
            source_slot.terminal_checkpoint_json
        )
        if (
            source_plan.slot_start_fingerprint != source_slot.slot_start_fingerprint
            or source_start.slot_start_fingerprint != source_slot.slot_start_fingerprint
        ):
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation Slot source start identity is inconsistent"
            )

        try:
            target_opening = opening_sporting_fingerprint_map[
                source_start.opening_week_fingerprint
            ]
            target_predecessor = (
                None
                if source_start.predecessor_checkpoint_fingerprint is None
                else checkpoint_map[source_start.predecessor_checkpoint_fingerprint]
            )
        except KeyError as exc:
            raise SimulationSlotForkRemapUnsupportedError(
                "Simulation Slot start references sporting/checkpoint evidence without a target mapping"
            ) from exc

        target_slot_start = fingerprint(
            {
                "run_id": run_id,
                "branch_id": target_branch_id,
                "week": source_plan.week.model_dump(mode="json"),
                "ordinal": source_plan.ordinal,
                "predecessor": target_predecessor,
                "players": [
                    player.model_dump(mode="json")
                    for player in source_start.players
                ],
            }
        )
        slot_start_map[source_slot.slot_start_fingerprint] = target_slot_start

        target_start = remap_sporting_checkpoint(
            source_start,
            run_id=run_id,
            source_branch_id=source_branch_id,
            target_branch_id=target_branch_id,
            opening_week_fingerprint_map=opening_sporting_fingerprint_map,
            slot_start_fingerprint_map=slot_start_map,
            predecessor_checkpoint_fingerprint_map=checkpoint_map,
            match_effect_fingerprint_map=effect_map,
        )
        target_plan = remap_slot_plan(
            source_plan,
            run_id=run_id,
            source_branch_id=source_branch_id,
            target_branch_id=target_branch_id,
            slot_start_fingerprint_map=slot_start_map,
        )

        slot_groups = sorted(
            groups_by_slot.get(
                (source_slot.week_ordinal, source_slot.slot_id), []
            ),
            key=lambda row: row.group_id,
        )
        if {row.group_id for row in slot_groups} != set(source_plan.group_ids):
            raise SimulationSlotForkRemapUnsupportedError(
                "Completed Simulation Slot group universe differs from its plan"
            )

        for source_group in slot_groups:
            remapped = remap_competitive_group_payload(
                source_group.payload_json,
                run_id=run_id,
                source_branch_id=source_branch_id,
                target_branch_id=target_branch_id,
                slot_start_fingerprint_map=slot_start_map,
            )
            group_payload = json.loads(remapped.payload_json)
            target_input = AuthoritativeMatchInput.model_validate_json(
                json.dumps(group_payload["authoritative_input"])
            )
            policy = MatchSportingEffectsPolicy.model_validate_json(
                json.dumps(group_payload["effects_policy"])
            )
            seed = target_input.engine_input.simulation_seed
            players = [
                projection.player_id
                for projection in target_input.player_projections
            ]
            command_fingerprint = fingerprint(
                {
                    "scope": [
                        run_id,
                        target_branch_id,
                        source_group.week_ordinal,
                        source_group.slot_id,
                        source_group.group_id,
                        source_group.match_id,
                    ],
                    "slot_start": target_slot_start,
                    "event_id": target_input.event_id,
                    "players": players,
                    "seed": seed,
                    "engine": MATCH_ENGINE_VERSION,
                    "projection": target_input.player_projections[
                        0
                    ].projection_policy_fingerprint,
                    "effects": policy.fingerprint,
                }
            )
            input_map[source_group.match_input_fingerprint] = (
                remapped.match_input_fingerprint
            )
            result_map[source_group.result_fingerprint] = (
                remapped.result_fingerprint
            )
            effect_map.update(remapped.effect_fingerprint_map)
            target_groups.append(
                SimulationEventGroupModel(
                    run_id=run_id,
                    branch_id=target_branch_id,
                    week_ordinal=source_group.week_ordinal,
                    slot_id=source_group.slot_id,
                    group_id=source_group.group_id,
                    command_fingerprint=command_fingerprint,
                    match_id=source_group.match_id,
                    match_input_fingerprint=remapped.match_input_fingerprint,
                    result_fingerprint=remapped.result_fingerprint,
                    payload_json=remapped.payload_json,
                )
            )

        target_terminal = remap_sporting_checkpoint(
            source_terminal,
            run_id=run_id,
            source_branch_id=source_branch_id,
            target_branch_id=target_branch_id,
            opening_week_fingerprint_map=opening_sporting_fingerprint_map,
            slot_start_fingerprint_map=slot_start_map,
            predecessor_checkpoint_fingerprint_map=checkpoint_map,
            match_effect_fingerprint_map=effect_map,
        )
        checkpoint_map[source_terminal.fingerprint] = target_terminal.fingerprint
        target_slots.append(
            SimulationSlotModel(
                run_id=run_id,
                branch_id=target_branch_id,
                week_ordinal=source_slot.week_ordinal,
                slot_id=source_slot.slot_id,
                slot_ordinal=source_slot.slot_ordinal,
                plan_fingerprint=target_plan.fingerprint,
                slot_start_fingerprint=target_slot_start,
                status="complete",
                payload_json=target_plan.model_dump_json(),
                slot_start_checkpoint_json=target_start.model_dump_json(),
                terminal_checkpoint_json=target_terminal.model_dump_json(),
            )
        )

    rebuilt = _component(
        target_slots,
        target_groups,
        include_commands="commands" in source,
        include_authorities="authorities" in source,
        schedules=(),
        include_schedules="schedules" in source,
        entry_fields=(),
        include_entry_fields="entry_fields" in source,
        wild_card_authorities=(),
        include_wild_card_authorities="wild_card_authorities" in source,
        draw_inputs=(),
        include_draw_inputs="draw_inputs" in source,
        draw_authorities=(),
        include_draw_authorities="draw_authorities" in source,
        draw_process_authorities=(),
        include_draw_process_authorities="draw_process_authorities" in source,
        draw_revisions=(),
        include_draw_revisions="draw_revisions" in source,
    )
    return RemappedSimulationSlotCore(
        component=rebuilt,
        match_inputs=input_map,
        results=result_map,
        match_effects=effect_map,
        terminal_checkpoints=checkpoint_map,
        slot_starts=slot_start_map,
    )
