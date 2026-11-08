import {describe,expect,it} from 'vitest'
import type {TourView,TourEdition,TourWeek} from '../api/calendarTour'
import {deriveNativeTourOperatorQueue} from './nativeTourOperatorQueue'

const calendar={schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:35,start_year:2030,season_count:3}
const week=(w:number,season=0):TourWeek=>({calendar,week:w,season_index:season})
const makeEdition=(id:string,w:number,extras:Partial<TourEdition>={}):TourEdition=>({
  edition:{edition_id:id,name:'Tour '+id,week:week(w),announcement_week:week(1),
    start_slot:1,main_entrant_count:4,point_table:{champion:100,finalist:60,semifinal:30},validity_weeks:52},
  submissions:[],field:null,draw:null,tournament_fingerprint:null,result_confirmed:false,...extras
})
const makeView=(editions:TourEdition[]=[makeEdition('first',30)],saved=true):TourView=>({
  schema_version:'calendar_tour_inspection.v1',run_id:'run-A',branch_id:'branch-B',
  saved_head_revision_id:'abcdef0123456789',draft_version:3,
  checkpoint_fingerprint:'a'.repeat(64),tour_fingerprint:'b'.repeat(64),
  saved,can_initialize:false,players:[],transition_blockers:[],
  season_transition_blockers:[],saved_completed_seasons:[],edition_evidence:{},
  state:{week:week(30),editions,rankings:[],transitions:[]}
})

describe('source-verified native Tour operator queue',()=>{
  it('classifies real Edition phases without claiming operator authorization',()=>{
    const withApplications=makeEdition('apps',30,{submissions:[{application_id:'x',player_id:'p1'}]})
    const field={direct_main_player_ids:['p1','p2','p3','p4'],below_qualification_cut_player_ids:[]}
    const withField=makeEdition('field',30,{field})
    const draw={main:{slots:[{slot_index:1,player_id:'p1'}]}}
    const drawn=makeEdition('drawn',30,{field,draw})
    const played=makeEdition('played',30,{field,draw,tournament_fingerprint:'f'.repeat(64)})
    const completed=makeEdition('finished',30,{field,draw,tournament_fingerprint:'f'.repeat(64),result_confirmed:true})
    const v=makeView([makeEdition('no-apps',30),withApplications,withField,drawn,played,completed],false)
    v.edition_evidence.played={matches:[{match_id:'m1'} as never],results:[]}
    const queue=deriveNativeTourOperatorQueue(v,'run-A','branch-B')
    expect(Object.fromEntries(queue.items.map(i=>[i.editionId,i.stage]))).toEqual({
      apps:'field',drawn:'play',field:'draw',finished:'reviewed',
      'no-apps':'applications',played:'results',
    })
    expect(queue.items.find(i=>i.editionId==='played')?.matches).toBe(1)
    expect(queue.items.find(i=>i.editionId==='drawn')?.results).toBe(0)
    expect(queue.source).toEqual({
      runId:'run-A',branchId:'branch-B',
      savedHead:'abcdef0123456789',workingDraft:true
    })
  })
  it('surfaces exact group tie evidence ahead of regular match review',()=>{
    const v=makeView([makeEdition('group',30,{
      field:{direct_main_player_ids:['p1','p2','p3','p4'],below_qualification_cut_player_ids:[]},
      draw:{topology:{group_slots:[{group_index:1,slot_index:1,player_id:'p1'}]}}
    })])
    v.groups={group:{tie_case:{
      group_index:1,player_ids:['p1','p2'],reason:'equal',
      source_match_results:[['m1','p1']]},standings:null,bracket:null}}
    expect(deriveNativeTourOperatorQueue(v,'run-A','branch-B').items[0].stage).toBe('group_tie')
  })
  it('handles 80 Editions without truncation and sorts by current, past, future',()=>{
    const editions=Array.from({length:80},(_,i)=>makeEdition('edition-'+String(i+1).padStart(2,'0'),(i%50)+1))
    const queue=deriveNativeTourOperatorQueue(makeView(editions),'run-A','branch-B')
    expect(queue.items).toHaveLength(80)
    expect(queue.items[0].period).toBe('current')
    expect(queue.items.filter(i=>i.period==='current')).toHaveLength(2)
    expect(queue.items.filter(i=>i.period==='past').length).toBeGreaterThan(0)
    expect(queue.items.filter(i=>i.period==='future').length).toBeGreaterThan(0)
    expect(new Set(queue.items.map(i=>i.sourceIndex)).size).toBe(80)
    expect(queue.items.find(i=>i.editionId==='edition-80')?.sourceIndex).toBe(79)
  })
  it('uses two-dimensional season/week boundaries instead of flattening IDs',()=>{
    const v=makeView([
      {...makeEdition('past',52),edition:{...makeEdition('past',52).edition,week:week(52,0)}},
      {...makeEdition('current',1),edition:{...makeEdition('current',1).edition,week:week(1,1)}},
      {...makeEdition('future',2),edition:{...makeEdition('future',2).edition,week:week(2,1)}},
    ])
    v.state!.week=week(1,1)
    expect(Object.fromEntries(
      deriveNativeTourOperatorQueue(v,'run-A','branch-B').items.map(i=>[i.editionId,i.period])
    )).toEqual({current:'current',past:'past',future:'future'})
  })
  it('rejects foreign source, missing authority, invalid/duplicate identity and schedule',()=>{
    const v=makeView()
    expect(()=>deriveNativeTourOperatorQueue(v,'another','branch-B')).toThrow(/source/)
    expect(()=>deriveNativeTourOperatorQueue(v,'run-A','another')).toThrow(/source/)
    expect(()=>deriveNativeTourOperatorQueue({...v,state:null},'run-A','branch-B')).toThrow(/source/)
    expect(()=>deriveNativeTourOperatorQueue(makeView([makeEdition('dup',30),makeEdition('dup',30)]),'run-A','branch-B')).toThrow(/invalid or duplicate/)
    expect(()=>deriveNativeTourOperatorQueue(makeView([makeEdition('bad',0)]),'run-A','branch-B')).toThrow(/invalid or duplicate/)
    expect(()=>deriveNativeTourOperatorQueue(makeView([makeEdition('bad',53)]),'run-A','branch-B')).toThrow(/invalid or duplicate/)
  })
  it('treats missing saved match evidence as unknown count 0, never as a match',()=>{
    const v=makeView([makeEdition('drawn',30,{
      draw:{main:{slots:[]}},
      field:{direct_main_player_ids:[],below_qualification_cut_player_ids:[]}
    })])
    const item=deriveNativeTourOperatorQueue(v,'run-A','branch-B').items[0]
    expect(item.stage).toBe('play')
    expect(item.matches).toBe(0)
    expect(item.results).toBe(0)
  })
})
