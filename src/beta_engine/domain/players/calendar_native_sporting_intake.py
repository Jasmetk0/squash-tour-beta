"""Pure end-of-week W-aware sporting evolution with exact 15yo birth adoption.

The established sporting development kernel remains authoritative. Current-week
players develop/recover first; newborns join only at target-week opening, from
their authenticated birth profile. No Saved/SQLite writer, ranking authority,
Health healing, or unrestricted Tour activation is implied.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_prospect_admission_bundle import (
    CalendarProspectAdmissionBundle,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarProspectBirthEvent, project_native_birth_sporting_roster,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarAnnualDevelopmentPolicy, develop_and_recover, records_fingerprint,
)
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarNativeSportingBirthAdvance(FrozenInput):
    """Signed birth + genuine end-of-completed-week development projection."""

    schema_version: Literal["calendar_native_sporting_birth_advance.v1"] = (
        "calendar_native_sporting_birth_advance.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    source_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    completed_week: RunWeekPosition
    target_week: RunWeekPosition
    source_birth_event: CalendarProspectBirthEvent
    seed: int
    policy: CalendarAnnualDevelopmentPolicy
    played_counts: tuple[tuple[str, int], ...]
    completed_players: tuple[PlayerSportingRecord, ...]
    developed_players: tuple[PlayerSportingRecord, ...]
    recovered_players: tuple[PlayerSportingRecord, ...]
    target_players: tuple[PlayerSportingRecord, ...]

    @model_validator(mode="after")
    def verify_canonical_stages(self):
        birth = self.source_birth_event
        if (
            (birth.run_id, birth.branch_id) != (self.run_id, self.branch_id)
            or birth.predecessor_fingerprint != self.source_lifecycle_fingerprint
            or birth.target_week != self.target_week
            or self.target_week.ordinal != self.completed_week.ordinal + 1
            or (self.completed_week.calendar.weeks_per_year,
                self.completed_week.calendar.season_start_year_week,
                self.completed_week.calendar.start_year) != (
                self.target_week.calendar.weeks_per_year,
                self.target_week.calendar.season_start_year_week,
                self.target_week.calendar.start_year)
            or self.completed_week.calendar.season_count > self.target_week.calendar.season_count
        ):
            raise ValueError("Native sporting birth advance has foreign target or predecessor")
        if type(self.seed) is not int:
            raise ValueError("Native sporting advance seed must be integer")
        identities = []
        for records in (
            self.completed_players, self.developed_players,
            self.recovered_players, self.target_players,
        ):
            ids = tuple(row.player_id for row in records)
            if ids != tuple(sorted(set(ids))) or any(len(p.attributes) != 57 for p in records):
                raise ValueError("Native sporting advance requires canonical full-57 rosters")
            identities.append(ids)
        old_ids, developed_ids, recovered_ids, target_ids = identities
        if (
            not old_ids
            or developed_ids != old_ids or recovered_ids != old_ids
            or target_ids != tuple(sorted((*old_ids, *(b.player_id for b in birth.births))))
        ):
            raise ValueError("Native sporting birth advance has inconsistent weekly population")
        if (
            tuple(pid for pid, _ in self.played_counts) != old_ids
            or any(type(n) is not int or n < 0 for _, n in self.played_counts)
        ):
            raise ValueError("Native sporting birth advance has invalid completed-week play counts")
        target = {p.player_id: p for p in self.target_players}
        if any(target[p.player_id] != p for p in self.recovered_players):
            raise ValueError("Native sporting birth cannot change developed old players at admission")
        for b in birth.births:
            new = target[b.player_id]
            if (
                new.attributes != b.sporting_profile.attributes
                or new.potential_ovr != b.sporting_profile.potential_ovr
                or new.potential_identity != b.sporting_profile.potential_identity
                or new.potential_provenance != b.sporting_profile.potential_provenance
                or new.development_timing != b.sporting_profile.development_timing
            ):
                raise ValueError("Native sporting newborn does not match exact 57-attribute birth source")
        return self

    @property
    def developed_players_fingerprint(self):
        return records_fingerprint(self.developed_players)

    @property
    def recovered_players_fingerprint(self):
        return records_fingerprint(self.recovered_players)

    @property
    def target_players_fingerprint(self):
        return records_fingerprint(self.target_players)

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def project_native_sporting_birth_advance(
    *, checkpoint, predecessor, birth_event: CalendarProspectBirthEvent,
    seed: int, policy: CalendarAnnualDevelopmentPolicy,
    played_counts: tuple[tuple[str, int], ...],
) -> CalendarNativeSportingBirthAdvance:
    """Reuse the *same* provisional W-aware sporting kernel as official Tour.

    The World-style age/policy inputs come from the authoritative current-week
    lifecycle, not the original static InitialWorld: newcomers from PREVIOUS
    weeks need development too, never skipped just because they were not in
    the initial population.

    played_counts must be independently proven against genuine completed-week
    match events by the eventual Signed Tour executor.
    """
    if (
        (checkpoint.run_id, checkpoint.branch_id) != (
            predecessor.run_id, predecessor.branch_id
        )
        or checkpoint.week != predecessor.week
        or checkpoint.source_initial_world_fingerprint
        != predecessor.source_initial_world_fingerprint
        or birth_event.predecessor_fingerprint != predecessor.fingerprint
        or (birth_event.run_id, birth_event.branch_id) != (
            predecessor.run_id, predecessor.branch_id
        )
        or birth_event.target_week.ordinal != checkpoint.week.ordinal + 1
    ):
        raise ValueError("Native sporting projection differs from its exact lifecycle/checkpoint")
    if type(seed) is not int or not isinstance(policy, CalendarAnnualDevelopmentPolicy):
        raise ValueError("Native sporting projection requires explicit official seed/policy")
    if (
        tuple(p.player_id for p in checkpoint.players)
        != tuple(p.player_id for p in predecessor.players)
    ):
        raise ValueError("Native sporting projection disagrees with current lifecycle roster")
    if (
        tuple(pid for pid, _ in played_counts)
        != tuple(p.player_id for p in checkpoint.players)
        or any(type(n) is not int or n < 0 for _, n in played_counts)
    ):
        raise ValueError("Native sporting projection requires actual completed-week counts")
    # Existing kernel needs ONLY .players (birth year/week) and .lifecycle_policy.
    # Do not change its historic algorithms, RNG namespace or W-dependent rate.
    calendar_world = SimpleNamespace(
        players=predecessor.players,
        lifecycle_policy=predecessor.policy,
    )
    developed, recovered = develop_and_recover(
        checkpoint, calendar_world,
        completed_week=checkpoint.week,
        seed=seed, policy=policy, counts=played_counts, official=True,
    )
    # Sporting birth projection uses the same 57-attribute/default bootstrap
    # already stage-authenticated by PR #1554, on top of this week's recovery.
    recovered_checkpoint = SimpleNamespace(
        run_id=checkpoint.run_id, branch_id=checkpoint.branch_id,
        week=checkpoint.week, players=recovered,
        bootstrap_policy=checkpoint.bootstrap_policy,
    )
    target_players = project_native_birth_sporting_roster(
        predecessor=predecessor, checkpoint=recovered_checkpoint,
        event=birth_event,
    )
    return CalendarNativeSportingBirthAdvance(
        run_id=checkpoint.run_id, branch_id=checkpoint.branch_id,
        source_checkpoint_fingerprint=checkpoint.fingerprint,
        source_lifecycle_fingerprint=predecessor.fingerprint,
        completed_week=checkpoint.week,
        target_week=birth_event.target_week, source_birth_event=birth_event,
        seed=seed, policy=policy, played_counts=played_counts,
        completed_players=checkpoint.players,
        developed_players=developed, recovered_players=recovered,
        target_players=target_players,
    )


class CalendarNativeAdmissionWeekProjection(FrozenInput):
    """One review hash binding Signed Health/lifecycle to actual weekly sport."""

    schema_version: Literal["calendar_native_admission_week_projection.v1"] = (
        "calendar_native_admission_week_projection.v1"
    )
    admission: CalendarProspectAdmissionBundle
    sporting_week: CalendarNativeSportingBirthAdvance
    signed_writer_supported: Literal[False] = False

    @model_validator(mode="after")
    def verify_common_birth_and_population(self):
        a, s = self.admission, self.sporting_week
        if (
            s.source_birth_event != a.event
            or s.source_checkpoint_fingerprint != a.source_checkpoint_fingerprint
            or s.source_lifecycle_fingerprint != a.event.predecessor_fingerprint
            or tuple(p.player_id for p in s.target_players)
            != tuple(p.player_id for p in a.lifecycle.players)
            or tuple(p.player_id for p in s.target_players)
            != tuple(p.player_id for p in a.health.proposed_profiles)
            or tuple(p.player_id for p in s.completed_players)
            != tuple(p.player_id for p in a.health.predecessor_profiles)
        ):
            raise ValueError("Native admission Week proposal disagrees with Signed birth/Health/sporting owners")
        old = {p.player_id: p for p in s.completed_players}
        baseline = {p.player_id: p for p in a.sporting}
        if any(baseline[pid] != row for pid, row in old.items()):
            raise ValueError("Native admission Week proposal has wrong original sporting population")
        newcomers = {b.player_id for b in a.event.births}
        target = {p.player_id: p for p in s.target_players}
        if any(target[pid] != baseline[pid] for pid in newcomers):
            raise ValueError("Native admission Week proposal changed newborn profile after birth")
        return self

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def combine_signed_admission_with_sporting_week(
    *, admission: CalendarProspectAdmissionBundle, checkpoint, predecessor,
    seed: int, policy: CalendarAnnualDevelopmentPolicy,
    played_counts: tuple[tuple[str, int], ...],
) -> CalendarNativeAdmissionWeekProjection:
    """Convert the existing Signed admission bundle into a full week projection."""
    if (
        admission.source_checkpoint_fingerprint != checkpoint.fingerprint
        or admission.event.predecessor_fingerprint != predecessor.fingerprint
    ):
        raise ValueError("Signed admission changed before sporting development review")
    sporting = project_native_sporting_birth_advance(
        checkpoint=checkpoint, predecessor=predecessor,
        birth_event=admission.event, seed=seed, policy=policy,
        played_counts=played_counts,
    )
    return CalendarNativeAdmissionWeekProjection(
        admission=admission, sporting_week=sporting,
    )
