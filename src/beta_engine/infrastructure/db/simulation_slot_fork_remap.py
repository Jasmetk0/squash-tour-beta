from __future__ import annotations

from dataclasses import dataclass

from beta_engine.domain.simulation_slots import (
    PlayerMatchSportingEffect,
    PlayerSportingCheckpoint,
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
