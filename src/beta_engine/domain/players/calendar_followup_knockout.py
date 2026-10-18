"""One atomic later-week four-player knockout from the Saved 57-attribute owner.

This is verified sporting tournament evidence, NOT an Official Tour Edition:
the bridge to historically configured points, Entry and Week Transition remains
explicitly absent. Nested matches carry normal MatchEngine replay authorities.
"""
from typing import Literal

from pydantic import Field, model_serializer, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_followup_points import (CalendarFollowupPointPolicy, CalendarFollowupPreparedAward, derive_followup_awards)
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch, append_continuation,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


ROUNDS = ("sf1", "sf2", "final")


class CalendarFollowupKnockout(FrozenInput):
    schema_version: Literal["calendar_followup_knockout.v1", "calendar_followup_knockout.v2"] = "calendar_followup_knockout.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    tournament_id: str = Field(min_length=1, max_length=94)
    command_id: str = Field(min_length=1, max_length=120)
    source_saved_head: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    week: RunWeekPosition
    seed: int
    entrant_ids: tuple[str, str, str, str]
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    matches: tuple[CalendarContinuationMatch, CalendarContinuationMatch, CalendarContinuationMatch]
    prepared_policy: CalendarFollowupPointPolicy | None = None
    prepared_awards: tuple[CalendarFollowupPreparedAward, ...] = ()
    scope: Literal["sporting_exhibition_knockout_not_official"] = (
        "sporting_exhibition_knockout_not_official"
    )

    @model_serializer(mode="wrap")
    def historical_shape(self, handler):
        body = handler(self)
        if self.schema_version == "calendar_followup_knockout.v1":
            body.pop("prepared_policy", None)
            body.pop("prepared_awards", None)
        return body

    @model_validator(mode="after")
    def validate_bracket(self):
        if len(set(self.entrant_ids)) != 4 or self.week.ordinal < 1:
            raise ValueError("Later-week knockout requires four distinct players after Week 1")
        for index, (match, suffix) in enumerate(zip(self.matches, ROUNDS, strict=True)):
            if (
                match.schema_version != "calendar_continuation_match.v2"
                or (match.run_id, match.branch_id) != (self.run_id, self.branch_id)
                or match.week != self.week
                or match.command_id != f"{self.command_id}:{suffix}"
                or match.match_id != f"{self.tournament_id}:{suffix}"
                or match.seed != self.seed + index
                or match.source_saved_head != self.source_saved_head
                or match.operator_label != self.operator_label
                or match.audit_reason != self.audit_reason
            ):
                raise ValueError("Knockout match identity or frozen execution input mismatch")
        semia, semib, final = self.matches
        def players(match):
            return (match.result.player_a_id, match.result.player_b_id)
        if (players(semia) != self.entrant_ids[:2]
            or players(semib) != self.entrant_ids[2:]
            or players(final) != (
                semia.result.winner_player_id, semib.result.winner_player_id
            )):
            raise ValueError("Knockout final must consume actual semifinal winners")
        request = dict(
            command_id=self.command_id,
            tournament_id=self.tournament_id,
            expected_saved_head=self.source_saved_head,
            expected_checkpoint_fingerprint=self.source_checkpoint_fingerprint,
            entrant_ids=self.entrant_ids,
            seed=self.seed,
            operator_label=self.operator_label,
            audit_reason=self.audit_reason,
        )
        if self.schema_version == "calendar_followup_knockout.v2":
            if self.prepared_policy is None or self.prepared_policy.validity_weeks != self.week.calendar.weeks_per_year:
                raise ValueError("Scored knockout requires explicitly reviewed W-valid prepared point policy")
            request["point_policy"] = self.prepared_policy.model_dump(mode="json")
            request["explicit_point_confirmation"] = True
            if self.prepared_awards != derive_followup_awards(self):
                raise ValueError("Prepared knockout points disagree with actual match results")
        elif self.prepared_policy is not None or self.prepared_awards:
            raise ValueError("Historical knockout v1 cannot acquire new prepared points")
        if self.request_fingerprint != canonical_hash({
            "run_id": self.run_id, "branch_id": self.branch_id, "command": request,
        }):
            raise ValueError("Knockout root request fingerprint mismatch")
        return self

    @property
    def sporting_fingerprint(self):
        payload = self.model_dump(mode="json")
        payload.pop("prepared_awards", None)
        return canonical_hash(payload)

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def append_followup_knockout(checkpoint, world, event: CalendarFollowupKnockout):
    """Rebuild all three real matches, then replace one event atomically.

    Nested match fingerprints, round ordering, terminal fatigue and projections
    must reproduce from the actual predecessor population. The event is *one*
    ledger entry, preserving its future Edition/point-award provenance boundary.
    """
    from beta_engine.domain.players.calendar_sporting_checkpoint import CalendarSportingCheckpoint

    if (
        checkpoint.schema_version not in {
            "calendar_sporting_checkpoint.v3", "calendar_sporting_checkpoint.v4",
            "calendar_sporting_checkpoint.v5",
        }
        or not checkpoint.week_events
        or (checkpoint.run_id, checkpoint.branch_id) != (event.run_id, event.branch_id)
        or checkpoint.fingerprint != event.source_checkpoint_fingerprint
        or checkpoint.week.ordinal != event.week.ordinal
        or event.command_id in {
            *(advance.command_id for advance in checkpoint.weekly_advances),
            *(entry.command_id for entry in checkpoint.played_continuations),
            *(tournament.command_id for tournament in checkpoint.tournaments),
        }
        or event.tournament_id in {
            tournament.tournament_id for tournament in checkpoint.tournaments
        }
        or set(event.entrant_ids) - {p.player_id for p in checkpoint.players}
    ):
        raise ValueError("Knockout source/roster or identity differs from Saved sporting state")

    intermediate = checkpoint
    for match in event.matches:
        intermediate = append_continuation(intermediate, world, match)
    successor = checkpoint.model_copy(update={
        "schema_version": ("calendar_sporting_checkpoint.v5"
                           if checkpoint.schema_version == "calendar_sporting_checkpoint.v5"
                           or event.schema_version == "calendar_followup_knockout.v2"
                           else "calendar_sporting_checkpoint.v4"),
        "players": intermediate.players,
        "week_events": checkpoint.week_events + (event,),
    })
    return CalendarSportingCheckpoint.model_validate_json(successor.model_dump_json())
