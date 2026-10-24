"""Physical pre-play authority for new terminal results, independent of own hashes."""


from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.models import BranchSavedRevisionModel

SCHEMA = 'calendar_terminal_edition_result.v1'


def verify_saved_terminal_results(repository, session, revision):
    # The ordinary component verifier already replayed actual sport/results.
    # Resolve only the terminal boundary's physical dependencies here; do not
    # decode/replay complete histories again or retain a cross-request proof.
    state = revision.payload.get('content', {}).get('calendar_tour_authority', {}).get('state')
    if not state:
        return
    confirmations = {
        r['request']['command'].get('edition_id'): r['result'].get('results', [])
        for r in state['receipts']
        if r['request']['command']['action'] == 'confirm-result'
    }
    candidates = []
    for authority in state['editions']:
        if not authority['result_confirmed']:
            continue
        week = authority['edition']['week']
        clock = RunCalendar.from_metadata(week['calendar'])
        results = confirmations.get(authority['edition']['edition_id'], [])
        if not isinstance(results, list) or any(not isinstance(r, dict) for r in results):
            raise ValueError('Malformed terminal result confirmation')
        if (any(r.get('schema_version') == SCHEMA for r in results)
            or clock.ordinal(week['season_index'], week['week']) == clock.weeks_per_year * clock.season_count - 1):
            candidates.append((authority, results))
    if not candidates:
        return
    # One ancestry walk for all relevant Editions; no per-result lineage replay.
    reachable = set()
    parent_id = revision.parent_revision_id
    while parent_id:
        if parent_id in reachable:
            raise ValueError('Terminal result source ancestry contains a cycle')
        reachable.add(parent_id)
        row = session.get(BranchSavedRevisionModel, parent_id)
        if row is None or row.run_id != revision.run_id:
            raise ValueError('Terminal result source ancestry is missing or foreign')
        ancestor = repository._validated_saved_revision_in_session(
            session=session, model=row, materialize_payload=False,
        )
        parent_id = ancestor.parent_revision_id
    for authority, results in candidates:
        source_id = authority['played_saved_head']
        row = session.get(BranchSavedRevisionModel, source_id)
        if source_id not in reachable or row is None or (row.run_id, row.branch_id) != (revision.run_id, revision.branch_id):
            raise ValueError('Terminal result played source is missing, foreign or unreachable')
        source = repository._validated_saved_revision_in_session(session=session, model=row)
        original = source.payload['content']['calendar_tour_authority']['state']
        frozen = next((a for a in original['editions'] if a['edition']['edition_id'] == authority['edition']['edition_id']), None)
        if frozen is None or any(frozen[key] != authority[key] for key in (
            'edition', 'created_command_id', 'created_saved_head', 'submissions',
            'ranking_authority', 'field', 'draw', 'draw_seed', 'draw_command_id',
        )) or frozen['tournament_fingerprint'] is not None:
            raise ValueError('Terminal result draw differs from its actual immutable pre-play source')
        clock = RunCalendar.from_metadata(source.payload['run']['run_calendar'])
        week = original['week']
        terminal = clock.ordinal(week['season_index'], week['week']) == clock.weeks_per_year * clock.season_count - 1
        if not results or any((r.get('schema_version') == SCHEMA) != terminal for r in results):
            raise ValueError('Terminal result kind disagrees with the actual played Saved horizon')
        if terminal and any(r['completed_week'] != {**week, 'calendar': clock.to_metadata()} for r in results):
            raise ValueError('Terminal result time differs from the actual played Saved clock')
