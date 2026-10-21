"""Independent same-week sporting continuation over an unchanged native past.

New matches consume the fork's current 57-attribute state and original factual
biography/Health sources. They never rewrite original events or award Tour points,
advance time, heal injuries or bootstrap neutral player values.
"""

from types import SimpleNamespace
from typing import Literal

from pydantic import Field, model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot,
    project_player_health,
)
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext
from beta_engine.domain.native_fork_baseline import NativeForkBaseline
from beta_engine.domain.players.calendar_canonical_match import canonical_participant
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
    continuation_anchor,
    continuation_effects,
)
from beta_engine.domain.players.calendar_match_state import CalendarMatchStatePolicy
from beta_engine.domain.players.calendar_native_competition import (
    native_projections,
    terminal_players,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import CanonicalMatchInputProjectionPolicy


class NativeForkSportingStep(FrozenInput):
    draft_version_before: int = Field(ge=0)
    match: CalendarContinuationMatch


class NativeForkSportingCheckpoint(FrozenInput):
    schema_version: Literal["native_fork_sporting.v1"] = "native_fork_sporting.v1"
    root_saved_revision_id: str = Field(min_length=1, max_length=128)
    baseline: NativeForkBaseline
    steps: tuple[NativeForkSportingStep, ...] = ()

    @property
    def run_id(self):
        return self.baseline.run_id

    @property
    def branch_id(self):
        return self.baseline.branch_id

    @property
    def week(self):
        return self.baseline.week

    @property
    def players(self):
        return terminal_players(
            self.baseline.sporting_players, tuple(s.match for s in self.steps)
        )

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def coherent_new_history(self):
        commands, matches = set(), set()
        for i, step in enumerate(self.steps):
            event = step.match
            prefix = self.model_copy(update={"steps": self.steps[:i]})
            if (
                (event.run_id, event.branch_id) != (self.run_id, self.branch_id)
                or event.schema_version != "calendar_continuation_match.v2"
                or event.week != self.week
                or event.sequence != i + 1
                or event.source_saved_head != self.root_saved_revision_id
                or event.source_checkpoint_fingerprint != prefix.fingerprint
                or event.source_health_fingerprint
                != self.baseline.source_health_fingerprint
                or event.command_id in commands
                or event.match_id in matches
                or (
                    i
                    and step.draft_version_before
                    != self.steps[i - 1].draft_version_before + 1
                )
            ):
                raise ValueError(
                    "Native fork sporting event has a foreign or discontinuous predecessor"
                )
            if any(
                p.source_sporting_fingerprint != prefix.fingerprint
                for p in event.canonical_projections
            ):
                raise ValueError(
                    "Native fork match does not consume its current sporting population"
                )
            _, effects = continuation_effects(
                prefix, event.input_context, event.result, event.state_policy
            )
            if effects != event.effects:
                raise ValueError(
                    "Native fork sporting effects differ from played evidence"
                )
            commands.add(event.command_id)
            matches.add(event.match_id)
        return self


def play_native_fork_match(checkpoint, command, *, draft_version, world, prospects):
    """Pure real MatchEngine execution; the caller authenticates actual DB sources."""
    if (
        command.expected_saved_head != checkpoint.root_saved_revision_id
        or command.expected_checkpoint_fingerprint != checkpoint.fingerprint
    ):
        raise ValueError("Native fork match command has a stale or foreign predecessor")
    if (world.run_id, world.branch_id) != (
        checkpoint.run_id,
        checkpoint.baseline.source_binding.source.branch_id,
    ) or world.fingerprint != checkpoint.baseline.source_initial_world_fingerprint:
        raise ValueError(
            "Native fork biography source differs from its original authority"
        )
    if any(
        command.command_id == s.match.command_id or command.match_id == s.match.match_id
        for s in checkpoint.steps
    ):
        raise ValueError("Native fork match or command identifier is already in use")
    if (
        checkpoint.steps
        and draft_version != checkpoint.steps[-1].draft_version_before + 1
    ):
        raise ValueError("Native fork match has a discontinuous Working Draft version")
    ids = (command.player_a_id, command.player_b_id)
    try:
        projections = native_projections(
            checkpoint,
            world,
            SimpleNamespace(players=checkpoint.baseline.lifecycle_players),
            prospects if prospects is not None else SimpleNamespace(records=()),
            ids,
        )
    except KeyError as exc:
        raise ValueError(
            "Native fork match lacks an actual original player biography"
        ) from exc
    profiles = {p.player_id: p for p in checkpoint.baseline.health_players}
    medical = EffectiveMatchHealthSnapshot(
        player_profiles=tuple(project_player_health(profiles[pid]) for pid in ids)
    )
    if any(p.numeric_calibration_required for p in medical.player_profiles):
        raise ValueError("Numeric Health effects remain unsupported")
    context = MatchContext(
        match_id=command.match_id,
        player_a=canonical_participant(projections[0]),
        player_b=canonical_participant(projections[1]),
        best_of=5,
        games_to=11,
        win_by=2,
    )
    inputs = {
        "schema_version": "calendar_continuation_match.v2",
        "run_id": checkpoint.run_id,
        "branch_id": checkpoint.branch_id,
        "week": checkpoint.week,
        "sequence": len(checkpoint.steps) + 1,
        "command_id": command.command_id,
        "match_id": command.match_id,
        "source_saved_head": command.expected_saved_head,
        "source_checkpoint_fingerprint": checkpoint.fingerprint,
        "seed": command.seed,
        "operator_label": command.operator_label,
        "audit_reason": command.audit_reason,
        "request_fingerprint": canonical_hash(
            {
                "run_id": checkpoint.run_id,
                "branch_id": checkpoint.branch_id,
                "command": command.model_dump(mode="json"),
            }
        ),
        "input_context": context,
        "canonical_projections": projections,
        "projection_policy": CanonicalMatchInputProjectionPolicy(),
        "state_policy": CalendarMatchStatePolicy(),
        "source_health_fingerprint": checkpoint.baseline.source_health_fingerprint,
        "effective_health": medical,
    }
    anchor = continuation_anchor(SimpleNamespace(**inputs))
    result = MatchEngine(DeterministicRng(command.seed)).simulate(
        context,
        log_anchor_hash=anchor,
        effective_match_health=medical,
    )
    _, effects = continuation_effects(
        checkpoint, context, result, inputs["state_policy"]
    )
    match = CalendarContinuationMatch(
        **inputs, result=result, effects=effects, log_anchor_hash=anchor
    )
    return NativeForkSportingCheckpoint(
        root_saved_revision_id=checkpoint.root_saved_revision_id,
        baseline=checkpoint.baseline,
        steps=(
            *checkpoint.steps,
            NativeForkSportingStep(draft_version_before=draft_version, match=match),
        ),
    )


def verify_native_fork_sporting(checkpoint, *, world, prospects, command_factory):
    """Replay every new event against actual source facts, not its own projections."""
    expected = NativeForkSportingCheckpoint(
        root_saved_revision_id=checkpoint.root_saved_revision_id,
        baseline=checkpoint.baseline,
    )
    for step in checkpoint.steps:
        event = step.match
        expected = play_native_fork_match(
            expected,
            command_factory(
                command_id=event.command_id,
                match_id=event.match_id,
                expected_saved_head=event.source_saved_head,
                expected_checkpoint_fingerprint=event.source_checkpoint_fingerprint,
                player_a_id=event.input_context.player_a.player.player_id,
                player_b_id=event.input_context.player_b.player.player_id,
                seed=event.seed,
                operator_label=event.operator_label,
                audit_reason=event.audit_reason,
            ),
            draft_version=step.draft_version_before,
            world=world,
            prospects=prospects,
        )
        if expected.steps[-1] != step:
            raise ValueError(
                "Native fork sporting history differs from actual MatchEngine replay"
            )
    if expected != checkpoint:
        raise ValueError("Native fork sporting checkpoint differs from actual replay")
    return checkpoint
