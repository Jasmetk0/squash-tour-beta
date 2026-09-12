"""Real command/SQLite tests for all-or-nothing disciplinary decision batches."""

import pytest
from sqlalchemy import event, text
from test_official_ranking_storage import database  # noqa: F401
from test_ranking_revision_state import captured  # noqa: F401
from test_ranking_zero_history import bootstrap, capture, command, version, week

from beta_engine.infrastructure.db.models import OfficialRankingCommandModel
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner, stage_ranking_week_command


@pytest.mark.smoke
def test_new_decision_correction_and_reordered_retry(database, captured):
    runner = RankingWeekCommandRunner(database)
    a = version()
    b = a.model_copy(update={'zero': a.zero.model_copy(update={'zero_id': 'zero-b', 'player_id': 'b'})})
    req = command(4, captured.entries[-1].inputs.players).model_copy(update={'zero_versions': (b, a)})
    snapshot = runner.execute(req)
    assert all(row.points == 0 for row in snapshot.rows)
    state = capture(database)
    assert state.zero_sources == (a, b)
    reordered = req.model_copy(update={'zero_versions': (a, b)})
    assert reordered.fingerprint == req.fingerprint
    assert runner.execute(reordered) == snapshot
    assert capture(database) == state
    correction = version(5, duration=1, previous=a)
    next_req = command(5, req.context.players).model_copy(update={'zero_versions': (correction,)})
    assert next(r for r in runner.execute(next_req).rows if r.player_id == 'a').points == 300
    assert runner.execute(req) == snapshot
    with pytest.raises(ValueError, match='different request'):
        runner.execute(req.model_copy(update={'zero_versions': (a,)}))


@pytest.mark.smoke
def test_bootstrap_records_zero_batch_and_receipt(database):
    req = bootstrap().model_copy(update={'discipline': 'stored_zeros', 'zero_versions': (version(1),)})
    runner = RankingWeekCommandRunner(database)
    result = runner.execute(req)
    state = capture(database)
    assert state.zero_sources == (version(1),)
    assert state.entries[0].inputs.disciplinary_zeros == (version(1).zero,)
    assert runner.execute(req) == result


@pytest.mark.smoke
def test_later_lineage_failure_rolls_back_earlier_zero_write(database, captured):
    first = version()
    invalid = first.model_copy(update={'zero': first.zero.model_copy(update={'zero_id': 'z-last'}), 'previous_fingerprint': '0' * 64})
    req = command(4, captured.entries[-1].inputs.players).model_copy(update={'zero_versions': (first, invalid)})
    # Caller catches the error and commits its outer transaction: the savepoint
    # must still remove the earlier valid zero write.
    with database.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        with pytest.raises(ValueError, match='missing predecessor'):
            stage_ranking_week_command(session, None, req)
    assert capture(database) == captured


@pytest.mark.smoke
def test_receipt_failure_rolls_back_zero_and_candidate(database, captured):
    req = command(4, captured.entries[-1].inputs.players).model_copy(update={'zero_versions': (version(),)})
    def fail(*args):
        raise RuntimeError('receipt failure')
    event.listen(OfficialRankingCommandModel, 'before_insert', fail)
    try:
        with pytest.raises(RuntimeError, match='receipt failure'):
            RankingWeekCommandRunner(database).execute(req)
    finally:
        event.remove(OfficialRankingCommandModel, 'before_insert', fail)
    assert capture(database) == captured


@pytest.mark.parametrize('damage', ['scope', 'boundary', 'player', 'duplicate', 'mode'])
def test_invalid_batch_is_rejected_before_writes(database, captured, damage):
    v = version()
    req = command(4, captured.entries[-1].inputs.players)
    if damage == 'scope':
        v = v.model_copy(update={'zero': v.zero.model_copy(update={'branch_id': 'other'})})
    elif damage == 'boundary':
        v = version(5)
    elif damage == 'player':
        v = v.model_copy(update={'zero': v.zero.model_copy(update={'player_id': 'missing'})})
    elif damage == 'mode':
        req = req.model_copy(update={'context': req.context.model_copy(update={'discipline': 'none'})})
    req = req.model_copy(update={'zero_versions': (v, v) if damage == 'duplicate' else (v,)})
    with pytest.raises(ValueError):
        RankingWeekCommandRunner(database).execute(req)
    assert capture(database) == captured


def test_legacy_serialization_omits_empty_batch():
    assert 'zero_versions' not in bootstrap().model_dump(mode='json')
    assert 'zero_versions' not in command(2, ()).model_dump(mode='json')


@pytest.mark.smoke
def test_zero_and_result_corrections_share_transaction_and_recovery(database, captured):
    from beta_engine.domain.rankings.result_history import RankingResultVersion
    from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state
    previous = captured.sources[-1]
    correction = RankingResultVersion(run_id='run', branch_id='branch', effective_week=week(4),
        previous_fingerprint=previous.fingerprint,
        result=previous.result.model_copy(update={'main_points': 500, 'source_fingerprint': 'corrected-award'}))
    req = command(4, captured.entries[-1].inputs.players).model_copy(update={
        'zero_versions': (version(duration=1),), 'corrections': (correction,),
    })
    runner = RankingWeekCommandRunner(database)
    bad = req.model_copy(update={'corrections': (correction.model_copy(update={'previous_fingerprint': '0'*64}),)})
    with pytest.raises(ValueError):
        runner.execute(bad)
    assert capture(database) == captured
    result = runner.execute(req)
    assert next(r for r in result.rows if r.player_id == 'a').points == 0
    saved = capture(database)
    assert saved.sources[-1] == correction
    assert next(r for r in runner.execute(command(5, req.context.players)).rows if r.player_id == 'a').points == 500
    for index, target in enumerate((captured, saved)):
        current = capture(database)
        with database.begin() as session:
            session.execute(text('BEGIN IMMEDIATE'))
            restore_ranking_revision_state(session, target.model_dump_json(), expected_fingerprint=target.fingerprint,
                expected_current_fingerprint=current.fingerprint, command_id=f'batch-recovery-{index}', run_id='run', branch_id='branch')
        assert capture(database) == target
    assert runner.execute(req) == result
