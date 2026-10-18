"""Actual Saved owner -> repeated real matches -> manual Save/restart/replay/restore."""
import pytest
from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint, COMPONENT_KEY
from tests.api.test_calendar_population_sporting_checkpoint import prepare, play, save, restore
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.api.test_player_generation_calendar_gate import _dump

pytestmark = pytest.mark.pr_critical


def root(server):
    return base(server).replace('/calendar-opening-knockout', '/calendar-continuation')


def command(view, first, second, name='after-ko'):
    return dict(command_id=name, match_id=name,
        expected_saved_head=view['saved_head_revision_id'],
        expected_checkpoint_fingerprint=view['checkpoint_fingerprint'],
        player_a_id=first, player_b_id=second, seed=922, operator_label='Admin',
        audit_reason='Continue with actual previously played state')


def save_continuation(server, played):
    code, view = _request('GET', root(server))
    assert code == 200 and not view['saved'], view
    code, saved = _request('POST', root(server) + '/save', dict(expected_draft_version=view['draft_version'],
        expected_calendar_sporting_fingerprint=played['checkpoint_fingerprint']))
    assert code == 201, saved
    return saved['saved_revision']


@pytest.mark.parametrize('clock', [RunCalendar(52,35,2030,3), RunCalendar(80,80,2100,3)])
def test_saved_terminal_state_is_consumed_by_two_successive_real_exhibitions(tmp_path, clock):
    path = tmp_path / 'continue.db'; db = f'sqlite:///{path}'
    with ApiServer(database_url=db) as server:
        repo, head = prepare(server, clock)
        knockout, _ = play(server, head)
        assert not _request('GET', root(server))[1]['can_play']
        opening = save(server, knockout)
        _, view = _request('GET', root(server))
        assert view['can_play'] and view['saved']
        with repo._session_factory() as session:
            initial = load_checkpoint(session, run_id='run', branch_id='branch')
        finalist = knockout['knockout']['matches'][-1]['result']['winner_player_id']
        outside = next(p.player_id for p in initial.players if p.player_id not in knockout['knockout']['entrant_ids'])
        cmd = command(view, finalist, outside)
        before = _dump(path)
        assert _request('POST', root(server) + '/simulate', {**cmd, 'expected_checkpoint_fingerprint':'f'*64})[0] == 409
        assert _dump(path) == before
        code, first = _request('POST', root(server) + '/simulate', cmd)
        assert code == 201, first
        m = first['match']; assert m['sequence'] == 1
        before_player = next(p for p in initial.players if p.player_id == finalist)
        projection = m['canonical_projections'][0]
        assert projection['canonical_attributes'] == [list(a) for a in before_player.attributes]
        assert projection['current_form'] == before_player.current_form
        assert projection['long_term_fatigue'] == before_player.long_term_fatigue > 0
        assert m['input_context']['player_a']['fatigue_modifier'] < 0
        assert m['canonical_projections'][1]['long_term_fatigue'] == 0
        assert _request('POST', root(server) + '/simulate', cmd) == (201, first)
        _, unsaved = _request('GET', root(server))
        assert not unsaved['can_play'] and not unsaved['saved']
        assert _request('POST', root(server) + '/simulate', command(unsaved, outside, finalist, 'blocked'))[0] == 409
        saved_first = save_continuation(server, first)
        component = saved_first['payload']['content'][COMPONENT_KEY]
        assert component['state']['schema_version'] == 'calendar_sporting_checkpoint.v2'
        assert len(component['state']['continuations']) == 1
        assert saved_first['payload']['content']['calendar_standalone_match'] == opening['payload']['content']['calendar_standalone_match']
        _, after_first = _request('GET', root(server))
        with repo._session_factory() as session:
            middle = load_checkpoint(session, run_id='run', branch_id='branch')
        for old, new in zip(initial.players, middle.players):
            if old.player_id not in {finalist, outside}: assert old == new
            assert old.attributes == new.attributes
        second_cmd = command(after_first, outside, finalist, 'second')
        code, second = _request('POST', root(server) + '/simulate', second_cmd)
        assert code == 201, second
        assert second['match']['sequence'] == 2
        middle_outsider = next(p for p in middle.players if p.player_id == outside)
        assert second['match']['canonical_projections'][0]['long_term_fatigue'] == middle_outsider.long_term_fatigue > 0
        saved_second = save_continuation(server, second)
        import copy
        from beta_engine.domain.run_packages import canonical_hash
        from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
        for fault in ('missing', 'reverse', 'reset', 'projection', 'review', 'downgrade'):
            damaged = copy.deepcopy(saved_second['payload'])
            cp = damaged['content'][COMPONENT_KEY]; state = cp['state']
            if fault == 'missing': state['continuations'].pop()
            elif fault == 'reverse': state['continuations'].reverse()
            elif fault == 'reset': state['players'][0]['long_term_fatigue'] = 99
            elif fault == 'projection': state['continuations'][0]['canonical_projections'][0]['long_term_fatigue'] = 0
            elif fault == 'review': state['continuations'][0]['source_saved_head'] = 'invented'
            elif fault == 'downgrade': state['schema_version'] = 'calendar_sporting_checkpoint.v1'
            cp['fingerprint'] = canonical_hash(state)
            with pytest.raises(ValueError):
                load_saved_calendar_match(damaged, run_id='run', branch_id='branch')

        assert _request('POST', root(server) + '/simulate', cmd) == (201, first)
        assert _request('GET', root(server) + '/after-ko/replay')[1]['exact_replay']
        assert _request('GET', root(server) + '/second/replay')[1]['exact_replay']
        assert _request('GET', base(server))[1]['population_sporting_checkpoint']['saved']
        assert _request('POST', root(server) + '/simulate', {**second_cmd, 'seed':923})[0] == 409
        assert repo.verify_branch_saved_revision_hash(revision_id=opening['revision_id'])
    with ApiServer(database_url=db) as restarted:
        assert _request('GET', root(restarted))[1]['matches'][-1]['saved']
        assert _request('GET', root(restarted) + '/second/replay')[1]['exact_replay']
        back = restore(restarted, opening['revision_id'])
        assert back['payload']['content'][COMPONENT_KEY]['state']['schema_version'] == 'calendar_sporting_checkpoint.v1'
        assert _request('GET', root(restarted))[1]['matches'] == []
        forward = restore(restarted, saved_second['revision_id'])
        assert forward['payload']['content'][COMPONENT_KEY] == saved_second['payload']['content'][COMPONENT_KEY]
        assert _request('GET', root(restarted) + '/after-ko/replay')[1]['exact_replay']


def test_concurrent_commands_and_injected_write_failure_cannot_duplicate_or_partly_update_state(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from beta_engine.application import calendar_continuation_service as service
    path = tmp_path / 'atomic-continue.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo, head = prepare(server, RunCalendar(52,1,2030,3))
        knockout, _ = play(server, head); save(server, knockout)
        _, view = _request('GET', root(server)); cmd = command(view, *view['player_ids'][:2])
        before = _dump(path)
        original = service.replace_checkpoint
        def fail(*args, **kwargs):
            original(*args, **kwargs)
            raise ValueError('Injected failure after native owner replacement')
        monkeypatch.setattr(service, 'replace_checkpoint', fail)
        assert _request('POST', root(server) + '/simulate', cmd)[0] == 409
        assert _dump(path) == before
        monkeypatch.setattr(service, 'replace_checkpoint', original)
        commands = [cmd, {**cmd, 'command_id':'rival', 'match_id':'rival'}]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda c: _request('POST', root(server) + '/simulate', c), commands))
        assert sorted(c for c, _ in outcomes) == [201, 409], outcomes
        assert len(_request('GET', root(server))[1]['matches']) == 1
        receipt = next(r for c, r in outcomes if c == 201)
        assert _request('POST', root(server) + '/save', {
            'expected_draft_version':view['draft_version'], 'expected_calendar_sporting_fingerprint':'f'*64})[0] == 409
        save_continuation(server, receipt)


def test_saved_health_change_and_horizon_extension_do_not_rewrite_continued_match(tmp_path):
    from tests.api.test_calendar_health_edit import baseline, edit_request, review, commit, save as save_health
    from tests.api.test_calendar_knockout_health_flow import command as knockout_command, save_knockout
    from tests.api.test_calendar_sporting_horizon_extension import extension, extend
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'continued-health.db'}") as server:
        repo, health_url, player, _ = baseline(server, RunCalendar(80,80,2100,3))
        edit = edit_request(player); assert commit(health_url, edit, review(health_url, edit))[0] == 200
        save_health(server)
        _, view = _request('GET', base(server))
        code, knockout = _request('POST', base(server) + '/simulate', knockout_command(view))
        assert code == 201, knockout
        save_knockout(server, knockout)
        _, v = _request('GET', root(server))
        ids = [player['player']['player_id'], next(p for p in v['player_ids'] if p != player['player']['player_id'])]
        cmd = command(v, *ids)
        code, played = _request('POST', root(server) + '/simulate', cmd)
        assert code == 201, played
        health_fp = played['match']['source_health_fingerprint']
        assert played['match']['effective_health']['player_profiles'][0]['highest_current_severity'] == 25
        assert not played['match']['effective_health']['numeric_effect_applied']
        saved = save_continuation(server, played)
        current = _request('GET', health_url)[1]
        correction = edit_request(current); correction.update(command_id='continued-medical-correction', mode='current_state_correction')
        correction['records'][0]['severity'] = 40
        assert commit(health_url, correction, review(health_url, correction))[0] == 200
        # Frozen historical replay is independent of unsaved current medicine.
        assert _request('GET', root(server) + '/after-ko/replay')[1]['exact_replay']
        assert _request('GET', root(server))[0] == 409  # new-play readiness stays guarded
        save_health(server)
        assert _request('GET', root(server) + '/after-ko/replay')[1]['exact_replay']
        code, checked = extension(server, 4); assert code == 200 and checked['can_save'], checked
        code, _ = extend(server, checked); assert code == 200
        _, current = _request('GET', root(server))
        code, second = _request('POST', root(server) + '/simulate', command(current, *ids, 'extended-match'))
        assert code == 201, second
        assert second['match']['week']['calendar']['season_count'] == 4
        assert second['match']['source_health_fingerprint'] != health_fp
        save_continuation(server, second)
        assert _request('POST', root(server) + '/simulate', cmd) == (201, played)
        assert repo.get_branch_saved_revision(revision_id=saved['revision_id']).payload == saved['payload']
