"""Native groups through real HTTP, SQLite and MatchEngine, never inserted scores."""
import os

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.tournaments.format_authority import TournamentGroupRulesPolicy
from tests.api.test_calendar_tour_flow import (
    command,
    execute,
    inspect,
    save_tour,
    setup,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def configuration(group_count=2, group_size=4, *, hybrid=True, width=52):
    rules = TournamentGroupRulesPolicy(run_id='run', branch_id='branch',
        effective_from_season_index=0, default_match_best_of=3, adopted_by_command_id='group-rules-v1')
    crossings = []
    if hybrid:
        pairs = [(1, 1, 2, 2), (2, 1, 1, 2)] if group_count == 2 else [
            (1, 1, 2, 2), (3, 1, 4, 2), (2, 1, 1, 2), (4, 1, 3, 2)]
        crossings = [{'match_index': i, 'top': {'group_index': a, 'finishing_position': b},
                      'bottom': {'group_index': c, 'finishing_position': d}}
                     for i, (a, b, c, d) in enumerate(pairs, 1)]
    return {'schema_version': 'native_group_configuration.v1',
        'format_kind': 'groups_knockout' if hybrid else 'groups',
        'rules': rules.model_dump(mode='json'), 'knockout_best_of': 5,
        'played_group_win_points': 7,
        'groups': {'group_count': group_count, 'group_size': group_size,
            'match_best_of': 3, 'rules_source_kind': 'season_policy',
            'group_rules_policy_fingerprint': rules.fingerprint,
            'group_rules_effective_from_season_index': 0,
            'advancing_per_group': 2 if hybrid else 0, 'knockout_crossings': crossings}}


def ready_groups(server, *, groups=2, size=4, hybrid=True, width=None, parallel=False):
    width = width or int(os.environ.get("NATIVE_GROUP_CALENDAR", "52"))
    repo, _ = setup(server, RunCalendar(width, 1, 2030, 2), groups * size + (4 if parallel else 0))
    view = inspect(server)
    week = view['state']['week']
    execute(server, command(view, 'create-edition', name='create-groups', data={
        'schema_version': 'calendar_tournament_edition.v3', 'simulation_seed': 891,
        'edition_id': 'native-groups', 'name': 'Configured groups',
        'week': {**week, 'week': 4}, 'announcement_week': {**week, 'week': 3},
        'start_slot': 1, 'main_entrant_count': groups * size, 'ranked': True,
        'validity_weeks': width,
        'point_table': ({'champion': 100, 'finalist': 60, 'semifinal': 30,
                         **({'quarterfinal': 15} if groups == 4 else {})} if hybrid else {}),
        'group_configuration': configuration(groups, size, hybrid=hybrid, width=width),
    }))
    save_tour(server)
    if parallel:
        execute(server, command(inspect(server), 'create-edition', name='create-parallel', data={
            'schema_version': 'calendar_tournament_edition.v2', 'simulation_seed': 182,
            'edition_id': 'parallel-knockout', 'name': 'Parallel original knockout',
            'week': {**week, 'week': 4}, 'announcement_week': {**week, 'week': 3},
            'start_slot': 1, 'main_entrant_count': 4, 'ranked': True,
            'validity_weeks': width, 'point_table': {'champion': 100, 'finalist': 60, 'semifinal': 30},
        }))
        save_tour(server)
    for target in (3, 4):
        execute(server, command(inspect(server), 'transition', name=f'week-{target}'))
        save_tour(server)
    execute(server, command(inspect(server), 'submit', edition_id='native-groups',
        data={'player_ids': [p['player_id'] for p in inspect(server)['players'][:groups * size]]}))
    for action in ('approve', 'draw'):
        execute(server, command(inspect(server), action, edition_id='native-groups'))
    save_tour(server)
    if parallel:
        execute(server, command(inspect(server), 'submit', name='parallel-submit', edition_id='parallel-knockout',
            data={'player_ids': [p['player_id'] for p in inspect(server)['players'][-4:]]}))
        for action in ('approve', 'draw'):
            execute(server, command(inspect(server), action, name='parallel-' + action, edition_id='parallel-knockout'))
        save_tour(server)
    return repo


def test_two_groups_real_fifteen_matches_save_restart_and_points(tmp_path):
    path = tmp_path / 'groups.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        ready_groups(server)
        result, request = execute(server, command(inspect(server), 'next-match', name='first-group-match'))
        assert result['remaining'] == 3
        assert _request('POST', server.base_url + '/admin/runs/run/branches/branch/calendar-tour/execute', request) == (201, result)
        view = inspect(server)
        frozen = view['next_slot']['snapshot_fingerprint']
        save_tour(server)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        view = inspect(server)
        assert view['next_slot']['snapshot_fingerprint'] == frozen
        for index in range(5):
            execute(server, command(inspect(server), 'next-slot', name=f'complete-slot-{index}'))
            save_tour(server)
        view = inspect(server)
        assert view['state']['editions'][0]['tournament_fingerprint']
        group = view['groups']['native-groups']
        assert [len(g['rows']) for g in group['standings']['groups']] == [4, 4]
        assert len(group['bracket']['matches']) == 3
        assert len(view['edition_evidence']['native-groups']['matches']) == 15
        execute(server, command(view, 'confirm-result', edition_id='native-groups'))
        save_tour(server)
        execute(server, command(inspect(server), 'transition', name='publish-groups'))
        save_tour(server)
        final = inspect(server)
        awards = final['state']['rankings'][-1]['rows']
        assert len(awards) == 8
        assert all(len(row['counted_results']) == 1 for row in awards)
        assert awards[0]['points'] >= 100


@pytest.mark.parametrize('groups,size,hybrid,match_count', [(4, 4, True, 31), (2, 4, False, 12), (1, 4, False, 6)])
def test_configured_four_groups_and_pure_groups(tmp_path, groups, size, hybrid, match_count):
    path = tmp_path / 'configured.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo = ready_groups(server, groups=groups, size=size, hybrid=hybrid)
        index = 0
        while inspect(server)['next_slot'] is not None:
            execute(server, command(inspect(server), 'next-slot', name=f'actual-slot-{index}'))
            save_tour(server)
            index += 1
        from beta_engine.infrastructure.db.calendar_sporting_checkpoint import (
            load_checkpoint,
        )
        with repo._session_factory() as session:
            cp = load_checkpoint(session, run_id='run', branch_id='branch')
        event = next(e for e in cp.tournaments if e.tournament_id == 'native-groups')
        assert len(event.matches) == match_count
        assert all(len(m.result.rally_log.events) > 0 for m in event.matches)
        assert [m.input_context.best_of for m in event.matches[:groups * size * (size - 1) // 2]] == [3] * (groups * size * (size - 1) // 2)
        if hybrid:
            assert all(m.input_context.best_of == 5 for m in event.matches[-(groups * 2 - 1):])
            assert len(event.knockout_bracket.matches) == groups * 2 - 1
            assert event.winner_player_id == event.matches[-1].result.winner_player_id
        else:
            assert event.knockout_bracket is None
            assert (event.winner_player_id is None) == (groups > 1)
        execute(server, command(inspect(server), 'confirm-result', edition_id='native-groups'))
        save_tour(server)
        execute(server, command(inspect(server), 'transition', name='publish-configured'))
        save_tour(server)
        rows = inspect(server)['state']['rankings'][-1]['rows']
        assert len(rows) == groups * size
        assert all(len(r['counted_results']) == 1 for r in rows)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        assert inspect(server)['state']['rankings'][-1]['rows'] == rows


@pytest.fixture(scope='module')
def prepared_groups(tmp_path_factory):
    path = tmp_path_factory.mktemp('native-group-fixture') / 'source.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        ready_groups(server)
    return path


def test_native_group_partial_independent_nested_forks_and_restore(tmp_path, prepared_groups):
    from tests.api.test_calendar_global_slots import copy_database, sporting
    from tests.api.test_calendar_population_sporting_checkpoint import restore
    from tests.api.test_native_fork_public_continuation import Tour, fork
    path = tmp_path / 'forks.db'
    copy_database(prepared_groups, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        execute(server, command(inspect(server), 'next-match', name='source-first'))
        partial = save_tour(server)
        source = sporting(server)
        created = fork(server, partial['revision_id'], name='Group fork')
        target = Tour(server, created['branch_id'])
        target.execute('next-match', 'fork-second')
        nested_source = target.save()
        nested_created = fork(server, nested_source['revision_id'], branch=created['branch_id'], name='Nested group fork')
        nested = Tour(server, nested_created['branch_id'])
        for i in range(5):
            nested.execute('next-slot', f'nested-slot-{i}')
            nested.save()
        assert len(nested.view()['edition_evidence']['native-groups']['matches']) == 15
        nested.execute('confirm-result', 'nested-confirm', edition_id='native-groups')
        nested.save()
        nested.advance('nested-publish')
        assert len(nested.view()['state']['rankings'][-1]['rows']) == 8
        assert sporting(server) == source
        assert target.view()['next_slot']['remaining'] == 2
        execute(server, command(inspect(server), 'next-slot', name='source-complete'))
        save_tour(server)
        restore(server, partial['revision_id'])
        assert inspect(server)['next_slot']['remaining'] == 3


def test_native_group_full_simulation_uses_same_slots_and_manual_saves(tmp_path, prepared_groups):
    from tests.api.test_calendar_global_slots import copy_database
    from tests.api.test_native_full_simulation_tasks import resume, reviewed, start
    path = tmp_path / 'worker.db'
    copy_database(prepared_groups, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        task = start(server, reviewed(server, {'season_index': 0, 'week': 5}, name='group-worker'))
        original_id = task['task_id']
        for index in range(5):
            assert task['checkpoint'] == 'native_manual_save_required', task
            save_tour(server)
            task = resume(server, task, f'saved-group-slot-{index}')
        assert task['checkpoint'] == 'native_result_review_required', task
        execute(server, command(inspect(server), 'confirm-result', edition_id='native-groups'))
        save_tour(server)
        task = resume(server, task, 'confirmed-group-result')
        assert task['checkpoint'] == 'native_manual_save_required', task
        save_tour(server)
        task = resume(server, task, 'saved-group-publication')
        assert task['task_id'] == original_id and task['state'] == 'target_reached', task
        assert len(inspect(server)['edition_evidence']['native-groups']['matches']) == 15


def test_native_groups_reject_stale_foreign_sources_rollback_and_rehashed_slot(tmp_path, prepared_groups, monkeypatch):
    import json

    from beta_engine.application import calendar_tour_service
    from beta_engine.domain.run_packages import canonical_hash
    from beta_engine.infrastructure.db.models import (
        CalendarPlayerSportingCheckpointModel,
        CalendarTourAuthorityModel,
    )
    from tests.api.test_calendar_global_slots import copy_database
    from tests.api.test_calendar_tour_flow import tour_url

    path = tmp_path / 'negative.db'
    copy_database(prepared_groups, path)
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo = server.app.state.runtime.repository
        original = inspect(server)
        stale = command(original, 'next-match', name='stale-source')
        for key in ('expected_saved_head', 'expected_checkpoint_fingerprint', 'expected_tour_fingerprint'):
            forged = {**stale, key: 'f' * 64}
            code, _ = _request('POST', tour_url(server) + '/preview', forged)
            assert code == 409
        foreign = {**stale, 'edition_id': 'foreign-edition'}
        assert _request('POST', tour_url(server) + '/preview', foreign)[0] == 409
        cmd = command(original, 'next-match', name='atomic-group-match')
        code, preview = _request('POST', tour_url(server) + '/preview', cmd)
        assert code == 200, preview
        body = {'command':cmd, 'expected_preview_fingerprint':preview['preview_fingerprint'], 'explicit_confirmation':True}
        def reject_after_write(name):
            if name == 'after_global_slot_matches_write':
                raise ValueError('Injected actual group write rollback')
        with monkeypatch.context() as patch:
            patch.setattr(calendar_tour_service, '_fault_injection_point', reject_after_write)
            assert _request('POST', tour_url(server) + '/execute', body)[0] == 409
        assert inspect(server)['checkpoint_fingerprint'] == original['checkpoint_fingerprint']
        code, result = _request('POST', tour_url(server) + '/execute', body)
        assert code == 201, result
        assert _request('POST', tour_url(server) + '/execute', body) == (201, result)
        save_tour(server)
        clean = inspect(server)
        with repo._session_factory.begin() as session:
            cp = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            tour = session.get(CalendarTourAuthorityModel, ('run', 'branch'))
            original_rows = cp.payload_json, cp.fingerprint, tour.payload_json, tour.fingerprint
            changed = json.loads(cp.payload_json)
            changed['events'][-1]['scheduled'][0]['seed'] += 1
            cp.payload_json, cp.fingerprint = json.dumps(changed), canonical_hash(changed)
            authority = json.loads(tour.payload_json)
            authority['checkpoint_fingerprint'] = cp.fingerprint
            tour.payload_json, tour.fingerprint = json.dumps(authority), canonical_hash(authority)
        assert _request('GET', tour_url(server))[0] == 409
        with repo._session_factory.begin() as session:
            cp = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            tour = session.get(CalendarTourAuthorityModel, ('run', 'branch'))
            cp.payload_json, cp.fingerprint, tour.payload_json, tour.fingerprint = original_rows
        assert inspect(server)['checkpoint_fingerprint'] == clean['checkpoint_fingerprint']


def test_mixed_formats_reverse_order_and_cold_restart(tmp_path):
    from tests.api.test_calendar_global_slots import copy_database, sporting
    source = tmp_path / 'mixed-source.db'
    with ApiServer(database_url=f'sqlite:///{source}') as server:
        ready_groups(server, parallel=True)
        view = inspect(server)['next_slot']
        assert view['remaining'] == 6 and not view['conflicts']
        mids = [m['match_id'] for m in view['matches']]
        assert {m['edition_id'] for m in view['matches']} == {'native-groups', 'parallel-knockout'}
    outcomes = []
    for mode in ('batch', 'reverse'):
        path = tmp_path / f'{mode}.db'
        copy_database(source, path)
        with ApiServer(database_url=f'sqlite:///{path}') as server:
            if mode == 'batch':
                execute(server, command(inspect(server), 'next-slot', name='batch'))
            else:
                for i, mid in enumerate(reversed(mids[3:])):
                    execute(server, command(inspect(server), 'next-match', name=f'first-{i}', data={'match_id': mid}))
                frozen = inspect(server)['next_slot']['snapshot_fingerprint']
            save_tour(server)
        with ApiServer(database_url=f'sqlite:///{path}') as server:
            if mode == 'reverse':
                assert inspect(server)['next_slot']['snapshot_fingerprint'] == frozen
                assert inspect(server)['next_slot']['remaining'] == 3
                for i, mid in enumerate(reversed(mids[:3])):
                    execute(server, command(inspect(server), 'next-match', name=f'rest-{i}', data={'match_id': mid}))
                save_tour(server)
            assert inspect(server)['next_slot']['number'] == 5
            cp = sporting(server)
            slot = cp.events[-1]
            assert len(slot.accepted) == 6
            assert all(m.result.rally_log.events for m in slot.accepted)
            outcomes.append(cp)
    assert outcomes[0] == outcomes[1], 'all sporting evidence must survive ordering and restart unchanged'
