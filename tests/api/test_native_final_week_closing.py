"""Real final-week Tour/worker, explicit Saves, closure and physical SQLite reopen."""

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from tests.api.test_calendar_tour_flow import command as tour_command
from tests.api.test_calendar_tour_flow import create_edition, setup
from tests.api.test_native_full_simulation_tasks import (
    approve_draw,
    execute_tour,
    inspect,
    resume,
    reviewed,
    save_tour,
    scope,
    start,
    wait,
)
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.smoke


def finish_tournament(server, task, edition_id):
    assert task['checkpoint'] == 'native_entry_review_required', task
    approve_draw(server, edition_id)
    task = resume(server, task, 'draw-saved-' + edition_id)
    assert task['checkpoint'] == 'native_manual_save_required', task
    view = inspect(server)
    assert not view['saved']
    evidence = view['edition_evidence'][edition_id]
    assert len(evidence['matches']) == 3
    assert all(m['rally_count'] > 0 for m in evidence['matches'])
    assert sum(r['main_points'] for r in evidence['results']) == 220
    save_tour(server)
    task = resume(server, task, 'played-saved-' + edition_id)
    assert task['checkpoint'] == 'native_result_review_required', task
    result, request = execute_tour(server, tour_command(inspect(server), 'confirm-result',
        name='confirm-' + edition_id, edition_id=edition_id))
    # Exact uncertain-response retry uses the original reviewed command.
    url = server.base_url + f"/admin/runs/run/branches/{getattr(server, 'native_task_branch', 'branch')}/calendar-tour"
    assert _request('POST', url + '/execute', request) == (201, result)
    assert not inspect(server)['saved']
    save_tour(server)
    task = resume(server, task, 'result-saved-' + edition_id)
    return task, evidence, request, result


@pytest.mark.parametrize('clock,forked', [
    (RunCalendar(4, 2, 2040, 1), False),
    (RunCalendar(4, 4, 2040, 1), True),
    (RunCalendar(52, 1, 2030, 1), False),
    (RunCalendar(61, 37, 2000, 1), True),
    (RunCalendar(80, 79, 2100, 1), True),
], ids=['short-original', 'short-fork', 'w52', 'w61', 'w80'])
def test_real_final_week_edition_closing_save_restart_and_extension(tmp_path, monkeypatch, clock, forked):
    from beta_engine.application import native_full_simulation_closure as closure_app
    from tests.api.test_calendar_sporting_horizon_extension import extend, extension
    from tests.api.test_native_fork_public_continuation import fork
    from tests.api.test_player_generation_calendar_gate import _dump

    database = tmp_path / 'final-week.sqlite'
    db = f'sqlite:///{database}'
    with ApiServer(database_url=db) as server:
        repo, _ = setup(server, clock, count=4)
        create_edition(server, 'terminal-cup', size=4, offset=clock.weeks_per_year - 2)
        original_source = inspect(server)['saved_head_revision_id']
        source = repo.get_branch_saved_revision(revision_id=original_source)
        branch = 'branch'
        if forked:
            branch = fork(server, original_source, name='Final-week independent timeline')['branch_id']
            server.native_task_branch = branch
        # Opening the chosen last week terminates before Entry or MatchEngine.
        opening_command = reviewed(server, {'season_index': 0, 'week': clock.weeks_per_year}, name='open-last-week')
        opening = start(server, opening_command)
        for index in range(clock.weeks_per_year):
            if opening['state'] == 'target_reached':
                break
            assert opening['checkpoint'] == 'native_manual_save_required', opening
            save_tour(server)
            opening = resume(server, opening, f'open-week-{index}')
            print(f"Final W{clock.weeks_per_year}: {branch} {opening['current_week']} {opening['checkpoint']}", flush=True)
        assert opening['state'] == 'target_reached', opening
        view = inspect(server)
        assert not view['edition_evidence']
        assert not view['state']['editions'][0]['result_confirmed']
        # A separate explicit Run-end command owns completion.
        original = reviewed(server, name='finish-original-run')
        task = start(server, original)
        task, _evidence, _confirmation, confirmed = finish_tournament(server, task, 'terminal-cup')
        assert task['checkpoint'] == 'native_final_closure_review_required', task
        for result in confirmed['results']:
            assert result['schema_version'] == 'calendar_terminal_edition_result.v1'
            assert 'first_publication_week' not in result
            assert result['completed_week']['calendar'] == clock.to_metadata()
            assert result['closing_eligibility_ordinal'] == clock.weeks_per_year
            assert result['branch_id'] == branch
        before_closure = inspect(server)
        assert not any(r['points'] for r in before_closure['state']['rankings'][-1]['rows'])
        url = scope(server) + '/native/finish-original-run/closure'
        code, review = _request('GET', url)
        assert code == 200, review
        if not forked:
            assert _request('GET', server.base_url + '/viewer/runs/run/calendar-tour/seasons/0')[0] == 409
        assert review['season_summary']['played_match_count'] == 3
        assert review['season_summary']['awarded_points'] == 220
        assert sorted(r['points'] for r in review['closing_ranking']['rows']) == [30, 30, 60, 100]
        assert all(len(r['counted_results']) == 1 for r in review['closing_ranking']['rows'])
        assert all(r['counted_results'][0]['edition_id'] == 'terminal-cup' for r in review['closing_ranking']['rows'])
        body = {'request_id': 'closure-approve', 'review_fingerprint': review['review_fingerprint'],
            'operator_label': 'Admin', 'audit_reason': 'Reviewed actual final-week matches and points', 'explicit_confirmation': True}
        assert _request('POST', url + '/save', body)[0] == 409
        assert _request('POST', url + '/approve', body)[0] == 200
        assert inspect(server)['state'] == before_closure['state']
        before = _dump(database)
        def fail(name):
            raise ValueError('Injected final-week closure late rollback')
        monkeypatch.setattr(closure_app, '_fault_injection_point', fail)
        save_body = {**body, 'request_id': 'closure-save'}
        assert _request('POST', url + '/save', save_body)[0] == 409
        assert _dump(database) == before
        monkeypatch.setattr(closure_app, '_fault_injection_point', lambda name: None)
        code, receipt = _request('POST', url + '/save', save_body)
        assert code == 201, receipt
        assert _request('POST', url + '/save', save_body) == (201, receipt)
        task = resume(server, task, 'complete-after-final-save')
        assert task['state'] == 'complete', task
        closed = repo.get_branch_saved_revision(revision_id=receipt['revision_id'])
        closed_state = inspect(server)['state']
        assert closed_state == before_closure['state']
        assert closed_state['week']['week'] == clock.weeks_per_year
        assert len(closed_state['rankings']) == clock.weeks_per_year - 1
        assert repo.get_branch_saved_revision(revision_id=original_source) == source
        if clock.weeks_per_year == 4 and not forked:
            from tests.api.native_final_week_tamper import (
                reject_rehashed_terminal_history,
            )
            reject_rehashed_terminal_history(database, closed, tmp_path)
        task_id, opening_id = task['task_id'], opening['task_id']
        from beta_engine.infrastructure.db.models import FullSimulationTaskModel
        with repo._session_factory() as session:
            original_task_bytes = session.get(FullSimulationTaskModel, task_id).payload_json
    # A fresh server/repository physically reopens the actual committed file.
    with ApiServer(database_url=db) as server:
        server.native_task_branch = branch
        assert wait(server, task_id)['state'] == 'complete'
        assert wait(server, opening_id)['state'] == 'target_reached'
        assert inspect(server)['state'] == closed_state
        assert inspect(server)['saved_completed_seasons'] == [0]
        report_url = server.base_url + f"/admin/runs/run/branches/{branch}/calendar-tour/seasons/0"
        code, report = _request('GET', report_url)
        assert code == 200, report
        assert report['selected']['closing_ranking']['rows'] == review_rows(closed, branch)
        assert sum(r['awarded_points'] for r in report['selected']['players']) == 220
        code, viewer = _request('GET', server.base_url + '/viewer/runs/run/calendar-tour/seasons/0')
        if not forked:
            assert code == 200, viewer
            assert viewer['selected']['closing_ranking']['rows'] == review_rows(closed, branch)
        else:
            assert code == 409, viewer
        # Explicit strict extension must not revive either terminal command.
        code, review = extension(server, 2)
        assert code == 200 and review['can_save'], review
        code, extended = extend(server, review, 'extend-completed-final-week')
        assert code == 200, extended
        assert wait(server, task_id)['original_command'] == original
        assert wait(server, task_id)['state'] == 'complete'
        assert wait(server, opening_id)['original_command'] == opening_command
        repo = server.app.state.runtime.repository
        with repo._session_factory() as session:
            assert session.get(FullSimulationTaskModel, task_id).payload_json == original_task_bytes
        assert repo.get_branch_saved_revision(revision_id=closed.revision_id) == closed
        assert repo.get_branch_saved_revision(revision_id=original_source) == source
        next_command = reviewed(server, {'season_index': 1, 'week': 1}, name='explicit-new-continuation')
        continued = start(server, next_command)
        assert continued['checkpoint'] == 'native_season_transition_review_required', continued
        next_url = scope(server) + '/native/explicit-new-continuation/season-transition'
        code, next_review = _request('GET', next_url)
        assert code == 200, next_review
        assert next_review['outgoing_season_closure']['closing_ranking']['rows'] == review_rows(closed, branch)
        approval = {**body, 'request_id': 'explicit-new-season', 'review_fingerprint': next_review['review_fingerprint']}
        assert _request('POST', next_url + '/approve', approval)[0] == 200
        continued = resume(server, continued, 'explicit-approved-continuation')
        assert continued['checkpoint'] == 'native_manual_save_required', continued
        save_tour(server)
        continued = resume(server, continued, 'explicit-next-season-saved')
        assert continued['state'] == 'target_reached', continued
        ranking = inspect(server)['state']['rankings'][-1]
        assert sorted(r['points'] for r in ranking['rows']) == [30, 30, 60, 100]
        assert all(len(r['counted_results']) == 1 for r in ranking['rows'])
        assert all(r['counted_results'][0]['first_publication_week'] == {'season_index': 1, 'week': 1} for r in ranking['rows'])
        if clock.weeks_per_year == 4 and forked:
            inherited = fork(server, closed.revision_id, branch=branch, name='Inherited final-week history')
            server.native_task_branch = inherited['branch_id']
            inherited_task = start(server, reviewed(server, {'season_index': 1, 'week': 1}, name='inherited-terminal-continuation'))
            assert inherited_task['checkpoint'] == 'native_season_transition_review_required', inherited_task
            inherited_url = scope(server) + '/native/inherited-terminal-continuation/season-transition'
            code, inherited_review = _request('GET', inherited_url)
            assert code == 200, inherited_review
            assert sorted(r['points'] for r in inherited_review['outgoing_season_closure']['closing_ranking']['rows']) == [30, 30, 60, 100]
            assert _request('POST', inherited_url + '/approve', {**body, 'request_id': 'approve-inherited-season', 'review_fingerprint': inherited_review['review_fingerprint']})[0] == 200
            inherited_task = resume(server, inherited_task, 'continue-inherited-season')
            assert inherited_task['checkpoint'] == 'native_manual_save_required', inherited_task
            save_tour(server)
            inherited_task = resume(server, inherited_task, 'save-inherited-season')
            assert inherited_task['state'] == 'target_reached', inherited_task
            assert sorted(r['points'] for r in inspect(server)['state']['rankings'][-1]['rows']) == [30, 30, 60, 100]
            server.native_task_branch = branch
            assert wait(server, task_id)['state'] == 'complete'
        if forked:
            server.native_task_branch = 'branch'
            assert inspect(server)['state']['week']['week'] == 2
            assert not inspect(server)['edition_evidence']


def review_rows(closed, branch):
    return closed.payload['run']['native_branch_closures'][branch]['closing_ranking']['rows']


def test_real_two_editions_outgoing_best_one_counts_one_result_per_player(tmp_path):
    clock = RunCalendar(5, 3, 2040, 1)
    db = f"sqlite:///{tmp_path / 'best-one.sqlite'}"
    with ApiServer(database_url=db) as server:
        setup(server, clock, count=4)
        view = inspect(server)
        execute_tour(server, tour_command(view, 'policy', name='outgoing-best-one', data={
            'effective_week': {**view['state']['week'], 'week': 3},
            'ranking': {'policy_id': 'actual-outgoing-best-one', 'best_n': 1},
        }))
        save_tour(server)
        create_edition(server, 'previous-cup', size=4, offset=2)
        create_edition(server, 'terminal-cup', size=4, offset=3)
        task = start(server, reviewed(server, name='two-editions-run-end'))
        for index in range(3):
            if task['checkpoint'] == 'native_entry_review_required':
                break
            assert task['checkpoint'] == 'native_manual_save_required', task
            save_tour(server)
            task = resume(server, task, f'prepare-prior-{index}')
        task, previous, _, _ = finish_tournament(server, task, 'previous-cup')
        assert task['checkpoint'] == 'native_manual_save_required', task
        save_tour(server)
        task = resume(server, task, 'open-terminal-after-prior-points')
        published = inspect(server)['state']['rankings'][-1]
        task, final, _, _ = finish_tournament(server, task, 'terminal-cup')
        assert task['checkpoint'] == 'native_final_closure_review_required', task
        code, review = _request('GET', scope(server) + '/native/two-editions-run-end/closure')
        assert code == 200, review
        assert review['season_summary']['played_match_count'] == 6
        assert review['season_summary']['awarded_points'] == 440
        assert review['closing_ranking']['policy']['best_n'] == 1
        expected = {}
        for evidence in (previous, final):
            for result in evidence['results']:
                expected[result['player_id']] = max(expected.get(result['player_id'], 0), result['main_points'])
        for row in review['closing_ranking']['rows']:
            assert row['points'] == expected[row['player_id']]
            assert len(row['counted_results']) == 1
        assert inspect(server)['state']['rankings'][-1] == published
