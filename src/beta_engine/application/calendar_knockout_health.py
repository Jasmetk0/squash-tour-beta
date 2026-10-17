"""Validate actual Saved calendar Health ownership before playing a knockout."""
from beta_engine.domain.players.calendar_initial_health import CalendarInitialHealthState
from beta_engine.domain.players.calendar_health import CalendarHealthState
from beta_engine.infrastructure.db.player_health_state import health_component, load_saved_health


def saved_knockout_health(session, *, revision, run_id, branch_id):
    payload = revision.saved_revision.payload
    saved = load_saved_health(payload, run_id=run_id, branch_id=branch_id)
    live = health_component(session, run_id=run_id, branch_id=branch_id)
    if live != payload.get('content', {}).get('player_health_state'):
        raise ValueError('Knockout Health must exactly match the Saved HEAD; Save or discard changes')
    if not saved:
        return None
    if len(saved) != 1 or not isinstance(saved[0], (CalendarInitialHealthState, CalendarHealthState)):
        raise ValueError('Knockout cannot bypass legacy or later-week Health ownership')
    if saved[0].week.ordinal != 0:
        raise ValueError('Opening knockout requires opening-week Health')
    # load_saved_health verifies hash, calendar, InitialWorld and full lifecycle roster.
    return saved[0]


def health_readiness(state):
    if state is None:
        return None
    return {
        'source_health_schema': state.schema_version,
        'source_health_fingerprint': state.fingerprint,
        'limited_player_ids': [p.player_id for p in state.players
            if any(r.lifecycle != 'Recovered' for r in p.records) or p.permanent_consequences],
        'numeric_effect_applied': False,
    }
