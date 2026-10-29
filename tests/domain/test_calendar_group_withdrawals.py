"""Fast adapter/version contracts; real HTTP tests prove persisted authority."""
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.tournaments.calendar_global_slots import (
    GlobalSlot,
    playing_slot_conflicts,
)
from beta_engine.domain.tournaments.calendar_group_withdrawals import (
    NativeGroupWalkover,
    NativeGroupWithdrawal,
    group_withdrawals,
    pending_group_walkovers,
)

pytestmark = pytest.mark.pr_critical


def record(**changes):
    values = {'run_id':'run', 'branch_id':'branch', 'edition_id':'group', 'group_index':1,
        'player_id':'A', 'week':RunWeekPosition(calendar=RunCalendar(52,1,2030,2),season_index=0,week=4),
        'slot_number':1, 'source_saved_head':'saved', 'source_checkpoint_fingerprint':'a'*64,
        'command_id':'withdraw', 'operator_label':'Admin', 'audit_reason':'Reviewed', 'reason_category':'illness'}
    return NativeGroupWithdrawal(**{**values, **changes})


def test_deduplication_rejects_contradictory_source_evidence():
    value = record()
    assert group_withdrawals((SimpleNamespace(group_withdrawals=(value,value)),)) == (value,)
    with pytest.raises(ValueError, match='Conflicting'):
        group_withdrawals((SimpleNamespace(group_withdrawals=(value,value.model_copy(update={'note':'changed'}))),))


def test_walkover_has_no_fabricated_match_data_or_simultaneous_player_conflict():
    from beta_engine.domain.tournaments.walkover_authority import (
        TournamentWalkoverResult,
    )
    r = record()
    group = SimpleNamespace(edition=SimpleNamespace(edition_id='group',group_configuration=True),
        draw=SimpleNamespace(schedule=SimpleNamespace(matches=(object(),))))
    other = SimpleNamespace(edition=SimpleNamespace(edition_id='other',group_configuration=None))
    def item(eid, mid, a, b):
        return SimpleNamespace(edition_id=eid,match_id=mid,index=0,
            projections=(SimpleNamespace(player_id=a),SimpleNamespace(player_id=b)))
    scheduled = (item('group','group:one','A','B'),item('other','other:one','A','C'))
    slot = SimpleNamespace(run_id='run',branch_id='branch',week=r.week,number=2,
        snapshot_fingerprint='b'*64,authorities=(group,other),remaining=scheduled,
        scheduled=scheduled,walkovers=(),inherited_match_ids=())
    cp = SimpleNamespace(events=(SimpleNamespace(group_withdrawals=(r,)),))
    pending = pending_group_walkovers(cp,slot)
    assert set(pending) == {'group:one'}
    result = pending['group:one'].result
    assert isinstance(result,TournamentWalkoverResult) and result.winner_player_id == 'B'
    assert not {'rally_log','duration','effects','games'} & set(type(result).model_fields)
    assert playing_slot_conflicts(cp,slot) == {}, 'Only the other actual match occupies player A'
    with pytest.raises(ValueError, match='Two withdrawn'):
        pending_group_walkovers(SimpleNamespace(events=(SimpleNamespace(group_withdrawals=(
            r,record(player_id='B',command_id='second'))),)),slot)


def test_historical_slots_cannot_acquire_nonplayed_data_and_equal_players_are_rejected():
    from beta_engine.domain.tournaments.walkover_authority import (
        TournamentWalkoverResult,
    )
    r = record()
    wo = NativeGroupWalkover(run_id='run',branch_id='branch',edition_id='group',week=r.week,
        slot_number=2,source_checkpoint_fingerprint='b'*64,withdrawal_fingerprint=r.fingerprint,
        result=TournamentWalkoverResult(match_id='group:one',winner_player_id='B',loser_player_id='A'))
    for schema in ('calendar_global_slot.v1','calendar_global_slot.v2'):
        with pytest.raises(ValueError, match='Historical slot'):
            GlobalSlot.model_construct(schema_version=schema,walkovers=(wo,)).canonical_evidence()
    with pytest.raises(ValueError, match='himself'):
        NativeGroupWalkover(**{**{key:getattr(wo,key) for key in type(wo).model_fields},
            'result':TournamentWalkoverResult(match_id='group:one',winner_player_id='A',loser_player_id='A')})


@pytest.mark.parametrize('hybrid,reward',[(True,0),(False,7)])
def test_undecided_hybrid_or_reward_policy_is_rejected_before_any_write(hybrid,reward):
    from beta_engine.application.calendar_native_groups import apply_group_withdrawal
    week = record().week
    authority = SimpleNamespace(draw=object(),tournament_fingerprint=None,
        edition=SimpleNamespace(schema_version='calendar_tournament_edition.v3',week=week,
            group_configuration=SimpleNamespace(format_kind='groups_knockout' if hybrid else 'groups',
                played_group_win_points=reward)))
    with pytest.raises(ValueError, match='zero Official'):
        apply_group_withdrawal(None,None,SimpleNamespace(week=week),authority,None,persist=False)
