"""Real SQLite zero-source resolution, immutable history and recovery."""

import json

import pytest
from sqlalchemy import text

from test_official_ranking_storage import database  # noqa: F401
from test_ranking_revision_state import captured  # noqa: F401
from test_ranking_bootstrap_command import command as bootstrap
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.domain.rankings.official import DisciplinaryZero, OfficialRankingPolicy, RankingWeek
from beta_engine.domain.rankings.zero_history import RankingZeroVersion
from beta_engine.domain.rankings.revision_state import RankingRevisionState
from beta_engine.infrastructure.db.models import OfficialRankingZeroVersionModel, RunBranchModel
from beta_engine.infrastructure.db.ranking_zero_history import OfficialRankingZeroStore
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state
from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner


def week(n):
    return RankingWeek(season_index=(n - 1) // 61, week=(n - 1) % 61 + 1)


def version(n=4, duration=3, previous=None):
    return RankingZeroVersion(effective_week=week(n), previous_fingerprint=previous.fingerprint if previous else None,
        zero=DisciplinaryZero(zero_id='zero-a', run_id='run', branch_id='branch', player_id='a',
            source_fingerprint=f'decision-{n}', effective_week=previous.zero.effective_week if previous else week(n), duration_weeks=duration))


def append(factory, v):
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        return OfficialRankingZeroStore(session).append(v)


def capture(factory):
    with factory.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        return capture_ranking_revision_state(session, run_id='run', branch_id='branch')


def command(n, players):
    return RankingWeekCommand(command_id=f'stored-zero-{n}', tournaments=(), context=RankingTransitionContext(
        run_id='run', branch_id='branch', completed_week=week(n-1), target_week=week(n), players=players,
        policy=OfficialRankingPolicy(policy_id='best-one', best_n=1), discipline='stored_zeros'))


@pytest.mark.smoke
def test_week_resolution_correction_expiry_replay_and_recovery(database, captured):
    first = version()
    append(database, first)
    runner = RankingWeekCommandRunner(database)
    request = command(4, captured.entries[-1].inputs.players)
    fourth = runner.execute(request)
    assert next(r for r in fourth.rows if r.player_id == 'a').points == 0
    # Shortening is effective only from week 5, without restarting the original interval.
    correction = version(5, duration=1, previous=first)
    append(database, correction)
    assert runner.execute(request) == fourth
    fifth = runner.execute(command(5, request.context.players))
    assert next(r for r in fifth.rows if r.player_id == 'a').points == 300
    state = capture(database)
    assert state.zero_sources == (first, correction)
    assert state.entries[-2].inputs.disciplinary_zeros == (first.zero,)
    assert state.entries[-1].inputs.disciplinary_zeros == (correction.zero,)
    assert state.entries[-1].inputs.zeros_from_history
    assert state.entries[-2].snapshot == fourth
    for i, target in enumerate((captured, state)):
        current = capture(database)
        with database.begin() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            restore_ranking_revision_state(session, target.model_dump_json(), expected_fingerprint=target.fingerprint,
                expected_current_fingerprint=current.fingerprint, command_id=f'zero-restore-{i}', run_id='run', branch_id='branch')
        assert capture(database) == target
    assert runner.execute(request) == fourth
    corrupted = json.loads(state.model_dump_json())
    corrupted['zero_sources'] = []
    with pytest.raises(ValueError, match='zero history differs'):
        RankingRevisionState.model_validate_json(json.dumps(corrupted))


def test_future_decisions_are_not_resolved_and_cannot_be_bypassed(database, captured):
    append(database, version(6))
    runner = RankingWeekCommandRunner(database)
    req = command(4, captured.entries[-1].inputs.players)
    with pytest.raises(ValueError, match='requires stored_zeros'):
        runner.execute(req.model_copy(update={'context': req.context.model_copy(update={'discipline': 'none'})}))
    assert capture(database).entries == captured.entries
    result = runner.execute(req)
    assert next(r for r in result.rows if r.player_id == 'a').points == 300
    assert capture(database).entries[-1].inputs.disciplinary_zeros == ()


def test_zero_only_state_restore_and_rollback(database):
    empty = capture(database)
    append(database, version())
    saved = capture(database)
    assert saved.entries == () and saved.zero_sources
    with pytest.raises(RuntimeError):
        with database.begin() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            restore_ranking_revision_state(session, empty.model_dump_json(), expected_fingerprint=empty.fingerprint,
                expected_current_fingerprint=saved.fingerprint, command_id='rollback', run_id='run', branch_id='branch')
            raise RuntimeError('outer world failure')
    assert capture(database) == saved


def test_bootstrap_uses_persisted_zeros(database):
    v = version(1)
    append(database, v)
    req = bootstrap().model_copy(update={'discipline': 'stored_zeros'})
    RankingWeekCommandRunner(database).execute(req)
    assert capture(database).entries[0].inputs.disciplinary_zeros == (v.zero,)


def test_conflicts_backdating_and_hash_corruption(database, captured):
    v = version()
    assert append(database, v) == append(database, v)
    with pytest.raises(ValueError, match='Conflicting'):
        append(database, version(duration=2))
    with pytest.raises(ValueError, match='backdate'):
        append(database, version(3).model_copy(update={'zero': version(3).zero.model_copy(update={'zero_id': 'backdated'})}))
    with database.begin() as session:
        row = session.get(OfficialRankingZeroVersionModel, ('run', 'branch', 'zero-a', 3))
        row.fingerprint = '0' * 64
    with pytest.raises(ValueError, match='fingerprint'):
        capture(database)


@pytest.mark.parametrize('change', [
    {'player_id': 'b'}, {'effective_week': week(3)}, {'run_id': 'other'}, {'zero_id': 'other'},
])
def test_correction_cannot_rewrite_identity(database, change):
    first = version()
    append(database, first)
    corrected = version(5, previous=first)
    with pytest.raises(ValueError):
        append(database, corrected.model_copy(update={'zero': corrected.zero.model_copy(update=change)}))


def test_scope_isolation_and_read_only(database):
    append(database, version())
    with database.begin() as session:
        assert OfficialRankingZeroStore(session).resolve(run_id='run', branch_id='other', week=week(5)) == ()
        session.get(RunBranchModel, 'branch').read_only = True
    with pytest.raises(ValueError, match='read-only'):
        append(database, version(5, previous=version()))


def test_legacy_revision_serialization_omits_extensions(database, captured):
    payload = captured.model_dump(mode='json')
    assert 'zero_sources' not in payload
    assert all('zeros_from_history' not in entry['inputs'] for entry in payload['entries'])
    assert RankingRevisionState.model_validate_json(json.dumps(payload)).fingerprint == captured.fingerprint


@pytest.mark.parametrize('case', ['missing_predecessor', 'wrong_predecessor', 'out_of_order', 'invalid_initial_week'])
def test_invalid_version_lineage_is_rejected(database, case):
    first = version()
    if case != 'missing_predecessor':
        append(database, first)
    candidate = version(5, previous=first)
    if case == 'wrong_predecessor':
        candidate = candidate.model_copy(update={'previous_fingerprint': '0' * 64})
    elif case == 'out_of_order':
        append(database, version(6, previous=first))
    elif case == 'invalid_initial_week':
        candidate = candidate.model_copy(update={'previous_fingerprint': None})
    with pytest.raises(ValueError):
        append(database, candidate)


def test_stored_mode_rejects_manual_inputs(database):
    req = bootstrap().model_copy(update={'discipline': 'stored_zeros', 'disciplinary_zeros': (version(1).zero,)})
    with pytest.raises(ValueError, match='explicit resolved_zeros'):
        RankingWeekCommandRunner(database).execute(req)
    assert capture(database).entries == ()
