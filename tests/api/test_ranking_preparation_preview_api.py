"""Preview and confirmation use real HTTP, SQLite and the production runner."""

import json
from urllib import request, error

import pytest
from sqlalchemy import text
from test_admin_ranking_candidates_api import api, dump  # noqa: F401
from test_admin_ranking_preparation_api import PREFIX, initial, weekly
from beta_engine.domain.rankings.zero_history import RankingZeroVersion
from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore


def confirm(client, kind, command, fingerprint):
    req = request.Request(client.base_url + PREFIX + '/prepare/' + kind, data=json.dumps(command).encode(),
        method='POST', headers={'Content-Type':'application/json','X-Ranking-Preview-Fingerprint':fingerprint})
    try:
        with request.urlopen(req) as response:
            return response.status, json.loads(response.read())
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@pytest.mark.smoke
def test_preview_is_read_only_and_confirm_matches_then_retries(api):
    client, _, path, *_ = api
    before = dump(path)
    preview = client.post(PREFIX + '/prepare/initial/preview', json=initial())
    assert preview.status_code == 200
    assert preview.json()['preview_only'] is True
    assert dump(path) == before
    expected = preview.json()['candidate']
    status, body = confirm(client, 'initial', initial(), expected['fingerprint'])
    assert status == 201 and body == expected
    assert client.get(PREFIX).json()['candidates'] == [expected]
    before = dump(path)
    assert confirm(client, 'initial', initial(), expected['fingerprint']) == (201, expected)
    assert client.post(PREFIX + '/prepare/initial/preview', json=initial()).json() == preview.json()
    assert dump(path) == before


@pytest.mark.smoke
def test_week_preview_rolls_back_zero_batch_and_stale_confirm_is_atomic(api):
    client, factory, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    req = weekly()
    before = dump(path)
    preview = client.post(PREFIX + '/prepare/week/preview', json=req)
    assert preview.status_code == 200
    assert dump(path) == before
    zero = req['zero_versions'][0]
    external = RankingZeroVersion.model_validate_json(json.dumps(zero | {'zero':zero['zero'] | {'zero_id':'external'}}))
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        OfficialRankingZeroStore(session).append(external)
    before = dump(path)
    assert confirm(client, 'week', req, preview.json()['candidate']['fingerprint'])[0] == 409
    assert dump(path) == before
    refreshed = client.post(PREFIX + '/prepare/week/preview', json=req)
    assert refreshed.status_code == 200
    assert refreshed.json()['candidate']['fingerprint'] != preview.json()['candidate']['fingerprint']
    assert dump(path) == before
    assert confirm(client, 'week', req, refreshed.json()['candidate']['fingerprint'])[0] == 201


@pytest.mark.parametrize('case', ['invalid_audit', 'lineage', 'wrong_fingerprint'])
def test_preview_failure_and_invalid_confirmation_leave_storage_unchanged(api, case):
    client, _, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    req = weekly()
    if case == 'invalid_audit':
        req['audit'] = req['audit'] | {'reason':' '}
    elif case == 'lineage':
        req['zero_versions'][0]['previous_fingerprint'] = '0'*64
    before = dump(path)
    if case == 'wrong_fingerprint':
        assert confirm(client, 'week', req, 'not-a-hash')[0] == 422
        assert confirm(client, 'week', req, '0'*64)[0] == 409
    else:
        assert client.post(PREFIX + '/prepare/week/preview', json=req).status_code in (409,422)
    assert dump(path) == before


@pytest.mark.smoke
def test_real_run_preview_confirm_save_and_reopen(tmp_path):
    from test_saved_revision_history_api import ApiServer, _create_run, _request
    path = tmp_path / 'workflow.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        run_id, branch_id, initial_revision = _create_run(server, display_name='Ranking workflow')
        root = f'{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates'
        command = initial() | {'run_id':run_id, 'branch_id':branch_id}
        before = dump(path)
        status, preview = _request('POST', root + '/prepare/initial/preview', command)
        assert status == 200 and preview['preview_only']
        assert dump(path) == before
        req = request.Request(root + '/prepare/initial', data=json.dumps(command).encode(), method='POST',
            headers={'Content-Type':'application/json', 'X-Ranking-Preview-Fingerprint':preview['candidate']['fingerprint']})
        with request.urlopen(req) as response:
            assert response.status == 201 and json.loads(response.read()) == preview['candidate']
        status, review = _request('GET', root + '/save/preview')
        assert status == 200 and review['can_save']
        status, saved = _request('POST', root + '/save', dict(expected_draft_version=review['draft_version'], expected_ranking_fingerprint=review['ranking_fingerprint']))
        assert status == 201
        assert saved['saved_revision']['parent_revision_id'] == initial_revision
        assert saved['viewer_branch_id'] == branch_id
        assert saved['saved_revision']['payload']['content']['ranking_preparation']['state']['entries'][0]['receipts'][0]['request_payload_json']
    with ApiServer(database_url=f'sqlite:///{path}') as reopened:
        root = f'{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates'
        assert _request('GET', root + '/save/preview')[1]['has_unsaved_changes'] is False
        assert _request('GET', root + '/0/1/inputs')[1]['command_audits'][0]['audit'] == command['audit']


def test_confirmation_binds_audit_and_exact_request_as_well_as_snapshot(api):
    client, _, path, *_ = api
    preview = client.post(PREFIX + '/prepare/initial/preview', json=initial()).json()
    changed = initial() | {'audit': initial()['audit'] | {'reason':'Changed after review'}}
    before = dump(path)
    req = request.Request(client.base_url + PREFIX + '/prepare/initial', data=json.dumps(changed).encode(), method='POST',
        headers={'Content-Type':'application/json','X-Ranking-Preview-Fingerprint':preview['candidate']['fingerprint'],
                 'X-Ranking-Preview-Request':preview['request_fingerprint']})
    with pytest.raises(error.HTTPError) as rejected:
        request.urlopen(req)
    assert rejected.value.code == 409
    assert dump(path) == before


@pytest.mark.smoke
def test_result_correction_preview_confirm_history_and_recovery(api):
    from beta_engine.domain.rankings.result_history import RankingResultVersion
    from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore
    from test_admin_ranking_preparation_api import capture
    from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state

    client, factory, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    original = RankingResultVersion.model_validate_json(json.dumps(dict(
        run_id='run', branch_id='empty', effective_week={'season_index':0,'week':2}, previous_fingerprint=None,
        result=dict(edition_id='edition', player_id='p', source_fingerprint='award',
                    completed_week={'season_index':0,'week':1}, first_publication_week={'season_index':0,'week':2},
                    qualification_points=10, main_points=100))))
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        OfficialRankingResultStore(session).append(original)
    second = weekly() | {'zero_versions':[]}
    old = client.post(PREFIX + '/prepare/week', json=second).json()
    assert old['snapshot']['rows'][0]['points'] == 110
    source = client.get(PREFIX + '/0/2/sources').json()['sources'][0]
    prior_state = capture(factory)
    req = second | {'command_id':'correct-award', 'context':second['context'] | {
        'completed_week':{'season_index':0,'week':2}, 'target_week':{'season_index':0,'week':3}},
        'corrections':[source['version'] | {'effective_week':{'season_index':0,'week':3},
            'previous_fingerprint':source['fingerprint'], 'result':source['version']['result'] | {
                'qualification_points':20, 'main_points':200, 'source_fingerprint':'appeal'}}]}
    before = dump(path)
    preview = client.post(PREFIX + '/prepare/week/preview', json=req)
    assert preview.status_code == 200 and dump(path) == before
    assert preview.json()['candidate']['snapshot']['rows'][0]['points'] == 220
    status, candidate = confirm(client, 'week', req, preview.json()['candidate']['fingerprint'])
    assert status == 201
    assert client.get(PREFIX + '/0/2').json() == old
    assert client.get(PREFIX + '/0/2/sources').json()['sources'][0] == source
    corrected = client.get(PREFIX + '/0/3/sources').json()['sources'][0]['version']
    for field in ('completed_week', 'first_publication_week', 'validity_weeks'):
        assert corrected['result'][field] == source['version']['result'][field]
    state = capture(factory)
    assert len(state.sources) == 2
    for index, target_state in enumerate((prior_state, state)):
        current = capture(factory)
        with factory.begin() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            restore_ranking_revision_state(session, target_state.model_dump_json(), expected_fingerprint=target_state.fingerprint,
                expected_current_fingerprint=current.fingerprint, command_id=f'corrected-recovery-{index}', run_id='run', branch_id='empty')
        assert capture(factory).fingerprint == target_state.fingerprint
    assert client.get(PREFIX + '/0/3/sources').json()['sources'][0]['version'] == corrected
    before = dump(path)
    assert confirm(client, 'week', req, candidate['fingerprint']) == (201, candidate)
    assert dump(path) == before


@pytest.mark.parametrize('damage', ['timing', 'stale_predecessor'])
def test_invalid_result_correction_rolls_back_zero_batch(api, damage):
    from beta_engine.domain.rankings.result_history import RankingResultVersion
    from beta_engine.infrastructure.db.ranking_result_history import OfficialRankingResultStore

    client, factory, path, *_ = api
    assert client.post(PREFIX + '/prepare/initial', json=initial()).status_code == 201
    source = RankingResultVersion.model_validate_json(json.dumps(dict(run_id='run', branch_id='empty',
        effective_week={'season_index':0,'week':2}, previous_fingerprint=None,
        result=dict(edition_id='edition', player_id='p', source_fingerprint='award', main_points=100,
                    completed_week={'season_index':0,'week':1}, first_publication_week={'season_index':0,'week':2}))))
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        OfficialRankingResultStore(session).append(source)
    assert client.post(PREFIX + '/prepare/week', json=weekly() | {'zero_versions':[]}).status_code == 201
    req = weekly()
    target = {'season_index':0,'week':3}
    req['command_id'] = 'bad-correction'
    req['context'].update(completed_week={'season_index':0,'week':2}, target_week=target)
    req['zero_versions'][0]['effective_week'] = target
    req['zero_versions'][0]['zero']['effective_week'] = target
    correction = source.model_dump(mode='json') | {'effective_week':target, 'previous_fingerprint':source.fingerprint}
    if damage == 'timing':
        correction['result']['validity_weeks'] = 62
    else:
        correction['previous_fingerprint'] = '0'*64
    req['corrections'] = [correction]
    before = dump(path)
    assert client.post(PREFIX + '/prepare/week/preview', json=req).status_code == 409
    assert client.post(PREFIX + '/prepare/week', json=req).status_code == 409
    assert dump(path) == before
