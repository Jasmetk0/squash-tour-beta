import pytest
from sqlalchemy import text
from test_official_ranking_storage import database  # noqa: F401
from test_ranking_revision_state import captured  # noqa: F401
from beta_engine.application.ranking_week_command import RankingWeekCommand
from beta_engine.application.official_ranking_transition import RankingTransitionContext
from beta_engine.domain.rankings.official import DisciplinaryZero, OfficialRankingPolicy, RankingWeek
from beta_engine.domain.rankings.revision_state import load_ranking_revision_state
from beta_engine.infrastructure.db.ranking_week_command import RankingWeekCommandRunner
from beta_engine.infrastructure.db.ranking_revision_state import capture_ranking_revision_state


@pytest.mark.smoke
def test_zero_replay_expiry_and_complete_revision_roundtrip(database,captured):
    runner=RankingWeekCommandRunner(database)
    z=DisciplinaryZero(zero_id='zero-a',run_id='run',branch_id='branch',player_id='a',source_fingerprint='sanction',effective_week=RankingWeek(season_index=0,week=4),duration_weeks=1)
    def command(n):
        return RankingWeekCommand(command_id=f'zero-week-{n}',tournaments=(),context=RankingTransitionContext(
            run_id='run',branch_id='branch',completed_week=RankingWeek(season_index=0,week=n-1),target_week=RankingWeek(season_index=0,week=n),
            players=captured.entries[-1].inputs.players,policy=OfficialRankingPolicy(policy_id='best-one',best_n=1),discipline='resolved_zeros',disciplinary_zeros=(z,),
        ))
    request=command(4)
    first=runner.execute(request)
    assert all(r.points==0 for r in first.rows)
    assert runner.execute(request)==first
    with pytest.raises(ValueError): runner.execute(request.model_copy(update={'context':request.context.model_copy(update={'disciplinary_zeros':()})}))
    second=runner.execute(command(5))
    assert next(r for r in second.rows if r.player_id=='a').points==300
    with database.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        state=capture_ranking_revision_state(session,run_id='run',branch_id='branch')
    assert state.entries[-2].inputs.disciplinary_zeros==(z,)
    assert state.entries[-2].snapshot==first
    assert load_ranking_revision_state(state.model_dump_json(),expected_fingerprint=state.fingerprint,run_id='run',branch_id='branch')==state
    from beta_engine.infrastructure.db.ranking_state_restore import restore_ranking_revision_state
    with database.begin() as session:
        session.execute(text('BEGIN IMMEDIATE'))
        restore_ranking_revision_state(session,captured.model_dump_json(),expected_fingerprint=captured.fingerprint,expected_current_fingerprint=state.fingerprint,command_id='before-zero',run_id='run',branch_id='branch')
        restore_ranking_revision_state(session,state.model_dump_json(),expected_fingerprint=state.fingerprint,expected_current_fingerprint=captured.fingerprint,command_id='with-zero',run_id='run',branch_id='branch')
        assert capture_ranking_revision_state(session,run_id='run',branch_id='branch')==state
