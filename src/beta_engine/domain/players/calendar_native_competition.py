"""Post-admission competition ledger; immutable v11 is its actual historical root.

No replacement World is constructed. Match inputs use the live sporting roster,
Signed lifecycle identities and Health. Unavailable legacy-only biography is
explicitly absent/unspecified rather than copied from another player.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Literal

from pydantic import model_validator

from beta_engine.core import DeterministicRng
from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot,
    project_player_health,
)
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext
from beta_engine.domain.players.calendar_canonical_match import canonical_participant
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
    continuation_anchor,
    continuation_effects,
)
from beta_engine.domain.players.calendar_followup_knockout import (
    ROUNDS,
    ROUNDS_EIGHT,
    CalendarFollowupKnockout,
)
from beta_engine.domain.players.calendar_followup_points import (
    CalendarFollowupEightPointPolicy,
    CalendarFollowupPointPolicy,
    derive_followup_awards,
)
from beta_engine.domain.players.calendar_match_state import CalendarMatchStatePolicy
from beta_engine.domain.players.calendar_native_sporting_checkpoint import (
    CalendarNativeSportingCheckpoint,
    CalendarNativeSportingWeek,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import (
    CanonicalMatchInputProjectionPolicy,
    project_player,
)


class CalendarNativeCompetitionCheckpoint(FrozenInput):
    schema_version: Literal["calendar_sporting_checkpoint.v12"] = (
        "calendar_sporting_checkpoint.v12"
    )
    run_id: str
    branch_id: str
    competition_root: CalendarNativeSportingCheckpoint
    events: tuple[CalendarNativeSportingWeek | CalendarFollowupKnockout, ...] = ()

    @model_validator(mode="after")
    def identity(self):
        if (self.run_id, self.branch_id) != (
            self.competition_root.run_id,
            self.competition_root.branch_id,
        ):
            raise ValueError("Native competition has a foreign historical root")
        return self

    @property
    def week(self):
        return (
            self.events[-1].advance.target_week
            if self.events and isinstance(self.events[-1], CalendarNativeSportingWeek)
            else self.events[-1].week
            if self.events
            else self.competition_root.week
        )

    @property
    def players(self):
        players = self.competition_root.players
        for event in self.events:
            players = (
                event.advance.target_players
                if isinstance(event, CalendarNativeSportingWeek)
                else terminal_players(players, event.matches)
            )
        return players

    @property
    def fingerprint(self):
        return canonical_hash(self.model_dump(mode="json"))

    @property
    def source_checkpoint(self):
        return self.competition_root.source_checkpoint

    @property
    def tournaments(self):
        return self.competition_root.tournaments + tuple(
            e for e in self.events if isinstance(e, CalendarFollowupKnockout)
        )

    @property
    def played_continuations(self):
        return self.competition_root.played_continuations + tuple(
            m
            for e in self.events
            if isinstance(e, CalendarFollowupKnockout)
            for m in e.matches
        )

    @property
    def weekly_advances(self):
        return self.source_checkpoint.weekly_advances

    @property
    def week_events(self):
        return self.source_checkpoint.week_events + tuple(
            e for e in self.events if isinstance(e, CalendarFollowupKnockout)
        )

    @property
    def continuations(self):
        return self.source_checkpoint.continuations

    @property
    def closures(self):
        return self.source_checkpoint.closures

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


def competition_checkpoint(checkpoint):
    if isinstance(checkpoint, CalendarNativeCompetitionCheckpoint):
        return checkpoint
    return CalendarNativeCompetitionCheckpoint(
        run_id=checkpoint.run_id,
        branch_id=checkpoint.branch_id,
        competition_root=checkpoint,
    )


def terminal_players(players, matches):
    for match in matches:
        effects = {e.player_id: e for e in match.effects}
        # Effects carry before/after state; use the same terminal state fields
        # generated by advance_played_slot (never derive from winner labels).
        players = tuple(
            p.model_copy(
                update={
                    "current_form": effects[p.player_id].form_after,
                    "match_sharpness": effects[p.player_id].sharpness_after,
                    "long_term_fatigue": effects[p.player_id].fatigue_after,
                }
            )
            if p.player_id in effects
            else p
            for p in players
        )
    return players


def native_projections(checkpoint, world, lifecycle, source, ids):
    records = {p.player_id: p for p in checkpoint.players}
    identities = {p.player_id: p for p in lifecycle.players}
    originals = {p.player_id: p for p in world.players}
    prospects = {p["prospect_id"]: p for p in source.records}
    if (
        len(set(ids)) != 2
        or not set(ids) <= records.keys()
        or not set(ids) <= identities.keys()
    ):
        raise ValueError("Match participants are not admitted to this population")
    projections = []
    for pid in ids:
        identity = identities[pid]
        if identity.status == "retired":
            raise ValueError("Retired player cannot play")
        original = originals.get(pid)
        # Legacy career metadata is neither generated nor simulated for a native
        # prospect. None and "unspecified" keep it absent at the DTO boundary.
        projections.append(
            project_player(
                records[pid],
                source_sporting_fingerprint=checkpoint.fingerprint,
                policy=CanonicalMatchInputProjectionPolicy(),
                profile_source_fingerprint=identity.source_generation_fingerprint,
                profile_provenance="Signed native lifecycle and current 57-attribute competition checkpoint; legacy-only metadata absent for prospects",
                age=identity.age,
                name=original.name
                if original
                else prospects[pid].get("display_name") or pid,
                nationality=original.nationality
                if original
                else prospects[pid]["country_code"],
                play_style=original.play_style if original else "unspecified",
                archetype=original.archetype if original else "unspecified",
                hidden_career_traits=original.hidden_career_traits
                if original
                else None,
            )
        )
    return tuple(projections)


def native_match_slot(authority, index):
    """The Edition's play slots, with one common frozen snapshot per round."""
    eight = authority.edition.main_entrant_count == 8
    round_index = (
        (0 if index < 4 else 1 if index < 6 else 2)
        if eight
        else (0 if index < 2 else 1)
    )
    return authority.edition.start_slot + 3 + round_index


def play_native_tournament(
    *,
    checkpoint,
    world,
    lifecycle,
    health,
    source,
    clock,
    authority,
    command,
    knockout=None,
):
    """One real MatchEngine bracket, same pre-round inputs for simultaneous matches."""
    initial = checkpoint
    cp = competition_checkpoint(checkpoint)
    ids = tuple(s.player_id for s in authority.draw.main.slots)
    rounds = ROUNDS_EIGHT if len(ids) == 8 else ROUNDS
    reserved_matches = {m.match_id for m in checkpoint.played_continuations}
    reserved_commands = {m.command_id for m in checkpoint.played_continuations}
    reserved_commands.update(t.command_id for t in checkpoint.tournaments)
    if knockout is not None:
        reserved_matches.update(m.input_context.match_id for m in knockout.matches)
        reserved_matches.add(knockout.match_id)
        reserved_commands.add(knockout.command_id)
    if (
        command.command_id in reserved_commands
        or authority.edition.edition_id
        in {t.tournament_id for t in checkpoint.tournaments}
        or any(
            f"{authority.edition.edition_id}:{suffix}" in reserved_matches
            or f"{command.command_id}:{suffix}" in reserved_commands
            for suffix in rounds
        )
    ):
        raise ValueError(
            "Native competition identity collides with existing played history"
        )
    eight = len(ids) == 8
    policy = (
        CalendarFollowupEightPointPolicy if eight else CalendarFollowupPointPolicy
    )(
        category_label=authority.edition.edition_id,
        validity_weeks=authority.edition.validity_weeks,
        **authority.edition.point_table,
    )
    inner_command = {
        "command_id": command.command_id,
        "tournament_id": authority.edition.edition_id,
        "expected_saved_head": command.expected_saved_head,
        "expected_checkpoint_fingerprint": checkpoint.fingerprint,
        "entrant_ids": list(ids),
        "seed": command.seed,
        "operator_label": command.operator_label,
        "audit_reason": command.audit_reason,
        "point_policy": policy.model_dump(mode="json"),
        "explicit_point_confirmation": True,
    }
    request_fp = canonical_hash(
        {
            "run_id": cp.run_id,
            "branch_id": cp.branch_id,
            "command": inner_command,
            "edition_authority_fingerprint": authority.execution_fingerprint,
        }
    )
    results = []
    prior_players = cp.players
    for index, suffix in enumerate(ROUNDS_EIGHT if eight else ROUNDS):
        # Players in a round are disjoint. Freeze the entire pre-round owner,
        # including its fingerprint; commit effects only at the round boundary.
        start, stop = (
            ((0, 4) if index < 4 else (4, 6) if index < 6 else (6, 7))
            if eight
            else ((0, 2) if index < 2 else (2, 3))
        )
        if index == start:
            baseline = SimpleNamespace(
                players=prior_players,
                fingerprint=canonical_hash(
                    {
                        "checkpoint": initial.fingerprint,
                        "round": start,
                        "slot": native_match_slot(authority, index),
                        "edition_authority_fingerprint": authority.execution_fingerprint,
                        "players": [p.model_dump(mode="json") for p in prior_players],
                    }
                ),
            )
        participants = (
            ids[2 * index : 2 * index + 2]
            if index < (4 if eight else 2)
            else tuple(
                results[i].result.winner_player_id
                for i in (
                    range((index - 4) * 2, (index - 4) * 2 + 2)
                    if eight and index < 6
                    else (4, 5)
                    if eight
                    else (0, 1)
                )
            )
        )
        projections = native_projections(
            baseline, world, lifecycle, source, participants
        )
        match_id = f"{authority.edition.edition_id}:{suffix}"
        ctx = MatchContext(
            match_id=match_id,
            player_a=canonical_participant(projections[0]),
            player_b=canonical_participant(projections[1]),
            best_of=5,
            games_to=11,
            win_by=2,
        )
        profiles = {p.player_id: p for p in health.players}
        medical = EffectiveMatchHealthSnapshot(
            player_profiles=tuple(
                project_player_health(profiles[pid]) for pid in participants
            )
        )
        if any(p.numeric_calibration_required for p in medical.player_profiles):
            raise ValueError("Numeric Health effects remain unsupported")
        nested = SimpleNamespace(
            command_id=f"{command.command_id}:{suffix}",
            match_id=match_id,
            expected_saved_head=command.expected_saved_head,
            expected_checkpoint_fingerprint=baseline.fingerprint,
            player_a_id=participants[0],
            player_b_id=participants[1],
            seed=command.seed + index,
            operator_label=command.operator_label,
            audit_reason=command.audit_reason,
        )
        inputs = {
            "schema_version": "calendar_continuation_match.v2",
            "run_id": cp.run_id,
            "branch_id": cp.branch_id,
            "week": lifecycle.week,
            "sequence": len(initial.played_continuations) + index + 1,
            "command_id": nested.command_id,
            "match_id": match_id,
            "source_saved_head": command.expected_saved_head,
            "source_checkpoint_fingerprint": baseline.fingerprint,
            "seed": nested.seed,
            "operator_label": command.operator_label,
            "audit_reason": command.audit_reason,
            "request_fingerprint": canonical_hash(
                {
                    "run_id": cp.run_id,
                    "branch_id": cp.branch_id,
                    "command": vars(nested),
                }
            ),
            "input_context": ctx,
            "canonical_projections": projections,
            "projection_policy": CanonicalMatchInputProjectionPolicy(),
            "state_policy": CalendarMatchStatePolicy(),
            "source_health_fingerprint": health.fingerprint,
            "effective_health": medical,
        }
        anchor = continuation_anchor(SimpleNamespace(**inputs))
        result = MatchEngine(DeterministicRng(nested.seed)).simulate(
            ctx, log_anchor_hash=anchor, effective_match_health=medical
        )
        _, effects = continuation_effects(baseline, ctx, result, inputs["state_policy"])
        results.append(
            CalendarContinuationMatch(
                **inputs, result=result, effects=effects, log_anchor_hash=anchor
            )
        )
        if index + 1 == stop:
            prior_players = terminal_players(prior_players, results[start:stop])
    event = CalendarFollowupKnockout.model_construct(
        schema_version="calendar_followup_knockout.v6",
        run_id=cp.run_id,
        branch_id=cp.branch_id,
        tournament_id=authority.edition.edition_id,
        command_id=command.command_id,
        source_saved_head=command.expected_saved_head,
        source_checkpoint_fingerprint=initial.fingerprint,
        week=lifecycle.week,
        seed=command.seed,
        entrant_ids=ids,
        operator_label=command.operator_label,
        audit_reason=command.audit_reason,
        request_fingerprint=request_fp,
        matches=tuple(results),
        prepared_policy=policy,
        edition_authority_fingerprint=authority.execution_fingerprint,
        scope="configured_tour_knockout",
    )
    event = CalendarFollowupKnockout.model_validate_json(
        event.model_copy(
            update={"prepared_awards": derive_followup_awards(event)}
        ).model_dump_json()
    )
    successor = cp.model_copy(update={"events": cp.events + (event,)})
    return event, successor
