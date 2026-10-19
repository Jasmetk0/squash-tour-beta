"""One atomic later-week four-player knockout from the Saved 57-attribute owner.

This is verified sporting tournament evidence, NOT an Official Tour Edition:
the bridge to historically configured points, Entry and Week Transition remains
explicitly absent. Nested matches carry normal MatchEngine replay authorities.
"""
from typing import Literal

from pydantic import Field, model_serializer, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_followup_points import (CalendarFollowupPointPolicy, CalendarFollowupEightPointPolicy, CalendarFollowupPreparedAward, derive_followup_awards)
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch, append_continuation,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


ROUNDS = ("sf1", "sf2", "final")
ROUNDS_EIGHT = ("qf1", "qf2", "qf3", "qf4", "sf1", "sf2", "final")


class CalendarFollowupKnockout(FrozenInput):
    schema_version: Literal["calendar_followup_knockout.v1", "calendar_followup_knockout.v2", "calendar_followup_knockout.v3", "calendar_followup_knockout.v4", "calendar_followup_knockout.v5"] = "calendar_followup_knockout.v1"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    tournament_id: str = Field(min_length=1, max_length=94)
    command_id: str = Field(min_length=1, max_length=120)
    source_saved_head: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    week: RunWeekPosition
    seed: int
    entrant_ids: tuple[str, ...] = Field(min_length=4, max_length=8)
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    matches: tuple[CalendarContinuationMatch, ...] = Field(min_length=3, max_length=7)
    prepared_policy: CalendarFollowupPointPolicy | CalendarFollowupEightPointPolicy | None = None
    prepared_awards: tuple[CalendarFollowupPreparedAward, ...] = ()
    edition_authority_fingerprint: str | None = Field(default=None,pattern=r"^[0-9a-f]{64}$")
    scope: Literal["sporting_exhibition_knockout_not_official", "configured_tour_knockout"] = (
        "sporting_exhibition_knockout_not_official"
    )

    @model_serializer(mode="wrap")
    def historical_shape(self, handler):
        body = handler(self)
        if self.schema_version != "calendar_followup_knockout.v5":
            body.pop("edition_authority_fingerprint", None)
        if self.schema_version in {"calendar_followup_knockout.v1", "calendar_followup_knockout.v3"}:
            body.pop("prepared_policy", None)
            body.pop("prepared_awards", None)
        return body

    @model_validator(mode="after")
    def validate_bracket(self):
        configured=self.schema_version=="calendar_followup_knockout.v5"
        if configured:
            if not self.edition_authority_fingerprint or self.scope!="configured_tour_knockout":
                raise ValueError("Configured tournament requires its pre-existing Edition/Entry/draw authority")
        elif self.edition_authority_fingerprint is not None or self.scope!="sporting_exhibition_knockout_not_official":
            raise ValueError("Historical exhibition cannot acquire Tour Edition authority")
        eight = len(self.entrant_ids)==8 if configured else self.schema_version in {"calendar_followup_knockout.v3", "calendar_followup_knockout.v4"}
        expected_field = 8 if eight else 4
        rounds = ROUNDS_EIGHT if eight else ROUNDS
        if (len(self.entrant_ids) != expected_field
            or len(set(self.entrant_ids)) != expected_field
            or len(self.matches) != len(rounds)
            or self.week.ordinal < 1):
            raise ValueError("Later knockout field, bracket or sporting week is invalid")
        for index, (match, suffix) in enumerate(zip(self.matches, rounds, strict=True)):
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
        def players(match):
            return (match.result.player_a_id, match.result.player_b_id)
        if eight:
            quarters, semis, final = self.matches[:4], self.matches[4:6], self.matches[6]
            correct = all(
                players(quarter) == tuple(self.entrant_ids[2*i:2*i+2])
                for i, quarter in enumerate(quarters)
            ) and all(
                players(semi) == (
                    quarters[2*i].result.winner_player_id,
                    quarters[2*i+1].result.winner_player_id,
                ) for i, semi in enumerate(semis)
            ) and players(final) == (
                semis[0].result.winner_player_id, semis[1].result.winner_player_id
            )
        else:
            semia, semib, final = self.matches
            correct = (
                players(semia) == self.entrant_ids[:2]
                and players(semib) == self.entrant_ids[2:]
                and players(final) == (
                    semia.result.winner_player_id, semib.result.winner_player_id
                )
            )
        if not correct:
            raise ValueError("Knockout next round must consume actual preceding winners")
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
        if self.schema_version in {"calendar_followup_knockout.v2", "calendar_followup_knockout.v4", "calendar_followup_knockout.v5"}:
            needed_type = (
                CalendarFollowupEightPointPolicy
                if eight
                else CalendarFollowupPointPolicy
            )
            if (
                not isinstance(self.prepared_policy, needed_type)
                or (not configured and self.prepared_policy.validity_weeks != self.week.calendar.weeks_per_year)
            ):
                raise ValueError("Scored knockout requires matching W-valid prepared point policy")
            request["point_policy"] = self.prepared_policy.model_dump(mode="json")
            request["explicit_point_confirmation"] = True
            if self.prepared_awards != derive_followup_awards(self):
                raise ValueError("Prepared knockout points disagree with actual match results")
        elif self.prepared_policy is not None or self.prepared_awards:
            raise ValueError("Unscored knockout cannot acquire prepared points")
        if self.request_fingerprint != canonical_hash({
            "run_id": self.run_id, "branch_id": self.branch_id, "command": request,
            **({"edition_authority_fingerprint":self.edition_authority_fingerprint} if configured else {}),
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
            "calendar_sporting_checkpoint.v5", "calendar_sporting_checkpoint.v6",
            "calendar_sporting_checkpoint.v7", "calendar_sporting_checkpoint.v8",
            "calendar_sporting_checkpoint.v9",
            "calendar_sporting_checkpoint.v10",
        }
        or not checkpoint.week_events
        or (checkpoint.run_id, checkpoint.branch_id) != (event.run_id, event.branch_id)
        or checkpoint.fingerprint != event.source_checkpoint_fingerprint
        or checkpoint.week.ordinal != event.week.ordinal
        or event.command_id in {
            *(advance.command_id for advance in checkpoint.weekly_advances),
            *(entry.command_id for entry in checkpoint.played_continuations),
            *(tournament.command_id for tournament in checkpoint.tournaments),
            *(closure.command_id for closure in checkpoint.closures),
        }
        or event.tournament_id in {
            tournament.tournament_id for tournament in checkpoint.tournaments
        }
        or set(event.entrant_ids) - {p.player_id for p in checkpoint.players}
    ):
        raise ValueError("Knockout source/roster or identity differs from Saved sporting state")

    # Each match still verifies source fingerprint, 57-attribute projections,
    # deterministic winner-fed identities and post-match player effects.
    # The intermediate seven-match prefixes are not externally persisted.
    # Validating/serializing the whole 1,000-player + match-log checkpoint on
    # EVERY round causes pathological Save/recovery latencies; validate once
    # after the complete atomic tournament is assembled below.
    intermediate = checkpoint
    for match in event.matches:
        intermediate = append_continuation(
            intermediate, world, match, _defer_checkpoint_validation=True,
        )
    successor = checkpoint.model_copy(update={
        "schema_version": (
            "calendar_sporting_checkpoint.v10"
            if checkpoint.schema_version == "calendar_sporting_checkpoint.v10"
            else "calendar_sporting_checkpoint.v9"
            if checkpoint.schema_version == "calendar_sporting_checkpoint.v9" or event.schema_version == "calendar_followup_knockout.v5"
            else
            "calendar_sporting_checkpoint.v8"
            if checkpoint.schema_version == "calendar_sporting_checkpoint.v8"
            else "calendar_sporting_checkpoint.v7"
            if checkpoint.schema_version == "calendar_sporting_checkpoint.v7"
            or event.schema_version == "calendar_followup_knockout.v4"
            else "calendar_sporting_checkpoint.v6"
            if checkpoint.schema_version == "calendar_sporting_checkpoint.v6"
            or event.schema_version == "calendar_followup_knockout.v3"
            else "calendar_sporting_checkpoint.v5"
            if checkpoint.schema_version == "calendar_sporting_checkpoint.v5"
            or event.schema_version == "calendar_followup_knockout.v2"
            else "calendar_sporting_checkpoint.v4"
        ),
        "players": intermediate.players,
        "week_events": checkpoint.week_events + (event,),
    })
    return CalendarSportingCheckpoint.model_validate_json(successor.model_dump_json())
