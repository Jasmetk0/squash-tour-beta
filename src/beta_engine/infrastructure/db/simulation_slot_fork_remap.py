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
