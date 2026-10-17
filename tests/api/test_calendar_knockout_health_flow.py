"""Actual Saved Health -> played knockout -> Save/restart/restore, no fake effects."""
from copy import deepcopy
import json

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.infrastructure.db.models import PlayerHealthWeekStateModel, CalendarStandaloneMatchModel
from tests.api.test_saved_revision_history_api import ApiServer, _request
from tests.api.test_calendar_initial_health import health_root
from tests.api.test_calendar_health_edit import baseline, edit_request, review, commit, save
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_calendar_knockout_awards_flow import proposal
from tests.api.test_calendar_signed_knockout_standings_flow import standings
from tests.api.test_calendar_standalone_match_flow import base as exhibition_base

pytestmark = pytest.mark.pr_critical


def command(view, command_id='health-ko'):
    return dict(command_id=command_id, match_id=command_id,
        expected_saved_head=view['saved_head_revision_id'],
        expected_initial_world_fingerprint=view['initial_world_fingerprint'],
        entrant_ids=view['player_ids'][:4], seed=872, operator_label='Admin',
        audit_reason='Use Saved Health facts, numeric effects unsupported')


def save_knockout(server, played):
    status, preview = _request('GET', base(server) + '/save/preview')
    assert status == 200 and preview['can_save'], preview
    status, saved = _request('POST', base(server) + '/save', {
        'expected_draft_version': preview['draft_version'],
        'expected_calendar_match_fingerprint': played['fingerprint'],
    })
    assert status == 201, saved
    return saved['saved_revision']


@pytest.mark.parametrize('clock', [RunCalendar(52, 35, 2030, 3), RunCalendar(80, 80, 2100, 3)])
def test_saved_health_facts_enter_matches_without_implicit_penalty_and_survive_restart(tmp_path, clock):
    db=f"sqlite:///{tmp_path / 'health-knockout.db'}"
    with ApiServer(database_url=db) as server:
        repo, health_url, player, baseline_saved = baseline(server, clock)
        before = deepcopy(baseline_saved['saved_revision'])
        status, view = _request('GET', base(server))
        assert status == 200, view
        assert view['health_readiness']['limited_player_ids'] == []
        assert _request('GET', exhibition_base(server))[0] == 409  # original exhibition guard stays
        # A known injury is explicit saved fact, not an inferred penalty/healing event.
        edit = edit_request(player)
        status, receipt = commit(health_url, edit, review(health_url, edit))
        assert status == 200, receipt
        assert _request('GET', base(server))[0] == 409  # unsaved Health never bypassed
        health_saved = save(server)['saved_revision']
        status, view = _request('GET', base(server))
        assert status == 200, view
        assert player['player']['player_id'] in view['health_readiness']['limited_player_ids']
        cmd = command(view)
        status, played = _request('POST', base(server) + '/simulate', cmd)
        assert status == 201, played
        ko = played['knockout']
        assert ko['schema_version'] == 'calendar_opening_knockout.v5'
        source = ko['health_source']
        assert source['source_health_fingerprint'] == view['health_readiness']['source_health_fingerprint']
        injured = next(p for p in source['profiles'] if p['player_id'] == player['player']['player_id'])
        assert injured['highest_current_severity'] == 25
        assert injured['numeric_calibration_required'] and not injured['numeric_effect_applied']
        for match in ko['matches']:
            snap = match['effective_health']
            assert not snap['numeric_effect_applied']
            assert [p['player_id'] for p in snap['player_profiles']] == [
                match['result']['player_a_id'], match['result']['player_b_id'],
            ]
        # Playing changes form/load, never the medical record or Health fingerprint.
        assert _request('GET', health_url)[1]['state_fingerprint'] == source['source_health_fingerprint']
        revision = save_knockout(server, played)
        points = proposal(revision['revision_id'], played['fingerprint'], clock.weeks_per_year)
        status, point_review = _request('POST', base(server) + '/awards/review', points)
        assert status == 200, point_review
        status, scored = _request('POST', base(server) + '/awards/apply', {
            'command_id': 'health-ko-points', 'proposal': points,
            'expected_preview_fingerprint': point_review['preview_fingerprint'], 'explicit_confirmation': True,
        })
        assert status == 201, scored
        revision = save_knockout(server, scored)
        assert _request('POST', base(server) + '/simulate', cmd) == (201, played)
        assert _request('GET', base(server) + '/health-ko/replay')[1]['exact_replay']
        assert repo.get_branch_saved_revision(revision_id=health_saved['revision_id']).payload == health_saved['payload']
        assert repo.get_branch_saved_revision(revision_id=before['revision_id']).payload == before['payload']

        # Later explicit medical correction must not rewrite a previously played input.
        current = _request('GET', health_url)[1]
        correction = edit_request(current)
        correction.update(command_id='later-health-correction', mode='current_state_correction')
        correction['records'][0]['severity'] = 40
        status, result = commit(health_url, correction, review(health_url, correction))
        assert status == 200, result
        corrected_revision = save(server)['saved_revision']
        assert _request('GET', base(server))[1]['knockout'] == ko
        assert _request('GET', base(server) + '/health-ko/replay')[1]['exact_replay']
        assert corrected_revision['payload']['content']['calendar_standalone_match'] == revision['payload']['content']['calendar_standalone_match']
        status, extension = _request('GET', server.base_url
            + '/run-containers/run/calendar/extension-review?new_season_count=4')
        assert status == 200 and extension['can_save'], extension
        status, extended = _request('POST', server.base_url + '/run-containers/run/calendar/extension-save', {
            'command_id': 'extend-health-ko', 'new_season_count': 4,
            'review_fingerprint': extension['review_fingerprint'], 'explicit_confirmation': True,
        })
        assert status == 200, extended
        final_head = next(b['saved_revision_id'] for b in extended['branches'] if b['branch_id'] == 'branch')
        assert _request('GET', base(server))[1]['knockout'] == ko
        assert standings(server, final_head)[1]['points_in_period']
        assert not standings(server, final_head, 1, 2)[1]['points_in_period']
    with ApiServer(database_url=db) as restarted:
        status, view = _request('GET', base(restarted))
        assert status == 200 and view['saved'], view
        assert view['knockout'] == ko
        assert view['health_readiness']['source_health_fingerprint'] != source['source_health_fingerprint']
        assert _request('GET', base(restarted) + '/health-ko/replay')[1]['exact_replay']
        assert restarted.app.state.runtime.repository.verify_branch_saved_revision_hash(revision_id=final_head)
        # Restoring health-only history removes played evidence; forward restore
        # reinstalls its original health inputs under the extended Run horizon.
        current = final_head
        for target, expected_ko in ((health_saved['revision_id'], None), (corrected_revision['revision_id'], ko)):
            url = restarted.base_url + '/run-containers/run/branches/branch/saved-revisions/' + target + '/restore'
            status, proof = _request('GET', url + '-preflight')
            assert status == 200 and proof['can_restore'], proof
            status, restored = _request('POST', url, {
                'expected_head_saved_revision_id': current, 'expected_draft_version': proof['draft_version'],
                'expected_current_viewer_branch_id': 'branch', 'explicit_confirmation': True,
            })
            assert status == 201, restored
            current = restored['saved_revision']['revision_id']
            status, inspected = _request('GET', base(restarted))
            assert status == 200 and inspected['knockout'] == expected_ko, inspected
            assert inspected['run_calendar']['season_count'] == 4
        assert _request('GET', base(restarted) + '/health-ko/replay')[1]['exact_replay']


def test_missing_saved_health_row_and_semantic_projection_tamper_fail_closed(tmp_path):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'bad-health.db'}") as server:
        repo, _, _, saved = baseline(server, RunCalendar(52, 35, 2030, 3))
        _, view = _request('GET', base(server))
        status, played = _request('POST', base(server) + '/simulate', command(view))
        assert status == 201, played
        with repo._session_factory.begin() as session:
            row = session.get(CalendarStandaloneMatchModel, ('run', 'branch', 'health-ko'))
            raw = json.loads(row.payload_json)
            raw['matches'][0]['effective_health']['player_profiles'].reverse()
            row.payload_json = json.dumps(raw)
            row.fingerprint = canonical_hash(raw)
        assert _request('GET', base(server))[0] == 409
        assert _request('GET', base(server) + '/health-ko/replay')[0] == 409
        assert _request('GET', base(server) + '/save/preview')[0] == 409
        with repo._session_factory.begin() as session:
            session.delete(session.get(PlayerHealthWeekStateModel, ('run', 'branch', 0)))
        assert _request('GET', base(server))[0] == 409
        assert repo.verify_branch_saved_revision_hash(revision_id=saved['saved_revision']['revision_id'])


@pytest.mark.parametrize('fault', ['missing', 'unsaved'])
def test_saved_health_cannot_be_missing_or_changed_behind_a_clean_draft(tmp_path, fault):
    with ApiServer(database_url=f"sqlite:///{tmp_path / 'drift.db'}") as server:
        repo, _, _, saved = baseline(server, RunCalendar(80, 80, 2100, 3))
        status, view = _request('GET', base(server))
        assert status == 200, view
        with repo._session_factory.begin() as session:
            row = session.get(PlayerHealthWeekStateModel, ('run', 'branch', 0))
            if fault == 'missing':
                session.delete(row)
            else:
                raw = json.loads(row.payload_json)
                raw['audit_label'] = 'Changed behind clean draft'
                row.payload_json = json.dumps(raw)
                row.fingerprint = canonical_hash(raw)
        assert _request('GET', base(server))[0] == 409
        assert _request('POST', base(server) + '/simulate', command(view))[0] == 409
        with repo._session_factory() as session:
            assert session.get(CalendarStandaloneMatchModel, ('run', 'branch', 'health-ko')) is None
        assert repo.verify_branch_saved_revision_hash(revision_id=saved['saved_revision']['revision_id'])
