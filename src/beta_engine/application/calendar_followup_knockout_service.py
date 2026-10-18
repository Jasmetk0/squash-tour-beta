"""Atomic 3-match later-week knockout from a genuine Saved sporting checkpoint.

Uses the existing MatchEngine and weekly owner, not a second player database.
An exact command retry reconstructs the original post-tournament fingerprint.
"""
from dataclasses import dataclass

from pydantic import Field, model_validator
from typing import Literal
from sqlalchemy import text

from beta_engine.application.calendar_continuation_service import (
    CalendarContinuationCommand,
    CalendarContinuationService,
    play_continuation_match,
)
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.players.calendar_continuation_match import append_continuation
from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
from beta_engine.domain.players.calendar_followup_points import (CalendarFollowupPointPolicy, CalendarFollowupEightPointPolicy, derive_followup_awards)
from beta_engine.domain.players.calendar_followup_knockout import (
    CalendarFollowupKnockout,
    ROUNDS, ROUNDS_EIGHT,
    append_followup_knockout,
)
from beta_engine.domain.players.calendar_sporting_checkpoint import (
    build_calendar_sporting_checkpoint,
)
from beta_engine.domain.players.calendar_sporting_week import (
    CalendarSportingWeekAdvance, append_sporting_week,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import replace_checkpoint


class CalendarFollowupKnockoutCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=120)
    tournament_id: str = Field(min_length=1, max_length=94)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entrant_ids: list[str] = Field(min_length=4, max_length=4)
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def distinct(self):
        if len(set(self.entrant_ids)) != 4 or any(not p.strip() for p in self.entrant_ids):
            raise ValueError("Later knockout requires four distinct nonempty entrant IDs")
        return self


class CalendarFollowupScoredCommand(CalendarFollowupKnockoutCommand):
    """Separate opted-in point command; v1 command fingerprint stays byte-compatible."""
    point_policy: CalendarFollowupPointPolicy
    explicit_point_confirmation: Literal[True]


class CalendarFollowupEightCommand(FrozenInput):
    """Seven real matches in a single eight-player, later-week knockout."""
    command_id: str = Field(min_length=1, max_length=120)
    tournament_id: str = Field(min_length=1, max_length=94)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    entrant_ids: list[str] = Field(min_length=8, max_length=8)
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def distinct(self):
        if len(set(self.entrant_ids)) != 8 or any(not p.strip() for p in self.entrant_ids):
            raise ValueError("Eight-player knockout requires eight distinct nonempty entrants")
        return self


class CalendarFollowupEightScoredCommand(CalendarFollowupEightCommand):
    """Reviewed eight-player scoring is a new operation, not a v3 retry."""
    point_policy: CalendarFollowupEightPointPolicy
    explicit_point_confirmation: Literal[True]


@dataclass(slots=True)
class CalendarFollowupKnockoutService:
    repository: object

    def _historical_successor(self, state, world, opening, event):
        prefix = build_calendar_sporting_checkpoint(world, opening, calendar_engine_player)
        for historical in (*state.continuations, *state.week_events):
            prefix = (
                append_sporting_week(prefix, world, opening, historical)
                if isinstance(historical, CalendarSportingWeekAdvance)
                else append_followup_knockout(prefix, world, historical)
                if isinstance(historical, CalendarFollowupKnockout)
                else append_continuation(prefix, world, historical)
            )
            if historical is event:
                return prefix
            from beta_engine.domain.players.calendar_tournament_closure import (
                append_native_tournament_closure,
            )
            for closure in state.closures:
                if closure.source_week_event_count == len(prefix.week_events) and (
                    closure not in prefix.closures
                ):
                    prefix = append_native_tournament_closure(prefix, closure)
        raise ValueError("Knockout event is absent from its Saved event history")

    @staticmethod
    def _receipt(event, successor):
        receipt = {
            "schema_version": "calendar_followup_knockout_receipt.v1",
            "tournament": event.model_dump(mode="json"),
            "fingerprint": event.fingerprint,
            "checkpoint_fingerprint": successor.fingerprint,
            "winner_player_id": event.matches[-1].result.winner_player_id,
            "scope": event.scope,
            "official_ranking_published": False,
        }
        if event.schema_version in {"calendar_followup_knockout.v2", "calendar_followup_knockout.v4"}:
            receipt["prepared_awards"] = [a.model_dump(mode="json") for a in event.prepared_awards]
            receipt["prepared_policy_fingerprint"] = event.prepared_policy.fingerprint
            receipt["publication_status"] = "prepared_not_official"
        return receipt

    def simulate(self, *, run_id, branch_id, command: CalendarFollowupKnockoutCommand | CalendarFollowupScoredCommand | CalendarFollowupEightCommand | CalendarFollowupEightScoredCommand):
        request_fp = canonical_hash({
            "run_id": run_id, "branch_id": branch_id,
            "command": command.model_dump(mode="json"),
        })
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            clock, revision, world, health, state, saved, evidence = (
                CalendarContinuationService(self.repository)._context(
                    session, run_id=run_id, branch_id=branch_id
                )
            )
            if state is None:
                raise ValueError("First play and Save a v5 opening knockout")
            opening = getattr(evidence, "knockout", evidence)
            for existing in state.tournaments:
                if (existing.command_id == command.command_id
                    or existing.tournament_id == command.tournament_id):
                    if (existing.command_id != command.command_id
                        or existing.tournament_id != command.tournament_id
                        or existing.request_fingerprint != request_fp):
                        raise ValueError("Knockout identity reused with different inputs")
                    successor = self._historical_successor(state, world, opening, existing)
                    return self._receipt(existing, successor)
            if (
                saved is None or saved.fingerprint != state.fingerprint
                or command.expected_saved_head != revision.saved_head_revision_id
                or command.expected_checkpoint_fingerprint != state.fingerprint
            ):
                raise ValueError("Save the sporting checkpoint before the next knockout")
            if not state.week_events or state.week.ordinal < 1:
                raise ValueError("Later knockout requires a Saved native sporting advance to Week 2 or later")
            reserved_commands = {
                opening.command_id,
                *(e.command_id for e in state.weekly_advances),
                *(e.command_id for e in state.played_continuations),
                *(e.command_id for e in state.tournaments),
                *(e.command_id for e in state.closures),
            }
            if (command.command_id in reserved_commands or command.tournament_id == opening.match_id):
                raise ValueError("Knockout identity collides with played history")
            reserved = {opening.match_id, *(m.input_context.match_id for m in opening.matches)}
            reserved.update(e.match_id for e in state.played_continuations)
            rounds = ROUNDS_EIGHT if isinstance(command, CalendarFollowupEightCommand) else ROUNDS
            if any(f"{command.tournament_id}:{suffix}" in reserved for suffix in rounds):
                raise ValueError("Knockout match ID collides with played match history")
            if any(f"{command.command_id}:{suffix}" in reserved_commands for suffix in rounds):
                raise ValueError("Knockout nested command ID collides with sporting history")
            if (isinstance(command, (CalendarFollowupEightScoredCommand, CalendarFollowupScoredCommand))
                    and command.point_policy.validity_weeks != clock.weeks_per_year):
                raise ValueError("Prepared point validity must equal the Run year W")
            prior = state
            results = []
            eight = isinstance(command, CalendarFollowupEightCommand)
            for index, suffix in enumerate(rounds):
                if eight and index < 4:
                    participants = command.entrant_ids[2*index:2*index+2]
                elif eight and index < 6:
                    start = (index - 4) * 2
                    participants = (
                        results[start].result.winner_player_id,
                        results[start + 1].result.winner_player_id,
                    )
                elif eight:
                    participants = (
                        results[4].result.winner_player_id,
                        results[5].result.winner_player_id,
                    )
                elif index < 2:
                    participants = command.entrant_ids[2*index:2*index+2]
                else:
                    participants = (
                        results[0].result.winner_player_id,
                        results[1].result.winner_player_id,
                    )
                inner = CalendarContinuationCommand(
                    command_id=f"{command.command_id}:{suffix}",
                    match_id=f"{command.tournament_id}:{suffix}",
                    expected_saved_head=command.expected_saved_head,
                    expected_checkpoint_fingerprint=prior.fingerprint,
                    player_a_id=participants[0],
                    player_b_id=participants[1],
                    seed=command.seed + index,
                    operator_label=command.operator_label,
                    audit_reason=command.audit_reason,
                )
                entry, prior = play_continuation_match(
                    state=prior, world=world, health=health, clock=clock,
                    run_id=run_id, branch_id=branch_id, command=inner,
                )
                results.append(entry)
            event_payload = dict(
                run_id=run_id, branch_id=branch_id,
                tournament_id=command.tournament_id,
                command_id=command.command_id,
                source_saved_head=command.expected_saved_head,
                source_checkpoint_fingerprint=state.fingerprint,
                week=RunWeekPosition(calendar=clock, season_index=state.week.season_index, week=state.week.week),
                seed=command.seed,
                entrant_ids=tuple(command.entrant_ids),
                operator_label=command.operator_label,
                audit_reason=command.audit_reason,
                request_fingerprint=request_fp,
                matches=tuple(results),
            )
            if isinstance(command, (CalendarFollowupEightScoredCommand, CalendarFollowupScoredCommand)):
                version = "calendar_followup_knockout.v4" if eight else "calendar_followup_knockout.v2"
                provisional = CalendarFollowupKnockout.model_construct(
                    **event_payload, schema_version=version,
                    prepared_policy=command.point_policy,
                )
                event = CalendarFollowupKnockout.model_validate_json(
                    provisional.model_copy(update={
                        "prepared_awards": derive_followup_awards(provisional),
                    }).model_dump_json()
                )
            elif eight:
                event = CalendarFollowupKnockout(
                    **event_payload, schema_version="calendar_followup_knockout.v3",
                )
            else:
                event = CalendarFollowupKnockout(**event_payload)
            successor = append_followup_knockout(state, world, event)
            if successor.players != prior.players:
                raise ValueError("Knockout terminal population differs from real match sequence")
            replace_checkpoint(session, previous=state, successor=successor)
            return self._receipt(event, successor)
