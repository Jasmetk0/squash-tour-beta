import { describe, expect, it } from 'vitest'
import {
  verifyContinuation, verifyNativeTournamentClosure,
  type ContinuationView, type NativeTournamentClosureCommand,
  type NativeTournamentClosureReceipt,
} from './calendarContinuation'

const fp = (c: string) => c.repeat(64)
const rounds = [
  ['qf1','a','b','a'],['qf2','c','d','c'],['qf3','e','f','e'],['qf4','g','h','g'],
  ['sf1','a','c','a'],['sf2','e','g','e'],['final','a','e','a'],
] as const
const matches = rounds.map(([round, a, b, winner], i) => ({
  match_id: 'draw:'+round, sequence: i+1, fingerprint: fp('b'),
  player_ids: [a,b] as [string,string], winner_player_id:winner, rally_count:50,
  saved:true,
}))
const placements = [
  ['a','champion',3,0,100], ['b','quarterfinal',0,1,15], ['c','semifinal',1,1,30],
  ['d','quarterfinal',0,1,15], ['e','finalist',2,1,60],
  ['f','quarterfinal',0,1,15], ['g','semifinal',1,1,30], ['h','quarterfinal',0,1,15],
] as const
const players = placements.map(([player_id,reached_stage,wins,losses,prepared_points])=>({
  player_id,reached_stage,wins,losses,prepared_points,
  played_match_ids:matches.filter(m=>m.player_ids.includes(player_id)).map(m=>m.match_id),
}))
const event = {
  tournament_id:'draw',command_id:'play-draw',fingerprint:fp('c'),week:2,
  entrant_ids:['a','b','c','d','e','f','g','h'],entrant_count:8,match_count:7,
  winner_player_id:'a',match_ids:matches.map(m=>m.match_id),saved:true,
  scope:'sporting_exhibition_knockout_not_official' as const,
  prepared_points_status:'prepared_not_official' as const,
  prepared_policy:{schema_version:'calendar_followup_point_policy.v2' as const,
    category_label:'Prepared only',champion:100,finalist:60,semifinal:30,quarterfinal:15,validity_weeks:52},
  prepared_awards:players.map(p=>({
    player_id:p.player_id,reached_stage:p.reached_stage,main_points:p.prepared_points,
    source_tournament_fingerprint:fp('d'),source_policy_fingerprint:fp('e'),
  })),
  result_closed:true,result_closure_saved:true,
}
const closed = {
  tournament_id:'draw',command_id:'close-draw',fingerprint:fp('f'),
  champion_player_id:'a',finalist_player_id:'e',source_tournament_fingerprint:fp('c'),
  scope:'played_native_result_closed_not_official' as const,saved:true,players,
}
const view: ContinuationView = {
  schema_version:'calendar_continuation_inspection.v1',
  run_id:'r',branch_id:'b',saved_head_revision_id:'saved',draft_version:2,
  checkpoint_fingerprint:fp('g'),player_ids:['a','b','c','d','e','f','g','h'],
  saved:true,can_play:true,limited_player_ids:[],health_numeric_effect_applied:false,
  sporting_week:{calendar:{weeks_per_year:52,season_start_year_week:52,start_year:2030,season_count:3},season_index:0,week:2},
  weekly_advance_count:1,weekly_advances:[{command_id:'wk',fingerprint:fp('h'),completed_week:1,target_week:2,saved:true}],
  matches,tournaments:[event],closures:[closed],
}
const command: NativeTournamentClosureCommand = {
  command_id:'close-draw',tournament_id:'draw',expected_saved_head:'saved',
  expected_checkpoint_fingerprint:fp('g'),operator_label:'Admin',
  audit_reason:'Reviewed result closure',explicit_result_confirmation:true,
}
const receipt: NativeTournamentClosureReceipt = {
  schema_version:'calendar_native_tournament_closure_receipt.v1',
  fingerprint:fp('f'),checkpoint_fingerprint:fp('i'),
  official_ranking_published:false,
  publication_status:'native_result_closed_not_official',
  closure:{
    ...closed,source_saved_head:'saved',source_checkpoint_fingerprint:fp('g'),
    source_week_event_count:2,source_prepared_awards_fingerprint:fp('j'),
    request_fingerprint:fp('k'),
  },
}
describe('signed played native result closure',()=>{
  it('inspects authentic seven-match per-player counters and never declares Official',()=>{
    expect(verifyContinuation(view,'r','b','saved')).toBe(view)
    expect(verifyNativeTournamentClosure(receipt,command,view)).toBe(receipt)
  })
  it('rejects a forged point, victory and historical match',()=>{
    const altered={...view,closures:[{...closed,players:players.map((p,i)=>i===0?{...p,wins:2}:p)}]}
    expect(()=>verifyContinuation(altered,'r','b','saved')).toThrow('closed-result history changed')
    const alteredPoints={...view,closures:[{...closed,players:players.map((p,i)=>i===0?{...p,prepared_points:800}:p)}]}
    expect(()=>verifyContinuation(alteredPoints,'r','b','saved')).toThrow('closed-result history changed')
    expect(()=>verifyNativeTournamentClosure({...receipt,closure:{...receipt.closure,source_tournament_fingerprint:fp('z')}},command,view))
      .toThrow('does not match')
  })
  it('keeps an old unclosed eight-player event readable',()=>{
    const existing={...event,result_closed:false,result_closure_saved:false}
    const old={...view,tournaments:[existing],closures:[]}
    expect(verifyContinuation(old,'r','b','saved')).toBe(old)
  })
})
