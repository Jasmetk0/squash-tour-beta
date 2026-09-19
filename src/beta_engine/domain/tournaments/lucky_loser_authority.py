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


class TournamentLuckyLoserQualificationMatchEvidence(FrozenInput):
    """One completed canonical Qualification match used by LL ordering."""

    match_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    round_number: int = Field(ge=1)
    winner_player_id: str = Field(min_length=1)
    loser_player_id: str = Field(min_length=1)
    result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentLuckyLoserCandidate(FrozenInput):
    """One bracket-Q loser frozen into canonical LL priority."""

    player_id: str = Field(min_length=1)
    priority_ordinal: int = Field(ge=1)
    qualification_round_reached: int = Field(ge=1)
    tournament_ranking: int = Field(ge=1)
    elimination_match_id: str = Field(min_length=1)
    elimination_result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class TournamentLuckyLoserOrderAuthority(FrozenInput):
    """Completed bracket-Qualification LL order from Master §15.8."""

    schema_version: Literal["tournament_lucky_loser_order.v1"] = (
        "tournament_lucky_loser_order.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    tournament_ranking_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    qualification_terminal_match_ids: tuple[str, ...]
    qualification_terminal_result_fingerprints: tuple[str, ...]
    candidates: tuple[TournamentLuckyLoserCandidate, ...]

    @model_validator(mode="after")
    def validate_order(self):
        if not self.qualification_terminal_match_ids:
            raise ValueError("LL order requires completed Qualification terminals")
        if len(self.qualification_terminal_match_ids) != len(
            self.qualification_terminal_result_fingerprints
        ):
            raise ValueError("LL terminal identity/result evidence differs in length")
        if len(set(self.qualification_terminal_match_ids)) != len(
            self.qualification_terminal_match_ids
        ):
            raise ValueError("LL order contains duplicate Q terminal identity")
        expected_ordinals = tuple(range(1, len(self.candidates) + 1))
        if tuple(item.priority_ordinal for item in self.candidates) != expected_ordinals:
            raise ValueError("LL candidate priority ordinals are not canonical")
        ids = tuple(item.player_id for item in self.candidates)
        if len(ids) != len(set(ids)):
            raise ValueError("LL order contains duplicate candidate player")
        keys = tuple(
            (
                -item.qualification_round_reached,
                item.tournament_ranking,
                item.player_id,
            )
            for item in self.candidates
        )
        if keys != tuple(sorted(keys)):
            raise ValueError(
                "LL order must prefer reached Q round, then Tournament Ranking Snapshot"
            )
        return self

    @property
    def ordered_player_ids(self) -> tuple[str, ...]:
        return tuple(item.player_id for item in self.candidates)

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentLuckyLoserOrderAuthorityBuilder:
    @staticmethod
    def build(
        *,
        draw: TournamentDrawAuthority,
        tournament_ranking_authority,
        completed_qualification_matches: tuple[
            TournamentLuckyLoserQualificationMatchEvidence, ...
        ],
    ) -> TournamentLuckyLoserOrderAuthority:
        scope = (draw.run_id, draw.branch_id, draw.event_id)
        if (
            tournament_ranking_authority.run_id,
            tournament_ranking_authority.branch_id,
            tournament_ranking_authority.event_id,
        ) != scope:
            raise ValueError("LL order ranking authority scope mismatch")
        if not draw.qualification_brackets:
            raise ValueError("LL order requires bracket Qualification")

        node_to_section: dict[str, str] = {}
        terminal_ids: list[str] = []
        for index, bracket in enumerate(draw.qualification_brackets, start=1):
            section_id = bracket.section_id or f"Q{index}"
            for node in bracket.nodes:
                if node.node_id in node_to_section:
                    raise ValueError("Qualification node identity is not unique")
                node_to_section[node.node_id] = section_id
            terminal = max(
                bracket.nodes,
                key=lambda item: (item.round_number, item.round_sequence),
            )
            terminal_ids.append(terminal.node_id)

        by_match = {item.match_id: item for item in completed_qualification_matches}
        if len(by_match) != len(completed_qualification_matches):
            raise ValueError("LL order contains duplicate completed Q match evidence")
        if not set(by_match).issubset(node_to_section):
            raise ValueError("LL order contains match outside canonical Qualification")
        for match in completed_qualification_matches:
            if node_to_section[match.match_id] != match.section_id:
                raise ValueError("LL Q match section differs from canonical Draw")

        missing_terminals = set(terminal_ids) - set(by_match)
        if missing_terminals:
            raise ValueError(
                "Lucky Loser order is unavailable until Qualification is complete"
            )

        ranking_by_player = {
            row.player_id: row.rank
            for row in tournament_ranking_authority.ranking_snapshot.rows
        }
        q_players = {
            slot.player_id
            for bracket in draw.qualification_brackets
            for slot in bracket.slots
            if slot.player_id is not None
        }

        losses: dict[str, TournamentLuckyLoserQualificationMatchEvidence] = {}
        for match in completed_qualification_matches:
            loser = match.loser_player_id
            if loser not in q_players:
                raise ValueError("LL candidate loss belongs to player outside Q field")
            if loser in losses:
                raise ValueError("Qualification player has multiple elimination losses")
            if loser not in ranking_by_player:
                raise ValueError(
                    "LL candidate is absent from Tournament Ranking Snapshot"
                )
            losses[loser] = match

        ordered = sorted(
            losses.items(),
            key=lambda item: (
                -item[1].round_number,
                ranking_by_player[item[0]],
                item[0],
            ),
        )
        candidates = tuple(
            TournamentLuckyLoserCandidate(
                player_id=player_id,
                priority_ordinal=index,
                qualification_round_reached=match.round_number,
                tournament_ranking=ranking_by_player[player_id],
                elimination_match_id=match.match_id,
                elimination_result_fingerprint=match.result_fingerprint,
            )
            for index, (player_id, match) in enumerate(ordered, start=1)
        )
        terminal_results = tuple(by_match[match_id] for match_id in terminal_ids)
        return TournamentLuckyLoserOrderAuthority(
            run_id=scope[0],
            branch_id=scope[1],
            event_id=scope[2],
            draw_authority_fingerprint=draw.fingerprint,
            tournament_ranking_authority_fingerprint=(
                tournament_ranking_authority.fingerprint
            ),
            qualification_terminal_match_ids=tuple(terminal_ids),
            qualification_terminal_result_fingerprints=tuple(
                item.result_fingerprint for item in terminal_results
            ),
            candidates=candidates,
        )


class TournamentLuckyLoserFillAuthority(FrozenInput):
    """One chronological LL placeholder bound to one frozen LL candidate."""

    schema_version: Literal["tournament_lucky_loser_fill.v1"] = (
        "tournament_lucky_loser_fill.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1, max_length=128)
    predecessor_draw_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_draw_input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    placeholder_id: str = Field(pattern=r"^LL[1-9][0-9]*$")
    lucky_loser_ordinal: int = Field(ge=1)
    physical_slot_index: int = Field(ge=1)
    order_authority: TournamentLuckyLoserOrderAuthority
    selected_candidate: TournamentLuckyLoserCandidate
    prior_assigned_player_ids: tuple[str, ...] = ()
    unavailable_player_ids: tuple[str, ...] = ()
    skipped_candidate_player_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_fill(self):
        if self.placeholder_id != f"LL{self.lucky_loser_ordinal}":
            raise ValueError("LL fill placeholder identity differs from ordinal")
        if (
            self.order_authority.run_id,
            self.order_authority.branch_id,
            self.order_authority.event_id,
        ) != (self.run_id, self.branch_id, self.event_id):
            raise ValueError("LL fill order authority scope mismatch")
        if tuple(sorted(set(self.unavailable_player_ids))) != self.unavailable_player_ids:
            raise ValueError("LL unavailable identities must be sorted and unique")
        if len(set(self.prior_assigned_player_ids)) != len(
            self.prior_assigned_player_ids
        ):
            raise ValueError("LL prior assignments must be unique")
        if self.selected_candidate.player_id in set(self.prior_assigned_player_ids):
            raise ValueError("LL selected candidate is already assigned")
        if self.selected_candidate.player_id in set(self.unavailable_player_ids):
            raise ValueError("LL selected candidate is unavailable")
        candidates = self.order_authority.candidates
        if self.selected_candidate not in candidates:
            raise ValueError("LL selected candidate is absent from frozen LL order")
        selected_index = candidates.index(self.selected_candidate)
        blocked = set(self.prior_assigned_player_ids) | set(self.unavailable_player_ids)
        expected_skipped = tuple(
            item.player_id
            for item in candidates[:selected_index]
            if item.player_id in blocked
        )
        if expected_skipped != self.skipped_candidate_player_ids:
            raise ValueError("LL skipped-candidate evidence differs from frozen order")
        if any(
            item.player_id not in blocked
            for item in candidates[:selected_index]
        ):
            raise ValueError("LL fill skipped an eligible higher-priority candidate")
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


class TournamentLuckyLoserFillAuthorityBuilder:
    @staticmethod
    def build(
        *,
        predecessor: TournamentDrawAuthority,
        predecessor_draw_input: TournamentDrawInputAuthority,
        command_id: str,
        order_authority: TournamentLuckyLoserOrderAuthority,
        unavailable_player_ids: tuple[str, ...],
    ) -> TournamentLuckyLoserFillAuthority:
        scope = (predecessor.run_id, predecessor.branch_id, predecessor.event_id)
        if (
            predecessor_draw_input.run_id,
            predecessor_draw_input.branch_id,
            predecessor_draw_input.event_id,
        ) != scope:
            raise ValueError("LL fill predecessor Draw Input scope mismatch")
        if predecessor.draw_input_fingerprint != predecessor_draw_input.fingerprint:
            raise ValueError("LL fill predecessor Draw/Input binding mismatch")
        if (
            order_authority.run_id,
            order_authority.branch_id,
            order_authority.event_id,
        ) != scope:
            raise ValueError("LL fill order authority scope mismatch")

        filled_count = len(predecessor_draw_input.lucky_loser_player_ids)
        if filled_count >= len(predecessor_draw_input.lucky_loser_placeholder_ids):
            raise ValueError("No unresolved Lucky Loser placeholder remains")
        expected_placeholder = predecessor_draw_input.lucky_loser_placeholder_ids[
            filled_count
        ]
        matching = [
            slot
            for slot in predecessor.main.slots
            if slot.entrant_kind == "lucky_loser_placeholder"
            and slot.placeholder_id == expected_placeholder
        ]
        if len(matching) != 1:
            raise ValueError("Next Lucky Loser placeholder is not present exactly once")
        slot = matching[0]
        prior = predecessor_draw_input.lucky_loser_player_ids
        unavailable = tuple(sorted(set(unavailable_player_ids)))
        blocked = set(prior) | set(unavailable)

        skipped = []
        selected = None
        for candidate in order_authority.candidates:
            if candidate.player_id in blocked:
                skipped.append(candidate.player_id)
                continue
            selected = candidate
            break
        if selected is None:
            raise ValueError(
                "Lucky Loser candidate pool is exhausted; external reserve fallback required"
            )

        return TournamentLuckyLoserFillAuthority(
            run_id=scope[0],
            branch_id=scope[1],
            event_id=scope[2],
            command_id=command_id,
            predecessor_draw_fingerprint=predecessor.fingerprint,
            predecessor_draw_input_fingerprint=predecessor_draw_input.fingerprint,
            placeholder_id=expected_placeholder,
            lucky_loser_ordinal=filled_count + 1,
            physical_slot_index=slot.slot_index,
            order_authority=order_authority,
            selected_candidate=selected,
            prior_assigned_player_ids=prior,
            unavailable_player_ids=unavailable,
            skipped_candidate_player_ids=tuple(skipped),
        )
