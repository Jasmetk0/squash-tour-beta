"""Immutable elimination bracket materialized from frozen hybrid group entrants."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.tournaments.hybrid_knockout_entrants_authority import (
    TournamentHybridKnockoutEntrantsAuthority,
)


def _fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class TournamentHybridKnockoutBracketMatch(FrozenInput):
    """One executable elimination match in the post-group hybrid bracket."""

    match_id: str = Field(min_length=1)
    round_number: int = Field(ge=1, le=16)
    match_index: int = Field(ge=1, le=64)
    participant_sources: tuple[str, str]

    @model_validator(mode="after")
    def validate_sources(self) -> "TournamentHybridKnockoutBracketMatch":
        if self.participant_sources[0] == self.participant_sources[1]:
            raise ValueError("Hybrid knockout match cannot use one source twice")
        if any(
            not source.startswith(("player:", "winner:"))
            for source in self.participant_sources
        ):
            raise ValueError("Hybrid knockout match source is unsupported")
        return self


class TournamentHybridKnockoutBracketAuthority(FrozenInput):
    """Frozen complete elimination tree after group positions resolve.

    The first round is copied exactly from the configured group crossings through
    TournamentHybridKnockoutEntrantsAuthority. Later rounds are winner-to-winner
    feeders in ordinary bracket order; there is no Ranking/Race reseeding.
    """

    schema_version: Literal["tournament_hybrid_knockout_bracket_authority.v1"] = (
        "tournament_hybrid_knockout_bracket_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    generated_by_command_id: str = Field(min_length=1, max_length=128)
    entrants_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    bracket_policy_id: Literal["configured_crossings_standard_winner_tree_no_reseed.v1"] = (
        "configured_crossings_standard_winner_tree_no_reseed.v1"
    )
    entrant_count: int = Field(ge=2, le=128)
    round_count: int = Field(ge=1, le=7)
    matches: tuple[TournamentHybridKnockoutBracketMatch, ...] = Field(min_length=1)
    terminal_match_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_bracket(self) -> "TournamentHybridKnockoutBracketAuthority":
        if self.entrant_count & (self.entrant_count - 1):
            raise ValueError("Hybrid knockout entrant count must be a power of two")
        expected_round_count = self.entrant_count.bit_length() - 1
        if self.round_count != expected_round_count:
            raise ValueError("Hybrid knockout round count differs from entrant count")
        expected_match_count = self.entrant_count - 1
        if len(self.matches) != expected_match_count:
            raise ValueError("Hybrid knockout bracket match count is incomplete")

        ids = tuple(match.match_id for match in self.matches)
        if len(ids) != len(set(ids)):
            raise ValueError("Hybrid knockout bracket contains duplicate match identity")

        by_round: dict[int, list[TournamentHybridKnockoutBracketMatch]] = {}
        for match in self.matches:
            by_round.setdefault(match.round_number, []).append(match)
        if tuple(sorted(by_round)) != tuple(range(1, self.round_count + 1)):
            raise ValueError("Hybrid knockout rounds must be contiguous from one")

        previous_ids: tuple[str, ...] = ()
        for round_number in range(1, self.round_count + 1):
            round_matches = tuple(
                sorted(by_round[round_number], key=lambda value: value.match_index)
            )
            expected_count = self.entrant_count // (2**round_number)
            if len(round_matches) != expected_count:
                raise ValueError("Hybrid knockout round has wrong match count")
            if tuple(match.match_index for match in round_matches) != tuple(
                range(1, expected_count + 1)
            ):
                raise ValueError(
                    "Hybrid knockout match indexes must be contiguous within each round"
                )
            if round_number == 1:
                if any(
                    not source.startswith("player:")
                    for match in round_matches
                    for source in match.participant_sources
                ):
                    raise ValueError(
                        "Hybrid knockout first round must contain resolved players"
                    )
            else:
                expected_sources = tuple(
                    f"winner:{match_id}" for match_id in previous_ids
                )
                actual_sources = tuple(
                    source
                    for match in round_matches
                    for source in match.participant_sources
                )
                if actual_sources != expected_sources:
                    raise ValueError(
                        "Hybrid knockout later round must preserve adjacent winner feeders"
                    )
            previous_ids = tuple(match.match_id for match in round_matches)

        if previous_ids != (self.terminal_match_id,):
            raise ValueError("Hybrid knockout terminal match identity is invalid")
        return self

    @property
    def fingerprint(self) -> str:
        return _fingerprint(self.model_dump(mode="json"))


class TournamentHybridKnockoutBracketBuilder:
    @staticmethod
    def build(
        *,
        entrants: TournamentHybridKnockoutEntrantsAuthority,
        command_id: str,
    ) -> TournamentHybridKnockoutBracketAuthority:
        if not command_id.strip() or len(command_id) > 128:
            raise ValueError("Hybrid Knockout Bracket requires a valid command ID")

        first_round = tuple(
            sorted(entrants.first_round_matches, key=lambda value: value.match_index)
        )
        entrant_count = len(first_round) * 2
        if entrant_count < 2 or entrant_count & (entrant_count - 1):
            raise ValueError(
                "Hybrid Knockout Bracket requires a power-of-two entrant field"
            )

        matches: list[TournamentHybridKnockoutBracketMatch] = []
        previous_ids: tuple[str, ...] = ()
        round_count = entrant_count.bit_length() - 1
        for round_number in range(1, round_count + 1):
            match_count = entrant_count // (2**round_number)
            current_ids: list[str] = []
            for match_index in range(1, match_count + 1):
                if round_number == 1:
                    source = first_round[match_index - 1]
                    match_id = source.match_id
                    participant_sources = (
                        f"player:{source.top_player_id}",
                        f"player:{source.bottom_player_id}",
                    )
                else:
                    match_id = (
                        f"{entrants.event_id}:hybrid:knockout:"
                        f"R{round_number}:M{match_index}"
                    )
                    feeder_start = (match_index - 1) * 2
                    participant_sources = (
                        f"winner:{previous_ids[feeder_start]}",
                        f"winner:{previous_ids[feeder_start + 1]}",
                    )

                matches.append(
                    TournamentHybridKnockoutBracketMatch(
                        match_id=match_id,
                        round_number=round_number,
                        match_index=match_index,
                        participant_sources=participant_sources,
                    )
                )
                current_ids.append(match_id)
            previous_ids = tuple(current_ids)

        return TournamentHybridKnockoutBracketAuthority(
            run_id=entrants.run_id,
            branch_id=entrants.branch_id,
            event_id=entrants.event_id,
            generated_by_command_id=command_id,
            entrants_authority_fingerprint=entrants.fingerprint,
            entrant_count=entrant_count,
            round_count=round_count,
            matches=tuple(matches),
            terminal_match_id=previous_ids[0],
        )
