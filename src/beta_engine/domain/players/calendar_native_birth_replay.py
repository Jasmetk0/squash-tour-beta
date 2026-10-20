"""Pure adversarial replay of native 15yo births and authentic Tour first Entry.

Prepared for the future immutable Saved v4 replay gate. This is deliberately
not a Saved decoder or permission to activate prospect rows in native Tour.
Callers MUST authenticate the Run-prospect source/HEAD/World and Tour receipts
before invoking this verifier. Historical v2/v3 serialized bytes never change.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarPlayerLifecycleState,
    CalendarTourLifecycleState,
    advance_calendar_lifecycle,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarTourLifecycleIntakeState,
    advance_calendar_lifecycle_with_prospects,
    build_calendar_prospect_birth_event,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarNativeBirthReplayProof(FrozenInput):
    """One immutable proof of a strictly verified source/birthday/Entry chain."""

    schema_version: Literal["calendar_native_birth_replay_proof.v1"] = (
        "calendar_native_birth_replay_proof.v1"
    )
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    source_run_prospect_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_world_package_id: str = Field(min_length=1)
    source_initial_world_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    last_week: RunWeekPosition
    lifecycle_fingerprints: tuple[str, ...] = Field(min_length=1)
    # None means an untouched v3 native Week step with no birth event.
    birth_event_fingerprints: tuple[str | None, ...]
    submission_fingerprints: tuple[str, ...]
    admitted_player_ids: tuple[str, ...]

    @model_validator(mode="after")
    def verify_proof_structure(self):
        if len(self.birth_event_fingerprints) + 1 != len(self.lifecycle_fingerprints):
            raise ValueError("Native replay proof has incomplete weekly history")
        if self.last_week.ordinal + 1 != len(self.lifecycle_fingerprints):
            raise ValueError("Native replay proof does not cover each Run week")
        if any(
            len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
            for value in self.lifecycle_fingerprints
        ):
            raise ValueError("Native replay requires canonical lifecycle hashes")
        if any(
            value is not None and (
                len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
            )
            for value in self.birth_event_fingerprints
        ):
            raise ValueError("Native replay requires canonical birth-event hashes")
        if (
            self.submission_fingerprints != tuple(sorted(set(self.submission_fingerprints)))
            or self.admitted_player_ids != tuple(sorted(set(self.admitted_player_ids)))
        ):
            raise ValueError("Native replay requires canonical evidence and player identities")
        return self

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.model_dump(mode="json"))


def _compatible_calendar(previous: RunWeekPosition, target: RunWeekPosition) -> bool:
    old, new = previous.calendar, target.calendar
    return (
        old.weeks_per_year == new.weeks_per_year
        and old.season_start_year_week == new.season_start_year_week
        and old.start_year == new.start_year
        and old.season_count <= new.season_count
    )


def verify_calendar_native_birth_history(
    *,
    states: tuple[CalendarPlayerLifecycleState | CalendarTourLifecycleState | CalendarTourLifecycleIntakeState, ...],
    source,
    world_package_id: str,
    submissions=(),
) -> CalendarNativeBirthReplayProof:
    """Recalculate *each* lifecycle week from the signed candidate source.

    - All native W/O birthday events must be present exactly once.
    - 15yo arrivals remain unranked/unentered until real valid Tour application.
    - A submission by an unknown, not-yet-born or retired player is rejected.
    - An actual valid submission becomes Tour entry in the NEXT lifecycle week,
      not retroactively in the submitted week.
    - Historic v3 can coexist with later v4, but cannot omit a due birth.
    - Compatible, strict horizon extension retains all prior immutable hashes.

    This is intentionally a pure future-validator primitive. It does NOT
    validate SQLite/Saved bytes and cannot authorize persistence by itself.
    """
    if (
        not states
        or not isinstance(states[0], CalendarPlayerLifecycleState)
        or source is None
        or source.run_id != states[0].run_id
        or type(world_package_id) is not str
        or not world_package_id
    ):
        raise ValueError("Native replay requires an original calendar lifecycle and Signed Run source")
    first = states[0]
    if first.week.ordinal != 0 or len(states) != states[-1].week.ordinal + 1:
        raise ValueError("Native replay requires contiguous opening-to-current weekly states")
    if (
        type(source.fingerprint) is not str or len(source.fingerprint) != 64
        or any(c not in "0123456789abcdef" for c in source.fingerprint)
    ):
        raise ValueError("Native replay source fingerprint is not canonical")
    if any(
        (s.run_id, s.branch_id) != (first.run_id, first.branch_id)
        or s.source_initial_world_fingerprint != first.source_initial_world_fingerprint
        for s in states
    ):
        raise ValueError("Native replay contains a foreign Run/Branch or InitialWorld")

    # The entries belong to prior ACTUAL submissions, not to birth identity.
    first_by_id = {}
    seen_applications = set()
    for sub in submissions:
        if (
            sub.schema_version != "tournament_application_submission_authority.v2"
            or (sub.run_id, sub.branch_id) != (first.run_id, first.branch_id)
            or not isinstance(sub.submission_week, RunWeekPosition)
        ):
            raise ValueError("Native replay requires scoped, calendar-owned real Tour Entry evidence")
        if sub.submission_week.ordinal > states[-1].week.ordinal:
            raise ValueError("Native replay contains a future Tour Entry outside owned history")
        if sub.application_id in seen_applications:
            raise ValueError("Native replay has a duplicate Tour application identity")
        seen_applications.add(sub.application_id)
        if not _compatible_calendar(first.week, sub.submission_week):
            raise ValueError("Native replay Tour Entry has an incompatible Run clock")
        if sub.submission_week.ordinal < len(states):
            current_population = {p.player_id: p for p in states[sub.submission_week.ordinal].players}
            player = current_population.get(sub.player_id)
            if player is None or player.status != "active" or player.age < 15:
                raise ValueError("Native replay has Entry before birth or after retirement")
        previous = first_by_id.get(sub.player_id)
        if previous is None or sub.decision_position < previous.decision_position:
            first_by_id[sub.player_id] = sub

    tokens = tuple(s.nr_tie_break_token for s in first_by_id.values())
    if len(tokens) != len(set(tokens)):
        raise ValueError("Native replay has duplicate first Entry tie-break tokens")
    all_previous = states[0]
    birth_fingerprints = []
    admitted_ids: set[str] = set()
    for current in states[1:]:
        if (
            not isinstance(current, (CalendarTourLifecycleState, CalendarTourLifecycleIntakeState))
            or current.week.ordinal != all_previous.week.ordinal + 1
            or not _compatible_calendar(all_previous.week, current.week)
        ):
            raise ValueError("Native replay is not a consecutive compatible Run calendar")
        event = build_calendar_prospect_birth_event(
            predecessor=all_previous,
            target=current.week,
            source=source.for_week(current.week.ordinal),
            world_package_id=world_package_id,
        )
        if isinstance(current, CalendarTourLifecycleIntakeState):
            if current.birth_event != event:
                raise ValueError("Native replay birth event differs from the Signed source")
            expected = advance_calendar_lifecycle_with_prospects(
                all_previous, event, submissions,
            )
            birth_fingerprints.append(event.fingerprint)
            admitted_ids.update(b.player_id for b in event.births)
        else:
            if event.births:
                raise ValueError("Native replay legacy lifecycle silently omitted a 15yo birth")
            expected = advance_calendar_lifecycle(
                all_previous, current.week, submissions,
            )
            birth_fingerprints.append(None)
        if current != expected or current.predecessor_fingerprint != all_previous.fingerprint:
            raise ValueError("Native replay lifecycle differs from genuine birthdays or first Tour Entry")
        all_previous = current

    # Verify that signed entry receipts could not have been published before
    # their player existed, INCLUDING earlier v3 steps without birth events.
    for sub in submissions:
        if sub.submission_week.ordinal < len(states):
            sealed = next(
                (s for s in states
                 if s.week.ordinal == sub.submission_week.ordinal),
                None,
            )
            if sealed is None or sub.player_id not in {p.player_id for p in sealed.players}:
                raise ValueError("Native replay Tour Entry uses an unadmitted athlete")
    return CalendarNativeBirthReplayProof(
        run_id=first.run_id, branch_id=first.branch_id,
        # Proofs bind the v1 snapshot effective at their own last week. Later
        # append-only epochs must not change a previously confirmed receipt;
        # earlier snapshots remain bound by the replayed birth-event hashes.
        source_run_prospect_fingerprint=source.for_week(states[-1].week.ordinal).fingerprint,
        source_world_package_id=world_package_id,
        source_initial_world_fingerprint=first.source_initial_world_fingerprint,
        last_week=states[-1].week,
        lifecycle_fingerprints=tuple(s.fingerprint for s in states),
        birth_event_fingerprints=tuple(birth_fingerprints),
        submission_fingerprints=tuple(sorted(s.fingerprint for s in submissions)),
        admitted_player_ids=tuple(sorted(admitted_ids)),
    )
