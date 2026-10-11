"""Real HTTP/SQLite preparation, audit, recovery and rejection tests."""

import json

import pytest
from sqlalchemy import text
from test_admin_ranking_candidates_api import api, dump  # noqa: F401
from beta_engine.infrastructure.db.models import OfficialRankingCommandModel, RunBranchModel
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state
from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state

PREFIX = '/admin/runs/run/branches/empty/ranking-candidates'
AUDIT = {'actor_label': 'Admin operator', 'reason': 'Prepare reviewed ranking inputs'}


def initial():
    return dict(command_id='prepare-initial', run_id='run', branch_id='empty', discipline='stored_zeros',
                policy={'policy_id': 'policy', 'best_n': 1}, players=[dict(player_id='p', tie_break_token='token',
                tour_entry_week={'season_index': 0, 'week': 1})], audit=AUDIT)


def weekly():
    start = initial()
    return dict(command_id='prepare-week', audit=AUDIT, tournaments=[], context=dict(
        run_id='run', branch_id='empty', discipline='stored_zeros', policy=start['policy'], players=start['players'],
        completed_week={'season_index': 0, 'week': 1}, target_week={'season_index': 0, 'week': 2}), zero_versions=[dict(
        effective_week={'season_index': 0, 'week': 2}, previous_fingerprint=None, zero=dict(
            zero_id='zero', run_id='run', branch_id='empty', player_id='p', source_fingerprint='decision',
            effective_week={'season_index': 0, 'week': 2}, duration_weeks=2))])


def capture(factory):
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        return capture_ranking_revision_state(session, run_id='run', branch_id='empty')


@pytest.mark.smoke
def test_prepare_inspect_retry_and_recovery_keep_audit(api):
    client, factory, path, *_ = api
    empty = capture(factory)
    response = client.post(PREFIX + '/prepare/initial', json=initial())
    assert response.status_code == 201
    assert response.json()['publication_status'] == 'candidate_only'
    response = client.post(PREFIX + '/prepare/week', json=weekly())
    assert response.status_code == 201
    before = dump(path)
    assert client.post(PREFIX + '/prepare/week', json=weekly()).json() == response.json()
    assert dump(path) == before
    data = client.get(PREFIX + '/0/2/inputs').json()
    assert data['command_audits'] == [{'command_id': 'prepare-week', 'audit': AUDIT}]
    assert data['zero_history_status'] == 'verified_stored_history'
    state = capture(factory)
    assert json.loads(state.entries[-1].receipts[0].request_payload_json)['audit'] == AUDIT
    for index, target in enumerate((empty, state)):
        current = capture(factory)
        with factory.begin() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            restore_ranking_revision_state(session, target.model_dump_json(), expected_fingerprint=target.fingerprint,
                expected_current_fingerprint=current.fingerprint, command_id=f'api-restore-{index}', run_id='run', branch_id='empty')
    assert client.get(PREFIX + '/0/2/inputs').json()['command_audits'] == data['command_audits']
    assert client.post(PREFIX + '/prepare/week', json=weekly()).json() == response.json()
    changed = weekly() | {'audit': AUDIT | {'reason': 'Different decision'}}
    before = dump(path)
    assert client.post(PREFIX + '/prepare/week', json=changed).status_code == 409
    assert dump(path) == before


@pytest.mark.parametrize('damage', ['missing_audit', 'blank_reason', 'coercion', 'unknown_field', 'scope', 'read_only', 'fork'])
def test_invalid_or_unsupported_preparation_does_not_write(api, damage):
    client, factory, path, *_ = api
    req = initial()
    expected = 422
    if damage == 'missing_audit':
        del req['audit']
    elif damage == 'blank_reason':
        req['audit'] = AUDIT | {'reason': '   '}
    elif damage == 'coercion':
        req['policy']['best_n'] = '15'
    elif damage == 'unknown_field':
        req['publish'] = True
    elif damage == 'scope':
        req['branch_id'] = 'branch'
        expected = 409
    else:
        expected = 409
        with factory.begin() as session:
            branch = session.get(RunBranchModel, 'empty')
            if damage == 'read_only':
                branch.read_only = True
            else:
                branch.forked_from_branch_id = 'branch'
    before = dump(path)
    assert client.post(PREFIX + '/prepare/initial', json=req).status_code == expected
    assert dump(path) == before


@pytest.mark.smoke
@pytest.mark.parametrize('damage', ['changed', 'missing'])
def test_missing_or_changed_request_audit_fails_closed(api, damage):
    client, factory, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    with factory.begin() as session:
        row = session.get(OfficialRankingCommandModel, ('run', 'empty', 'prepare-initial'))
        row.request_payload_json = None if damage == 'missing' else row.request_payload_json.replace('Admin operator', 'forged operator')
    before = dump(path)
    assert client.get(PREFIX + '/0/1/inputs').status_code == 409
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 409
    assert dump(path) == before


def test_failed_zero_batch_does_not_leave_partial_sources(api):
    client, _, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    req = weekly()
    req['zero_versions'].append(req['zero_versions'][0] | {
        'previous_fingerprint': '0'*64, 'zero': req['zero_versions'][0]['zero'] | {'zero_id': 'z-broken'},
    })
    before = dump(path)
    assert client.post(PREFIX + '/prepare/week', json=req).status_code == 409
    assert dump(path) == before


def test_legacy_tournament_file_binding_is_not_exposed_as_scoped_ingestion(api):
    client, _, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    req = weekly()
    req['tournaments'] = [dict(run_id='run', branch_id='empty', edition_id='edition', event_id='legacy-file',
        completed_week={'season_index': 0, 'week': 1}, first_publication_week={'season_index': 0, 'week': 2},
        validity_weeks=61, ranking_status='ranked', expected_result_fingerprint='0'*64, expected_award_fingerprint='0'*64)]
    before = dump(path)
    assert client.post(PREFIX + '/prepare/week', json=req).status_code == 409
    assert dump(path) == before


def test_existing_database_adds_nullable_request_column_and_reads_legacy_receipts(api):
    from beta_engine.infrastructure.db.repositories import SimulationPersistenceRepository
    client, factory, _, *_ = api
    engine = factory.kw['bind']
    with engine.begin() as connection:
        connection.exec_driver_sql('ALTER TABLE official_ranking_commands DROP COLUMN request_payload_json')
    SimulationPersistenceRepository(engine=engine, session_factory=factory).bootstrap_schema()
    with factory() as session:
        legacy = session.get(OfficialRankingCommandModel, ('run', 'branch', 'command'))
        assert legacy.request_payload_json is None
        assert legacy.request_fingerprint == '1'*64
    assert client.get('/admin/runs/run/branches/branch/ranking-candidates/1/1/inputs').status_code == 200
