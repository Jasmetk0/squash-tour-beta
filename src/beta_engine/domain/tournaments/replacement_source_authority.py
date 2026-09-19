"""Canonical replacement-source priority for Main Draw vacancies."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthority
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthority
from beta_engine.domain.tournaments.lucky_loser_authority import (
    TournamentLuckyLoserOrderAuthority,
    TournamentLuckyLoserQualificationWinnerEvidence,
)
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthority,
)
from beta_engine.domain.tournaments.wild_card_authority import TournamentWildCardAuthority


TournamentReplacementSource = Literal[
    "walkover",
    "reserve_wild_card",
    "qualification_promotion",
    "lucky_loser_pending",
    "lucky_loser",
    "external_reserve",
    "bye",
]


class TournamentDrawStartEvidence(FrozenInput):
    match_id: str = Field(min_length=1)
    result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentReplacementSourceAuthority(FrozenInput):
    """One immutable answer to 'where does this Main vacancy get filled from?'"""

    schema_version: Literal[
        "tournament_replacement_source.v1",
        "tournament_replacement_source.v2",
    ] = "tournament_replacement_source.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    withdrawn_player_id: str = Field(min_length=1)
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_slot_index: int = Field(ge=1)
    qualification_winner_evidence: TournamentLuckyLoserQualificationWinnerEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    source: TournamentReplacementSource
    selected_player_id: str | None = Field(
        default=None,
        min_length=1,
        exclude_if=lambda value: value is None,
    )
    source_ordinal: int | None = Field(
        default=None,
        ge=1,
        exclude_if=lambda value: value is None,
    )
    qualification_start_evidence: TournamentDrawStartEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    main_start_evidence: TournamentDrawStartEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    replacement_cutoff_authority: TournamentPlayerReplacementCutoffAuthority
    lucky_loser_order_authority: TournamentLuckyLoserOrderAuthority | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )
    unavailable_player_ids: tuple[str, ...] = ()
    prior_lucky_loser_player_ids: tuple[str, ...] = ()
    external_reserve_player_ids: tuple[str, ...] = ()
    base_wild_card_authority_fingerprint: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{64}$",
        exclude_if=lambda value: value is None,
    )

    @model_validator(mode="after")
    def validate_source(self):
        if self.schema_version == "tournament_replacement_source.v1":
            if self.qualification_winner_evidence is not None:
                raise ValueError("Historical replacement source v1 cannot carry Q-winner evidence")
        elif self.qualification_winner_evidence is None:
            raise ValueError("Q-winner replacement source v2 requires terminal evidence")
        elif self.qualification_winner_evidence.winner_player_id != self.withdrawn_player_id:
            raise ValueError("Q-winner replacement evidence belongs to another player")

        if tuple(sorted(set(self.unavailable_player_ids))) != self.unavailable_player_ids:
            raise ValueError("Replacement-source unavailable identities must be sorted")
        if len(set(self.prior_lucky_loser_player_ids)) != len(
            self.prior_lucky_loser_player_ids
        ):
            raise ValueError("Replacement-source prior LL assignments must be unique")
        if len(set(self.external_reserve_player_ids)) != len(
            self.external_reserve_player_ids
        ):
            raise ValueError("Replacement-source external reserve order has duplicates")

        player_sources = {
            "reserve_wild_card",
            "qualification_promotion",
            "lucky_loser",
            "external_reserve",
        }
        if self.source in player_sources:
            if self.selected_player_id is None or self.source_ordinal is None:
                raise ValueError("Player replacement source requires player and ordinal")
        elif self.selected_player_id is not None or self.source_ordinal is not None:
            raise ValueError("Non-player replacement source cannot carry player selection")

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
            raise ValueError("Replacement-source cutoff scope mismatch")
        if self.source == "walkover":
            if cutoff.status != "walkover_required":
                raise ValueError("W/O source requires closed replacement cutoff")
        elif cutoff.status != "replacement_open":
            raise ValueError("Replacement source requires open cutoff")

        if self.source in {"lucky_loser_pending", "lucky_loser", "external_reserve"}:
            if self.qualification_start_evidence is None:
                raise ValueError("Post-Q-start source requires Qualification start evidence")
        if self.source == "lucky_loser":
            if self.lucky_loser_order_authority is None:
                raise ValueError("Lucky Loser source requires frozen LL order")
            if self.source_ordinal is None or self.source_ordinal > len(
                self.lucky_loser_order_authority.candidates
            ):
                raise ValueError("Lucky Loser source ordinal is outside frozen LL order")
            candidate = self.lucky_loser_order_authority.candidates[
                self.source_ordinal - 1
            ]
            if candidate.player_id != self.selected_player_id:
                raise ValueError("Lucky Loser selection differs from frozen LL order")
        if self.source == "bye":
            if self.main_start_evidence is not None:
                raise ValueError("BYE fallback is only canonical before Main starts")
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


class TournamentReplacementSourceAuthorityBuilder:
    @staticmethod
    def build(
        *,
        predecessor: TournamentDrawAuthority,
        predecessor_draw_input: TournamentDrawInputAuthority,
        withdrawn_player_id: str,
        replacement_cutoff_authority: TournamentPlayerReplacementCutoffAuthority,
        qualification_start_evidence: TournamentDrawStartEvidence | None,
        main_start_evidence: TournamentDrawStartEvidence | None,
        base_wild_card_authority: TournamentWildCardAuthority | None,
        lucky_loser_order_authority: TournamentLuckyLoserOrderAuthority | None,
        external_reserve_player_ids: tuple[str, ...],
        unavailable_player_ids: tuple[str, ...] = (),
        qualification_winner_evidence: TournamentLuckyLoserQualificationWinnerEvidence | None = None,
    ) -> TournamentReplacementSourceAuthority:
        scope = (predecessor.run_id, predecessor.branch_id, predecessor.event_id)
        if (
            predecessor_draw_input.run_id,
            predecessor_draw_input.branch_id,
            predecessor_draw_input.event_id,
        ) != scope:
            raise ValueError("Replacement-source Draw Input scope mismatch")
        if predecessor.draw_input_fingerprint != predecessor_draw_input.fingerprint:
            raise ValueError("Replacement-source predecessor Draw/Input mismatch")

        if qualification_winner_evidence is not None:
            evidence = qualification_winner_evidence
            if evidence.winner_player_id != withdrawn_player_id:
                raise ValueError("Q-winner replacement evidence belongs to another player")
            bracket = next(
                (
                    item
                    for item in predecessor.qualification_brackets
                    if (item.section_id or "") == evidence.section_id
                ),
                None,
            )
            if bracket is None:
                raise ValueError("Q-winner replacement evidence references missing Q section")
            terminal = max(
                bracket.nodes,
                key=lambda item: (item.round_number, item.round_sequence),
            )
            if terminal.node_id != evidence.terminal_match_id:
                raise ValueError("Q-winner replacement evidence references wrong Q terminal")
            slots = [
                slot
                for slot in predecessor.main.slots
                if slot.entrant_kind == "qualifier_placeholder"
                and slot.placeholder_id == evidence.section_id
            ]
            if len(slots) != 1:
                raise ValueError("Replacement-source cannot resolve linked Main Q slot")
            slot = slots[0]
            if slot.player_id is not None or slot.seed_number is not None:
                raise ValueError("Linked Main Q slot must remain an unseeded placeholder")
        else:
            slots = [
                slot for slot in predecessor.main.slots
                if slot.player_id == withdrawn_player_id
            ]
            if len(slots) != 1:
                raise ValueError("Replacement-source cannot resolve one active Main slot")
            slot = slots[0]

        authority_schema = (
            "tournament_replacement_source.v2"
            if qualification_winner_evidence is not None
            else "tournament_replacement_source.v1"
        )

        if replacement_cutoff_authority.status == "already_eliminated":
            raise ValueError("Already-eliminated player cannot create a new Main vacancy")
        if replacement_cutoff_authority.status == "walkover_required":
            return TournamentReplacementSourceAuthority(
                schema_version=authority_schema,
                run_id=scope[0],
                branch_id=scope[1],
                event_id=scope[2],
                withdrawn_player_id=withdrawn_player_id,
                predecessor_draw_fingerprint=predecessor.fingerprint,
                predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                physical_slot_index=slot.slot_index,
                qualification_winner_evidence=qualification_winner_evidence,
                source="walkover",
                qualification_start_evidence=qualification_start_evidence,
                main_start_evidence=main_start_evidence,
                replacement_cutoff_authority=replacement_cutoff_authority,
                unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                prior_lucky_loser_player_ids=(
                    predecessor_draw_input.lucky_loser_player_ids
                ),
                external_reserve_player_ids=external_reserve_player_ids,
                base_wild_card_authority_fingerprint=(
                    base_wild_card_authority.fingerprint
                    if base_wild_card_authority is not None
                    else None
                ),
            )

        unavailable = set(unavailable_player_ids)
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

        # WC slots must consume RWC priority before the ordinary phase source.
        if slot.entry_status == "wild_card":
            if base_wild_card_authority is None:
                raise ValueError("WC replacement source requires base WC authority")
            for ordinal, candidate in enumerate(
                base_wild_card_authority.reserve_wild_card_player_ids,
                start=1,
            ):
                if candidate in unavailable or candidate in main_players:
                    continue
                return TournamentReplacementSourceAuthority(
                    schema_version=authority_schema,
                    run_id=scope[0],
                    branch_id=scope[1],
                    event_id=scope[2],
                    withdrawn_player_id=withdrawn_player_id,
                    predecessor_draw_fingerprint=predecessor.fingerprint,
                    predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                    physical_slot_index=slot.slot_index,
                    qualification_winner_evidence=qualification_winner_evidence,
                    source="reserve_wild_card",
                    selected_player_id=candidate,
                    source_ordinal=ordinal,
                    qualification_start_evidence=qualification_start_evidence,
                    main_start_evidence=main_start_evidence,
                    replacement_cutoff_authority=replacement_cutoff_authority,
                    unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                    prior_lucky_loser_player_ids=(
                        predecessor_draw_input.lucky_loser_player_ids
                    ),
                    external_reserve_player_ids=external_reserve_player_ids,
                    base_wild_card_authority_fingerprint=base_wild_card_authority.fingerprint,
                )

        # Before Qualification starts, the active Q list remains the ordinary source.
        if qualification_start_evidence is None:
            pre_q_priority = tuple(
                dict.fromkeys(
                    (
                        *predecessor_draw_input.qualification_player_ids,
                        *external_reserve_player_ids,
                    )
                )
            )
            for ordinal, candidate in enumerate(pre_q_priority, start=1):
                if candidate in unavailable or candidate in main_players:
                    continue
                return TournamentReplacementSourceAuthority(
                    schema_version=authority_schema,
                    run_id=scope[0],
                    branch_id=scope[1],
                    event_id=scope[2],
                    withdrawn_player_id=withdrawn_player_id,
                    predecessor_draw_fingerprint=predecessor.fingerprint,
                    predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                    physical_slot_index=slot.slot_index,
                    qualification_winner_evidence=qualification_winner_evidence,
                    source="qualification_promotion",
                    selected_player_id=candidate,
                    source_ordinal=ordinal,
                    replacement_cutoff_authority=replacement_cutoff_authority,
                    unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                    prior_lucky_loser_player_ids=(
                        predecessor_draw_input.lucky_loser_player_ids
                    ),
                    external_reserve_player_ids=external_reserve_player_ids,
                    base_wild_card_authority_fingerprint=(
                        base_wild_card_authority.fingerprint
                        if base_wild_card_authority is not None
                        else None
                    ),
                )
        # After Qualification starts, new Main vacancies belong to the LL workflow.
        else:
            if lucky_loser_order_authority is None:
                return TournamentReplacementSourceAuthority(
                    schema_version=authority_schema,
                    run_id=scope[0],
                    branch_id=scope[1],
                    event_id=scope[2],
                    withdrawn_player_id=withdrawn_player_id,
                    predecessor_draw_fingerprint=predecessor.fingerprint,
                    predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                    physical_slot_index=slot.slot_index,
                    qualification_winner_evidence=qualification_winner_evidence,
                    source="lucky_loser_pending",
                    qualification_start_evidence=qualification_start_evidence,
                    main_start_evidence=main_start_evidence,
                    replacement_cutoff_authority=replacement_cutoff_authority,
                    unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                    prior_lucky_loser_player_ids=(
                        predecessor_draw_input.lucky_loser_player_ids
                    ),
                    external_reserve_player_ids=external_reserve_player_ids,
                    base_wild_card_authority_fingerprint=(
                        base_wild_card_authority.fingerprint
                        if base_wild_card_authority is not None
                        else None
                    ),
                )
            blocked = (
                unavailable
                | set(predecessor_draw_input.lucky_loser_player_ids)
                | main_players
            )
            for candidate in lucky_loser_order_authority.candidates:
                if candidate.player_id in blocked:
                    continue
                return TournamentReplacementSourceAuthority(
                    schema_version=authority_schema,
                    run_id=scope[0],
                    branch_id=scope[1],
                    event_id=scope[2],
                    withdrawn_player_id=withdrawn_player_id,
                    predecessor_draw_fingerprint=predecessor.fingerprint,
                    predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                    physical_slot_index=slot.slot_index,
                    qualification_winner_evidence=qualification_winner_evidence,
                    source="lucky_loser",
                    selected_player_id=candidate.player_id,
                    source_ordinal=candidate.priority_ordinal,
                    qualification_start_evidence=qualification_start_evidence,
                    main_start_evidence=main_start_evidence,
                    replacement_cutoff_authority=replacement_cutoff_authority,
                    lucky_loser_order_authority=lucky_loser_order_authority,
                    unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                    prior_lucky_loser_player_ids=(
                        predecessor_draw_input.lucky_loser_player_ids
                    ),
                    external_reserve_player_ids=external_reserve_player_ids,
                    base_wild_card_authority_fingerprint=(
                        base_wild_card_authority.fingerprint
                        if base_wild_card_authority is not None
                        else None
                    ),
                )

        # External reserves follow the same frozen ranking order after LL exhaustion.
        blocked_external = unavailable | main_players | qualification_players
        for ordinal, candidate in enumerate(external_reserve_player_ids, start=1):
            if candidate in blocked_external:
                continue
            return TournamentReplacementSourceAuthority(
                schema_version=authority_schema,
                run_id=scope[0],
                branch_id=scope[1],
                event_id=scope[2],
                withdrawn_player_id=withdrawn_player_id,
                predecessor_draw_fingerprint=predecessor.fingerprint,
                predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                physical_slot_index=slot.slot_index,
                qualification_winner_evidence=qualification_winner_evidence,
                source="external_reserve",
                selected_player_id=candidate,
                source_ordinal=ordinal,
                qualification_start_evidence=qualification_start_evidence,
                main_start_evidence=main_start_evidence,
                replacement_cutoff_authority=replacement_cutoff_authority,
                lucky_loser_order_authority=lucky_loser_order_authority,
                unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                prior_lucky_loser_player_ids=(
                    predecessor_draw_input.lucky_loser_player_ids
                ),
                external_reserve_player_ids=external_reserve_player_ids,
                base_wild_card_authority_fingerprint=(
                    base_wild_card_authority.fingerprint
                    if base_wild_card_authority is not None
                    else None
                ),
            )

        if main_start_evidence is None:
            return TournamentReplacementSourceAuthority(
                schema_version=authority_schema,
                run_id=scope[0],
                branch_id=scope[1],
                event_id=scope[2],
                withdrawn_player_id=withdrawn_player_id,
                predecessor_draw_fingerprint=predecessor.fingerprint,
                predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
                physical_slot_index=slot.slot_index,
                qualification_winner_evidence=qualification_winner_evidence,
                source="bye",
                qualification_start_evidence=qualification_start_evidence,
                replacement_cutoff_authority=replacement_cutoff_authority,
                lucky_loser_order_authority=lucky_loser_order_authority,
                unavailable_player_ids=tuple(sorted(set(unavailable_player_ids))),
                prior_lucky_loser_player_ids=(
                    predecessor_draw_input.lucky_loser_player_ids
                ),
                external_reserve_player_ids=external_reserve_player_ids,
                base_wild_card_authority_fingerprint=(
                    base_wild_card_authority.fingerprint
                    if base_wild_card_authority is not None
                    else None
                ),
            )

        raise ValueError(
            "No replacement source remains after Main start while this player's "
            "replacement cutoff is still open; policy is not yet explicit"
        )
