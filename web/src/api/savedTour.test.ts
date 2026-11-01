import {describe,it,expect} from 'vitest'
import {matchesSavedTourContext,validSavedTourCalendar,validSavedTourEdition,validSavedTourMatchDetail,
  validSavedTourRallyTransition,validSavedTourRallyPagePair} from './savedTour'
import type {SavedTourCalendar,SavedTourEdition,SavedTourEvent,SavedTourMatchDetail} from './savedTour'
const event:SavedTourEvent={event_id:'open',season:'2002/2003',season_week:12,
  event_name:'Open',template_id:'tpl',category:'DIAMOND',tour_level:'WORLD',
  host_country:'CZE',host_city:'Brno',region:'EUROPE',main_draw_size:16,
  qualification_draw_size:8,seeds_count:4,qualifier_spots:4,wild_cards:2,byes:0,
  ranking_status:'ranked',result_published:false,champion_player_id:null,finalist_player_id:null}
const calendar:SavedTourCalendar={schema_version:'run_saved_tour_calendar.v1',
  source:'reachable_saved_revision',run_id:'r',branch_id:'b',revision_branch_id:'original',
  saved_revision_id:'rev',season_index:2,season:'2002/2003',week_count:61,
  calendar_status:'ready',edition_count:1,editions:[event]}
const edition:SavedTourEdition={schema_version:'run_saved_tour_edition.v1',
  source:'reachable_saved_revision',run_id:'r',branch_id:'b',revision_branch_id:'original',
  saved_revision_id:'rev',season_index:2,edition:event,published_result:null,
  lifecycle_status:'unavailable'}
describe('strict Saved Tour response identity',()=>{
  it('accepts only exact pending audited group ties before final standings exist',()=>{
    const schedule={
      schema_version:'run_saved_tour_group_schedule.v1' as const,
      source:'saved_tournament_group_match_schedule_authority.v1' as const,
      run_id:'r',revision_branch_id:'original',event_id:'open',
      authority_fingerprint:'b'.repeat(64),group_count:1,group_size:3,match_day_count:3,
      matches:[
        {match_id:'ab',group_index:1,match_day_ordinal:1,match_order:1,
          top_player_id:'A',bottom_player_id:'B',best_of:3 as const},
        {match_id:'ac',group_index:1,match_day_ordinal:2,match_order:1,
          top_player_id:'A',bottom_player_id:'C',best_of:3 as const},
        {match_id:'bc',group_index:1,match_day_ordinal:3,match_order:1,
          top_player_id:'B',bottom_player_id:'C',best_of:3 as const}
      ]
    }
    const decision={group_index:1,case_fingerprint:'a'.repeat(64),
      ordered_player_ids:['C','A','B'],admin_reason:'Review of tied sporting criteria.'}
    const valid=(decisions:typeof decision[])=>
      validSavedTourEdition({...edition,group_schedule:schedule,
        group_standings:null,pending_group_tie_decisions:decisions},'r','b','rev',2,'open')
    expect(valid([decision])).toBe(true)
    expect(valid([])).toBe(true)
    expect(valid([{...decision,ordered_player_ids:['C','A','A']}])).toBe(false)
    expect(valid([{...decision,ordered_player_ids:['C','not-in-group']}])).toBe(false)
    expect(valid([{...decision,group_index:2}])).toBe(false)
    expect(valid([{...decision,case_fingerprint:'stale'}])).toBe(false)
    expect(valid([{...decision,admin_reason:' '}])).toBe(false)
    expect(valid([decision,decision])).toBe(false)
    expect(validSavedTourEdition({...edition,pending_group_tie_decisions:[decision]},
      'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,group_schedule:schedule,
      pending_group_tie_decisions:[decision],revision_branch_id:'foreign'},
      'r','b','rev',2,'open')).toBe(false)
  })

  it('accepts frozen group table points and explicit tie audit only in its original branch',()=>{
    const schedule={
      schema_version:'run_saved_tour_group_schedule.v1' as const,
      source:'saved_tournament_group_match_schedule_authority.v1' as const,
      run_id:'r',revision_branch_id:'original',event_id:'open',
      authority_fingerprint:'b'.repeat(64),
      group_count:1,group_size:2,match_day_count:1,
      matches:[{match_id:'g1',group_index:1,match_day_ordinal:1,match_order:1,
        top_player_id:'A',bottom_player_id:'B',best_of:3 as const}]
    }
    const player=(position:number,player_id:string)=>({
      position,player_id,wins:1,losses:0,group_points:4,
      played_matches:1,walkovers_received:0,walkovers_conceded:0,
      games_won:2,games_lost:0,points_won:22,points_lost:8
    })
    const standings={
      schema_version:'run_saved_tour_group_standings.v1' as const,
      source:'saved_tournament_group_standings_authority' as const,
      run_id:'r',revision_branch_id:'original',event_id:'open',
      authority_fingerprint:'c'.repeat(64),
      group_schedule_fingerprint:schedule.authority_fingerprint,
      groups:[{group_index:1,rows:[player(1,'A'),player(2,'B')]}],
      tie_decisions:[{group_index:1,case_fingerprint:'d'.repeat(64),
        ordered_player_ids:['A','B'],admin_reason:'Audited final table'}]
    }
    const valid=(x:typeof standings)=>validSavedTourEdition({
      ...edition,group_schedule:schedule,group_standings:x
    },'r','b','rev',2,'open')
    expect(valid(standings)).toBe(true)
    expect(valid({...standings,revision_branch_id:'b'})).toBe(false)
    expect(valid({...standings,group_schedule_fingerprint:'a'.repeat(64)})).toBe(false)
    expect(valid({...standings,groups:[{group_index:1,rows:[player(1,'A'),player(2,'A')]}]})).toBe(false)
    expect(valid({...standings,groups:[{group_index:1,rows:[player(1,'A'),player(3,'B')]}]})).toBe(false)
    expect(valid({...standings,groups:[{group_index:1,rows:[{...player(1,'A'),group_points:-1},player(2,'B')]}]})).toBe(false)
    expect(valid({...standings,tie_decisions:[{...standings.tie_decisions[0],admin_reason:' ' }]})).toBe(false)
    expect(validSavedTourEdition({...edition,group_standings:standings},'r','b','rev',2,'open')).toBe(false)
  })

  it('accepts validated saved group chronology and rejects foreign, repeated or forged pairs',()=>{
    const source={
      schema_version:'run_saved_tour_group_schedule.v1' as const,
      source:'saved_tournament_group_match_schedule_authority.v1' as const,
      run_id:'r',revision_branch_id:'original',event_id:'open',
      authority_fingerprint:'d'.repeat(64),
      group_count:1,group_size:2,match_day_count:1,
      matches:[{match_id:'g1',group_index:1,match_day_ordinal:1,
        match_order:1,top_player_id:'A',bottom_player_id:'B',best_of:3 as const}]
    }
    const model={...edition,group_schedule:source}
    expect(validSavedTourEdition(model,'r','b','rev',2,'open')).toBe(true)
    expect(validSavedTourEdition({...model,group_schedule:{...source,revision_branch_id:'b'}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...model,group_schedule:{...source,authority_fingerprint:'stale'}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...model,group_schedule:{...source,matches:[
      {...source.matches[0],top_player_id:'A',bottom_player_id:'A'}]}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...model,group_schedule:{...source,matches:[
      {...source.matches[0],group_index:2}]}},'r','b','rev',2,'open')).toBe(false)
  })

  it('verifies only adjacent real Saved frames across a 25-rally page boundary',()=>{
    const prev={rally_index:25,set_number:1,server_player_id:'A',winner_player_id:'A',
      score_a_before:24,score_b_before:0,score_a_after:25,score_b_after:0,
      sets_a_after:0,sets_b_after:0,set_complete:false,match_complete:false}
    const next={...prev,rally_index:26,score_a_before:25,score_a_after:26}
    expect(validSavedTourRallyTransition(prev,next)).toBe(true)
    expect(validSavedTourRallyTransition(prev,{...next,score_a_before:125})).toBe(false)
    expect(validSavedTourRallyTransition(prev,{...next,rally_index:27})).toBe(false)
    expect(validSavedTourRallyTransition(prev,{...next,sets_a_after:1})).toBe(false)
    expect(validSavedTourRallyTransition(prev,{...next,sets_a_after:-1})).toBe(false)
    expect(validSavedTourRallyTransition({...prev,match_complete:true},next)).toBe(false)
    const won={...prev,set_complete:true,sets_a_after:1}
    const newGame={...next,set_number:2,score_a_before:0,score_a_after:1,sets_a_after:1}
    expect(validSavedTourRallyTransition(won,newGame)).toBe(true)
    expect(validSavedTourRallyTransition(won,{...newGame,score_a_before:1})).toBe(false)
    expect(validSavedTourRallyTransition(won,{...newGame,set_number:3})).toBe(false)
    expect(validSavedTourRallyTransition(won,{...newGame,sets_a_after:2})).toBe(false)
    expect(validSavedTourRallyTransition(won,{...newGame,set_complete:true,sets_a_after:2})).toBe(true)
    expect(validSavedTourRallyTransition(won,next)).toBe(false)
  })
  it('requires stable canonical match authority for adjacent Saved pages',()=>{
    const base:SavedTourMatchDetail={
      schema_version:'run_saved_tour_match_detail.v1',source:'reachable_saved_revision',
      run_id:'r',branch_id:'b',revision_branch_id:'ancestor',
      saved_revision_id:'rev',season_index:2,event_id:'open',match_id:'final',
      match:{match_id:'final',draw_type:'main',round_number:1,bracket_position:1,
        winner_player_id:'A',loser_player_id:'B',scoreline:'3-0'},
      replay_status:'available',player_a_id:'A',player_b_id:'B',
      offset:0,limit:25,total_rallies:27,has_more:true,
      rallies:[{rally_index:25,set_number:1,server_player_id:'A',winner_player_id:'A',
        score_a_before:24,score_b_before:0,score_a_after:25,score_b_after:0,
        sets_a_after:0,sets_b_after:0,set_complete:false,match_complete:false}]
    }
    const following:SavedTourMatchDetail={...base,offset:25,has_more:false,
      rallies:[{...base.rallies[0],rally_index:26,score_a_before:25,score_a_after:26}]}
    expect(validSavedTourRallyPagePair(base,following)).toBe(true)
    expect(validSavedTourRallyPagePair(following,base)).toBe(false)
    expect(validSavedTourRallyPagePair(base,{...following,total_rallies:28})).toBe(false)
    expect(validSavedTourRallyPagePair(base,{...following,revision_branch_id:'foreign'})).toBe(false)
    expect(validSavedTourRallyPagePair(base,{...following,
      match:{...following.match,scoreline:'3-2'}})).toBe(false)
    expect(validSavedTourRallyPagePair(base,{...following,player_a_id:'B'})).toBe(false)
    expect(validSavedTourRallyPagePair(base,{...following,offset:50})).toBe(false)
    expect(validSavedTourRallyPagePair(base,{...following,rallies:[]})).toBe(false)
  })
  it('rejects stale, foreign and forged archived match pages',()=>{
    const data:SavedTourMatchDetail={
      schema_version:'run_saved_tour_match_detail.v1',
      source:'reachable_saved_revision' as const,
      run_id:'r',branch_id:'b',revision_branch_id:'original',
      saved_revision_id:'rev',season_index:2,event_id:'open',match_id:'final',
      match:{match_id:'final',draw_type:'main',round_number:2,
        bracket_position:1,winner_player_id:'A',loser_player_id:'B',scoreline:'3-2'},
      replay_status:'available' as const,player_a_id:'A',player_b_id:'B',
      offset:0,limit:25,total_rallies:1,has_more:false,
      rallies:[{rally_index:1,set_number:1,server_player_id:'A',
        winner_player_id:'A',score_a_before:0,score_b_before:0,score_a_after:1,
        score_b_after:0,sets_a_after:0,sets_b_after:0,
        set_complete:true,match_complete:true}]
    }
    const valid=(v:SavedTourMatchDetail)=>validSavedTourMatchDetail(v,'r','b','rev',2,'open','final',0,25)
    expect(valid(data)).toBe(true)
    expect(valid({...data,saved_revision_id:'new-head'})).toBe(false)
    expect(valid({...data,branch_id:'foreign'})).toBe(false)
    expect(valid({...data,event_id:'other'})).toBe(false)
    expect(valid({...data,match:{...data.match,match_id:'unrelated'}})).toBe(false)
    expect(valid({...data,replay_status:'unavailable'})).toBe(false)
    expect(valid({...data,rallies:[{...data.rallies[0],rally_index:26}]})).toBe(false)
    expect(valid({...data,has_more:true})).toBe(false)
    expect(valid({...data,player_a_id:'unknown'})).toBe(false)
    expect(valid({...data,offset:25})).toBe(false)
    for(const bad of [
      {...data.rallies[0],score_a_after:'1' as unknown as number},
      {...data.rallies[0],score_b_before:-1},
      {...data.rallies[0],sets_a_after:1.5},
      {...data.rallies[0],set_complete:'false' as unknown as boolean},
      {...data.rallies[0],match_complete:null as unknown as boolean},
      {...data.rallies[0],set_number:0}
    ])expect(valid({...data,rallies:[bad]})).toBe(false)
    expect(valid({...data,match:{...data.match,round_number:0}})).toBe(false)
    expect(valid({...data,match:{...data.match,scoreline:''}})).toBe(false)
    // Page-local score continuity is an invariant of the real MatchEngine log.
    const two={...data,total_rallies:2,has_more:false,rallies:[
      {...data.rallies[0],set_complete:false,match_complete:false},
      {...data.rallies[0],rally_index:2,score_a_before:1,score_a_after:2,
        sets_a_after:1,set_complete:true,match_complete:true}
    ]}
    const validTwo=(m:SavedTourMatchDetail)=>validSavedTourMatchDetail(
      m,'r','b','rev',2,'open','final',0,25)
    expect(validTwo(two)).toBe(true)
    expect(validTwo({...two,rallies:[two.rallies[0],{
      ...two.rallies[1],score_a_before:0
    }]})).toBe(false)
    expect(validTwo({...two,rallies:[two.rallies[0],{
      ...two.rallies[1],match_complete:true,set_complete:false
    }]})).toBe(false)
    expect(validTwo({...two,rallies:[{
      ...two.rallies[0],match_complete:true,set_complete:true
    },two.rallies[1]]})).toBe(false)
    expect(validTwo({...two,rallies:[two.rallies[0],{
      ...two.rallies[1],score_a_after:0
    }]})).toBe(false)
    expect(validTwo({...two,rallies:[two.rallies[0],{
      ...two.rallies[1],set_number:2
    }]})).toBe(false)
    expect(validTwo({...two,rallies:[two.rallies[0],{
      ...two.rallies[1],sets_a_after:2
    }]})).toBe(false)
    const endOfGame={...two.rallies[0],set_complete:true,match_complete:false,sets_a_after:1}
    const nextGame={...two.rallies[1],set_number:2,score_a_before:0,score_a_after:1,
      sets_a_after:1,set_complete:false,match_complete:false}
    expect(validTwo({...two,rallies:[endOfGame,nextGame]})).toBe(true)
    expect(validTwo({...two,rallies:[endOfGame,{...nextGame,score_a_before:1}]})).toBe(false)
    expect(validTwo({...two,rallies:[{
      ...two.rallies[0],winner_player_id:null,score_a_after:1
    },two.rallies[1]]})).toBe(false)
  })

  it('validates explicit Run/selected Branch/revision/season and original ancestry owner',()=>{
    expect(validSavedTourCalendar(calendar,'r','b','rev',2)).toBe(true)
    expect(matchesSavedTourContext(edition,'r','b','rev',2)).toBe(true)
    expect(validSavedTourCalendar(calendar,'other','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar(calendar,'r','other','rev',2)).toBe(false)
    expect(validSavedTourCalendar(calendar,'r','b','stale',2)).toBe(false)
    expect(validSavedTourCalendar(calendar,'r','b','rev',0)).toBe(false)
    expect(validSavedTourCalendar({...calendar,revision_branch_id:''},'r','b','rev',2)).toBe(false)
  })
  it('rejects forged publication flags and malformed published final IDs at the API boundary',()=>{
    const valid=(entry:SavedTourEvent)=>
      validSavedTourCalendar({...calendar,editions:[entry]},'r','b','rev',2)
    const wire=(overrides:Record<string,unknown>)=>
      ({...event,...overrides} as SavedTourEvent)
    expect(valid(event)).toBe(true)
    expect(valid(wire({result_published:'false'}))).toBe(false)
    expect(valid(wire({result_published:1}))).toBe(false)
    expect(valid(wire({result_published:null}))).toBe(false)
    expect(valid(wire({result_published:true,champion_player_id:23}))).toBe(false)
    expect(valid(wire({result_published:true,finalist_player_id:''}))).toBe(false)
    expect(valid(wire({result_published:true,champion_player_id:'A',finalist_player_id:'A'}))).toBe(false)
    expect(valid(wire({result_published:true,champion_player_id:null,finalist_player_id:null}))).toBe(false)
    expect(valid(wire({result_published:true,champion_player_id:'A',finalist_player_id:null}))).toBe(false)
    expect(valid(wire({result_published:true,champion_player_id:null,finalist_player_id:'B'}))).toBe(false)
    expect(valid(wire({result_published:true,champion_player_id:'A',finalist_player_id:'B'}))).toBe(true)
    expect(valid(wire({result_published:false,champion_player_id:'stale'}))).toBe(true)
    expect(validSavedTourCalendar({...calendar,calendar_status:'absent' as 'ready'},'r','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar({...calendar,calendar_status:'empty'},'r','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar({...calendar,editions:[null as unknown as SavedTourEvent]},'r','b','rev',2)).toBe(false)
    expect(valid(wire({event_id:23}))).toBe(false)
    expect(valid(wire({event_id:' '}))).toBe(false)
    expect(valid(wire({season_week:1.5}))).toBe(false)
    expect(valid(wire({season_week:Number.MAX_SAFE_INTEGER+1}))).toBe(false)
  })
  it('refuses inconsistent published winners between Edition label and canonical result',()=>{
    const winner={...event,result_published:true,champion_player_id:'P1',finalist_player_id:'P2'}
    const result={
      schema_version:'viewer_tournament_result.v1' as const,
      product_run_id:'r',viewer_branch_id:'original',event_id:'open',
      completed_season_index:2,completed_week:12,champion_player_id:'P1',
      finalist_player_id:'P2',qualification_winner_ids:[],players:[],matches:[]
    }
    const valid=(e:SavedTourEdition)=>
      validSavedTourEdition(e,'r','b','rev',2,'open')
    expect(valid({...edition,edition:winner,published_result:result})).toBe(true)
    // An Edition's own recorded time must match the selected historical season,
    // even if its published result was forged to agree with that wrong week.
    expect(valid({...edition,edition:{...event,season:'2003/2004'}})).toBe(false)
    expect(valid({...edition,edition:{...event,season:'2002/03'}})).toBe(true)
    expect(valid({...edition,edition:{...event,season_week:0}})).toBe(false)
    expect(valid({...edition,edition:{...event,season_week:62}})).toBe(false)
    expect(valid({...edition,edition:{...event,season_week:1.5}})).toBe(false)
    expect(valid({...edition,edition:{...event,season_week:Number.MAX_SAFE_INTEGER+1}})).toBe(false)
    expect(valid({...edition,edition:{...event,event_id:17 as unknown as string}})).toBe(false)
    expect(valid({...edition,edition:{...winner,season:'2001/02'},published_result:result})).toBe(false)
    expect(valid({...edition,edition:{...winner,season_week:13},published_result:result})).toBe(false)
    expect(valid({...edition,edition:{...winner,champion_player_id:null},published_result:{
      ...result,champion_player_id:null as unknown as string
    }})).toBe(false)
    expect(valid({...edition,edition:winner,published_result:{...result,champion_player_id:'P3'}})).toBe(false)
    expect(valid({...edition,edition:winner,published_result:{...result,finalist_player_id:'P3'}})).toBe(false)
    expect(valid({...edition,edition:winner,published_result:{
      ...result,schema_version:'wrong' as 'viewer_tournament_result.v1'
    }})).toBe(false)
    expect(valid({...edition,edition:{...winner,result_published:'false' as unknown as boolean},published_result:result})).toBe(false)
    expect(valid({...edition,edition:{...winner,finalist_player_id:'P1'},published_result:result})).toBe(false)
    expect(valid({...edition,edition:winner,published_result:{
      ...result,matches:undefined as unknown as typeof result.matches
    }})).toBe(false)
    const match={match_id:'final',draw_type:'main',round_number:2,
      bracket_position:1,winner_player_id:'P1',loser_player_id:'P2',scoreline:'3-1'}
    const published=(matches:typeof match[])=>
      valid({...edition,edition:winner,published_result:{...result,matches}})
    expect(published([match])).toBe(true)
    expect(published([match,match])).toBe(false)
    expect(published([{...match,round_number:0}])).toBe(false)
    expect(published([{...match,bracket_position:0}])).toBe(false)
    expect(published([{...match,scoreline:''}])).toBe(false)
    expect(published([{...match,winner_player_id:'',loser_player_id:'P2'}])).toBe(false)
    expect(published([{...match,loser_player_id:'P1'}])).toBe(false)
    expect(published([{...match,loser_player_id:null as unknown as string}])).toBe(true)
    expect(valid({...edition,edition:winner,published_result:{
      ...result,players:[{player_id:'P1',draw_type:'main',reached_stage:'champion',
        wins:-1,losses:0}]
    }})).toBe(false)
  })
  it('rejects duplicates, invalid weeks and cross-season source rows',()=>{
    expect(validSavedTourCalendar({...calendar,editions:[event,event],edition_count:2},'r','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar({...calendar,editions:[{...event,season_week:62}]},'r','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar({...calendar,editions:[{...event,season:'2000/2001'}]},'r','b','rev',2)).toBe(false)
  })
  it('accepts both supported season spellings for empty and populated calendars',()=>{
    const short={...event,season:'2002/03'}
    const populated={...calendar,editions:[short]}
    expect(validSavedTourCalendar(populated,'r','b','rev',2)).toBe(true)
    expect(validSavedTourCalendar({...populated,season:'2002/03'},'r','b','rev',2)).toBe(true)
    const empty={...calendar,calendar_status:'empty' as const,edition_count:0,editions:[]}
    expect(validSavedTourCalendar(empty,'r','b','rev',2)).toBe(true)
    expect(validSavedTourCalendar({...empty,season:'2002/03'},'r','b','rev',2)).toBe(true)
    // Last supported season checks the century-correct compact label, too.
    const last={...calendar,season_index:49,season:'2049/2050',
      editions:[{...event,season:'2049/50'}]}
    expect(validSavedTourCalendar(last,'r','b','rev',49)).toBe(true)
  })
  it('rejects malformed, wrong-year and wrong-request calendar seasons even when empty',()=>{
    const empty={...calendar,calendar_status:'empty' as const,edition_count:0,editions:[]}
    for(const invalid of ['2001/2002','2002/04','2002/2004','2002/3','2002/2103',
      '2050/2051','2002/03 ', '2002/2003/04']){
      expect(validSavedTourCalendar({...empty,season:invalid},'r','b','rev',2)).toBe(false)
      expect(validSavedTourCalendar({...calendar,editions:[{...event,season:invalid}]},
        'r','b','rev',2)).toBe(false)
    }
    expect(validSavedTourCalendar(calendar,'r','b','rev',3)).toBe(false)
    expect(validSavedTourCalendar({...empty,season_index:3},'r','b','rev',3)).toBe(false)
    expect(validSavedTourCalendar({...empty,season_index:50},'r','b','rev',50)).toBe(false)
  })
  it('does not infer a result from a calendar completed status',()=>{
    expect(validSavedTourEdition(edition,'r','b','rev',2,'open')).toBe(true)
    expect(validSavedTourEdition({...edition,edition:{...event,result_published:true}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition(edition,'r','b','rev',2,'other')).toBe(false)
    expect(validSavedTourEdition({...edition,saved_revision_id:'today'},'r','b','rev',2,'open')).toBe(false)
  })

  it('refuses forged Match Day ordering and foreign historical schedule scope',()=>{
    const match={global_slot_ordinal:2,match_day_ordinal:1,match_order:2,
      draw_phase:'main' as const,round_number:1,group_id:'g2',match_id:'m2'}
    const schedule={
      schema_version:'run_saved_tour_match_schedule.v1' as const,
      source:'saved_week_simulation_schedule.v2' as const,
      run_id:'r',revision_branch_id:'original',event_id:'open',
      season_index:2,season_week:12,week_schedule_fingerprint:'a'.repeat(64),slots:[match]
    }
    const inScope={...edition,match_schedule:schedule}
    expect(validSavedTourEdition(inScope,'r','b','rev',2,'open')).toBe(true)
    expect(validSavedTourEdition({...edition,match_schedule:{...schedule,run_id:'foreign'}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,match_schedule:{...schedule,season_week:11}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,match_schedule:{...schedule,slots:[match,{...match}]}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,match_schedule:{...schedule,week_schedule_fingerprint:'tampered'}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,match_schedule:{...schedule,slots:[{...match,match_day_ordinal:0}]}},'r','b','rev',2,'open')).toBe(false)
  })
  it('rejects foreign Entry/Draw authorities and inconsistent first-round slots',()=>{
    const fields={schema_version:'viewer_tournament_entry_field.v1' as const,
      product_run_id:'r',viewer_branch_id:'original',event_id:'open',
      field_sequence:1,mode:'initial' as const,main_draw_capacity:2,
      active_main_entrant_count:2,effective_main_bye_count:0,
      direct_main_player_ids:['A','B'],qualification_player_ids:[],
      alternate_player_ids:[],withdrawn_player_ids:[]}
    const slots=[{slot_index:1,entrant_kind:'player' as const,player_id:'A',
      placeholder_id:null,seed_number:1,entry_status:null},
      {slot_index:2,entrant_kind:'player' as const,player_id:'B',
      placeholder_id:null,seed_number:2,entry_status:null}]
    const draw={schema_version:'viewer_tournament_draw.v1' as const,
      product_run_id:'r',viewer_branch_id:'original',event_id:'open',
      revision_count:0,main:{draw_type:'main' as const,section_id:null,
        bracket_size:2,slots},qualification_sections:[]}
    expect(validSavedTourEdition({...edition,entry_field:fields,draw},'r','b','rev',2,'open')).toBe(true)
    expect(validSavedTourEdition({...edition,entry_field:{...fields,viewer_branch_id:'b'},draw},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,entry_field:fields,draw:{...draw,event_id:'foreign'}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,entry_field:fields,draw:{...draw,main:{...draw.main,slots:[slots[0],slots[0]]}}},'r','b','rev',2,'open')).toBe(false)
    expect(validSavedTourEdition({...edition,draw},'r','b','rev',2,'open')).toBe(false)
  })
})
