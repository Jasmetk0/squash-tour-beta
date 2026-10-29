"""Explicit current-fact fork roots, never reassigned original historical events."""

from typing import Literal

from pydantic import Field, model_serializer, model_validator

from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.native_fork_baseline import NativeForkBaseline
from beta_engine.domain.players.calendar_followup_knockout import (
    CalendarFollowupKnockout,
)
from beta_engine.domain.players.calendar_health import (
    CalendarHealthEditEvidence,
    CalendarHealthOrigin,
    CalendarHealthProfile,
)
from beta_engine.domain.players.calendar_lifecycle import (
    CalendarTourLifecycleIdentity,
    CalendarTourLifecycleState,
)
from beta_engine.domain.players.calendar_native_competition import terminal_players
from beta_engine.domain.players.calendar_native_health_transition import (
    CalendarNativeHealthTransitionState,
)
from beta_engine.domain.players.calendar_native_sporting_intake import (
    CalendarNativeSportingBirthAdvance,
)
from beta_engine.domain.players.calendar_prospect_birth import (
    CalendarTourLifecycleIntakeState,
)
from beta_engine.domain.players.lifecycle import PlayerLifecyclePolicy
from beta_engine.domain.players.sporting import PlayerSportingRecord
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.calendar_global_slots import (
    GlobalSlot,
    completed_tournaments,
)
from beta_engine.domain.tournaments.calendar_tour import CalendarTourState


class ForkLifecycleRoot(FrozenInput):
    schema_version: Literal["native_fork_lifecycle_root.v1"] = (
        "native_fork_lifecycle_root.v1"
    )
    run_id: str
    branch_id: str
    week: RunWeekPosition
    players: tuple[CalendarTourLifecycleIdentity, ...]
    policy: PlayerLifecyclePolicy
    source_initial_world_fingerprint: str
    source_baseline_fingerprint: str
    source_lifecycle_fingerprint: str

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


class ForkHealthRoot(FrozenInput):
    schema_version: Literal["native_fork_health_root.v1"] = "native_fork_health_root.v1"
    run_id: str
    branch_id: str
    week: RunWeekPosition
    source_health_week: RunWeekPosition
    players: tuple[CalendarHealthProfile, ...]
    source_initial_world_fingerprint: str
    source_baseline_fingerprint: str
    source_health_fingerprint: str
    origin: CalendarHealthOrigin
    admin_edits: tuple[CalendarHealthEditEvidence, ...] = ()

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))


class ForkTourState(CalendarTourState):
    schema_version: Literal["native_fork_tour.v1"] = "native_fork_tour.v1"
    source_tour_fingerprint: str
    inherited_transition_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_state(self):
        if (
            not self.rankings
            or not self.policies
            or len(self.rankings)
            != len(self.transitions) - self.inherited_transition_count + 1
        ):
            raise ValueError("Fork Tour ranking/transition suffix differs")
        if any(
            (r.run_id, r.branch_id) != (self.run_id, self.branch_id)
            for r in self.rankings
        ):
            raise ValueError("Fork current ranking has a foreign owner")
        if len({a.edition.edition_id for a in self.editions}) != len(
            self.editions
        ) or len({r.command_id for r in self.receipts}) != len(self.receipts):
            raise ValueError("Fork Tour has duplicate Edition or command IDs")
        return self


class ForkRuntimeCommand(FrozenInput):
    draft_version_before: int = Field(ge=0)
    request: dict
    result: dict




class NativeForkRuntime(FrozenInput):
    schema_version: Literal["native_fork_runtime.v1", "native_fork_runtime.v2"] = "native_fork_runtime.v1"
    baseline: NativeForkBaseline
    root_saved_revision_id: str = Field(min_length=1, max_length=128)
    players: tuple[PlayerSportingRecord, ...]
    lifecycle: (
        ForkLifecycleRoot
        | CalendarTourLifecycleIntakeState
        | CalendarTourLifecycleState
    )
    health: ForkHealthRoot | CalendarNativeHealthTransitionState
    tour: ForkTourState
    tournaments: tuple[CalendarFollowupKnockout, ...] = ()
    advances: tuple[CalendarNativeSportingBirthAdvance, ...] = ()
    journal: tuple[ForkRuntimeCommand, ...] = ()
    global_slots: tuple[GlobalSlot, ...] = ()

    @model_serializer(mode="wrap")
    def historical_shape(self, handler):
        value = handler(self)
        if not self.global_slots:
            value.pop("global_slots", None)
        return value

    @property
    def run_id(self):
        return self.baseline.run_id

    @property
    def branch_id(self):
        return self.baseline.branch_id

    @property
    def week(self):
        return self.lifecycle.week

    @property
    def checkpoint_fingerprint(self):
        return canonical_hash(
            {
                "schema_version": "native_fork_competition.v1",
                "baseline": self.baseline.fingerprint,
                "root": self.root_saved_revision_id,
                "players": [p.model_dump(mode="json") for p in self.players],
                "lifecycle": self.lifecycle.fingerprint,
                "health": self.health.fingerprint,
                "tournaments": [t.fingerprint for t in self.tournaments],
                "advances": [a.fingerprint for a in self.advances],
                **({"global_slots": [s.fingerprint for s in self.global_slots]} if self.global_slots else {}),
            }
        )

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def coherent_current_authorities(self):
        if bool(self.global_slots) != (self.schema_version == "native_fork_runtime.v2"):
            raise ValueError("Global fork slots require the explicit runtime v2 contract")
        if any(
            (a.run_id, a.branch_id) != (self.run_id, self.branch_id)
            or a.week != self.week
            for a in (self.lifecycle, self.health, self.tour)
        ):
            raise ValueError("Fork current owners/clocks differ")
        ids = tuple(p.player_id for p in self.players)
        if (
            not ids
            or ids != tuple(sorted(set(ids)))
            or any(
                tuple(p.player_id for p in a.players) != ids
                for a in (self.lifecycle, self.health)
            )
        ):
            raise ValueError("Fork current populations differ")
        if (
            self.tour.checkpoint_fingerprint != self.checkpoint_fingerprint
            or self.tour.lifecycle_fingerprint != self.lifecycle.fingerprint
        ):
            raise ValueError("Fork Tour is detached from current authorities")
        return self


class ForkCompetitionView:
    """Read/operation view over unchanged source events and new target evidence."""

    schema_version = "native_fork_competition.v1"

    def __init__(self, runtime, original, events=()):
        self.runtime, self.original, self.events = runtime, original, events

    @property
    def run_id(self):
        return self.runtime.run_id

    @property
    def branch_id(self):
        return self.runtime.branch_id

    @property
    def week(self):
        return self.runtime.week

    @property
    def players(self):
        return terminal_players(
            self.runtime.players, tuple(m for e in self.events for m in e.matches)
        )

    @property
    def fingerprint(self):
        return self.runtime.model_copy(
            update={
                "players": self.players,
                "tournaments": self.runtime.tournaments + self.events,
            }
        ).checkpoint_fingerprint

    @property
    def bootstrap_policy(self):
        return self.original.bootstrap_policy

    @property
    def source_initial_world_fingerprint(self):
        return self.runtime.baseline.source_initial_world_fingerprint

    @property
    def tournaments(self):
        old = self.original.tournaments + self.runtime.tournaments + self.events
        known = {t.tournament_id for t in old}
        return old + tuple(t for t in completed_tournaments(self.history_global_slots, owner=self.branch_id) if t.tournament_id not in known)

    @property
    def played_continuations(self):
        return self.original.played_continuations + tuple(
            m for e in self.runtime.tournaments + self.events for m in e.matches
        ) + tuple(m for s in self.runtime.global_slots for m in s.accepted)

    @property
    def week_events(self):
        return self.original.week_events + self.runtime.tournaments + self.events

    @property
    def continuations(self):
        return self.original.continuations

    @property
    def closures(self):
        return self.original.closures

    def model_copy(self, *, update):
        if set(update) != {"events"}:
            raise ValueError("Unsupported fork sporting view update")
        return ForkCompetitionView(self.runtime, self.original, update["events"])


    @property
    def global_slots(self):
        return self.runtime.global_slots

    @property
    def history_global_slots(self):
        return tuple(getattr(self.original, "history_global_slots", getattr(self.original, "events", ()))) + self.runtime.global_slots

    def with_global_slot(self, slot):
        previous = self.runtime.global_slots
        replacing = bool(previous and previous[-1].number == slot.number and previous[-1].week == slot.week)
        old_ids = {m.match_id for m in previous[-1].accepted} if replacing else set()
        players = terminal_players(self.runtime.players, tuple(m for m in slot.accepted if m.match_id not in old_ids))
        runtime = self.runtime.model_copy(update={"schema_version": "native_fork_runtime.v2", "global_slots": (*previous[:-1], slot) if replacing else (*previous, slot), "players": players})
        return ForkCompetitionView(runtime, self.original)

    def with_group_tie_decision(self, index, slot):
        """Update owned administrative evidence without reaccepting old matches."""
        previous = self.runtime.global_slots
        if not 0 <= index < len(previous):
            raise ValueError("Group tie slot is not owned by this fork")
        old = previous[index]
        if (slot.model_copy(update={"group_tie_decisions": old.group_tie_decisions}) != old
            or slot.group_tie_decisions[:-1] != old.group_tie_decisions
            or len(slot.group_tie_decisions) != len(old.group_tie_decisions) + 1):
            raise ValueError("Group tie update must only append one administrative decision")
        runtime = self.runtime.model_copy(update={
            "global_slots": (*previous[:index], slot, *previous[index + 1:]),
        })
        return ForkCompetitionView(runtime, self.original)

    def with_group_withdrawal(self, index, slot):
        previous = self.runtime.global_slots
        if not 0 <= index < len(previous):
            raise ValueError('Withdrawal slot is not owned by this fork')
        old = previous[index]
        if (slot.model_copy(update={'schema_version': old.schema_version,
                'group_withdrawals': old.group_withdrawals}) != old
            or slot.group_withdrawals[:-1] != old.group_withdrawals
            or len(slot.group_withdrawals) != len(old.group_withdrawals) + 1):
            raise ValueError('Withdrawal must only append one administrative record')
        runtime = self.runtime.model_copy(update={'global_slots': (
            *previous[:index], slot, *previous[index+1:])})
        return ForkCompetitionView(runtime, self.original)
