"""Actual two-week MatchEngine component proof, not native Tour acceptance."""
from types import SimpleNamespace

import pytest

from beta_engine.domain.calendar.run_calendar import RunCalendar
from beta_engine.domain.calendar.run_week_position import RunWeekPosition
from beta_engine.domain.run_packages import canonical_hash
from beta_engine.domain.tournaments.draw_authority import TournamentDrawAuthorityBuilder
from beta_engine.domain.tournaments.draw_input_authority import TournamentDrawInputAuthorityBuilder
from beta_engine.domain.tournaments.entry_field import TournamentEntryApplication, TournamentEntryFieldCapacity, TournamentEntryFieldResolver
from beta_engine.domain.tournaments.ranking_snapshot_authority import TournamentRankingSnapshotAuthority
from beta_engine.domain.tournaments.wild_card_authority import TournamentWildCardAuthorityBuilder
from beta_engine.domain.tournaments.knockout_run_schedule import KnockoutRoundPosition, KnockoutRunSchedule
from beta_engine.domain.tournaments.scheduled_knockout_feeders import ScheduledKnockoutFeederPlan, scheduled_knockout_progress
from beta_engine.domain.tournaments.calendar_global_slots import calculate_match
from beta_engine.domain.players.calendar_canonical_match import CalendarCanonicalPlayerSource
from beta_engine.domain.players.calendar_continuation_match import CalendarContinuationMatch
from beta_engine.domain.players.sporting_bootstrap import derive_bootstrap_record
from beta_engine.domain.players.sporting import PlayerSportingBootstrapPolicy
from beta_engine.domain.players.calendar_native_competition import terminal_players
from beta_engine.domain.players.health import PlayerHealthProfile
from beta_engine.domain.matches.health import EffectiveMatchHealthSnapshot, project_player_health
from beta_engine.domain.simulation_slots import CanonicalMatchInputProjectionPolicy, project_player
from tests.domain.test_match_engine import _player
from tests.infrastructure.test_tournament_draw_authority import ranking_snapshot
from beta_engine.application.atp_sporting_package_adapter import build_atp_sporting_package, parse_sporting_profile

pytestmark=pytest.mark.pr_critical
PLAYERS=tuple(f'P{i:03d}' for i in range(44))


def plan():
    event='atp_2025_rotterdam'
    ranking=TournamentRankingSnapshotAuthority(run_id='run',branch_id='branch',event_id=event,
        ranking_week=ranking_snapshot(PLAYERS).week,ranking_snapshot=ranking_snapshot(PLAYERS),adopted_by_command_id='ranking')
    applications=tuple(TournamentEntryApplication(application_id=f'app-{p}',run_id='run',branch_id='branch',event_id=event,
        player_id=p,entry_window='main',decision_slot_ordinal=10,nr_tie_break_token=p,eligible=True) for p in PLAYERS[:-4])
    capacity=TournamentEntryFieldCapacity.for_main_entrant_count(main_entrant_count=32,qualification_draw_size=16,qualifier_spots=4,wild_card_slots=4)
    field=TournamentEntryFieldResolver.build_initial(authority=ranking,applications=applications,capacity=capacity)
    wc=TournamentWildCardAuthorityBuilder.build(field=field,field_sequence=1,command_id='wc',original_wild_card_player_ids=PLAYERS[-4:])
    inputs=TournamentDrawInputAuthorityBuilder.build(authority=ranking,field=field,field_sequence=1,command_id='input',draw_seed=555,
        main_seed_count=8,qualification_seed_count=None,schema_version='tournament_draw_input_authority.v3',wild_card_authority=wc)
    draw=TournamentDrawAuthorityBuilder.build(draw_input=inputs,command_id='draw')
    clock=RunCalendar(52,1,2025,2)
    def position(w,s): return KnockoutRoundPosition(week=RunWeekPosition(calendar=clock,season_index=0,week=w),slot=s)
    schedule=KnockoutRunSchedule(calendar=clock,qualification=tuple(position(5,s) for s in (1,2)),main=tuple(position(6,s) for s in range(1,6)))
    entity=build_atp_sporting_package().entities[2]
    profile=parse_sporting_profile(entity.payload)
    return ScheduledKnockoutFeederPlan(source_saved_revision_id='saved',source_saved_content_hash='a'*64,
        source_profile_fingerprint=entity.fingerprint,profile=profile,profile_payload_fingerprint=canonical_hash(profile.model_dump(mode='json')),
        draw_input=inputs,draw=draw,schedule=schedule)


@pytest.fixture(scope='module')
def played():
    p=plan()
    profiles={pid:CalendarCanonicalPlayerSource(player=_player(player_id=pid,base=55+i%25),
        source_generation_fingerprint=f'explicit-test-{pid}',potential_ability=90) for i,pid in enumerate(PLAYERS)}
    roster=tuple(derive_bootstrap_record(v,PlayerSportingBootstrapPolicy()) for v in profiles.values())
    matches=()
    positions={}
    frozen=[]
    for current in (*p.schedule.qualification,*p.schedule.main):
        progress,due=scheduled_knockout_progress(plan=p,matches=matches,positions=positions,current=current)
        assert due
        snapshot=canonical_hash({'plan':p.fingerprint,'position':current.model_dump(mode='json'),
            'players':[r.model_dump(mode='json') for r in roster],'accepted':[m.fingerprint for m in matches]})
        slot=SimpleNamespace(run_id=p.draw.run_id,branch_id=p.draw.branch_id,week=current.week,players=roster,
            snapshot_fingerprint=snapshot,source_health_fingerprint='c'*64)
        records={r.player_id:r for r in roster}
        made=[]
        for ready in due:
            projections=[]
            for pid in ready.player_ids:
                bio=profiles[pid]
                projections.append(project_player(records[pid],source_sporting_fingerprint=snapshot,
                    policy=CanonicalMatchInputProjectionPolicy(),profile_source_fingerprint=bio.source_generation_fingerprint,
                    profile_provenance='Explicit component test population',age=bio.player.age,name=bio.player.name,
                    nationality=bio.player.nationality,play_style=bio.player.play_style,archetype=bio.player.archetype,
                    hidden_career_traits=bio.player.hidden_career_traits))
            item=SimpleNamespace(match_id=ready.match_id,seed=ready.seed,sequence=len(matches)+len(made)+1,
                source_saved_head=p.source_saved_revision_id,projections=tuple(projections),
                health=EffectiveMatchHealthSnapshot(player_profiles=tuple(project_player_health(PlayerHealthProfile(player_id=pid)) for pid in ready.player_ids)))
            made.append(calculate_match(slot,item))
        frozen.append((current,tuple(made)))
        assert terminal_players(roster,made)==terminal_players(roster,tuple(reversed(made)))
        roster=terminal_players(roster,made)
        matches+=tuple(made)
        positions.update({m.match_id:current for m in made})
        if current == p.schedule.qualification[-1]:
            # Reopen the frozen plan and ordinary match DTOs between phases.
            # This is serialization recovery, not a native database Save claim.
            p=ScheduledKnockoutFeederPlan.model_validate_json(p.model_dump_json())
            matches=tuple(CalendarContinuationMatch.model_validate_json(m.model_dump_json()) for m in matches)
    return p,matches,positions,frozen


def test_real_qualification_winners_feed_main_in_following_week(played):
    p,matches,positions,batches=played
    progress,due=scheduled_knockout_progress(plan=p,matches=matches,positions=positions,current=p.schedule.main[-1])
    assert not due and not progress.ready_matches and progress.champion_player_id
    assert len(matches)==43 and len(progress.qualification_winners)==4
    assert len([m for m in matches if m.week.week==5])==12
    assert len([m for m in matches if m.week.week==6])==31
    assert all(m.result.rally_log.events for m in matches)
    assert scheduled_knockout_progress(plan=p,matches=tuple(reversed(matches)),positions=positions,current=p.schedule.main[-1])==(progress,due)
    assert ScheduledKnockoutFeederPlan.model_validate_json(p.model_dump_json())==p
    q_winners={pid for _,pid in progress.qualification_winners}
    main_first=[m for m in batches[2][1]]
    assert q_winners <= {pid for m in main_first for pid in (m.result.player_a_id,m.result.player_b_id)}


@pytest.mark.parametrize('damage',['wrong_week','wrong_slot','future','missing_position','duplicate','stale_head','stale_seed'])
def test_rejects_wrong_schedule_or_result_source(played,damage):
    p,accepted,positions,_=played
    matches=list(accepted);positions=dict(positions);current=p.schedule.main[-1]
    first=matches[0]
    if damage=='wrong_week': positions[first.match_id]=p.schedule.main[0]
    if damage=='wrong_slot': positions[first.match_id]=p.schedule.qualification[1]
    if damage=='future': current=p.schedule.qualification[0]
    if damage=='missing_position': positions.pop(first.match_id)
    if damage=='duplicate': matches.append(first)
    if damage=='stale_head': matches[0]=first.model_copy(update={'source_saved_head':'foreign'})
    if damage=='stale_seed': matches[0]=first.model_copy(update={'seed':first.seed+1})
    with pytest.raises(ValueError): scheduled_knockout_progress(plan=p,matches=tuple(matches),positions=positions,current=current)


def test_cannot_skip_an_unplayed_qualification_round():
    p=plan()
    with pytest.raises(ValueError,match='earlier knockout round'):
        scheduled_knockout_progress(plan=p,matches=(),positions={},current=p.schedule.main[0])


def test_edited_nested_source_profile_is_rejected():
    p=plan()
    p.profile.main_points['champion']+=1
    with pytest.raises(ValueError,match='Frozen scheduled sporting profile changed'):
        scheduled_knockout_progress(plan=p,matches=(),positions={},current=p.schedule.qualification[0])


def test_partial_field_cannot_silently_add_byes():
    p=plan()
    altered=p.draw_input.model_copy(update={'qualification_player_ids':p.draw_input.qualification_player_ids[:-1]})
    changed=p.model_copy(update={'draw_input':altered})
    with pytest.raises(ValueError):
        scheduled_knockout_progress(plan=changed,matches=(),positions={},current=p.schedule.qualification[0])
