import json
import pytest
from beta_engine.domain.rankings.official import DisciplinaryZero, OfficialRankingSnapshot
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from test_ranking_tie_explanations import PLAYERS, POLICY, result, week
from beta_engine.domain.rankings.official import calculate_official_ranking


def zero(identity='z',start=3,duration=2,player='a'):
    return DisciplinaryZero(zero_id=identity,run_id='run',branch_id='branch',player_id=player,source_fingerprint='discipline-source',effective_week=week(start),duration_weeks=duration)
RESULTS=(result('a',100),result('a',70,edition='second'),result('b',80))


def calculate(zeros=(),target=3):
    return calculate_official_ranking(run_id='run',branch_id='branch',week=week(target),policy=POLICY,players=PLAYERS,results=RESULTS,disciplinary_zeros=zeros)


@pytest.mark.parametrize('target,points',[(2,170),(3,100),(4,100),(5,170)])
def test_zero_occupies_one_slot_only_during_explicit_interval(target,points):
    snapshot=calculate((zero(),),target)
    row=next(r for r in snapshot.rows if r.player_id=='a')
    assert row.points==points
    assert len(row.disciplinary_zeros)==(1 if target in (3,4) else 0)
    RankingInputManifest(players=PLAYERS,results=RESULTS,disciplinary_zeros=(zero(),)).verify(snapshot,None)


def test_independent_stacking_expiry_and_excess_zeros_preserve_all_identities():
    zeros=(zero('a',3,1),zero('b',3,2),zero('c',3,3))
    assert next(r for r in calculate(zeros,3).rows if r.player_id=='a').points==0
    assert len(next(r for r in calculate(zeros,3).rows if r.player_id=='a').disciplinary_zeros)==3
    assert next(r for r in calculate(zeros,4).rows if r.player_id=='a').points==0
    assert next(r for r in calculate(zeros,5).rows if r.player_id=='a').points==100
    assert next(r for r in calculate(zeros,6).rows if r.player_id=='a').points==170
    assert calculate(zeros).fingerprint==calculate(zeros[::-1]).fingerprint


def test_expiry_across_season_boundary_and_final_run_week():
    from beta_engine.domain.rankings.official import RankingWeek
    z=zero().model_copy(update={'effective_week':RankingWeek(season_index=0,week=61),'duration_weeks':2})
    assert z.active_at(RankingWeek(season_index=1,week=1))
    assert not z.active_at(RankingWeek(season_index=1,week=2))
    z=z.model_copy(update={'effective_week':RankingWeek(season_index=49,week=61)})
    assert z.active_at(RankingWeek(season_index=49,week=61))


@pytest.mark.parametrize('damage',['scope','player','duplicate','duration'])
def test_invalid_zero_is_rejected(damage):
    z=zero()
    if damage=='scope': z=z.model_copy(update={'branch_id':'other'})
    if damage=='player': z=z.model_copy(update={'player_id':'unknown'})
    if damage=='duration': z=z.model_copy(update={'duration_weeks':0})
    with pytest.raises(ValueError): calculate((z,z) if damage=='duplicate' else (z,))


def test_loaded_snapshot_rejects_bypassing_zero_capacity():
    snapshot=calculate()
    payload=snapshot.model_dump(mode='json')
    payload['rows'][0]['disciplinary_zeros']=[zero().model_dump(mode='json')]
    with pytest.raises(ValueError,match='Best N'):
        OfficialRankingSnapshot.model_validate_json(json.dumps(payload))


def test_empty_extension_preserves_legacy_serialization():
    assert 'disciplinary_zeros' not in calculate().model_dump_json()
    assert 'disciplinary_zeros' not in RankingInputManifest(players=PLAYERS,results=RESULTS).model_dump_json()


def test_transition_requires_explicit_resolved_discipline_mode():
    from beta_engine.application.official_ranking_transition import RankingTransitionContext
    data=dict(run_id='run',branch_id='branch',completed_week=week(2),target_week=week(3),policy=POLICY,players=PLAYERS,disciplinary_zeros=(zero(),))
    with pytest.raises(ValueError,match='resolved_zeros'):
        RankingTransitionContext(**data,discipline='none')
    assert RankingTransitionContext(**data,discipline='resolved_zeros').disciplinary_zeros==(zero(),)
