"""Durable native birth ledger, preserving the exact historical v1-v10 owner.

v11 composes an unchanged authenticated checkpoint with complete native weekly
stages. Decoding is not authority: Saved loading must replay every stage against
the actual Signed lifecycle, prospect source, Health and effective Tour policy.
"""
from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from beta_engine.domain.players.calendar_native_sporting_intake import (
    CalendarNativeSportingBirthAdvance, project_native_sporting_birth_advance,
)
from beta_engine.domain.players.calendar_prospect_birth import build_calendar_prospect_birth_event
from beta_engine.domain.players.calendar_sporting_checkpoint import CalendarSportingCheckpoint
from beta_engine.domain.players.calendar_sporting_week import played_counts
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash


class CalendarNativeSportingWeek(FrozenInput):
    schema_version: Literal["calendar_native_sporting_week.v1"] = "calendar_native_sporting_week.v1"
    advance: CalendarNativeSportingBirthAdvance
    lifecycle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    health_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    health_history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class CalendarNativeSportingCheckpoint(FrozenInput):
    schema_version: Literal["calendar_sporting_checkpoint.v11"] = "calendar_sporting_checkpoint.v11"
    run_id: str = Field(min_length=1)
    branch_id: str = Field(min_length=1)
    source_checkpoint: CalendarSportingCheckpoint
    native_weeks: tuple[CalendarNativeSportingWeek, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_native_chain(self):
        root = self.source_checkpoint
        if (self.run_id, self.branch_id) != (root.run_id, root.branch_id):
            raise ValueError("Native checkpoint has a foreign historical owner")
        if not self.native_weeks[0].advance.source_birth_event.births:
            raise ValueError("Checkpoint v11 requires a genuine first birthday admission")
        body = self.model_dump(mode="json")
        previous_hash, previous_week, previous_players = root.fingerprint, root.week, root.players
        previous_life = None
        for index, entry in enumerate(self.native_weeks):
            event = entry.advance
            if (
                (event.run_id, event.branch_id) != (self.run_id, self.branch_id)
                or event.source_checkpoint_fingerprint != previous_hash
                or event.completed_week != previous_week
                or event.completed_players != previous_players
                or (previous_life is not None and event.source_lifecycle_fingerprint != previous_life)
            ):
                raise ValueError("Native checkpoint weekly predecessor or population differs")
            previous_hash = canonical_hash({**body, "native_weeks": body["native_weeks"][:index+1]})
            previous_week, previous_players = event.target_week, event.target_players
            previous_life = entry.lifecycle_fingerprint
        return self

    @property
    def week(self):
        return self.native_weeks[-1].advance.target_week

    @property
    def players(self):
        return self.native_weeks[-1].advance.target_players

    @property
    def source_initial_world_fingerprint(self):
        return self.source_checkpoint.source_initial_world_fingerprint

    @property
    def source_knockout_fingerprint(self):
        return self.source_checkpoint.source_knockout_fingerprint

    @property
    def source_saved_head(self):
        return self.source_checkpoint.source_saved_head

    @property
    def bootstrap_policy(self):
        return self.source_checkpoint.bootstrap_policy

    @property
    def tournaments(self):
        return self.source_checkpoint.tournaments

    @property
    def week_events(self):
        return self.source_checkpoint.week_events

    @property
    def continuations(self):
        return self.source_checkpoint.continuations

    @property
    def closures(self):
        return self.source_checkpoint.closures

    @property
    def played_continuations(self):
        return self.source_checkpoint.played_continuations

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


def append_native_sporting_week(previous, advance, *, lifecycle_fingerprint,
                               health_fingerprint, health_history_fingerprint):
    if isinstance(previous, CalendarNativeSportingCheckpoint):
        root, history = previous.source_checkpoint, previous.native_weeks
    elif isinstance(previous, CalendarSportingCheckpoint):
        root, history = previous, ()
    else:
        raise ValueError("Native sporting ledger requires its actual checkpoint")
    entry = CalendarNativeSportingWeek(
        advance=advance, lifecycle_fingerprint=lifecycle_fingerprint,
        health_fingerprint=health_fingerprint,
        health_history_fingerprint=health_history_fingerprint,
    )
    return CalendarNativeSportingCheckpoint(
        run_id=previous.run_id, branch_id=previous.branch_id,
        source_checkpoint=root, native_weeks=(*history, entry),
    )


def verify_native_sporting_checkpoint(state, *, lifecycle, health, source,
                                      world_package_id, knockout, policy_for_week):
    """Replay an already authenticated root against complete Signed inputs.

    This version deliberately supports natural weekly evolution only after the
    first birth. It cannot invent post-birth matches. A future match writer must
    add actual played evidence before such a week can claim nonzero play counts.
    """
    if not lifecycle or not health or source is None:
        raise ValueError("Native checkpoint requires Signed lifecycle, Health and prospect source")
    if (
        len(lifecycle) != state.week.ordinal + 1
        or len(health) != len(lifecycle)
        or tuple(s.week.ordinal for s in lifecycle) != tuple(range(len(lifecycle)))
        or tuple(s.week.ordinal for s in health) != tuple(range(len(health)))
        or any((s.run_id, s.branch_id) != (state.run_id, state.branch_id)
               for s in (*lifecycle, *health))
    ):
        raise ValueError("Native checkpoint lacks its exact complete Signed week history")
    expected = state.source_checkpoint
    for entry in state.native_weeks:
        stored = entry.advance
        predecessor = lifecycle[expected.week.ordinal]
        target = lifecycle[stored.target_week.ordinal]
        target_health = health[stored.target_week.ordinal]
        if (
            predecessor.week != expected.week
            or predecessor.source_initial_world_fingerprint != expected.source_initial_world_fingerprint
            or target.week != stored.target_week
            or entry.lifecycle_fingerprint != target.fingerprint
            or entry.health_fingerprint != target_health.fingerprint
            or entry.health_history_fingerprint != canonical_hash([
                h.model_dump(mode="json") for h in health[:target.week.ordinal+1]
            ])
        ):
            raise ValueError("Native checkpoint differs from actual Signed lifecycle/Health")
        event = build_calendar_prospect_birth_event(
            predecessor=predecessor, target=stored.target_week, source=source,
            world_package_id=world_package_id,
        )
        if event.births and getattr(target, "birth_event", None) != event:
            raise ValueError("Native sporting birthday differs from actual Signed lifecycle")
        counts = (played_counts(expected, knockout)
                  if isinstance(expected, CalendarSportingCheckpoint)
                  else tuple((p.player_id, 0) for p in expected.players))
        rebuilt = project_native_sporting_birth_advance(
            checkpoint=expected, predecessor=predecessor, birth_event=event,
            seed=stored.seed, policy=policy_for_week(expected.week), played_counts=counts,
        )
        if rebuilt != stored:
            raise ValueError("Native sporting week differs from genuine source and completed-week development")
        expected = append_native_sporting_week(
            expected, rebuilt, lifecycle_fingerprint=target.fingerprint,
            health_fingerprint=target_health.fingerprint,
            health_history_fingerprint=entry.health_history_fingerprint,
        )
    if expected != state:
        raise ValueError("Native checkpoint differs from the replayed complete population")
