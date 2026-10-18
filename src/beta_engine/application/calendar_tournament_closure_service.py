"""Atomic Saved native sporting result closure, NOT Official publication."""
from dataclasses import dataclass
from typing import Literal

from pydantic import Field
from sqlalchemy import text

from beta_engine.application.calendar_continuation_service import CalendarContinuationService
from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
from beta_engine.domain.players.calendar_followup_knockout import CalendarFollowupKnockout, append_followup_knockout
from beta_engine.domain.players.calendar_continuation_match import append_continuation
from beta_engine.domain.players.calendar_sporting_checkpoint import build_calendar_sporting_checkpoint
from beta_engine.domain.players.calendar_sporting_week import CalendarSportingWeekAdvance, append_sporting_week
from beta_engine.domain.players.calendar_tournament_closure import (
    CalendarNativeTournamentClosure, append_native_tournament_closure, derive_closed_players,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import replace_checkpoint


class CalendarNativeTournamentClosureCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    tournament_id: str = Field(min_length=1)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_checkpoint_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)
    explicit_result_confirmation: Literal[True]


@dataclass(slots=True)
class CalendarNativeTournamentClosureService:
    repository: object

    @staticmethod
    def _receipt(closure, successor):
        return {
            "schema_version": "calendar_native_tournament_closure_receipt.v1",
            "closure": closure.model_dump(mode="json"),
            "fingerprint": closure.fingerprint,
            "checkpoint_fingerprint": successor.fingerprint,
            "official_ranking_published": False,
            "publication_status": "native_result_closed_not_official",
        }

    @staticmethod
    def _original_successor(state, world, opening, target):
        prefix = build_calendar_sporting_checkpoint(world, opening, calendar_engine_player)
        for event in (*state.continuations, *state.week_events):
            if isinstance(event, CalendarSportingWeekAdvance):
                prefix = append_sporting_week(prefix, world, opening, event)
            elif isinstance(event, CalendarFollowupKnockout):
                prefix = append_followup_knockout(prefix, world, event)
            else:
                prefix = append_continuation(prefix, world, event)
            for closure in state.closures:
                if (closure.source_week_event_count == len(prefix.week_events)
                        and closure not in prefix.closures):
                    prefix = append_native_tournament_closure(prefix, closure)
                    if closure is target:
                        return prefix
        raise ValueError("Native result closure is missing from immutable sporting history")

    def close(self, *, run_id, branch_id, command: CalendarNativeTournamentClosureCommand):
        request_fp = canonical_hash({
            "run_id": run_id, "branch_id": branch_id, "command": command.model_dump(mode="json"),
        })
        with self.repository._session_factory.begin() as session:
            session.execute(text("BEGIN IMMEDIATE"))
            _, revision, world, _, state, saved, evidence = (
                CalendarContinuationService(self.repository)._context(
                    session, run_id=run_id, branch_id=branch_id,
                )
            )
            if state is None:
                raise ValueError("Native result closure requires a played sporting checkpoint")
            opening = getattr(evidence, "knockout", evidence)
            for previous in state.closures:
                if (previous.command_id == command.command_id
                        or previous.tournament_id == command.tournament_id):
                    if (previous.command_id != command.command_id
                            or previous.tournament_id != command.tournament_id
                            or previous.request_fingerprint != request_fp):
                        raise ValueError("Closed tournament identity was already used")
                    return self._receipt(
                        previous, self._original_successor(state, world, opening, previous),
                    )
            from beta_engine.infrastructure.db.calendar_tour import require_exhibition_timeline
            require_exhibition_timeline(session, run_id, branch_id)
            if (saved is None or saved.fingerprint != state.fingerprint
                    or revision.saved_head_revision_id != command.expected_saved_head
                    or state.fingerprint != command.expected_checkpoint_fingerprint):
                raise ValueError("Save the completed tournament before closing its result")
            if (not state.week_events or not state.tournaments
                    or state.week_events[-1] is not state.tournaments[-1]
                    or state.week.ordinal != state.tournaments[-1].week.ordinal
                    or state.tournaments[-1].schema_version != "calendar_followup_knockout.v4"
                    or command.tournament_id != state.tournaments[-1].tournament_id):
                raise ValueError("Only the latest Saved scored eight-player tournament can close")
            if command.command_id in {
                opening.command_id,
                *(e.command_id for e in state.weekly_advances),
                *(e.command_id for e in state.played_continuations),
                *(e.command_id for e in state.tournaments),
            }:
                raise ValueError("Result closure command conflicts with played sporting identity")

            tournament = state.tournaments[-1]
            closure = CalendarNativeTournamentClosure(
                run_id=run_id, branch_id=branch_id,
                command_id=command.command_id,
                tournament_id=command.tournament_id,
                source_saved_head=command.expected_saved_head,
                source_checkpoint_fingerprint=state.fingerprint,
                source_week_event_count=len(state.week_events),
                source_tournament_fingerprint=tournament.fingerprint,
                source_prepared_awards_fingerprint=canonical_hash([
                    a.model_dump(mode="json") for a in tournament.prepared_awards
                ]),
                request_fingerprint=request_fp,
                operator_label=command.operator_label,
                audit_reason=command.audit_reason,
                champion_player_id=tournament.matches[-1].result.winner_player_id,
                finalist_player_id=tournament.matches[-1].result.loser_player_id,
                players=derive_closed_players(tournament),
            )
            successor = append_native_tournament_closure(state, closure)
            if successor.players != state.players or successor.week != state.week:
                raise ValueError("Result closure must not mutate player state or sporting clock")
            replace_checkpoint(session, previous=state, successor=successor)
            return self._receipt(closure, successor)
