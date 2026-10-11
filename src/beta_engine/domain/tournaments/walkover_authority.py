"""Canonical post-cutoff walkover authority.

A walkover is a tournament-progression result, not a played Match Engine result.
It therefore carries no rally/timeline/stamina evidence and produces no sporting
effects.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput, RankingWeek
from beta_engine.domain.tournaments.replacement_cutoff_authority import (
    TournamentPlayerReplacementCutoffAuthority,
)


class TournamentWalkoverResult(FrozenInput):
    schema_version: Literal["tournament_walkover_result.v1"] = (
        "tournament_walkover_result.v1"
    )
    match_id: str = Field(min_length=1)
    winner_player_id: str = Field(min_length=1)
    loser_player_id: str = Field(min_length=1)
    scoreline: Literal["W/O"] = "W/O"


class TournamentWalkoverAuthority(FrozenInput):
    schema_version: Literal["tournament_walkover_authority.v1"] = (
        "tournament_walkover_authority.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RankingWeek
    slot_id: str = Field(min_length=1)
    slot_start_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    group_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    match_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1, max_length=128)
    draw_authority_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    withdrawn_player_id: str = Field(min_length=1)
    winner_player_id: str = Field(min_length=1)
    source_real_match_id: str = Field(min_length=1)
    participant_sources: tuple[str, str]
    resolved_player_ids: tuple[str, str]
    replacement_cutoff_authority: TournamentPlayerReplacementCutoffAuthority

    @model_validator(mode="after")
    def validate_walkover(self):
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
            raise ValueError("Walkover cutoff authority scope mismatch")
        if cutoff.status != "walkover_required":
            raise ValueError("Walkover requires a closed player replacement cutoff")
        if not cutoff.played_matches:
            raise ValueError("Walkover requires prior real-match evidence")
        latest = cutoff.played_matches[-1]
        if (
            latest.match_id != self.source_real_match_id
            or latest.outcome != "win"
        ):
            raise ValueError(
                "Walkover source must be the withdrawn player's latest real-match win"
            )
        if self.winner_player_id == self.withdrawn_player_id:
            raise ValueError("Walkover winner and withdrawn player must differ")
        if set(self.resolved_player_ids) != {
            self.withdrawn_player_id,
            self.winner_player_id,
        }:
            raise ValueError(
                "Walkover resolved participants differ from winner/withdrawn identities"
            )
        expected_withdrawn_source = f"winner:{self.source_real_match_id}"
        if self.participant_sources.count(expected_withdrawn_source) != 1:
            raise ValueError(
                "Walkover target must consume the withdrawn player's latest win exactly once"
            )
        if any(
            not source.startswith(("player:", "winner:"))
            for source in self.participant_sources
        ):
            raise ValueError("Walkover participant source is invalid")
        return self

    @property
    def result(self) -> TournamentWalkoverResult:
        return TournamentWalkoverResult(
            match_id=self.match_id,
            winner_player_id=self.winner_player_id,
            loser_player_id=self.withdrawn_player_id,
        )

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentWalkoverAuthorityBuilder:
    @staticmethod
    def build(
        *,
        run_id: str,
        branch_id: str,
        week: RankingWeek,
        slot_id: str,
        slot_start_fingerprint: str,
        group_id: str,
        event_id: str,
        match_id: str,
        command_id: str,
        draw_authority_fingerprint: str,
        withdrawn_player_id: str,
        winner_player_id: str,
        source_real_match_id: str,
        participant_sources: tuple[str, str],
        resolved_player_ids: tuple[str, str],
        replacement_cutoff_authority: TournamentPlayerReplacementCutoffAuthority,
    ) -> TournamentWalkoverAuthority:
        return TournamentWalkoverAuthority(
            run_id=run_id,
            branch_id=branch_id,
            week=week,
            slot_id=slot_id,
            slot_start_fingerprint=slot_start_fingerprint,
            group_id=group_id,
            event_id=event_id,
            match_id=match_id,
            command_id=command_id,
            draw_authority_fingerprint=draw_authority_fingerprint,
            withdrawn_player_id=withdrawn_player_id,
            winner_player_id=winner_player_id,
            source_real_match_id=source_real_match_id,
            participant_sources=participant_sources,
            resolved_player_ids=resolved_player_ids,
            replacement_cutoff_authority=replacement_cutoff_authority,
        )
