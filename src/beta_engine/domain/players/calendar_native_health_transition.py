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
        or (previous_health.week.calendar.weeks_per_year,
            previous_health.week.calendar.season_start_year_week,
            previous_health.week.calendar.start_year)
        != (old.calendar.weeks_per_year, old.calendar.season_start_year_week,
            old.calendar.start_year)
        or previous_health.week.calendar.season_count > new.calendar.season_count
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
        p.player_id: CalendarHealthProfile.model_validate_json(p.model_dump_json())
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


def prepare_native_health_history(
    *, saved_health: tuple[NativeHealthPredecessor, ...],
    signed_lifecycle: tuple[NativeLifecycle, ...],
    next_lifecycle: CalendarTourLifecycleState | CalendarTourLifecycleIntakeState,
) -> tuple[NativeHealthPredecessor, ...]:
    """Preserve a verified Saved prefix and prepare every missing natural Week.

    The caller must authenticate Saved Health and the complete Signed lifecycle
    (including the Run source/actual Entry). This does not manufacture earlier
    injuries, apply healing or write SQLite. Each omitted Health week is an
    exact fact carry against its own historical lifecycle; the new birthday is
    admitted only at the final target, never retroactively in the backfill.
    """
    if not saved_health or not signed_lifecycle:
        raise ValueError("Native Health preparation requires Saved Health and full lifecycle")
    first = signed_lifecycle[0]
    if not isinstance(first, CalendarPlayerLifecycleState) or first.week.ordinal != 0:
        raise ValueError("Native Health preparation requires the original lifecycle")
    previous = None
    for ordinal, life in enumerate(signed_lifecycle):
        if (
            life.week.ordinal != ordinal
            or (life.run_id, life.branch_id) != (first.run_id, first.branch_id)
            or life.source_initial_world_fingerprint != first.source_initial_world_fingerprint
            or (life.week.calendar.weeks_per_year, life.week.calendar.season_start_year_week,
                life.week.calendar.start_year)
            != (first.week.calendar.weeks_per_year, first.week.calendar.season_start_year_week,
                first.week.calendar.start_year)
            or (previous is not None and (
                life.predecessor_fingerprint != previous.fingerprint
                or life.week.calendar.season_count < previous.week.calendar.season_count
            ))
        ):
            raise ValueError("Native Health preparation has incomplete/foreign lifecycle history")
        previous = life
    if len(saved_health) > len(signed_lifecycle) or saved_health[-1].week.ordinal >= len(signed_lifecycle):
        raise ValueError("Native Health preparation cannot use future Health")
    for ordinal, health in enumerate(saved_health):
        life = signed_lifecycle[ordinal]
        if ordinal and (
            isinstance(health, CalendarInitialHealthState)
            or (isinstance(saved_health[ordinal-1], CalendarNativeHealthTransitionState)
                and not isinstance(health, CalendarNativeHealthTransitionState))
        ):
            raise ValueError("Native Health preparation cannot downgrade its Saved authority")
        if (
            health.week.ordinal != ordinal
            or (health.run_id, health.branch_id) != (first.run_id, first.branch_id)
            or health.source_initial_world_fingerprint != first.source_initial_world_fingerprint
            or tuple(p.player_id for p in health.players) != tuple(p.player_id for p in life.players)
            or (health.week.calendar.weeks_per_year,
                health.week.calendar.season_start_year_week, health.week.calendar.start_year)
            != (life.week.calendar.weeks_per_year,
                life.week.calendar.season_start_year_week, life.week.calendar.start_year)
            or health.week.calendar.season_count > life.week.calendar.season_count
            or health.week.calendar.season_count < first.week.calendar.season_count
            or (ordinal == 0 and health.predecessor_fingerprint is not None)
            or (ordinal > 0 and (
                health.predecessor_fingerprint != saved_health[ordinal-1].fingerprint
                or health.week.calendar.season_count < saved_health[ordinal-1].week.calendar.season_count
            ))
        ):
            raise ValueError("Native Health preparation differs from its exact Saved prefix")
        if isinstance(health, CalendarNativeHealthTransitionState) and (
            ordinal == 0 or health != advance_native_health_week(
                previous_health=saved_health[ordinal-1],
                previous_lifecycle=signed_lifecycle[ordinal-1], next_lifecycle=life,
            )
        ):
            raise ValueError("Native Health preparation has forged natural Health history")
    prepared = list(saved_health)
    for life in (*signed_lifecycle[len(saved_health):], next_lifecycle):
        predecessor = signed_lifecycle[prepared[-1].week.ordinal]
        prepared.append(advance_native_health_week(
            previous_health=prepared[-1], previous_lifecycle=predecessor,
            next_lifecycle=life,
        ))
    return tuple(prepared)
