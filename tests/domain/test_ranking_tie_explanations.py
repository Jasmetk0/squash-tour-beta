import pytest
from beta_engine.domain.rankings.official import OfficialRankingPlayer, OfficialRankingPolicy, OfficialRankingResult, RankingWeek, calculate_official_ranking
from beta_engine.domain.rankings.input_manifest import RankingInputManifest
from beta_engine.domain.rankings.tie_explanations import explain_ranking_ties


def week(n): return RankingWeek(season_index=0, week=n)
PLAYERS = tuple(OfficialRankingPlayer(player_id=p, tie_break_token=p, tour_entry_week=week(1)) for p in ('a', 'b'))
POLICY = OfficialRankingPolicy(policy_id='policy', best_n=2)


def result(player, points, completed=1, edition='edition'):
    return OfficialRankingResult(edition_id=edition, player_id=player, source_fingerprint='source',
        completed_week=week(completed), first_publication_week=week(completed + 1), main_points=points)


def snapshot(players=PLAYERS, results=(), previous=None, target=4):
    return calculate_official_ranking(run_id='run', branch_id='branch', week=week(target), policy=POLICY,
                                     players=players, results=results, previous=previous)


@pytest.mark.parametrize('results,reason,high,low,slot', [
    ((result('a',100),result('b',60),result('b',40,edition='second')), 'result_profile',100,60,1),
    ((result('a',100,2),result('b',100)), 'completion_age',1,0,1),
    ((), 'stored_token','a','b',None),
])
def test_reports_exact_first_deciding_layer(results,reason,high,low,slot):
    current = snapshot(results=results)
    manifest = RankingInputManifest(players=PLAYERS, results=results)
    before = current.model_dump_json()
    tie, = explain_ranking_ties(current, manifest, None)
    assert (tie.reason,tie.higher_value,tie.lower_value,tie.result_slot) == (reason,high,low,slot)
    assert (tie.higher_player_id,tie.lower_player_id,tie.higher_rank,tie.lower_rank)==('a','b',1,2)
    assert current.model_dump_json() == before
    reversed_inputs = RankingInputManifest(players=PLAYERS[::-1],results=results[::-1])
    assert explain_ranking_ties(current,reversed_inputs,None)==(tie,)


def test_previous_position_overrides_token_at_zero_points():
    previous = snapshot(results=(result('b',100),), target=3)
    current = snapshot(previous=previous)
    tie, = explain_ranking_ties(current, RankingInputManifest(players=PLAYERS,results=()),previous)
    assert tie.reason=='previous_position' and tie.higher_player_id=='b'
    assert (tie.higher_value,tie.lower_value)==(1,2)


def test_previously_ranked_zero_precedes_new_player_and_ignores_zero_age():
    previous = snapshot(players=PLAYERS[1:], target=3)
    results=(result('a',0,2),result('b',0))
    current = snapshot(results=results, previous=previous)
    tie, = explain_ranking_ties(current,RankingInputManifest(players=PLAYERS,results=results),previous)
    assert tie.reason=='previous_position' and tie.higher_player_id=='b'
    assert tie.lower_value is None


def test_different_totals_have_no_tie_explanation():
    results=(result('a',100),)
    assert explain_ranking_ties(snapshot(results=results),RankingInputManifest(players=PLAYERS,results=results),None)==()


@pytest.mark.parametrize('damage',['manifest','snapshot','previous'])
def test_unverified_history_is_rejected(damage):
    previous=snapshot(target=3)
    current=snapshot(previous=previous)
    manifest=RankingInputManifest(players=PLAYERS,results=())
    if damage=='manifest': manifest=RankingInputManifest(players=PLAYERS[:1],results=())
    if damage=='snapshot': current=current.model_copy(update={'input_fingerprint':'0'*64})
    if damage=='previous': previous=None
    with pytest.raises(ValueError): explain_ranking_ties(current,manifest,previous)
