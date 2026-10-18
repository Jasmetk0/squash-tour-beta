"""Atomic SQLite + Saved Revision ownership for native population sporting state."""
import json

from beta_engine.domain.players.calendar_sporting_checkpoint import (
    CalendarSportingCheckpoint, build_calendar_sporting_checkpoint,
)
from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel

COMPONENT_KEY = 'calendar_player_sporting_checkpoint'


def load_checkpoint(session, *, run_id, branch_id):
    row = session.get(CalendarPlayerSportingCheckpointModel, (run_id, branch_id))
    if row is None:
        return None
    state = CalendarSportingCheckpoint.model_validate_json(row.payload_json)
    if (state.run_id, state.branch_id, state.fingerprint) != (run_id, branch_id, row.fingerprint):
        raise ValueError('Calendar sporting checkpoint SQLite identity/hash mismatch')
    return state


def put_checkpoint(session, state):
    if session.get(CalendarPlayerSportingCheckpointModel, (state.run_id, state.branch_id)):
        raise ValueError('Calendar sporting checkpoint already exists; cannot overwrite')
    session.add(CalendarPlayerSportingCheckpointModel(
        run_id=state.run_id, branch_id=state.branch_id,
        fingerprint=state.fingerprint, payload_json=state.model_dump_json(),
    ))
    session.flush()


def _knockout(evidence):
    # Prepared points wrap rather than replace the original played authority.
    return getattr(evidence, 'knockout', evidence)


def verify_checkpoint(state, world, evidence):
    from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
    knockout = _knockout(evidence)
    required = knockout is not None and knockout.schema_version == 'calendar_opening_knockout.v5'
    if not required:
        if state is not None:
            raise ValueError('Orphan calendar sporting checkpoint without its v5 played source')
        return
    if state is None or world is None:
        raise ValueError('Played v5 knockout requires its complete population sporting checkpoint')
    expected = build_calendar_sporting_checkpoint(world, knockout, calendar_engine_player)
    from beta_engine.domain.players.calendar_continuation_match import append_continuation
    reserved_ids = {knockout.match_id, *(m.input_context.match_id for m in knockout.matches)}
    from beta_engine.domain.players.calendar_sporting_week import CalendarSportingWeekAdvance, append_sporting_week
    from beta_engine.domain.players.calendar_followup_knockout import (
        CalendarFollowupKnockout, append_followup_knockout,
    )
    from beta_engine.domain.players.calendar_tournament_closure import (
        append_native_tournament_closure,
    )
    closures_by_count = {entry.source_week_event_count: entry for entry in state.closures}
    if len(closures_by_count) != len(state.closures):
        raise ValueError('Native tournament result closure has duplicate event boundaries')
    closed_counts = set()
    for entry in (*state.continuations, *state.week_events):
        if isinstance(entry, CalendarSportingWeekAdvance):
            expected = append_sporting_week(expected, world, knockout, entry)
        elif isinstance(entry, CalendarFollowupKnockout):
            if (entry.command_id == knockout.command_id
                or any(m.match_id in reserved_ids or m.command_id == knockout.command_id
                       for m in entry.matches)):
                raise ValueError('Later knockout reuses original opening knockout identity')
            expected = append_followup_knockout(expected, world, entry)
        else:
            if entry.match_id in reserved_ids or entry.command_id == knockout.command_id:
                raise ValueError('Continuation reuses original knockout identity')
            expected = append_continuation(expected, world, entry)
        index = len(expected.week_events)
        if index in closures_by_count and index not in closed_counts:
            expected = append_native_tournament_closure(expected, closures_by_count[index])
            closed_counts.add(index)
    if closed_counts != set(closures_by_count):
        raise ValueError('Native result closure has no matching sporting event')
    if state != expected:
        raise ValueError('Calendar sporting checkpoint differs from population and played terminal evidence')


def saved_checkpoint(payload, evidence, *, run_id, branch_id):
    from beta_engine.infrastructure.db.initial_world_state import load_saved_initial_world
    component = payload.get('content', {}).get(COMPONENT_KEY)
    state = None
    if component is not None:
        if not isinstance(component, dict) or set(component) != {'fingerprint', 'state'}:
            raise ValueError('Malformed Saved calendar sporting checkpoint component')
        state = CalendarSportingCheckpoint.model_validate_json(json.dumps(component['state']))
        if (state.run_id, state.branch_id, state.fingerprint) != (run_id, branch_id, component['fingerprint']):
            raise ValueError('Saved calendar sporting checkpoint identity/hash mismatch')
    knockout = _knockout(evidence)
    required = knockout is not None and knockout.schema_version == 'calendar_opening_knockout.v5'
    world = load_saved_initial_world(payload, run_id=run_id, branch_id=branch_id) if required or state else None
    verify_checkpoint(state, world, evidence)
    if state:
        from beta_engine.domain.calendar.run_calendar import RunCalendar
        clock = RunCalendar.from_metadata(payload['run']['run_calendar'])
        last = state.week.calendar
        if state.continuations and not state.week_events:
            last = state.continuations[-1].week.calendar
        if (last.weeks_per_year, last.season_start_year_week, last.start_year) != (clock.weeks_per_year, clock.season_start_year_week, clock.start_year) or last.season_count > clock.season_count:
            raise ValueError('Saved continuation clock exceeds its Run horizon')
    return state


def capture_checkpoint(session, payload, evidence, *, run_id, branch_id):
    from beta_engine.infrastructure.db.initial_world_state import get_initial_world
    state = load_checkpoint(session, run_id=run_id, branch_id=branch_id)
    world = get_initial_world(session, run_id=run_id, branch_id=branch_id) if state or evidence else None
    verify_checkpoint(state, world, evidence)
    if state is not None:
        payload['content'][COMPONENT_KEY] = {'fingerprint': state.fingerprint, 'state': state.model_dump(mode='json')}


def restore_checkpoint(session, *, current_payload, target_payload, current, target, run_id, branch_id):
    expected = saved_checkpoint(current_payload, current, run_id=run_id, branch_id=branch_id)
    replacement = saved_checkpoint(target_payload, target, run_id=run_id, branch_id=branch_id)
    live = load_checkpoint(session, run_id=run_id, branch_id=branch_id)
    if live != expected:
        raise ValueError('Live calendar sporting checkpoint differs from current Saved HEAD')
    row = session.get(CalendarPlayerSportingCheckpointModel, (run_id, branch_id))
    if row is not None:
        session.delete(row)
        session.flush()
    if replacement is not None:
        put_checkpoint(session, replacement)


def replace_checkpoint(session, *, previous, successor):
    live = load_checkpoint(session, run_id=previous.run_id, branch_id=previous.branch_id)
    if live != previous or (successor.run_id, successor.branch_id) != (previous.run_id, previous.branch_id):
        raise ValueError('Population sporting checkpoint changed before atomic replacement')
    row = session.get(CalendarPlayerSportingCheckpointModel, (previous.run_id, previous.branch_id))
    row.fingerprint = successor.fingerprint
    row.payload_json = successor.model_dump_json()
    session.flush()
