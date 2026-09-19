"""Canonical post-draw Reserve Wild Card replacement authority."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
)


class TournamentPostDrawWildCardRepairAuthority(FrozenInput):
    schema_version: Literal["tournament_post_draw_wild_card_repair.v1"] = (
        "tournament_post_draw_wild_card_repair.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1, max_length=128)
    base_wild_card_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    wildcard_index: int = Field(ge=1)
    physical_slot_index: int = Field(ge=1)
    withdrawn_player_id: str = Field(min_length=1)
    replacement_player_id: str = Field(min_length=1)
    reserve_ordinal: int = Field(ge=1)
    unavailable_player_ids: tuple[str, ...] = ()
    replacement_cutoff_authority: TournamentPlayerReplacementCutoffAuthority

    @model_validator(mode="after")
    def validate_repair(self):
        if self.withdrawn_player_id == self.replacement_player_id:
            raise ValueError("RWC repair cannot replace a player with itself")
        if tuple(sorted(set(self.unavailable_player_ids))) != self.unavailable_player_ids:
            raise ValueError("RWC unavailable identities must be sorted and unique")
        cutoff = self.replacement_cutoff_authority
        if (
            cutoff.run_id,
            cutoff.branch_id,
            cutoff.event_id,
            cutoff.player_id,
        ) != (
            self.run_id,
            self.branch_id,
            self.event_id,
            self.withdrawn_player_id,
        ):
            raise ValueError("RWC replacement cutoff scope mismatch")
        if cutoff.status != "replacement_open":
            raise ValueError("RWC repair requires replacement-open cutoff authority")
        return self

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentPostDrawWildCardRepairAuthorityBuilder:
    @staticmethod
    def build(
        *,
        predecessor: TournamentDrawAuthority,
        predecessor_draw_input: TournamentDrawInputAuthority,
        base_wild_card_authority: TournamentWildCardAuthority,
        command_id: str,
        withdrawn_player_id: str,
        unavailable_player_ids: tuple[str, ...],
        replacement_cutoff_authority: TournamentPlayerReplacementCutoffAuthority,
    ) -> TournamentPostDrawWildCardRepairAuthority:
        scope = (predecessor.run_id, predecessor.branch_id, predecessor.event_id)
        if (
            predecessor_draw_input.run_id,
            predecessor_draw_input.branch_id,
            predecessor_draw_input.event_id,
        ) != scope:
            raise ValueError("RWC predecessor Draw Input scope mismatch")
        if (
            base_wild_card_authority.run_id,
            base_wild_card_authority.branch_id,
            base_wild_card_authority.event_id,
        ) != scope:
            raise ValueError("RWC base Wild Card authority scope mismatch")
        if (
            predecessor.draw_input_fingerprint
            != predecessor_draw_input.fingerprint
        ):
            raise ValueError("RWC predecessor Draw/Input binding mismatch")
        if (
            predecessor_draw_input.wild_card_authority_fingerprint
            != base_wild_card_authority.fingerprint
        ):
            raise ValueError("RWC repair references a different base Wild Card authority")
        if predecessor_draw_input.schema_version not in {
            "tournament_draw_input_authority.v3",
            "tournament_draw_input_authority.v4",
        }:
            raise ValueError("Post-draw RWC repair requires canonical WC Draw Input")

        wc_players = predecessor_draw_input.wild_card_player_ids
        if wc_players.count(withdrawn_player_id) != 1:
            raise ValueError("RWC repair withdrawal is not an active WC holder")
        wildcard_index = wc_players.index(withdrawn_player_id) + 1

        matching_slots = [
            slot
            for slot in predecessor.main.slots
            if slot.player_id == withdrawn_player_id
        ]
        if len(matching_slots) != 1:
            raise ValueError("RWC repair cannot resolve the withdrawn physical slot")
        slot = matching_slots[0]
        if slot.entry_status != "wild_card":
            raise ValueError("RWC repair target physical slot is not a WC slot")
        if slot.seed_number is not None:
            raise ValueError(
                "Seeded WC withdrawal requires the later seed-aware WC repair slice"
            )

        unavailable = set(base_wild_card_authority.unavailable_player_ids)
        unavailable.update(unavailable_player_ids)
        unavailable.update(predecessor_draw_input.withdrawn_player_ids)
        unavailable.add(withdrawn_player_id)

        main_players = {
            item.player_id
            for item in predecessor.main.slots
            if item.player_id is not None
        }
        qualification_players = {
            item.player_id
            for bracket in predecessor.qualification_brackets
            for item in bracket.slots
            if item.player_id is not None
        }

        replacement_player_id = None
        reserve_ordinal = None
        for ordinal, reserve in enumerate(
            base_wild_card_authority.reserve_wild_card_player_ids,
            start=1,
        ):
            if reserve in unavailable:
                continue
            if reserve in main_players:
                # Direct/Main or already-used WC players do not need another WC.
                continue
            if reserve in qualification_players:
                raise ValueError(
                    "Highest-priority available RWC is active in Qualification; "
                    "cross-draw atomic RWC promotion is required"
                )
            replacement_player_id = reserve
            reserve_ordinal = ordinal
            break

        if replacement_player_id is None or reserve_ordinal is None:
            raise ValueError(
                "No external RWC is available; ordinary replacement fallback is required"
            )

        return TournamentPostDrawWildCardRepairAuthority(
            run_id=scope[0],
            branch_id=scope[1],
            event_id=scope[2],
            command_id=command_id,
            base_wild_card_authority_fingerprint=base_wild_card_authority.fingerprint,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
            wildcard_index=wildcard_index,
            physical_slot_index=slot.slot_index,
            withdrawn_player_id=withdrawn_player_id,
            replacement_player_id=replacement_player_id,
            reserve_ordinal=reserve_ordinal,
            unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
            replacement_cutoff_authority=replacement_cutoff_authority,
        )
