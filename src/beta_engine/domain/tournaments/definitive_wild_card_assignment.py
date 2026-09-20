"""Definitive Wild Card assignment timing authority for Tour-entry truth."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.tour_entry import PlayerTourEntryTrigger
from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.wild_card_authority import (
    TournamentWildCardAuthority,
)


DefinitiveWildCardSource = Literal["original_wc", "reserve_wc"]


class DefinitiveWildCardAssignmentAuthority(FrozenInput):
    """Freeze the exact moment one valid WC/RWC becomes definitive in the field."""

    schema_version: Literal["definitive_wild_card_assignment_authority.v1"] = (
        "definitive_wild_card_assignment_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    wildcard_index: int = Field(ge=1)
    assignment_source: DefinitiveWildCardSource
    reserve_ordinal: int | None = Field(default=None, ge=1)
    assignment_week: RankingWeek
    decision_slot_ordinal: int = Field(ge=1)
    source_wild_card_command_id: str = Field(min_length=1, max_length=128)
    source_wild_card_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_field_sequence: int = Field(ge=1)
    provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_source(self):
        if self.assignment_source == "reserve_wc" and self.reserve_ordinal is None:
            raise ValueError("Definitive RWC assignment requires reserve ordinal")
        if self.assignment_source == "original_wc" and self.reserve_ordinal is not None:
            raise ValueError("Original WC assignment cannot carry reserve ordinal")
        return self

    @classmethod
    def from_resolution(
        cls,
        *,
        authority: TournamentWildCardAuthority,
        wildcard_index: int,
        assignment_week: RankingWeek,
        decision_slot_ordinal: int,
        provenance: str,
    ) -> "DefinitiveWildCardAssignmentAuthority":
        try:
            slot = next(
                item for item in authority.slots if item.wildcard_index == wildcard_index
            )
        except StopIteration as exc:
            raise ValueError("Wild Card slot is absent from source authority") from exc
        if slot.source == "unfilled" or slot.active_player_id is None:
            raise ValueError("Unfilled Wild Card slot is not a definitive assignment")

        return cls(
            run_id=authority.run_id,
            branch_id=authority.branch_id,
            event_id=authority.event_id,
            player_id=slot.active_player_id,
            wildcard_index=slot.wildcard_index,
            assignment_source=slot.source,
            reserve_ordinal=slot.reserve_ordinal,
            assignment_week=assignment_week,
            decision_slot_ordinal=decision_slot_ordinal,
            source_wild_card_command_id=authority.resolved_by_command_id,
            source_wild_card_authority_fingerprint=authority.fingerprint,
            source_entry_field_fingerprint=authority.entry_field_fingerprint,
            source_field_sequence=authority.field_sequence,
            provenance=provenance,
        )

    @property
    def decision_position(self) -> tuple[int, int]:
        return (self.assignment_week.ordinal, self.decision_slot_ordinal)

    @property
    def source_evidence_id(self) -> str:
        return f"{self.source_wild_card_command_id}:wc:{self.wildcard_index}"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def to_tour_entry_trigger(self) -> PlayerTourEntryTrigger:
        return PlayerTourEntryTrigger(
            run_id=self.run_id,
            branch_id=self.branch_id,
            player_id=self.player_id,
            event_id=self.event_id,
            trigger_kind="definitive_wild_card_assignment",
            trigger_week=self.assignment_week,
            decision_slot_ordinal=self.decision_slot_ordinal,
            source_evidence_id=self.source_evidence_id,
            source_evidence_fingerprint=self.fingerprint,
            provenance=self.provenance,
        )
