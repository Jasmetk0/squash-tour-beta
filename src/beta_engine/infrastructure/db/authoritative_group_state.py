"""Typed decoder for persisted authoritative Simulation Slot group evidence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import cast

from beta_engine.domain.matches.models import MatchResult
from beta_engine.domain.simulation_slots import (
    AuthoritativeMatchInput,
    MatchSportingEffectsPolicy,
    PlayerMatchSportingEffect,
    PlayerSportingCheckpoint,
    fingerprint,
)
from beta_engine.domain.tournaments.walkover_authority import (
    TournamentWalkoverAuthority,
    TournamentWalkoverResult,
)


@dataclass(frozen=True)
class AuthoritativeGroupResult:
    authoritative_input: AuthoritativeMatchInput
    result: MatchResult
    result_fingerprint: str
    effects: tuple[PlayerMatchSportingEffect, PlayerMatchSportingEffect]
    terminal_checkpoint: PlayerSportingCheckpoint
    exact_retry: bool = False


@dataclass(frozen=True)
class AuthoritativeWalkoverGroupResult:
    authoritative_input: TournamentWalkoverAuthority
    result: TournamentWalkoverResult
    result_fingerprint: str
    effects: tuple[PlayerMatchSportingEffect, ...]
    terminal_checkpoint: PlayerSportingCheckpoint
    exact_retry: bool = False


AuthoritativeTournamentGroupResult = (
    AuthoritativeGroupResult | AuthoritativeWalkoverGroupResult
)


def load_authoritative_group(
    row, *, exact_retry: bool = False
) -> AuthoritativeTournamentGroupResult:
    """Decode and semantically validate one immutable persisted group row."""
    payload = json.loads(row.payload_json)
    if payload.get("schema_version") == "authoritative_walkover_group.v1":
        authority = TournamentWalkoverAuthority.model_validate_json(
            json.dumps(payload.get("walkover_authority"))
        )
        result = TournamentWalkoverResult.model_validate_json(
            json.dumps(payload.get("result"))
        )
        result_fp = fingerprint(
            {
                "authority": authority.fingerprint,
                "result": result.model_dump(mode="json"),
            }
        )
        command = fingerprint(
            {
                "kind": "authoritative_walkover_group.v1",
                "authority": authority.model_dump(mode="json"),
            }
        )
        if (
            authority.run_id,
            authority.branch_id,
            authority.week.ordinal,
            authority.slot_id,
            authority.group_id,
            authority.match_id,
        ) != (
            row.run_id,
            row.branch_id,
            row.week_ordinal,
            row.slot_id,
            row.group_id,
            row.match_id,
        ):
            raise ValueError("persisted W/O group scope or match mismatch")
        if (
            authority.fingerprint != row.match_input_fingerprint
            or payload.get("result_fingerprint") != row.result_fingerprint
            or result_fp != row.result_fingerprint
            or command != row.command_fingerprint
            or result != authority.result
        ):
            raise ValueError("persisted W/O authority/result fingerprint mismatch")
        terminal = PlayerSportingCheckpoint(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            week=authority.week,
            slot_id=authority.slot_id,
            slot_ordinal=0,
            opening_week_fingerprint=authority.slot_start_fingerprint,
            slot_start_fingerprint=authority.slot_start_fingerprint,
            predecessor_checkpoint_fingerprint=None,
            applied_effect_fingerprints=(),
            players=(),
        )
        return AuthoritativeWalkoverGroupResult(
            authority, result, row.result_fingerprint, (), terminal, exact_retry
        )

    protected = AuthoritativeMatchInput.model_validate_json(
        json.dumps(payload["authoritative_input"])
    )
    result = MatchResult.model_validate(payload["result"])
    effects = tuple(
        PlayerMatchSportingEffect.model_validate_json(json.dumps(value))
        for value in payload["effects"]
    )
    if len(effects) != 2:
        raise ValueError("authoritative competitive match requires two effects")
    paired_effects = cast(
        tuple[PlayerMatchSportingEffect, PlayerMatchSportingEffect], effects
    )
    result_fp = fingerprint(
        {"input": protected.fingerprint, "result": result.model_dump(mode="json")}
    )
    if (
        protected.fingerprint != row.match_input_fingerprint
        or payload["result_fingerprint"] != row.result_fingerprint
        or result_fp != row.result_fingerprint
    ):
        raise ValueError("persisted match input/result fingerprint mismatch")
    if (
        protected.run_id,
        protected.branch_id,
        protected.week.ordinal,
        protected.slot_id,
        protected.group_id,
        protected.match_id,
    ) != (
        row.run_id,
        row.branch_id,
        row.week_ordinal,
        row.slot_id,
        row.group_id,
        row.match_id,
    ) or result.match_id != protected.match_id:
        raise ValueError("persisted authoritative group scope or match mismatch")
    if any(
        effect.match_input_fingerprint != protected.fingerprint
        or effect.authoritative_result_fingerprint != row.result_fingerprint
        for effect in paired_effects
    ):
        raise ValueError("persisted match/effect evidence mismatch")
    projections = {item.player_id: item for item in protected.player_projections}
    try:
        policy = MatchSportingEffectsPolicy.model_validate_json(
            json.dumps(payload["effects_policy"])
        )
    except (KeyError, ValueError) as exc:
        raise ValueError(
            "persisted match effects policy is missing or corrupt"
        ) from exc
    if any(
        effect.player_id not in projections
        or effect.pre_match_sporting_fingerprint != protected.slot_start_fingerprint
        or effect.policy_id != policy.policy_id
        or effect.policy_fingerprint != policy.fingerprint
        or (effect.form_before, effect.sharpness_before, effect.fatigue_before)
        != (
            projections[effect.player_id].current_form,
            projections[effect.player_id].match_sharpness,
            projections[effect.player_id].long_term_fatigue,
        )
        or effect.form_after
        != min(
            policy.form_max,
            max(policy.form_min, effect.form_before + effect.form_delta),
        )
        or effect.sharpness_after
        != min(
            policy.sharpness_max,
            max(policy.sharpness_min, effect.sharpness_before + effect.sharpness_delta),
        )
        or effect.fatigue_after
        != min(
            policy.fatigue_max,
            max(policy.fatigue_min, effect.fatigue_before + effect.fatigue_delta),
        )
        for effect in paired_effects
    ):
        raise ValueError("persisted match effect semantics are corrupt")
    terminal = PlayerSportingCheckpoint(
        run_id=protected.run_id,
        branch_id=protected.branch_id,
        week=protected.week,
        slot_id=protected.slot_id,
        slot_ordinal=0,
        opening_week_fingerprint=protected.slot_start_fingerprint,
        slot_start_fingerprint=protected.slot_start_fingerprint,
        predecessor_checkpoint_fingerprint=None,
        applied_effect_fingerprints=tuple(
            sorted(e.fingerprint for e in paired_effects)
        ),
        players=(),
    )
    return AuthoritativeGroupResult(
        protected, result, row.result_fingerprint, paired_effects, terminal, exact_retry
    )
