"""Run-calendar health facts. No healing probabilities or sporting authority."""

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_initial_health import (
    CalendarInitialHealthState,
)
from beta_engine.domain.players.health import PlayerHealthProfile, PlayerHealthRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarHealthRecord(PlayerHealthRecord):
    onset_week: RunWeekPosition | None = None
    recovered_week: RunWeekPosition | None = None

    @model_validator(mode="after")
    def calendar_facts(self):
        if self.lifecycle == "Recovered" and self.severity != 0:
            raise ValueError("Recovered health record must have zero acute severity")
        if (
            self.onset_week is not None
            and self.recovered_week is not None
            and self.onset_week.calendar != self.recovered_week.calendar
        ):
            raise ValueError("Health dates must belong to the same Run calendar")
        return self


class CalendarHealthProfile(PlayerHealthProfile):
    records: tuple[CalendarHealthRecord, ...] = ()

    @model_validator(mode="after")
    def recurrence_order(self):
        by_id = {r.record_id: r for r in self.records}
        for record in self.records:
            if record.recurrence_of_record_id is None:
                continue
            source = by_id[record.recurrence_of_record_id]
            if record.started_before_run:
                if not source.started_before_run:
                    raise ValueError(
                        "Pre-Run recurrence cannot precede its in-Run source"
                    )
            elif source.onset_week is not None:
                if (
                    source.onset_week.calendar != record.onset_week.calendar
                    or source.onset_week.ordinal > record.onset_week.ordinal
                ):
                    raise ValueError("Health recurrence cannot precede its source")
            if source.recovered_week is not None and (
                record.onset_week is None
                or source.recovered_week.calendar != record.onset_week.calendar
                or source.recovered_week.ordinal > record.onset_week.ordinal
            ):
                raise ValueError("Health recurrence cannot precede source recovery")
        return self


class CalendarHealthOrigin(FrozenInput):
    schema_version: Literal["calendar_health_origin.v1"] = "calendar_health_origin.v1"
    baseline_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    command_id: str
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    initialization_policy: Literal["fresh_without_history.v1"]
    audit_label: str
    audit_reason: str

    @classmethod
    def from_baseline(cls, state: CalendarInitialHealthState):
        return cls(
            baseline_fingerprint=state.fingerprint,
            **{
                key: getattr(state, key)
                for key in (
                    "command_id",
                    "request_fingerprint",
                    "initialization_policy",
                    "audit_label",
                    "audit_reason",
                )
            },
        )


class CalendarHealthEditEvidence(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    before_state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_run_id: str
    source_branch_id: str
    player_id: str
    mode: Literal["pre_start_input", "current_state_correction"]
    audit_label: str
    audit_reason: str


class CalendarHealthState(FrozenInput):
    schema_version: Literal["player_health_calendar_state.v2"] = (
        "player_health_calendar_state.v2"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[CalendarHealthProfile, ...] = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    origin: CalendarHealthOrigin
    admin_edits: tuple[CalendarHealthEditEvidence, ...] = Field(min_length=1)
    stage_provenance: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_facts(self):
        ids = tuple(p.player_id for p in self.players)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("Calendar Health roster must be canonical and unique")
        commands = tuple(
            (e.source_run_id, e.source_branch_id, e.command_id)
            for e in self.admin_edits
        )
        if len(commands) != len(set(commands)):
            raise ValueError("Calendar Health edit identities must be unique")
        if any(
            e.player_id not in ids or e.source_run_id != self.run_id
            for e in self.admin_edits
        ):
            raise ValueError(
                "Calendar Health edit evidence differs from its owner/roster"
            )
        for player in self.players:
            for record in player.records:
                for date in (record.onset_week, record.recovered_week):
                    if date is not None and (
                        date.calendar != self.week.calendar
                        or date.ordinal > self.week.ordinal
                    ):
                        raise ValueError(
                            "Health fact has a foreign calendar or future date"
                        )
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def carry_calendar_health_forward(
    predecessor: CalendarHealthState,
    *,
    target: RunWeekPosition,
    target_player_ids: tuple[str, ...],
) -> CalendarHealthState:
    """Pure fact carry; does not authorize Week/Season sporting progression."""
    if (
        target.calendar != predecessor.week.calendar
        or target.ordinal != predecessor.week.ordinal + 1
    ):
        raise ValueError(
            "Calendar Health carry requires matching calendar and consecutive weeks"
        )
    ids = tuple(sorted(set(target_player_ids)))
    if len(ids) != len(target_player_ids) or set(
        p.player_id for p in predecessor.players
    ) - set(ids):
        raise ValueError("Calendar Health carry cannot duplicate or drop identities")
    previous = {p.player_id: p for p in predecessor.players}
    return CalendarHealthState(
        **{
            k: getattr(predecessor, k)
            for k in (
                "run_id",
                "branch_id",
                "source_initial_world_fingerprint",
                "origin",
                "admin_edits",
            )
        },
        week=target,
        players=tuple(
            previous.get(pid, CalendarHealthProfile(player_id=pid)) for pid in ids
        ),
        predecessor_fingerprint=predecessor.fingerprint,
        stage_provenance="calendar_health_carry.v1:unchanged-facts;no-healing-or-sporting-authority",
    )
