"""Actual seeded group results and non-played W/O through HTTP/SQLite."""

import pytest

from beta_engine.infrastructure.db.calendar_sporting_checkpoint import load_checkpoint
from tests.api.test_calendar_global_slots import copy_database
from tests.api.test_calendar_native_groups import ready_groups
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    tour_url,
)
from tests.api.test_player_generation_calendar_gate import _dump
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


@pytest.fixture(scope='module')
def withdrawal_source(tmp_path_factory):
    path = tmp_path_factory.mktemp('native-wo-source') / 'tour.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        ready_groups(server, groups=1, hybrid=False, group_win_points=0)
        execute(server, command(inspect(server), 'next-slot', name='real-first-group-day'))
        save_tour(server)
    # Clone this source with SQLite backup below: the latest committed Save
    # can still be in WAL while a pooled connection keeps the source open.
    return path


def checkpoint(server):
    with server.app.state.runtime.repository._session_factory() as session:
        return load_checkpoint(session, run_id='run', branch_id='branch')


def test_withdrawal_real_results_walkover_save_reopen_and_no_match_effects(
    tmp_path, withdrawal_source, monkeypatch,
):
    path = tmp_path / 'withdrawal.db'
    copy_database(withdrawal_source, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        view = inspect(server)
        # Pick the actual first-day loser, without editing any simulated result.
        cp = checkpoint(server)
        previous = tuple(m.model_dump(mode='json') for m in cp.played_continuations)
        pid = cp.played_continuations[-1].result.loser_player_id
        cmd = command(view, 'withdraw-group', edition_id='native-groups',
            data={'player_id': pid, 'reason_category': 'illness', 'note': 'Reviewed withdrawal'})
        before = _dump(path)
        code, preview = _request('POST', tour_url(server) + '/preview', cmd)
        assert code == 200, preview
        assert _dump(path) == before, 'Preview must not install a withdrawal or W/O'
        request = {'command': cmd, 'expected_preview_fingerprint': preview['preview_fingerprint'],
                   'explicit_confirmation': True}
        import beta_engine.application.calendar_tour_service as service
        original = service._fault_injection_point

        def fail_after_write(name):
            if name == 'after_group_withdrawal_write':
                raise ValueError('injected withdrawal rollback')
            return original(name)

        monkeypatch.setattr(service, '_fault_injection_point', fail_after_write)
        assert _request('POST', tour_url(server) + '/execute', request)[0] == 409
        assert _dump(path) == before
        monkeypatch.setattr(service, '_fault_injection_point', original)
        code, result = _request('POST', tour_url(server) + '/execute', request)
        assert code == 201, result
        assert len(result['remaining_walkover_match_ids']) == 2
        assert _request('POST', tour_url(server) + '/execute', request) == (201, result)
        assert tuple(m.model_dump(mode='json') for m in checkpoint(server).played_continuations) == previous
        save_tour(server)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        view = inspect(server)
        assert view['groups']['native-groups']['withdrawals'][0]['player_id'] == pid
        wo = next(m for m in view['next_slot']['matches'] if m.get('completion') == 'walkover')
        players = checkpoint(server).players
        execute(server, command(view, 'next-match', name='first-actual-walkover', data={'match_id': wo['match_id']}))
        assert checkpoint(server).players == players, 'A non-played match has no physical effects'
        assert tuple(m.model_dump(mode='json') for m in checkpoint(server).played_continuations) == previous
        save_tour(server)
        for index in range(3):
            if inspect(server)['next_slot'] is None:
                break
            execute(server, command(inspect(server), 'next-slot', name=f'resolve-remaining-{index}'))
            save_tour(server)
        cp = checkpoint(server)
        event = next(t for t in cp.tournaments if t.tournament_id == 'native-groups')
        assert len(event.matches) == 4 and len(event.walkovers) == 2
        assert len(cp.played_continuations) == 4
        assert all(m.result.rally_log.events for m in event.matches)
        assert {m.match_id for m in event.matches}.isdisjoint(m.match_id for m in event.walkovers)
        assert all(r.result.scoreline == 'W/O' and r.result.loser_player_id == pid for r in event.walkovers)
        receipts = event.standings.source_results
        assert sum(r.result_kind == 'walkover' for r in receipts) == 2
        assert all(not r.games for r in receipts if r.result_kind == 'walkover')
        assert sum(r.walkovers_received for g in event.standings.groups for r in g.rows) == 2
        execute(server, command(inspect(server), 'confirm-result', edition_id='native-groups'))
        save_tour(server)
        execute(server, command(inspect(server), 'transition', name='publish-nonplayed-group-results'))
        save_tour(server)
        final = inspect(server)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        assert inspect(server)['state'] == final['state']


def test_nested_fork_retains_partial_walkover_without_reowning_source(tmp_path, withdrawal_source):
    from tests.api.test_native_fork_public_continuation import Tour, fork
    path = tmp_path / 'fork-withdrawal.db'
    copy_database(withdrawal_source, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        original = inspect(server)
        pid = checkpoint(server).played_continuations[-1].result.loser_player_id
        created = fork(server, original['saved_head_revision_id'], name='Withdrawal target')
        target = Tour(server, created['branch_id'])
        target.execute('withdraw-group', 'target-withdrawal', edition_id='native-groups',
            data={'player_id':pid, 'reason_category':'injury'})
        target.save()
        wo = next(m for m in target.view()['next_slot']['matches'] if m.get('completion') == 'walkover')
        target.execute('next-match', 'target-wo', data={'match_id':wo['match_id']})
        partial = target.save()
        nested_created = fork(server, partial['revision_id'], branch=target.branch, name='Nested W/O target')
        nested = Tour(server, nested_created['branch_id'])
        for index in range(2):
            nested.execute('next-slot', f'nested-remaining-{index}')
            nested.save()
        group = nested.view()['groups']['native-groups']
        assert len(group['walkovers']) == 2
        assert len(nested.view()['edition_evidence']['native-groups']['matches']) == 4
        assert inspect(server) == original, 'Fork W/O must not alter the source branch'
        assert target.view()['next_slot']['remaining'] == 1
        nested.execute('confirm-result', 'nested-confirm', edition_id='native-groups')
        nested.save()
        final = nested.view()
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        assert Tour(server, nested_created['branch_id']).view()['state'] == final['state']


def test_worker_uses_nonplayed_results_and_explicit_manual_saves(tmp_path, withdrawal_source):
    from tests.api.test_native_full_simulation_tasks import resume, reviewed, start
    path = tmp_path / 'worker-withdrawal.db'
    copy_database(withdrawal_source, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        pid = checkpoint(server).played_continuations[-1].result.loser_player_id
        execute(server, command(inspect(server), 'withdraw-group', edition_id='native-groups',
            data={'player_id':pid, 'reason_category':'personal'}))
        save_tour(server)
        task = start(server, reviewed(server, {'season_index':0,'week':5}, name='withdrawal-worker'))
        original_id = task['task_id']
        for index in range(2):
            assert task['checkpoint'] == 'native_manual_save_required', task
            save_tour(server)
            task = resume(server, task, f'worker-slot-saved-{index}')
        assert task['checkpoint'] == 'native_result_review_required', task
        execute(server, command(inspect(server), 'confirm-result', edition_id='native-groups'))
        save_tour(server)
        task = resume(server, task, 'worker-result-reviewed')
        assert task['checkpoint'] == 'native_manual_save_required', task
        save_tour(server)
        task = resume(server, task, 'worker-publication-saved')
        assert task['state'] == 'target_reached' and task['task_id'] == original_id, task
        event = next(t for t in checkpoint(server).tournaments if t.tournament_id == 'native-groups')
        assert len(event.matches) == 4 and len(event.walkovers) == 2


def test_withdrawal_rejects_stale_foreign_duplicate_and_rehashed_evidence(tmp_path, withdrawal_source):
    import json

    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )
    path = tmp_path / 'negative-withdrawal.db'
    copy_database(withdrawal_source, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        original = inspect(server)
        pid = checkpoint(server).played_continuations[-1].result.loser_player_id
        cmd = command(original, 'withdraw-group', edition_id='native-groups',
            data={'player_id':pid,'reason_category':'illness'})
        bad = [{**cmd,key:'f'*64} for key in (
            'expected_saved_head','expected_checkpoint_fingerprint','expected_tour_fingerprint')]
        bad += [{**cmd,'edition_id':'foreign'}, {**cmd,'data':{'player_id':'foreign','reason_category':'illness'}},
                {**cmd,'data':{'player_id':pid}}, {**cmd,'data':{**cmd['data'],'reason_category':'invented'}}]
        before = _dump(path)
        for value in bad:
            assert _request('POST',tour_url(server)+'/preview',value)[0] == 409
            assert _dump(path) == before
        execute(server,cmd)
        save_tour(server)
        duplicate = command(inspect(server),'withdraw-group',name='duplicate-withdrawal',
            edition_id='native-groups',data=cmd['data'])
        before = _dump(path)
        assert _request('POST',tour_url(server)+'/preview',duplicate)[0] == 409
        assert _dump(path) == before
        repo = server.app.state.runtime.repository
        with repo._session_factory.begin() as session:
            cp = session.get(CalendarPlayerSportingCheckpointModel,('run','branch'))
            tour = session.get(CalendarTourAuthorityModel,('run','branch'))
            saved = cp.payload_json,cp.fingerprint,tour.payload_json,tour.fingerprint
            body = json.loads(cp.payload_json)
            body['events'][-1]['group_withdrawals'][0]['reason_category'] = 'travel'
            cp.payload_json,cp.fingerprint = json.dumps(body),canonical_hash(body)
            changed = json.loads(tour.payload_json);changed['checkpoint_fingerprint'] = cp.fingerprint
            tour.payload_json,tour.fingerprint = json.dumps(changed),canonical_hash(changed)
        assert _request('GET',tour_url(server))[0] == 409, 'Declared hashes cannot replace actual command replay'
        with repo._session_factory.begin() as session:
            cp = session.get(CalendarPlayerSportingCheckpointModel,('run','branch'))
            tour = session.get(CalendarTourAuthorityModel,('run','branch'))
            cp.payload_json,cp.fingerprint,tour.payload_json,tour.fingerprint = saved
        assert inspect(server)['groups']['native-groups']['withdrawals'][0]['reason_category'] == 'illness'


def test_walkover_and_actual_match_order_share_frozen_input_across_restart(tmp_path, withdrawal_source):
    common = tmp_path / 'common-withdrawn.db'
    copy_database(withdrawal_source,common)
    with ApiServer(database_url=f'sqlite:///{common}') as server:
        pid = checkpoint(server).played_continuations[-1].result.loser_player_id
        execute(server,command(inspect(server),'withdraw-group',edition_id='native-groups',
            data={'player_id':pid,'reason_category':'illness'}))
        save_tour(server)
        mids = [m['match_id'] for m in inspect(server)['next_slot']['matches']]
    outcomes = []
    bulk = tmp_path / 'bulk.db'
    copy_database(common,bulk)
    with ApiServer(database_url=f'sqlite:///{bulk}') as server:
        execute(server,command(inspect(server),'next-slot',name='batch-resolve'))
        outcomes.append(checkpoint(server))
    reverse = tmp_path / 'reverse.db'
    copy_database(common,reverse)
    with ApiServer(database_url=f'sqlite:///{reverse}') as server:
        execute(server,command(inspect(server),'next-match',name='reverse-first',data={'match_id':mids[-1]}))
        frozen = inspect(server)['next_slot']['snapshot_fingerprint']
        save_tour(server)
    with ApiServer(database_url=f'sqlite:///{reverse}') as server:
        assert inspect(server)['next_slot']['snapshot_fingerprint'] == frozen
        execute(server,command(inspect(server),'next-match',name='reverse-last',data={'match_id':mids[0]}))
        outcomes.append(checkpoint(server))
    assert outcomes[0] == outcomes[1], 'W/O and real matches must preserve complete frozen sporting evidence'
