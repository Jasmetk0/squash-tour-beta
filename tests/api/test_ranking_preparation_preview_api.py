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


@pytest.mark.smoke
def test_authoritative_week_inputs_are_server_resolved_and_preview_is_read_only(tmp_path):
    from test_saved_revision_history_api import ApiServer, _create_run, _request
    path = tmp_path / 'authority.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        run_id, branch_id, revision_id = _create_run(server, display_name='Authority workflow')
        root = f'{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates'
        bootstrap = initial() | {'run_id': run_id, 'branch_id': branch_id}
        assert _request('POST', root + '/prepare/initial', bootstrap)[0] == 201
        authority = {
            'run_id': run_id, 'branch_id': branch_id, 'base_revision_id': revision_id,
            'completed_week': {'season_index': 0, 'week': 1},
            'target_week': {'season_index': 0, 'week': 2},
            'players': bootstrap['players'], 'policy': bootstrap['policy'],
            'provenance': 'Explicit independent Run roster/policy snapshot',
            'adopted_by_command_id': 'adopt-week-2', 'audit': bootstrap['audit'],
        }
        assert _request('POST', root + '/transition-authorities', authority)[0] == 201
        request_body = {'command_id': 'authority-week-2', 'target_week': authority['target_week'],
                        'tournaments': [], 'audit': bootstrap['audit']}
        before = dump(path)
        status, preview = _request('POST', root + '/prepare/week/authoritative/preview', request_body)
        assert status == 200 and dump(path) == before
        req = request.Request(root + '/prepare/week/authoritative', data=json.dumps(request_body).encode(), method='POST',
            headers={'Content-Type': 'application/json',
                     'X-Ranking-Preview-Fingerprint': preview['candidate']['fingerprint'],
                     'X-Ranking-Preview-Request': preview['request_fingerprint']})
        with request.urlopen(req) as response:
            assert response.status == 201
        forged = request_body | {'players': []}
        assert _request('POST', root + '/prepare/week/authoritative/preview', forged)[0] in (409, 422)
        status, review = _request('GET', root + '/save/preview')
        assert status == 200 and review['can_save']
        status, saved = _request('POST', root + '/save', {
            'expected_draft_version': review['draft_version'],
            'expected_ranking_fingerprint': review['ranking_fingerprint'],
        })
        assert status == 201
        state = saved['saved_revision']['payload']['content']['ranking_preparation']['state']
        assert state['transition_authorities'][0]['base_revision_id'] == revision_id
    with ApiServer(database_url=f'sqlite:///{path}') as reopened:
        root = f'{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates'
        assert _request('GET', root + '/save/preview')[1]['has_unsaved_changes'] is False
        assert _request('POST', root + '/prepare/week/authoritative', request_body)[0] == 201


@pytest.mark.smoke
def test_real_tournament_adoption_candidate_save_reopen_and_restore(tmp_path):
    """Production tournament files -> HTTP -> SQLite -> Saved Revision recovery."""
    import sys
    from pathlib import Path
    from test_saved_revision_history_api import ApiServer, _create_run, _request
    sys.path.insert(0, str(Path(__file__).parents[1] / 'application'))
    from test_season_event_simulation_service import make_simulation_service
    from beta_engine.application.season_event_simulation_service import SimulateOneEventRequest

    simulation, event_id = make_simulation_service(tmp_path / 'sport')
    outcome = simulation.simulate_one_event(
        event_id=event_id, request=SimulateOneEventRequest(dry_run=False, seed=71)
    )
    assert outcome.report is not None and not outcome.validation_errors
    points = simulation.point_awards_service
    result = points.result_service.get_event_result(event_id=event_id).result_package
    awards = points.get_event_point_awards(event_id=event_id).award_package
    assert result is not None and awards is not None
    path = tmp_path / 'owned-workflow.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        app = server.app
        app.state.season_active_players_config_path = points.active_players_service.active_players_path
        app.state.season_calendar_registry_path = points.calendar_service.calendar_registry_path
        app.state.tournament_templates_config_path = points.template_service.config_path
        app.state.season_matches_registry_path = points.result_service.match_service.matches_path
        app.state.season_event_results_registry_path = points.result_service.results_path
        app.state.season_point_awards_registry_path = points.awards_path
        app.state.points_config_path = points.points_config_path
        run_id, branch_id, initial_revision = _create_run(server, display_name='Owned tournament workflow')
        root = f'{server.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates'
        players = [dict(player_id=p.player_id, tie_break_token=p.player_id,
                        tour_entry_week={'season_index':0, 'week':1}) for p in result.player_results]
        bootstrap = dict(kind='initial_ranking.v1', command_id='owned-bootstrap', run_id=run_id,
            branch_id=branch_id, target_week={'season_index':0,'week':1},
            policy={'policy_id':'owned-policy'}, players=players, discipline='none',
            audit={'actor_label':'Admin operator', 'reason':'Establish pre-tournament baseline'})
        assert _request('POST', root + '/prepare/initial', bootstrap)[0] == 201
        if result.season_week > 1:
            assert result.season_week == 2
            bridge = dict(command_id='prepare-pre-event-week', tournaments=[], corrections=[],
                context=dict(run_id=run_id, branch_id=branch_id,
                    completed_week={'season_index':0,'week':1}, target_week={'season_index':0,'week':2},
                    policy={'policy_id':'owned-policy'}, players=players, discipline='none'),
                audit={'actor_label':'Admin operator', 'reason':'Prepare the event completion week'})
            assert _request('POST', root + '/prepare/week', bridge)[0] == 201
        binding = dict(run_id=run_id, branch_id=branch_id, edition_id='owned-edition', event_id=event_id,
            completed_week={'season_index':0,'week':result.season_week}, first_publication_week={'season_index':0,'week':result.season_week + 1},
            validity_weeks=61, ranking_status='ranked',
            expected_result_fingerprint=result.metadata.build_fingerprint,
            expected_award_fingerprint=awards.metadata.build_fingerprint)
        weekly_command = dict(command_id='adopt-and-rank', tournaments=[binding], corrections=[],
            context=dict(run_id=run_id, branch_id=branch_id,
                    completed_week={'season_index':0,'week':result.season_week},
                    target_week={'season_index':0,'week':result.season_week + 1},
                policy={'policy_id':'owned-policy'}, players=players, discipline='none'),
            audit={'actor_label':'Admin operator', 'reason':'Review and prepare Official candidate'})
        before = dump(path)
        status, preview = _request('POST', root + '/prepare/week/preview', weekly_command)
        assert status == 200, preview
        assert dump(path) == before
        req = request.Request(root + '/prepare/week', data=json.dumps(weekly_command).encode(), method='POST',
            headers={'Content-Type':'application/json',
                     'X-Ranking-Preview-Fingerprint':preview['candidate']['fingerprint'],
                     'X-Ranking-Preview-Request':preview['request_fingerprint']})
        with request.urlopen(req) as response:
            candidate = json.loads(response.read())
        assert {row['player_id']: row['points'] for row in candidate['snapshot']['rows']} == {
            award.player_id: award.ranking_points_awarded for award in awards.awards
        }
        # Lost-response retry is byte-for-byte idempotent and no longer reads files.
        points.awards_path.write_text('changed after adoption')
        with request.urlopen(req) as response:
            assert json.loads(response.read()) == candidate
        save_status, review = _request('GET', root + '/save/preview')
        assert save_status == 200 and review['can_save']
        save_status, saved = _request('POST', root + '/save', {
            'expected_draft_version':review['draft_version'],
            'expected_ranking_fingerprint':review['ranking_fingerprint']})
        assert save_status == 201
        saved_revision = saved['saved_revision']['revision_id']
        state = saved['saved_revision']['payload']['content']['ranking_preparation']['state']
        assert state['tournament_sources'][0]['binding'] == binding
        assert state['tournament_sources'][0]['awards']['metadata']['build_fingerprint'] == awards.metadata.build_fingerprint
    with ApiServer(database_url=f'sqlite:///{path}') as reopened:
        root = f'{reopened.base_url}/admin/runs/{run_id}/branches/{branch_id}/ranking-candidates'
        assert _request('GET', root + f'/0/{result.season_week + 1}')[1] == candidate
        # Restore the parent removes adoption; restoring the saved revision reinstalls all evidence.
        restore_root = f'{reopened.base_url}/run-containers/{run_id}/branches/{branch_id}/saved-revisions'
        restore_request = {'expected_head_saved_revision_id':saved_revision,
            'expected_draft_version':saved['working_draft']['draft_version'],
            'expected_current_viewer_branch_id':branch_id, 'explicit_confirmation':True}
        status, restored = _request('POST', restore_root + f'/{initial_revision}/restore', restore_request)
        assert status == 201
        assert _request('GET', root)[1]['candidates'] == []
        restore_request = {'expected_head_saved_revision_id':restored['saved_revision']['revision_id'],
            'expected_draft_version':restored['working_draft']['draft_version'],
            'expected_current_viewer_branch_id':branch_id, 'explicit_confirmation':True}
        status, _ = _request('POST', restore_root + f'/{saved_revision}/restore', restore_request)
        assert status == 201
        assert _request('GET', root + f'/0/{result.season_week + 1}')[1] == candidate


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
