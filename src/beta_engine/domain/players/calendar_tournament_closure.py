"""Signed closure of actually played native tournament results (NOT Official).

Distinct from provisional score editing and any legacy Official Tour writer.
A closure is a new persisted event anchored to one previously Saved, scored
eight-player knockout and every actual MatchEngine result.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarClosedPlayerResult(FrozenInput):
    player_id: str = Field(min_length=1)
    reached_stage: Literal["quarterfinal", "semifinal", "finalist", "champion"]
    played_match_ids: tuple[str, ...] = Field(min_length=1, max_length=3)
    wins: int = Field(ge=0, le=3)
    losses: int = Field(ge=0, le=1)
    prepared_points: int = Field(ge=0, le=1000000)


class CalendarNativeTournamentClosure(FrozenInput):
    schema_version: Literal["calendar_native_tournament_closure.v1"] = (
        "calendar_native_tournament_closure.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    command_id: str = Field(min_length=1, max_length=128)
    tournament_id: str = Field(min_length=1)
    source_saved_head: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_week_event_count: int = Field(ge=1)
    source_tournament_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_prepared_awards_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    champion_player_id: str = Field(min_length=1)
    finalist_player_id: str = Field(min_length=1)
    players: tuple[CalendarClosedPlayerResult, ...] = Field(min_length=8, max_length=8)
    scope: Literal["played_native_result_closed_not_official"] = (
        "played_native_result_closed_not_official"
    )

    @model_validator(mode="after")
    def validate_identity(self):
        if (
            tuple(p.player_id for p in self.players) !=
            tuple(sorted({p.player_id for p in self.players}))
            or len(self.players) != 8
            or sum(p.wins for p in self.players) != 7
            or sum(p.losses for p in self.players) != 7
            or sorted(p.reached_stage for p in self.players)
            != sorted(["quarterfinal"] * 4 + ["semifinal"] * 2 + ["finalist", "champion"])
            or next(p.player_id for p in self.players if p.reached_stage == "champion")
            != self.champion_player_id
            or next(p.player_id for p in self.players if p.reached_stage == "finalist")
            != self.finalist_player_id
        ):
            raise ValueError("Native result closure has invalid eight-player finishing ledger")
        request = {
            "command_id": self.command_id,
            "tournament_id": self.tournament_id,
            "expected_saved_head": self.source_saved_head,
            "expected_checkpoint_fingerprint": self.source_checkpoint_fingerprint,
            "operator_label": self.operator_label,
            "audit_reason": self.audit_reason,
            "explicit_result_confirmation": True,
        }
        if self.request_fingerprint != canonical_hash({
            "run_id": self.run_id, "branch_id": self.branch_id, "command": request,
        }):
            raise ValueError("Native result closure root command fingerprint mismatch")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def derive_closed_players(tournament):
    """Rebuild every player result from seven authentic, winner-fed MatchEngine logs."""
    if tournament.schema_version != "calendar_followup_knockout.v4" or len(tournament.matches) != 7:
        raise ValueError("Only actual seven-match, scored eight-player native knockouts can close")
    awards = {a.player_id: a for a in tournament.prepared_awards}
    counts = {pid: {"ids": [], "wins": 0, "losses": 0} for pid in tournament.entrant_ids}
    for match in tournament.matches:
        winner = match.result.winner_player_id
        loser = match.result.loser_player_id
        if (winner not in counts or loser not in counts or winner == loser
            or {winner, loser} != {match.result.player_a_id, match.result.player_b_id}):
            raise ValueError("Native closure match winners disagree with entrant identity")
        for pid in (winner, loser):
            counts[pid]["ids"].append(match.match_id)
        counts[winner]["wins"] += 1
        counts[loser]["losses"] += 1
    return tuple(
        CalendarClosedPlayerResult(
            player_id=pid,
            reached_stage=awards[pid].reached_stage,
            played_match_ids=tuple(counts[pid]["ids"]),
            wins=counts[pid]["wins"],
            losses=counts[pid]["losses"],
            prepared_points=awards[pid].main_points,
        ) for pid in sorted(counts)
    )


def append_native_tournament_closure(checkpoint, closure):
    """Replay a closure at exactly its original event-count boundary."""
    from beta_engine.domain.players.calendar_sporting_checkpoint import CalendarSportingCheckpoint

    tournaments = checkpoint.tournaments
    if (
        checkpoint.schema_version not in {
            "calendar_sporting_checkpoint.v7", "calendar_sporting_checkpoint.v8",
        }
        or not tournaments or checkpoint.week_events[-1] is not tournaments[-1]
        or tournaments[-1].schema_version != "calendar_followup_knockout.v4"
        or (closure.run_id, closure.branch_id) != (checkpoint.run_id, checkpoint.branch_id)
        or closure.source_checkpoint_fingerprint != checkpoint.fingerprint
        or closure.source_week_event_count != len(checkpoint.week_events)
        or closure.source_tournament_fingerprint != tournaments[-1].fingerprint
        or closure.source_prepared_awards_fingerprint != canonical_hash([
            a.model_dump(mode="json") for a in tournaments[-1].prepared_awards
        ])
        or closure.tournament_id != tournaments[-1].tournament_id
        or closure.champion_player_id != tournaments[-1].matches[-1].result.winner_player_id
        or closure.finalist_player_id != tournaments[-1].matches[-1].result.loser_player_id
        or closure.players != derive_closed_players(tournaments[-1])
        or any(previous.tournament_id == closure.tournament_id
               or previous.command_id == closure.command_id
               for previous in checkpoint.closures)
        or closure.command_id in {
            *(t.command_id for t in tournaments),
            *(m.command_id for m in checkpoint.played_continuations),
            *(w.command_id for w in checkpoint.weekly_advances),
        }
    ):
        raise ValueError("Native result closure differs from its signed Saved tournament")
    return CalendarSportingCheckpoint.model_validate_json(
        checkpoint.model_copy(update={
            "schema_version": "calendar_sporting_checkpoint.v8",
            "closures": checkpoint.closures + (closure,),
        }).model_dump_json()
    )
