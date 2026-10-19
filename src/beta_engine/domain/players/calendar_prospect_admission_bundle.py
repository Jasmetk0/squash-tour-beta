"""Signed-source native 15yo admission: coupled pure lifecycle/sporting/Health truth.

This model deliberately stages the *complete* target population without a
database write. Historic Saved Health and Tour checkpoint schemas are untouched;
the eventual native writer must version its replay, Entry and ranking authorities
before it may persist this bundle.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_health import CalendarHealthProfile, CalendarHealthState
from beta_engine.domain.players.calendar_initial_health import CalendarInitialHealthState
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleState, CalendarTourLifecycleState,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarProspectBirthEvent, CalendarTourLifecycleIntakeState,
    advance_calendar_lifecycle_with_prospects, build_calendar_prospect_birth_event,
    project_native_birth_sporting_roster,
)
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarProspectHealthProjection(FrozenInput):
    """Exactly preserves existing Health facts and gives newborns EMPTY history."""

    schema_version: Literal["calendar_prospect_health_projection.v1"] = (
        "calendar_prospect_health_projection.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    source_health_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_health_week: RunWeekPosition
    target_week: RunWeekPosition
    birth_event: CalendarProspectBirthEvent
    predecessor_profiles: tuple[PlayerHealthProfile, ...]
    proposed_profiles: tuple[PlayerHealthProfile, ...]

    @model_validator(mode="after")
    def verify_conserved_health_facts(self):
        birth = self.birth_event
        if ((self.run_id, self.branch_id) != (birth.run_id, birth.branch_id)
            or self.target_week != birth.target_week):
            raise ValueError("Birth Health projection differs from the Signed event")
        if (
            self.source_health_week.ordinal >= self.target_week.ordinal
            or self.source_health_week.calendar.weeks_per_year != self.target_week.calendar.weeks_per_year
            or self.source_health_week.calendar.season_start_year_week != self.target_week.calendar.season_start_year_week
            or self.source_health_week.calendar.start_year != self.target_week.calendar.start_year
            or self.source_health_week.calendar.season_count > self.target_week.calendar.season_count
        ):
            raise ValueError("Birth Health projection has a foreign or future source week")
        original = tuple(profile.player_id for profile in self.predecessor_profiles)
        proposed = tuple(profile.player_id for profile in self.proposed_profiles)
        additions = tuple(b.player_id for b in birth.births)
        if original != tuple(sorted(set(original))) or proposed != tuple(sorted(set(proposed))):
            raise ValueError("Birth Health projection requires canonical unique players")
        if set(original) & set(additions) or set(proposed) != set(original) | set(additions):
            raise ValueError("Birth Health projection lost or duplicated identities")
        by_id = {p.player_id: p for p in self.proposed_profiles}
        for profile in self.predecessor_profiles:
            if by_id[profile.player_id] != profile:
                raise ValueError("Birth Health projection must preserve existing injury history")
        for player_id in additions:
            new = by_id[player_id]
            if new.records or new.permanent_consequences:
                raise ValueError("Birth Health projection cannot invent newborn health facts")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def project_native_birth_health(*, health, event: CalendarProspectBirthEvent, predecessor):
    """Project from authenticated initial/current Saved Health, with no fake healing."""
    if not isinstance(health, (CalendarInitialHealthState, CalendarHealthState)):
        raise ValueError("Native birth requires verified calendar Health authority")
    if (
        (health.run_id, health.branch_id) != (event.run_id, event.branch_id)
        or health.source_initial_world_fingerprint != predecessor.source_initial_world_fingerprint
        or health.week.ordinal > predecessor.week.ordinal
    ):
        raise ValueError("Native birth Health source differs from Original World or lifecycle")
    old_ids = tuple(row.player_id for row in predecessor.players)
    health_ids = tuple(row.player_id for row in health.players)
    if health_ids != old_ids:
        raise ValueError("Native birth Health and predecessor lifecycle rosters disagree")
    if any(
        profile.permanent_consequences or any(r.lifecycle != "Recovered" for r in profile.records)
        for profile in health.players
    ):
        raise ValueError("Native birth cannot bypass unsupported active Health healing")
    previous = tuple(health.players)
    proposed = tuple(sorted(
        (*previous, *(CalendarHealthProfile(player_id=b.player_id) for b in event.births)),
        key=lambda p: p.player_id,
    ))
    return CalendarProspectHealthProjection(
        run_id=event.run_id, branch_id=event.branch_id,
        source_health_fingerprint=health.fingerprint, source_health_week=health.week,
        target_week=event.target_week, birth_event=event,
        predecessor_profiles=previous, proposed_profiles=proposed,
    )


class CalendarProspectAdmissionBundle(FrozenInput):
    """One indivisible proposed future population across three domain owners."""

    schema_version: Literal["calendar_prospect_admission_bundle.v1"] = (
        "calendar_prospect_admission_bundle.v1"
    )
    saved_head_revision_id: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    event: CalendarProspectBirthEvent
    lifecycle: CalendarTourLifecycleIntakeState
    sporting: tuple[PlayerSportingRecord, ...]
    health: CalendarProspectHealthProjection
    # Explicit unimplemented downstream authorities: no silent participation.
    ranking_and_entry_adoption_supported: Literal[False] = False
    tour_signed_writer_supported: Literal[False] = False

    @model_validator(mode="after")
    def verify_atomic_proposed_roster(self):
        event = self.event
        health = self.health
        if (
            self.lifecycle.birth_event != event
            or health.birth_event != event
            or self.lifecycle.week != event.target_week
            or self.lifecycle.predecessor_fingerprint != event.predecessor_fingerprint
            or health.target_week != event.target_week
        ):
            raise ValueError("Native admission bundle has unbound birth/Health/lifecycle evidence")
        life_ids = tuple(p.player_id for p in self.lifecycle.players)
        sporting_ids = tuple(p.player_id for p in self.sporting)
        health_ids = tuple(p.player_id for p in health.proposed_profiles)
        if life_ids != sporting_ids or life_ids != health_ids:
            raise ValueError("Native admission bundle has mismatched domain populations")
        if any(len(p.attributes) != 57 for p in self.sporting):
            raise ValueError("Native admission bundle has incomplete sporting profiles")
        by_id = {p.player_id: p for p in self.sporting}
        for arrival in event.births:
            player = by_id[arrival.player_id]
            if (
                player.attributes != arrival.sporting_profile.attributes
                or player.potential_ovr != arrival.sporting_profile.potential_ovr
                or player.potential_identity != arrival.sporting_profile.potential_identity
            ):
                raise ValueError("Native admission bundle sporting birth differs from Signed source")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def build_native_prospect_admission_bundle(
    *, predecessor: CalendarPlayerLifecycleState | CalendarTourLifecycleState,
    checkpoint, health: CalendarInitialHealthState | CalendarHealthState,
    source, target: RunWeekPosition, world_package_id: str,
    saved_head_revision_id: str, submissions=(),
) -> CalendarProspectAdmissionBundle:
    """Full 57-attribute and Health-conserving, read-only next-week proposal."""
    if checkpoint.week != predecessor.week:
        raise ValueError("Native birth predecessor is not current sporting owner")
    event = build_calendar_prospect_birth_event(
        predecessor=predecessor, target=target,
        source=source, world_package_id=world_package_id,
    )
    lifecycle = advance_calendar_lifecycle_with_prospects(
        predecessor, event, submissions,
    )
    sporting = project_native_birth_sporting_roster(
        predecessor=predecessor, checkpoint=checkpoint, event=event,
    )
    proposed_health = project_native_birth_health(
        health=health, event=event, predecessor=predecessor,
    )
    return CalendarProspectAdmissionBundle(
        saved_head_revision_id=saved_head_revision_id,
        source_checkpoint_fingerprint=checkpoint.fingerprint,
        event=event, lifecycle=lifecycle,
        sporting=sporting, health=proposed_health,
    )
