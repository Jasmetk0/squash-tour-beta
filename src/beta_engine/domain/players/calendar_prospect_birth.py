"""Versioned, pure W-aware native 15th-birthday lifecycle adoption evidence.

This is a real, deterministic *proposed* birth-week lifecycle transition.
Production Tour must not persist v4 until sporting, Health, ranking and Saved
replay share this exact event. v2/v3 historical lifecycle bytes never change.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleState, CalendarTourLifecycleIdentity,
    CalendarTourLifecycleState, advance_calendar_lifecycle,
)
from beta_engine.domain.players.prospect_sporting_profile import (
    ProspectSportingProfile, materialize_prospect_sporting_profile,
    validate_persisted_prospect_sporting_profile,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash

NATIVE_SOURCE_TYPE = "native_calendar_15yo_cohort"
NATIVE_POLICY_VERSION = "native_calendar_15yo_cohort_v1"


class CalendarProspectBirth(FrozenInput):
    """Entire immutable 57-attribute sporting and identity proof for one arrival."""

    player_id: str = Field(min_length=1)
    country_code: str = Field(pattern=r"^[A-Z]{3}$")
    birth_year: int
    birth_year_week: int = Field(ge=1)
    source_record_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_generation_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    sporting_profile: ProspectSportingProfile

    @model_validator(mode="after")
    def match_frozen_identity(self):
        if self.sporting_profile.player_id != self.player_id:
            raise ValueError("Native birth identity differs from sporting profile")
        return self


class CalendarProspectBirthEvent(FrozenInput):
    schema_version: Literal["calendar_prospect_birth_event.v1"] = (
        "calendar_prospect_birth_event.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    predecessor_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_run_prospect_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_world_package_id: str = Field(min_length=1)
    target_week: RunWeekPosition
    births: tuple[CalendarProspectBirth, ...]

    @model_validator(mode="after")
    def validate_births(self):
        ids = tuple(b.player_id for b in self.births)
        if ids != tuple(sorted(set(ids))):
            raise ValueError("Native birth event requires sorted unique player identities")
        year_week = self.target_week.calendar_position
        for birth in self.births:
            if birth.birth_year + 15 != year_week.calendar_year or birth.birth_year_week != year_week.year_week:
                raise ValueError("Native birth event is not the exact 15th birthday")
            expected = canonical_hash({
                "source_run_prospect_fingerprint": self.source_run_prospect_fingerprint,
                "source_record_fingerprint": birth.source_record_fingerprint,
                "player_id": birth.player_id,
                "sporting_profile_fingerprint": birth.sporting_profile.fingerprint,
            })
            if birth.source_generation_fingerprint != expected:
                raise ValueError("Native birth source generation proof is invalid")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


class CalendarTourLifecycleIntakeState(CalendarTourLifecycleState):
    """Separate v4 successor; never serialize intake through historical v3."""

    schema_version: Literal["player_lifecycle_calendar_state.v4"] = (
        "player_lifecycle_calendar_state.v4"
    )
    birth_event: CalendarProspectBirthEvent

    @model_validator(mode="after")
    def verify_arrivals(self):
        event = self.birth_event
        if (
            (event.run_id, event.branch_id) != (self.run_id, self.branch_id)
            or event.target_week != self.week
            or event.predecessor_fingerprint != self.predecessor_fingerprint
        ):
            raise ValueError("Native lifecycle birth event has foreign scope or predecessor")
        players = {row.player_id: row for row in self.players}
        for birth in event.births:
            person = players.get(birth.player_id)
            if (
                person is None
                or person.age != 15
                or person.birth_year != birth.birth_year
                or person.birth_year_week != birth.birth_year_week
                or person.source_generation_fingerprint != birth.source_generation_fingerprint
                or person.status != "active"
                or person.tour_entry_week is not None
                or person.tie_break_token is not None
            ):
                raise ValueError("Native lifecycle arrival differs from its signed birth evidence")
        return self


def build_calendar_prospect_birth_event(
    *, predecessor: CalendarPlayerLifecycleState | CalendarTourLifecycleState,
    target: RunWeekPosition, source,
    world_package_id: str,
) -> CalendarProspectBirthEvent:
    """Convert an already authenticated Saved Run prospect snapshot to birth evidence.

    Caller owns authenticated Saved/prospect/live equality; this pure function
    checks row date/World/policy/57 attributes/seeds and identity collisions.
    A record belongs to exactly one W-aware target calendar position.
    """
    if source is None or source.run_id != predecessor.run_id:
        raise ValueError("Native birth requires a Signed, Run-matching prospect source")
    if target.ordinal != predecessor.week.ordinal + 1:
        raise ValueError("Native birth requires the next consecutive Run week")
    if (
        predecessor.week.calendar.weeks_per_year,
        predecessor.week.calendar.season_start_year_week,
        predecessor.week.calendar.start_year,
    ) != (
        target.calendar.weeks_per_year,
        target.calendar.season_start_year_week,
        target.calendar.start_year,
    ) or predecessor.week.calendar.season_count > target.calendar.season_count:
        raise ValueError("Native birth cannot reinterpret or shorten the Run calendar")

    clock = target.calendar
    original_ids = {p.player_id for p in predecessor.players}
    rows = source.records
    ids = [row.get("prospect_id") for row in rows]
    if (
        any(type(pid) is not str or not pid for pid in ids)
        or ids != sorted(set(ids))
    ):
        raise ValueError("Signed Run prospect source identities are not canonical")

    incoming: list[CalendarProspectBirth] = []
    for row in rows:
        birth_year, birth_week = row.get("birth_year"), row.get("birth_year_week")
        if (
            type(birth_year) is not int or type(birth_week) is not int
            or not 1 <= birth_week <= clock.weeks_per_year
        ):
            raise ValueError("Native source has an invalid Run calendar birth date")
        position = clock.calendar_to_season(birth_year + 15, birth_week)
        if position is None:
            # A real source row claiming a season owned by this Run cannot
            # escape validation by placing its birthday outside the horizon.
            if row.get("season_start_year") in range(
                clock.start_year, clock.start_year + clock.season_count
            ):
                raise ValueError("Native source birth date differs from its Run week")
            continue
        if (
            row.get("season_start_year") != clock.start_year + position.season_index
            or row.get("season_week") != position.season_week
            or row.get("calendar_year") != position.calendar_year
            or row.get("year_week") != position.year_week
            or row.get("age") != 15
        ):
            raise ValueError("Native source birth date differs from its Run week")
        if position != target.calendar_position:
            continue
        if (
            row.get("world_id") != world_package_id
            or row.get("source_type") != NATIVE_SOURCE_TYPE
            or row.get("cohort_policy_version") != NATIVE_POLICY_VERSION
            or row.get("profile_version") != "prospect_profile_v1"
            or row.get("status") != "prospect"
        ):
            raise ValueError("Native birth does not belong to the Saved World or native source policy")
        pid = row["prospect_id"]
        if pid in original_ids:
            raise ValueError("Native birth collides with an existing lifecycle player")
        country = row.get("country_code")
        if type(country) is not str or len(country) != 3 or not country.isascii() or not country.isupper() or not country.isalpha():
            raise ValueError("Native birth requires a canonical country identity")
        profile = validate_persisted_prospect_sporting_profile(
            profile=row.get("profile", {}),
            development=row.get("development", {}),
            potential=row.get("potential", {}),
        )
        if profile.player_id != pid:
            raise ValueError("Native birth profile belongs to a different player")
        for field in ("profile_seed", "development_seed", "potential_seed"):
            if type(row.get(field)) is not str or not row[field]:
                raise ValueError("Native birth requires canonical deterministic seeds")
        replayed = materialize_prospect_sporting_profile(
            player_id=pid, profile_seed=row["profile_seed"],
            development_seed=row["development_seed"],
            potential_seed=row["potential_seed"],
        )
        if replayed != profile:
            raise ValueError("Native birth profile cannot be regenerated from frozen seeds")
        fingerprint = canonical_hash(row)
        provenance = canonical_hash({
            "source_run_prospect_fingerprint": source.fingerprint,
            "source_record_fingerprint": fingerprint,
            "player_id": pid,
            "sporting_profile_fingerprint": profile.fingerprint,
        })
        incoming.append(CalendarProspectBirth(
            player_id=pid, country_code=country, birth_year=birth_year,
            birth_year_week=birth_week, source_record_fingerprint=fingerprint,
            source_generation_fingerprint=provenance, sporting_profile=profile,
        ))
        original_ids.add(pid)
    return CalendarProspectBirthEvent(
        run_id=predecessor.run_id, branch_id=predecessor.branch_id,
        predecessor_fingerprint=predecessor.fingerprint,
        source_run_prospect_fingerprint=source.fingerprint,
        source_world_package_id=world_package_id,
        target_week=target,
        births=tuple(sorted(incoming, key=lambda p: p.player_id)),
    )


def advance_calendar_lifecycle_with_prospects(
    predecessor: CalendarPlayerLifecycleState | CalendarTourLifecycleState,
    event: CalendarProspectBirthEvent,
    submissions=(),
) -> CalendarTourLifecycleIntakeState:
    """Pure birth + retirement + previous Entry, with no DB or Tour writes."""
    if (
        (event.run_id, event.branch_id) != (predecessor.run_id, predecessor.branch_id)
        or event.predecessor_fingerprint != predecessor.fingerprint
        or event.target_week.ordinal != predecessor.week.ordinal + 1
    ):
        raise ValueError("Native birth event does not match lifecycle predecessor")
    advanced = advance_calendar_lifecycle(
        predecessor, event.target_week, submissions,
    )
    current = {p.player_id for p in advanced.players}
    if any(b.player_id in current for b in event.births):
        raise ValueError("Native lifecycle birth duplicates an existing player")
    additions = tuple(
        CalendarTourLifecycleIdentity(
            player_id=b.player_id,
            birth_year=b.birth_year,
            birth_year_week=b.birth_year_week,
            age=15, status="active",
            source_generation_fingerprint=b.source_generation_fingerprint,
            retirement_effective_week=None,
            tour_entry_week=None, tie_break_token=None,
        )
        for b in event.births
    )
    return CalendarTourLifecycleIntakeState(
        run_id=advanced.run_id, branch_id=advanced.branch_id,
        week=advanced.week,
        players=tuple(sorted((*advanced.players, *additions), key=lambda p: p.player_id)),
        source_initial_world_fingerprint=advanced.source_initial_world_fingerprint,
        predecessor_fingerprint=advanced.predecessor_fingerprint,
        policy=advanced.policy,
        birth_event=event,
    )


def project_native_birth_sporting_roster(
    *, predecessor, checkpoint, event: CalendarProspectBirthEvent,
) -> tuple:
    """Pure canonical 57-attribute sporting *proposal* for an exact birth event.

    It retains every historical sporting record byte-for-byte and creates
    entrants from their original prepared 57-attribute profile, using the
    checkpoint's persisted provisional bootstrap defaults. Does NOT install
    a checkpoint or claim Health/Saved activation.
    """
    from beta_engine.domain.players.sporting import PlayerSportingRecord

    if (
        (checkpoint.run_id, checkpoint.branch_id)
        != (event.run_id, event.branch_id)
        or checkpoint.week != predecessor.week
        or event.predecessor_fingerprint != predecessor.fingerprint
        or event.target_week.ordinal != checkpoint.week.ordinal + 1
    ):
        raise ValueError("Native birth sporting proposal has a foreign predecessor")
    original_ids = tuple(person.player_id for person in predecessor.players)
    sporting_ids = tuple(person.player_id for person in checkpoint.players)
    if original_ids != sporting_ids:
        raise ValueError("Native birth sporting proposal disagrees with lifecycle identities")
    if any(b.player_id in sporting_ids for b in event.births):
        raise ValueError("Native birth sporting proposal duplicates an existing athlete")
    policy = checkpoint.bootstrap_policy
    newborns = tuple(
        PlayerSportingRecord(
            player_id=b.player_id,
            attributes=b.sporting_profile.attributes,
            potential_ovr=b.sporting_profile.potential_ovr,
            potential_identity=b.sporting_profile.potential_identity,
            potential_provenance=b.sporting_profile.potential_provenance,
            development_timing=b.sporting_profile.development_timing,
            current_form=policy.default_form,
            long_term_form_norm=policy.default_form_norm,
            match_sharpness=policy.default_match_sharpness,
            long_term_fatigue=policy.default_fatigue,
            health_state="unsupported",
        )
        for b in event.births
    )
    return tuple(sorted((*checkpoint.players, *newborns), key=lambda p: p.player_id))
