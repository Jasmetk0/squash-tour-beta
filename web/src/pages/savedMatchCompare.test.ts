import {describe,expect,it} from 'vitest'
import {comparePublishedSavedMatches} from './savedMatchCompare'
import type {SavedTourEdition,SavedTourEvent} from '../api/savedTour'
import type {SavedRevisionHistoryEntry} from '../api/types'

const event:SavedTourEvent={
  event_id:'event',season:'2000/2001',season_week:9,event_name:'Test Open',
  template_id:'template',category:'Bronze',tour_level:'World Tour',
  host_country:'CZE',host_city:'Brno',region:'Europe',main_draw_size:4,
  qualification_draw_size:0,seeds_count:2,qualifier_spots:0,wild_cards:0,byes:0,
  ranking_status:'published',result_published:true,
  champion_player_id:'p1',finalist_player_id:'p2'
}
const revision=(id:string,owner:string):SavedRevisionHistoryEntry=>({
  revision_id:id,revision_branch_id:owner,sequence:id==='old'?1:2,
  kind:'manual_save',parent_revision_id:id==='old'?null:'old',
  payload_schema_version:'run_saved_revision_v1',content_hash_algorithm:'sha256',
  content_hash:'hash-'+id,created_at:'2026-10-14 09:00:00',
  is_shared_revision:id==='old',is_branch_head:id==='new',
  change_summary:{summary:'actual saved revision'}
})
const a=revision('old','parent'),b=revision('new','fork')
const match=(match_id:string,winner='p1',scoreline='3-1')=>({
  match_id,draw_type:'main' as const,round_number:1,bracket_position:1,
  winner_player_id:winner,loser_player_id:winner==='p1'?'p2':'p1',scoreline
})
const state=(rev:SavedRevisionHistoryEntry,matches:ReturnType<typeof match>[],
  e:SavedTourEvent=event):SavedTourEdition=>({
  schema_version:'run_saved_tour_edition.v1',source:'reachable_saved_revision',
  run_id:'run',branch_id:'fork',revision_branch_id:rev.revision_branch_id,
  saved_revision_id:rev.revision_id,season_index:0,edition:e,
  published_result:e.result_published?{
    schema_version:'viewer_tournament_result.v1',product_run_id:'run',
    viewer_branch_id:rev.revision_branch_id,event_id:'event',
    completed_season_index:0,completed_week:9,
    champion_player_id:'p1',finalist_player_id:'p2',
    qualification_winner_ids:[],players:[],matches
  }:null,lifecycle_status:'unavailable'
})
const compare=(left:SavedTourEdition,right:SavedTourEdition)=>
  comparePublishedSavedMatches('run','fork',0,'event',a,b,
    left.edition,right.edition,left,right)
describe('Exact published Saved match comparison',()=>{
  it('shows added, removed, changed and unchanged authoritative match IDs and exact result fields',()=>{
    const left=state(a,[match('same'),match('changed'),match('removed')])
    const right=state(b,[match('same'),match('changed','p2','3-2'),match('added')])
    const r=compare(left,right)!
    expect(r.availability).toBe('published')
    expect(r.counts).toEqual({added:1,removed:1,changed:1,unchanged:1})
    expect(r.rows.map(x=>[x.matchId,x.status])).toEqual([
      ['added','added'],['changed','changed'],['removed','removed'],['same','unchanged']
    ])
    expect(r.rows[1].changedFields).toEqual([
      'winner_player_id','loser_player_id','scoreline'
    ])
    expect(r.rows[1].a?.winner_player_id).toBe('p1')
    expect(r.rows[1].b?.winner_player_id).toBe('p2')
  })
  it('does not infer absent/unpublished match evidence as an absent match',()=>{
    const unpublished={...event,result_published:false,
      champion_player_id:null,finalist_player_id:null}
    const result=compare(state(a,[],unpublished),state(b,[match('played')]))!
    expect(result.availability).toBe('unpublished')
    expect(result.rows).toEqual([])
    expect(result.counts.added).toBe(0)
  })
  it('fails closed on foreign original owner, tampered calendar or duplicate matches',()=>{
    const left=state(a,[match('first')]),right=state(b,[match('second')])
    expect(compare(left,{...right,revision_branch_id:'unreachable'})).toBeNull()
    expect(compare({...left,edition:{...event,season_week:8}},right)).toBeNull()
    expect(compare(left,{...right,published_result:{
      ...right.published_result!,matches:[match('duplicate'),match('duplicate')]
    }})).toBeNull()
    expect(compare(left,{...right,published_result:{
      ...right.published_result!,matches:[match('invalid','p1','')]
    }})).toBeNull()
    expect(comparePublishedSavedMatches('run','other',0,'event',a,b,
      event,event,left,right)).toBeNull()
  })
  it('accepts truthful published results with no canonical matches',()=>{
    const result=compare(state(a,[]),state(b,[]))!
    expect(result.availability).toBe('published')
    expect(result.rows).toEqual([])
  })
})
