"""Real sequential matches from Saved calendar sporting checkpoints, manual Save."""
from dataclasses import dataclass
from types import SimpleNamespace

from pydantic import Field, model_validator
from sqlalchemy import text

from beta_engine.application.calendar_opening_knockout_service import (
    CalendarOpeningKnockoutService,
)
from beta_engine.core import DeterministicRng
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.matches.health import (
    EffectiveMatchHealthSnapshot,
    project_player_health,
)
from beta_engine.domain.matches.match_engine import MatchEngine
from beta_engine.domain.matches.models import MatchContext
from beta_engine.domain.players.calendar_canonical_match import canonical_participant
from beta_engine.domain.players.calendar_continuation_match import (
    CalendarContinuationMatch,
    append_continuation,
    continuation_anchor,
    continuation_effects,
    continuation_projections,
)
from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
from beta_engine.domain.players.calendar_match_state import CalendarMatchStatePolicy
from beta_engine.domain.players.calendar_sporting_checkpoint import (
    build_calendar_sporting_checkpoint,
)
from beta_engine.domain.rankings.official import FrozenInput
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.simulation_slots import CanonicalMatchInputProjectionPolicy
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
    load_checkpoint,
    replace_checkpoint,
    saved_checkpoint,
)
from beta_engine.infrastructure.db.calendar_standalone_match_state import (
    load_match_rows,
)


class CalendarContinuationCommand(FrozenInput):
    command_id: str = Field(min_length=1, max_length=128)
    match_id: str = Field(min_length=1, max_length=100)
    expected_saved_head: str = Field(min_length=1, max_length=128)
    expected_checkpoint_fingerprint: str = Field(pattern=r'^[0-9a-f]{64}$')
    player_a_id: str = Field(min_length=1, max_length=128)
    player_b_id: str = Field(min_length=1, max_length=128)
    seed: int
    operator_label: str = Field(min_length=1, max_length=160)
    audit_reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode='after')
    def distinct(self):
        if self.player_a_id == self.player_b_id:
            raise ValueError('Continuation needs two distinct players')
        return self


def play_continuation_match(*, state, world, health, clock, run_id, branch_id, command):
    """Execute and rebuild one real MatchEngine match inside caller-owned transaction.

    The caller separately checks Saved HEAD and permissions before calling this
    reducer. This helper is shared by standalone and atomic tournament execution.
    """
    request_fp = canonical_hash({'run_id': run_id, 'branch_id': branch_id, 'command': command.model_dump(mode='json')})
    ids = (command.player_a_id, command.player_b_id)
    projections = continuation_projections(state, world, ids)
    ctx = MatchContext(match_id=command.match_id,
        player_a=canonical_participant(projections[0]), player_b=canonical_participant(projections[1]),
        best_of=5, games_to=11, win_by=2)
    medical = None
    if health:
        profiles = {p.player_id: p for p in health.players}
        medical = EffectiveMatchHealthSnapshot(player_profiles=tuple(project_player_health(profiles[pid]) for pid in ids))
    inputs = dict(schema_version=('calendar_continuation_match.v2' if state.week_events else 'calendar_continuation_match.v1'), run_id=run_id, branch_id=branch_id,
        week=RunWeekPosition(calendar=clock, season_index=state.week.season_index, week=state.week.week), sequence=len(state.played_continuations) + 1,
        command_id=command.command_id, match_id=command.match_id,
        source_saved_head=command.expected_saved_head, source_checkpoint_fingerprint=state.fingerprint,
        seed=command.seed, operator_label=command.operator_label, audit_reason=command.audit_reason,
        request_fingerprint=request_fp, input_context=ctx, canonical_projections=projections,
        projection_policy=CanonicalMatchInputProjectionPolicy(), state_policy=CalendarMatchStatePolicy(),
        source_health_fingerprint=health.fingerprint if health else None, effective_health=medical)
    anchor = continuation_anchor(SimpleNamespace(**inputs))
    result = MatchEngine(DeterministicRng(command.seed)).simulate(ctx, log_anchor_hash=anchor, effective_match_health=medical)
    _, effects = continuation_effects(state, ctx, result, inputs['state_policy'])
    entry = CalendarContinuationMatch(**inputs, result=result, effects=effects, log_anchor_hash=anchor)
    successor = append_continuation(state, world, entry)
    return entry, successor


@dataclass(slots=True)
class CalendarContinuationService:
    repository: object

    def _context(self, session, *, run_id, branch_id):
        clock, revision, world, health = CalendarOpeningKnockoutService(self.repository)._context(
            session, run_id=run_id, branch_id=branch_id)
        checkpoint = load_checkpoint(session, run_id=run_id, branch_id=branch_id)
        rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
        evidence = rows[0] if len(rows) == 1 else None
        from beta_engine.infrastructure.db.calendar_standalone_match_state import (
            load_saved_calendar_match,
        )
        saved_evidence = load_saved_calendar_match(revision.saved_revision.payload, run_id=run_id, branch_id=branch_id)
        saved = saved_checkpoint(revision.saved_revision.payload, saved_evidence,
            run_id=run_id, branch_id=branch_id)
        if saved is not None:
            root = getattr(evidence, 'knockout', evidence)
            saved_root = getattr(saved_evidence, 'knockout', saved_evidence)
            if checkpoint is None or root is None or root.fingerprint != saved_root.fingerprint:
                raise ValueError('Live sporting owner or original knockout differs from Saved history')

        # Unsaved initial knockout has no Saved owner yet; inspection is allowed.
        return clock, revision, world, health, checkpoint, saved, evidence

    def inspect(self, *, run_id, branch_id):
        with self.repository._session_factory() as session:
            session.execute(text('BEGIN'))
            clock, revision, world, health, state, saved, _ = self._context(session, run_id=run_id, branch_id=branch_id)
            return {
                'schema_version': 'calendar_continuation_inspection.v1',
                'run_id': run_id, 'branch_id': branch_id,
                'saved_head_revision_id': revision.saved_head_revision_id,
                'draft_version': revision.working_draft.draft_version,
                'player_ids': [p.player_id for p in world.players],
                'checkpoint_fingerprint': state.fingerprint if state else None,
                'saved': bool(state and saved and state.fingerprint == saved.fingerprint),
                'can_play': bool(state and saved and state.fingerprint == saved.fingerprint),
                'run_calendar': clock.to_metadata(),
                'sporting_week': RunWeekPosition(calendar=clock, season_index=state.week.season_index, week=state.week.week).model_dump(mode='json') if state else None,
                'weekly_advance_count': len(state.weekly_advances) if state else 0,
                'tournaments': [{
                    'tournament_id': event.tournament_id,
                    'command_id': event.command_id,
                    'fingerprint': event.fingerprint,
                    'week': event.week.week,
                    'entrant_ids': list(event.entrant_ids),
                    'winner_player_id': event.matches[-1].result.winner_player_id,
                    'match_ids': [match.match_id for match in event.matches],
                    'saved': bool(saved and any(
                        original.fingerprint == event.fingerprint for original in saved.tournaments
                    )),
                    'scope': event.scope,
                    'prepared_points_status': (
                        'prepared_not_official' if event.schema_version == 'calendar_followup_knockout.v2'
                        else 'not_prepared'
                    ),
                    'prepared_policy': (
                        event.prepared_policy.model_dump(mode='json') if event.prepared_policy else None
                    ),
                    'prepared_awards': [
                        award.model_dump(mode='json') for award in event.prepared_awards
                    ],
                } for event in state.tournaments] if state else [],
                'weekly_advances': [{'command_id':e.command_id,'fingerprint':e.fingerprint,'completed_week':e.completed_week.week,'target_week':e.target_week.week,'saved':bool(saved and any(s.fingerprint == e.fingerprint for s in saved.weekly_advances))} for e in state.weekly_advances] if state else [],
                'health_numeric_effect_applied': False,
                'limited_player_ids': [p.player_id for p in health.players if project_player_health(p).numeric_calibration_required] if health else [],
                'matches': [{
                    'match_id': e.match_id, 'sequence': e.sequence, 'week': e.week.week, 'fingerprint': e.fingerprint,
                    'player_ids': [e.input_context.player_a.player.player_id, e.input_context.player_b.player.player_id],
                    'winner_player_id': e.result.winner_player_id, 'rally_count': len(e.result.rally_log.events),
                    'saved': bool(saved and i < len(saved.played_continuations) and saved.played_continuations[i].fingerprint == e.fingerprint),
                } for i, e in enumerate(state.played_continuations)] if state else [],
            }

    def simulate(self, *, run_id, branch_id, command: CalendarContinuationCommand):
        request_fp = canonical_hash({'run_id': run_id, 'branch_id': branch_id, 'command': command.model_dump(mode='json')})
        with self.repository._session_factory.begin() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            clock, revision, world, health, state, saved, evidence = self._context(session, run_id=run_id, branch_id=branch_id)
            if state is None:
                raise ValueError('First play and Save a v5 opening knockout to establish population sporting authority')
            knockout = getattr(evidence, 'knockout', evidence)
            # Nested matches are owned by an atomic tournament command. Their
            # identities must never be replayed as independent exhibition writes.
            if any(
                existing.command_id == command.command_id
                or existing.match_id == command.match_id
                for event in state.tournaments for existing in event.matches
            ):
                raise ValueError('Tournament matches cannot be reissued as individual exhibitions')
            for existing in state.played_continuations:
                if existing.command_id == command.command_id or existing.match_id == command.match_id:
                    if existing.command_id != command.command_id or existing.request_fingerprint != request_fp:
                        raise ValueError('Continuation command/match ID already used with different input')
                    prefix = build_calendar_sporting_checkpoint(world, knockout, calendar_engine_player)
                    from beta_engine.domain.players.calendar_sporting_week import (
                        CalendarSportingWeekAdvance, append_sporting_week,
                    )
                    from beta_engine.domain.players.calendar_followup_knockout import (
                        CalendarFollowupKnockout, append_followup_knockout,
                    )
                    for entry in (*state.continuations, *state.week_events):
                        prefix = (
                            append_sporting_week(prefix, world, knockout, entry)
                            if isinstance(entry, CalendarSportingWeekAdvance)
                            else append_followup_knockout(prefix, world, entry)
                            if isinstance(entry, CalendarFollowupKnockout)
                            else append_continuation(prefix, world, entry)
                        )
                        if getattr(entry, 'match_id', None) == existing.match_id:
                            break
                    return self._receipt(existing, prefix)
            if (saved is None or saved.fingerprint != state.fingerprint
                    or revision.saved_head_revision_id != command.expected_saved_head
                    or state.fingerprint != command.expected_checkpoint_fingerprint):
                raise ValueError('Save the current checkpoint and review its exact Saved HEAD before a new match')
            if any(e.command_id == command.command_id for e in state.weekly_advances):
                raise ValueError('Command identity already used by sporting week advance')
            if command.match_id in {knockout.match_id, *(m.input_context.match_id for m in knockout.matches)} or command.command_id == knockout.command_id:
                raise ValueError('Continuation cannot reuse the original knockout identity')
            entry, successor = play_continuation_match(
                state=state, world=world, health=health, clock=clock,
                run_id=run_id, branch_id=branch_id, command=command,
            )
            replace_checkpoint(session, previous=state, successor=successor)
            return self._receipt(entry, successor)

    @staticmethod
    def _receipt(entry, checkpoint):
        return {'match': entry.model_dump(mode='json'), 'fingerprint': entry.fingerprint,
                'checkpoint_fingerprint': checkpoint.fingerprint}

    def replay(self, *, run_id, branch_id, match_id):
        with self.repository._session_factory() as session:
            session.execute(text('BEGIN'))
            # Historical replay consumes frozen authority, never current medical
            # readiness or permission to start another sporting command.
            from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
                verify_checkpoint,
            )
            from beta_engine.infrastructure.db.initial_world_state import (
                get_initial_world,
            )
            state = load_checkpoint(session, run_id=run_id, branch_id=branch_id)
            rows = load_match_rows(session, run_id=run_id, branch_id=branch_id)
            world = get_initial_world(session, run_id=run_id, branch_id=branch_id)
            verify_checkpoint(state, world, rows[0] if len(rows) == 1 else None)
            entry = next((e for e in state.played_continuations if e.match_id == match_id), None) if state else None
            if entry is None:
                raise KeyError('Calendar continuation match not found')
            result = MatchEngine(DeterministicRng(entry.seed)).simulate(entry.input_context,
                log_anchor_hash=entry.log_anchor_hash, effective_match_health=entry.effective_health)
            if result.model_dump(mode='json') != entry.result.model_dump(mode='json'):
                raise ValueError('Continuation replay disagrees with the original MatchEngine history')
            return {'match_id': match_id, 'fingerprint': entry.fingerprint,
                'winner_player_id': result.winner_player_id, 'rally_count': len(result.rally_log.events), 'exact_replay': True}
