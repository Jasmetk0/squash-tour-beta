"""Player-specific replacement cutoff from authoritative real-match evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Iterable, Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput


TournamentReplacementCutoffStatus = Literal[
    "replacement_open",
    "walkover_required",
    "already_eliminated",
]
TournamentPlayedMatchOutcome = Literal["win", "loss"]


class TournamentPlayedMatchCutoffEvidence(FrozenInput):
    match_id: str = Field(min_length=1)
    # RankingWeek.ordinal is zero-based: season 0 / week 1 is ordinal 0.
    week_ordinal: int = Field(ge=0)
    slot_id: str = Field(min_length=1)
    slot_ordinal: int = Field(ge=1)
    group_id: str = Field(min_length=1)
    result_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    opponent_player_id: str = Field(min_length=1)
    outcome: TournamentPlayedMatchOutcome


class TournamentPlayerReplacementCutoffAuthority(FrozenInput):
    """Frozen proof of whether one player's physical slot may still be replaced.

    Canonical BYEs never create authoritative SimulationEventGroup receipts, so they
    do not close this cutoff. In the current atomic match-execution model, the first
    committed competitive group is also the first durable evidence that the player's
    first real match has started.
    """

    schema_version: Literal["tournament_player_replacement_cutoff.v1"] = (
        "tournament_player_replacement_cutoff.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)
    player_id: str = Field(min_length=1)
    status: TournamentReplacementCutoffStatus
    played_matches: tuple[TournamentPlayedMatchCutoffEvidence, ...] = ()

    @model_validator(mode="after")
    def validate_cutoff(self):
        keys = tuple(
            (item.week_ordinal, item.slot_ordinal, item.group_id, item.match_id)
            for item in self.played_matches
        )
        if keys != tuple(sorted(keys)):
            raise ValueError("Replacement cutoff played-match evidence is not chronological")
        match_ids = tuple(item.match_id for item in self.played_matches)
        if len(match_ids) != len(set(match_ids)):
            raise ValueError("Replacement cutoff contains duplicate real-match identity")

        if not self.played_matches:
            if self.status != "replacement_open":
                raise ValueError(
                    "Replacement cutoff without a real match must remain open"
                )
        else:
            expected = (
                "walkover_required"
                if self.played_matches[-1].outcome == "win"
                else "already_eliminated"
            )
            if self.status != expected:
                raise ValueError(
                    "Replacement cutoff status differs from latest real-match outcome"
                )
        return self

    @property
    def first_real_match(self) -> TournamentPlayedMatchCutoffEvidence | None:
        return self.played_matches[0] if self.played_matches else None

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()


class TournamentPlayerReplacementCutoffAuthorityBuilder:
    @staticmethod
    def build(
        *,
        run_id: str,
        branch_id: str,
        event_id: str,
        player_id: str,
        played_matches: Iterable[TournamentPlayedMatchCutoffEvidence],
    ) -> TournamentPlayerReplacementCutoffAuthority:
        ordered = tuple(
            sorted(
                played_matches,
                key=lambda item: (
                    item.week_ordinal,
                    item.slot_ordinal,
                    item.group_id,
                    item.match_id,
                ),
            )
        )
        status: TournamentReplacementCutoffStatus
        if not ordered:
            status = "replacement_open"
        elif ordered[-1].outcome == "win":
            status = "walkover_required"
        else:
            status = "already_eliminated"
        return TournamentPlayerReplacementCutoffAuthority(
            run_id=run_id,
            branch_id=branch_id,
            event_id=event_id,
            player_id=player_id,
            status=status,
            played_matches=ordered,
        )
