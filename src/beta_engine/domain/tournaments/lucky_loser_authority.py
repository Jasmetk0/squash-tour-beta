"""Canonical Lucky Loser vacancy authority after Qualification has started."""

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


class TournamentLuckyLoserVacancyAuthority(FrozenInput):
    """One chronological Main Draw vacancy converted into LL1 / LL2 / ..."""

    schema_version: Literal["tournament_lucky_loser_vacancy.v1"] = (
        "tournament_lucky_loser_vacancy.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1, max_length=128)
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    withdrawn_player_id: str = Field(min_length=1)
    physical_slot_index: int = Field(ge=1)
    lucky_loser_ordinal: int = Field(ge=1)
    placeholder_id: str = Field(pattern=r"^LL[1-9][0-9]*$")
    vacated_main_seed_number: int | None = Field(
        default=None,
        ge=1,
        exclude_if=lambda value: value is None,
    )
    withdrawn_player_cutoff_authority: TournamentPlayerReplacementCutoffAuthority
    qualification_start_authority: TournamentPlayerReplacementCutoffAuthority

    @model_validator(mode="after")
    def validate_authority(self):
        if self.placeholder_id != f"LL{self.lucky_loser_ordinal}":
            raise ValueError("LL placeholder identity differs from chronological ordinal")
        scope = (self.run_id, self.branch_id, self.event_id)
        cutoff = self.withdrawn_player_cutoff_authority
        if (
            cutoff.run_id,
            cutoff.branch_id,
            cutoff.event_id,
            cutoff.player_id,
        ) != (*scope, self.withdrawn_player_id):
            raise ValueError("LL withdrawn-player cutoff scope mismatch")
        if cutoff.status != "replacement_open":
            raise ValueError("LL vacancy requires replacement-open withdrawn-player cutoff")

        qualification = self.qualification_start_authority
        if (
            qualification.run_id,
            qualification.branch_id,
            qualification.event_id,
        ) != scope:
            raise ValueError("LL Qualification-start evidence scope mismatch")
        if not qualification.played_matches:
            raise ValueError("LL vacancy requires real Qualification-start evidence")
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


class TournamentLuckyLoserVacancyAuthorityBuilder:
    @staticmethod
    def build(
        *,
        predecessor: TournamentDrawAuthority,
        predecessor_draw_input: TournamentDrawInputAuthority,
        command_id: str,
        withdrawn_player_id: str,
        lucky_loser_ordinal: int,
        withdrawn_player_cutoff_authority: TournamentPlayerReplacementCutoffAuthority,
        qualification_start_authority: TournamentPlayerReplacementCutoffAuthority,
        qualification_origin_player_ids: tuple[str, ...],
    ) -> TournamentLuckyLoserVacancyAuthority:
        scope = (predecessor.run_id, predecessor.branch_id, predecessor.event_id)
        if (
            predecessor_draw_input.run_id,
            predecessor_draw_input.branch_id,
            predecessor_draw_input.event_id,
        ) != scope:
            raise ValueError("LL predecessor Draw Input scope mismatch")
        if predecessor.draw_input_fingerprint != predecessor_draw_input.fingerprint:
            raise ValueError("LL predecessor Draw/Input binding mismatch")
        if not predecessor.qualification_brackets:
            raise ValueError("Lucky Loser vacancy requires a Qualification draw")
        if qualification_start_authority.player_id not in set(
            qualification_origin_player_ids
        ):
            raise ValueError(
                "LL Qualification-start evidence is not owned by the frozen Q field"
            )
        if not qualification_start_authority.played_matches:
            raise ValueError("Qualification has not started")

        matching = [
            slot for slot in predecessor.main.slots
            if slot.player_id == withdrawn_player_id
        ]
        if len(matching) != 1:
            raise ValueError("LL vacancy cannot resolve one active Main player slot")
        slot = matching[0]
        if slot.entry_status == "wild_card":
            raise ValueError(
                "WC slot must exhaust Reserve Wild Card priority before LL fallback"
            )
        if withdrawn_player_id not in set(predecessor_draw_input.direct_main_player_ids):
            raise ValueError(
                "First LL vacancy slice supports direct Main withdrawals only"
            )

        return TournamentLuckyLoserVacancyAuthority(
            run_id=scope[0],
            branch_id=scope[1],
            event_id=scope[2],
            command_id=command_id,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
            withdrawn_player_id=withdrawn_player_id,
            physical_slot_index=slot.slot_index,
            lucky_loser_ordinal=lucky_loser_ordinal,
            placeholder_id=f"LL{lucky_loser_ordinal}",
            vacated_main_seed_number=slot.seed_number,
            withdrawn_player_cutoff_authority=withdrawn_player_cutoff_authority,
            qualification_start_authority=qualification_start_authority,
        )
