"""Actual population-wide native sporting authority, atomic Save/restore and fail-closed coupling."""
import json
import copy

import pytest
from sqlalchemy import select

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.players.calendar_engine_player import calendar_engine_player
from beta_engine.domain.players.calendar_canonical_match import CalendarCanonicalPlayerSource
from beta_engine.domain.players.sporting import PlayerSportingBootstrapPolicy
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.infrastructure.db.calendar_sporting_checkpoint import COMPONENT_KEY, load_checkpoint
from beta_engine.infrastructure.db.initial_world_state import get_initial_world
from beta_engine.infrastructure.db.models import CalendarPlayerSportingCheckpointModel, CalendarStandaloneMatchModel
from tests.api.test_calendar_initial_world_adoption import (
    _world, request as population_request, review, confirm, root as population_root,
)
from tests.api.test_calendar_opening_knockout_flow import base
from tests.api.test_player_generation_calendar_gate import _dump, _generation
from tests.api.test_saved_revision_history_api import ApiServer, _request

pytestmark = pytest.mark.pr_critical


def prepare(server, clock, count=8):
    repo, _ = _world(server, clock)
    command = population_request(server, generation=_generation(target_pool_size=count))
    checked = review(server, command)
    code, adopted = confirm(server, command, checked)
    assert code == 201, adopted
    _, preview = _request('GET', population_root(server) + '/save/preview')
    code, saved = _request('POST', population_root(server) + '/save', {
        'expected_draft_version': preview['draft_version'],
        'expected_initial_world_fingerprint': adopted['fingerprint'],
    })
    assert code == 201, saved
    return repo, saved['saved_revision']['revision_id']


def play(server, head):
    code, before = _request('GET', base(server))
    assert code == 200, before
    command = dict(command_id='world-owner', match_id='world-owner', expected_saved_head=head,
        expected_initial_world_fingerprint=before['initial_world_fingerprint'],
        entrant_ids=before['player_ids'][:4], seed=833, operator_label='Admin',
        audit_reason='Persist the population, preserving nonparticipants')
    code, receipt = _request('POST', base(server) + '/simulate', command)
    assert code == 201, receipt
    return receipt, command


def save(server, receipt):
    code, preview = _request('GET', base(server) + '/save/preview')
    assert code == 200 and preview['can_save'], preview
    code, result = _request('POST', base(server) + '/save', {
        'expected_draft_version': preview['draft_version'],
        'expected_calendar_match_fingerprint': receipt['fingerprint'],
    })
    assert code == 201, result
    return result['saved_revision']


def restore(server, revision):
    url = server.base_url + f'/run-containers/run/branches/branch/saved-revisions/{revision}/restore'
    code, preflight = _request('GET', url + '-preflight')
    assert code == 200 and preflight['can_restore'], preflight
    code, result = _request('POST', url, {
        'expected_head_saved_revision_id': preflight['saved_head_revision_id'],
        'expected_draft_version': preflight['draft_version'],
        'expected_current_viewer_branch_id': 'branch', 'explicit_confirmation': True,
    })
    assert code == 201, result
    revision_id = result['saved_revision']['revision_id']
    stored = server.app.state.runtime.repository.get_branch_saved_revision(revision_id=revision_id)
    return {'revision_id': revision_id, 'payload': stored.payload}


@pytest.mark.parametrize('clock,count', [(RunCalendar(52, 35, 2030, 3), 8), (RunCalendar(80, 80, 2100, 3), 8), (RunCalendar(52, 35, 2030, 3), 1000)])
def test_entire_population_saved_restarted_and_restored_without_resetting_played_state(tmp_path, clock, count):
    path = tmp_path / 'population-owner.db'
    db = f'sqlite:///{path}'
    with ApiServer(database_url=db) as server:
        repo, head = prepare(server, clock, count)
        with repo._session_factory() as session:
            world = get_initial_world(session, run_id='run', branch_id='branch')
        receipt, command = play(server, head)
        knockout = receipt['knockout']
        assert knockout['schema_version'] == 'calendar_opening_knockout.v5'
        with repo._session_factory() as session:
            checkpoint = load_checkpoint(session, run_id='run', branch_id='branch')
        assert checkpoint.week.calendar == clock and checkpoint.week.ordinal == 0
        assert len(checkpoint.players) == count
        terminal = {p['player_id']: p for p in knockout['sporting']['terminal']}
        for record in checkpoint.players:
            assert len(record.attributes) == 57
            profile = next(p for p in world.players if p.player_id == record.player_id)
            baseline = derive_bootstrap_record(CalendarCanonicalPlayerSource(
                player=calendar_engine_player(profile), potential_ability=profile.potential_ability,
                source_generation_fingerprint=profile.source_generation_fingerprint,
            ), PlayerSportingBootstrapPolicy())
            assert record.attributes == baseline.attributes
            if record.player_id in terminal:
                state = terminal[record.player_id]
                assert (record.current_form, record.match_sharpness, record.long_term_fatigue) == (
                    state['current_form'], state['match_sharpness'], state['long_term_fatigue'])
                assert record.long_term_fatigue > 0
            else:
                assert record == baseline
        before = _dump(path)
        assert _request('POST', base(server) + '/simulate', command) == (201, receipt)
        _, view = _request('GET', base(server))
        assert not view['population_sporting_checkpoint']['saved']
        fp = checkpoint.fingerprint
        outsider = next(p for p in checkpoint.players if p.player_id not in terminal)
        url = base(server) + '/sporting-checkpoint/players/' + outsider.player_id
        query = f'?expected_saved_head={head}&expected_checkpoint_fingerprint={fp}'
        code, record = _request('GET', url + query)
        assert code == 200 and record['player'] == outsider.model_dump(mode='json'), record
        assert _request('GET', url + f'?expected_saved_head=stale&expected_checkpoint_fingerprint={fp}')[0] == 409
        assert _request('GET', url + f'?expected_saved_head={head}&expected_checkpoint_fingerprint=stale')[0] == 409
        assert _request('GET', base(server) + '/sporting-checkpoint/players/foreign' + query)[0] == 404
        assert _dump(path) == before
        saved = save(server, receipt)
        assert saved['payload']['content'][COMPONENT_KEY]['state'] == checkpoint.model_dump(mode='json')
        # Even if an attacker rehashes a component, it cannot detach the owner
        # from the exact persisted population or replace the unchanged outsiders.
        from beta_engine.infrastructure.db.calendar_standalone_match_state import load_saved_calendar_match
        from beta_engine.domain.run_packages import canonical_hash
        for damage in ('missing', 'orphan', 'foreign', 'state', 'world', 'week'):
            changed = copy.deepcopy(saved['payload'])
            component = changed['content'][COMPONENT_KEY]
            if damage == 'missing': del changed['content'][COMPONENT_KEY]
            elif damage == 'orphan': del changed['content']['calendar_standalone_match']
            else:
                raw = component['state']
                if damage == 'foreign': raw['branch_id'] = 'foreign'
                if damage == 'state': raw['players'][-1]['long_term_fatigue'] = 99
                if damage == 'world': raw['source_initial_world_fingerprint'] = 'f' * 64
                if damage == 'week': raw['week']['calendar']['season_count'] += 1
                component['fingerprint'] = canonical_hash(raw)
            with pytest.raises(ValueError):
                load_saved_calendar_match(changed, run_id='run', branch_id='branch')

        assert repo.verify_branch_saved_revision_hash(revision_id=head)
        assert repo.verify_branch_saved_revision_hash(revision_id=saved['revision_id'])
        # Fork remains explicit unsupported; never copy an owner with source-Branch bindings.
        assert _request('POST', server.base_url + '/run-containers/run/branches', {
            'source_branch_id': 'branch', 'source_saved_revision_id': saved['revision_id']})[0] == 409
        assert _request('GET', base(server))[1]['population_sporting_checkpoint']['saved']
    with ApiServer(database_url=db) as restarted:
        assert _request('GET', base(restarted))[1]['population_sporting_checkpoint']['fingerprint'] == fp
        assert _request('GET', base(restarted) + '/world-owner/replay')[1]['exact_replay']
        reverted = restore(restarted, head)
        assert COMPONENT_KEY not in reverted['payload']['content']
        with restarted.app.state.runtime.repository._session_factory() as session:
            assert load_checkpoint(session, run_id='run', branch_id='branch') is None
        forward = restore(restarted, saved['revision_id'])
        assert forward['payload']['content'][COMPONENT_KEY] == saved['payload']['content'][COMPONENT_KEY]
        assert _request('GET', base(restarted) + '/world-owner/replay')[1]['exact_replay']


def test_population_write_failure_rolls_back_the_already_played_match(tmp_path, monkeypatch):
    from beta_engine.infrastructure.db import calendar_sporting_checkpoint as storage
    path = tmp_path / 'atomic.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo, head = prepare(server, RunCalendar.earth_default())
        _, view = _request('GET', base(server))
        command = dict(command_id='failed', match_id='failed', expected_saved_head=head,
            expected_initial_world_fingerprint=view['initial_world_fingerprint'], entrant_ids=view['player_ids'][:4],
            seed=833, operator_label='Admin', audit_reason='Atomic failure injection')
        before = _dump(path)
        def fail(*args):
            raise ValueError('Injected native checkpoint persistence failure')
        monkeypatch.setattr(storage, 'put_checkpoint', fail)
        assert _request('POST', base(server) + '/simulate', command)[0] == 409
        assert _dump(path) == before
        with repo._session_factory() as session:
            assert session.scalar(select(CalendarStandaloneMatchModel)) is None
            assert session.scalar(select(CalendarPlayerSportingCheckpointModel)) is None


@pytest.mark.parametrize('damage', ['missing', 'outsider_fatigue', 'canonical_attribute', 'source'])
def test_even_rehashed_live_checkpoint_corruption_blocks_save_and_inspection(tmp_path, damage):
    from beta_engine.domain.run_packages import canonical_hash
    path = tmp_path / 'corrupt.db'
    with ApiServer(database_url=f'sqlite:///{path}') as server:
        repo, head = prepare(server, RunCalendar.earth_default())
        receipt, _ = play(server, head)
        with repo._session_factory.begin() as session:
            row = session.get(CalendarPlayerSportingCheckpointModel, ('run', 'branch'))
            if damage == 'missing':
                session.delete(row)
            else:
                raw = json.loads(row.payload_json)
                outsider = next(p for p in raw['players'] if p['player_id'] not in receipt['knockout']['entrant_ids'])
                if damage == 'outsider_fatigue': outsider['long_term_fatigue'] = 1
                if damage == 'canonical_attribute': outsider['attributes'][0][1] = (outsider['attributes'][0][1] + 1) % 201
                if damage == 'source': raw['source_knockout_fingerprint'] = 'f' * 64
                row.payload_json = json.dumps(raw)
                row.fingerprint = canonical_hash(raw)
        before = _dump(path)
        assert _request('GET', base(server))[0] == 409
        assert _request('GET', base(server) + '/save/preview')[0] == 409
        assert _dump(path) == before
