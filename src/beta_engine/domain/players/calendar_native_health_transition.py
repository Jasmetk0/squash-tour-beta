"""Versioned Health carry across native Tour weeks and authenticated 15yo births.

This is a pure, strict replay primitive; it does NOT authorize a Tour
transition or silently mutate Saved snapshots. The future atomic writer must
commit the matching Lifecycle, Sporting, Health, Ranking and Tour receipts.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_health import (
    CalendarHealthEditEvidence, CalendarHealthOrigin, CalendarHealthProfile,
    CalendarHealthState,
)
from beta_engine.domain.players.calendar_initial_health import CalendarInitialHealthState
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleState, CalendarTourLifecycleState,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarProspectBirthEvent, CalendarTourLifecycleIntakeState,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarNativeHealthTransitionState(FrozenInput):
    """Complete, calendar-owned natural Health Week state (no invented healing)."""

    schema_version: Literal["player_health_calendar_state.v3"] = (
        "player_health_calendar_state.v3"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    week: RunWeekPosition
    players: tuple[CalendarHealthProfile, ...] = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    birth_event: CalendarProspectBirthEvent | None = None
    origin: CalendarHealthOrigin
    admin_edits: tuple[CalendarHealthEditEvidence, ...] = ()
    stage_provenance: Literal["native_health_week_carry.v1"] = (
        "native_health_week_carry.v1"
    )

    @model_validator(mode="after")
    def verify_scoped_population(self):
        ids = tuple(p.player_id for p in self.players)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("Native v3 Health requires a unique sorted population")
        if self.week.ordinal < 1:
            raise ValueError("Native v3 Health must follow initial Week 1")
        if self.birth_event and (
            (self.birth_event.run_id, self.birth_event.branch_id)
            != (self.run_id, self.branch_id)
            or self.birth_event.target_week != self.week
        ):
            raise ValueError("Native v3 Health contains a foreign birthday event")
        if len({
            (e.source_run_id, e.source_branch_id, e.command_id)
            for e in self.admin_edits
        }) != len(self.admin_edits):
            raise ValueError("Native v3 Health has duplicate Admin history")
        if any(e.player_id not in ids or e.source_run_id != self.run_id
               for e in self.admin_edits):
            raise ValueError("Native v3 Health contains foreign Admin evidence")
        for person in self.players:
            for record in person.records:
                for date in (record.onset_week, record.recovered_week):
                    if date and (
                        date.ordinal > self.week.ordinal
                        or (date.calendar.weeks_per_year,
                            date.calendar.season_start_year_week,
                            date.calendar.start_year)
                        != (self.week.calendar.weeks_per_year,
                            self.week.calendar.season_start_year_week,
                            self.week.calendar.start_year)
                        or date.calendar.season_count > self.week.calendar.season_count
                    ):
                        raise ValueError("Native v3 Health contains future/foreign illness dates")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


NativeHealthPredecessor = (
    CalendarInitialHealthState | CalendarHealthState | CalendarNativeHealthTransitionState
)
NativeLifecycle = (
    CalendarPlayerLifecycleState | CalendarTourLifecycleState
    | CalendarTourLifecycleIntakeState
)


def advance_native_health_week(
    *,
    previous_health: NativeHealthPredecessor,
    previous_lifecycle: NativeLifecycle,
    next_lifecycle: CalendarTourLifecycleState | CalendarTourLifecycleIntakeState,
) -> CalendarNativeHealthTransitionState:
    """Replay one complete Week from genuine lifecycle, with no healing fiction.

    Earlier Signed health profiles are copied without changes. A genuine v4
    lifecycle birthday creates an empty health profile. No other source may
    add, drop or modify identities; v3 life cannot secretly admit a player.
    """
    old, new = previous_lifecycle.week, next_lifecycle.week
    if (
        new.ordinal != old.ordinal + 1
        or previous_health.week.ordinal != old.ordinal
        or (old.calendar.weeks_per_year, old.calendar.season_start_year_week,
            old.calendar.start_year)
        != (new.calendar.weeks_per_year, new.calendar.season_start_year_week,
            new.calendar.start_year)
        or old.calendar.season_count > new.calendar.season_count
        or (
            previous_health.run_id, previous_health.branch_id,
            previous_lifecycle.run_id, previous_lifecycle.branch_id,
            next_lifecycle.run_id, next_lifecycle.branch_id
        ) != (
            previous_lifecycle.run_id, previous_lifecycle.branch_id,
            previous_lifecycle.run_id, previous_lifecycle.branch_id,
            previous_lifecycle.run_id, previous_lifecycle.branch_id
        )
        or previous_health.source_initial_world_fingerprint
        != previous_lifecycle.source_initial_world_fingerprint
        or next_lifecycle.source_initial_world_fingerprint
        != previous_lifecycle.source_initial_world_fingerprint
        or next_lifecycle.predecessor_fingerprint != previous_lifecycle.fingerprint
    ):
        raise ValueError("Native v3 Health requires the exact consecutive Signed lifecycle")
    old_ids = tuple(p.player_id for p in previous_lifecycle.players)
    present_ids = tuple(p.player_id for p in previous_health.players)
    next_ids = tuple(p.player_id for p in next_lifecycle.players)
    if old_ids != present_ids:
        raise ValueError("Native v3 Health predecessor roster differs from Signed life")
    births: tuple[str, ...] = ()
    event: CalendarProspectBirthEvent | None = None
    if isinstance(next_lifecycle, CalendarTourLifecycleIntakeState):
        event = next_lifecycle.birth_event
        if (
            event.predecessor_fingerprint != previous_lifecycle.fingerprint
            or event.target_week != next_lifecycle.week
        ):
            raise ValueError("Native v3 Health birthday does not match Signed life")
        births = tuple(p.player_id for p in event.births)
    if (
        next_ids != tuple(sorted((*old_ids, *births)))
        or set(old_ids) & set(births)
    ):
        raise ValueError("Native v3 Health rejects missing or unsourced newcomers")
    by_id = {
        p.player_id: CalendarHealthProfile.model_validate(p.model_dump(mode="json"))
        for p in previous_health.players
    }
    for pid in births:
        by_id[pid] = CalendarHealthProfile(player_id=pid)
    origin = (
        CalendarHealthOrigin.from_baseline(previous_health)
        if isinstance(previous_health, CalendarInitialHealthState)
        else previous_health.origin
    )
    edits = (
        () if isinstance(previous_health, CalendarInitialHealthState)
        else previous_health.admin_edits
    )
    return CalendarNativeHealthTransitionState(
        run_id=next_lifecycle.run_id, branch_id=next_lifecycle.branch_id,
        week=new, players=tuple(by_id[pid] for pid in next_ids),
        source_initial_world_fingerprint=next_lifecycle.source_initial_world_fingerprint,
        predecessor_fingerprint=previous_health.fingerprint,
        source_lifecycle_fingerprint=next_lifecycle.fingerprint,
        birth_event=event, origin=origin, admin_edits=edits,
    )
