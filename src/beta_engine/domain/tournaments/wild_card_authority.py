"""Canonical Run/Branch-owned Wild Card and Reserve Wild Card resolution."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.entry_field import TournamentEntryField


WildCardResolutionSource = Literal["original_wc", "reserve_wc", "unfilled"]


class TournamentWildCardSlotResolution(FrozenInput):
    wildcard_index: int = Field(ge=1)
    original_player_id: str | None = None
    active_player_id: str | None = None
    source: WildCardResolutionSource
    reserve_ordinal: int | None = Field(default=None, ge=1)
    released_because_direct_acceptance: bool = False

    @model_validator(mode="after")
    def validate_resolution(self):
        if self.source == "unfilled":
            if self.active_player_id is not None or self.reserve_ordinal is not None:
                raise ValueError("Unfilled WC slot cannot carry an active player")
        elif not self.active_player_id:
            raise ValueError("Resolved WC slot requires an active player")
        if self.source == "reserve_wc" and self.reserve_ordinal is None:
            raise ValueError("RWC resolution requires reserve ordering evidence")
        if self.source != "reserve_wc" and self.reserve_ordinal is not None:
            raise ValueError("Only RWC resolution may carry reserve ordinal")
        return self


class TournamentWildCardAuthority(FrozenInput):
    schema_version: Literal[
        "tournament_wild_card_authority.v1",
        "tournament_wild_card_authority.v2",
        "tournament_wild_card_authority.v3",
    ] = "tournament_wild_card_authority.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    resolved_by_command_id: str = Field(min_length=1, max_length=128)
    entry_field_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    field_sequence: int = Field(ge=1)
    decision_week: RankingWeek | None = None
    decision_slot_ordinal: int | None = Field(default=None, ge=1)
    selection_policy_id: str | None = Field(default=None, min_length=1, max_length=128)
    operator_label: str | None = Field(default=None, min_length=1, max_length=128)
    audit_reason: str | None = Field(default=None, min_length=1, max_length=512)
    original_wild_card_player_ids: tuple[str | None, ...]
    reserve_wild_card_player_ids: tuple[str, ...] = ()
    unavailable_player_ids: tuple[str, ...] = ()
    slots: tuple[TournamentWildCardSlotResolution, ...]
    adjusted_qualification_player_ids: tuple[str, ...]
    adjusted_below_qualification_cut_player_ids: tuple[str, ...]

    @model_validator(mode="after")
    def validate_structure(self):
        audit = (self.selection_policy_id, self.operator_label, self.audit_reason)
        if self.schema_version == "tournament_wild_card_authority.v1":
            if self.decision_week is not None or self.decision_slot_ordinal is not None:
                raise ValueError("Historical WC authority v1 cannot carry global-slot chronology")
            if any(value is not None for value in audit):
                raise ValueError("Historical WC authority v1 cannot carry Admin review audit")
        elif self.schema_version == "tournament_wild_card_authority.v2":
            if self.decision_week is None or self.decision_slot_ordinal is None:
                raise ValueError("WC authority v2 requires exact decision week and global slot ordinal")
            if any(value is not None for value in audit):
                raise ValueError("WC authority v2 cannot carry v3 Admin review audit")
        else:
            if self.decision_week is None or self.decision_slot_ordinal is None:
                raise ValueError("WC authority v3 requires exact decision week and global slot ordinal")
            if any(value is None for value in audit):
                raise ValueError("WC authority v3 requires complete Admin review audit")
            if self.operator_label != self.operator_label.strip():
                raise ValueError("WC Admin operator label must be trimmed")
            if self.audit_reason != self.audit_reason.strip():
                raise ValueError("WC Admin audit reason must be trimmed")
        expected = tuple(range(1, len(self.slots) + 1))
        actual = tuple(slot.wildcard_index for slot in self.slots)
        if actual != expected:
            raise ValueError("WC slots must be canonical and contiguous")
        active = tuple(
            slot.active_player_id for slot in self.slots if slot.active_player_id
        )
        if len(active) != len(set(active)):
            raise ValueError("A player cannot occupy more than one WC slot")
        if len(self.reserve_wild_card_player_ids) != len(
            set(self.reserve_wild_card_player_ids)
        ):
            raise ValueError("RWC ordering cannot contain duplicate players")
        if len(self.unavailable_player_ids) != len(set(self.unavailable_player_ids)):
            raise ValueError("Unavailable WC identities must be unique")
        return self

    @property
    def active_wild_card_player_ids(self) -> tuple[str, ...]:
        return tuple(
            slot.active_player_id
            for slot in self.slots
            if slot.active_player_id is not None
        )

    @property
    def fingerprint(self) -> str:
        payload = self.model_dump(mode="json")
        # Historical readers must retain their exact pre-extension payload shape.
        if self.schema_version == "tournament_wild_card_authority.v1":
            payload.pop("decision_week", None)
            payload.pop("decision_slot_ordinal", None)
        if self.schema_version in {
            "tournament_wild_card_authority.v1",
            "tournament_wild_card_authority.v2",
        }:
            payload.pop("selection_policy_id", None)
            payload.pop("operator_label", None)
            payload.pop("audit_reason", None)
        return hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentWildCardAuthorityBuilder:
    @staticmethod
    def build(
        *,
        field: TournamentEntryField,
        field_sequence: int,
        command_id: str,
        original_wild_card_player_ids: tuple[str | None, ...],
        reserve_wild_card_player_ids: tuple[str, ...] = (),
        unavailable_player_ids: tuple[str, ...] = (),
        decision_week: RankingWeek | None = None,
        decision_slot_ordinal: int | None = None,
        selection_policy_id: str | None = None,
        operator_label: str | None = None,
        audit_reason: str | None = None,
    ) -> TournamentWildCardAuthority:
        if (decision_week is None) != (decision_slot_ordinal is None):
            raise ValueError("WC decision chronology requires week and slot ordinal together")
        audit = (selection_policy_id, operator_label, audit_reason)
        if any(value is not None for value in audit) and any(value is None for value in audit):
            raise ValueError("WC Admin review audit must be supplied as one complete set")
        if any(value is not None for value in audit) and decision_week is None:
            raise ValueError("WC Admin review audit requires chronology-aware authority")
        schema_version = (
            "tournament_wild_card_authority.v3"
            if selection_policy_id is not None
            else (
                "tournament_wild_card_authority.v2"
                if decision_week is not None
                else "tournament_wild_card_authority.v1"
            )
        )
        slot_count = field.capacity.wild_card_slots
        if len(original_wild_card_player_ids) != slot_count:
            raise ValueError(
                "WC nomination count must equal reserved Wild Card slot count"
            )
        if len(reserve_wild_card_player_ids) != len(set(reserve_wild_card_player_ids)):
            raise ValueError("RWC ordering cannot contain duplicate players")

        direct = set(field.direct_main_player_ids)
        unavailable = set(unavailable_player_ids)
        used: set[str] = set()
        reserve_cursor = 0
        slots: list[TournamentWildCardSlotResolution] = []

        for index, original in enumerate(original_wild_card_player_ids, start=1):
            released_direct = original is not None and original in direct
            candidate = (
                original
                if original is not None
                and original not in direct
                and original not in unavailable
                and original not in used
                else None
            )
            source: WildCardResolutionSource = "original_wc"
            reserve_ordinal = None

            if candidate is None:
                source = "unfilled"
                while reserve_cursor < len(reserve_wild_card_player_ids):
                    reserve = reserve_wild_card_player_ids[reserve_cursor]
                    reserve_cursor += 1
                    if (
                        reserve in direct
                        or reserve in unavailable
                        or reserve in used
                    ):
                        continue
                    candidate = reserve
                    source = "reserve_wc"
                    reserve_ordinal = reserve_cursor
                    break

            if candidate is not None:
                used.add(candidate)

            slots.append(
                TournamentWildCardSlotResolution(
                    wildcard_index=index,
                    original_player_id=original,
                    active_player_id=candidate,
                    source=source,
                    reserve_ordinal=reserve_ordinal,
                    released_because_direct_acceptance=released_direct,
                )
            )

        active_wc = {
            slot.active_player_id for slot in slots if slot.active_player_id is not None
        }
        qualification = [
            player_id
            for player_id in field.qualification_player_ids
            if player_id not in active_wc
        ]
        below = [
            player_id
            for player_id in field.below_qualification_cut_player_ids
            if player_id not in active_wc
        ]
        q_target = len(field.qualification_player_ids)
        needed = max(0, q_target - len(qualification))
        qualification.extend(below[:needed])
        below = below[needed:]

        return TournamentWildCardAuthority(
            schema_version=schema_version,
            run_id=field.run_id,
            branch_id=field.branch_id,
            event_id=field.event_id,
            resolved_by_command_id=command_id,
            entry_field_fingerprint=field.fingerprint,
            field_sequence=field_sequence,
            decision_week=decision_week,
            decision_slot_ordinal=decision_slot_ordinal,
            selection_policy_id=selection_policy_id,
            operator_label=operator_label,
            audit_reason=audit_reason,
            original_wild_card_player_ids=original_wild_card_player_ids,
            reserve_wild_card_player_ids=reserve_wild_card_player_ids,
            unavailable_player_ids=tuple(sorted(unavailable)),
            slots=tuple(slots),
            adjusted_qualification_player_ids=tuple(qualification),
            adjusted_below_qualification_cut_player_ids=tuple(below),
        )
