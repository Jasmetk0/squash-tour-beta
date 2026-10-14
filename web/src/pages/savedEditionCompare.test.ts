import {describe,expect,it} from 'vitest'
import {compareSavedSeasonEditions} from './savedEditionCompare'
import type {SavedTourCalendar,SavedTourEvent} from '../api/savedTour'
import type {SavedRevisionHistoryEntry} from '../api/types'

const revision=(id:string,owner:string):SavedRevisionHistoryEntry=>({
  revision_id:id,revision_branch_id:owner,sequence:id==='old'?1:2,
  kind:'manual_save',parent_revision_id:id==='old'?null:'old',
  payload_schema_version:'run_saved_revision_v1',
  content_hash_algorithm:'sha256',content_hash:'hash-'+id,
  created_at:'2026-10-14 09:01:00',is_shared_revision:id==='old',
  is_branch_head:id==='new',change_summary:{summary:'Actual Save'}
})
const a=revision('old','parent'),b=revision('new','fork')
const edition=(id:string,patch:Partial<SavedTourEvent>={}):SavedTourEvent=>({
  event_id:id,season:'2000/2001',season_week:13,event_name:'Open '+id,
  template_id:'template',category:'Bronze',tour_level:'World Tour',
  host_country:'CZE',host_city:'Brno',region:'Europe',
  main_draw_size:8,qualification_draw_size:0,seeds_count:2,qualifier_spots:0,
  wild_cards:0,byes:0,ranking_status:'unpublished',result_published:false,
  champion_player_id:null,finalist_player_id:null,...patch
})
const saved=(id:string,owner:string,events:SavedTourEvent[]):SavedTourCalendar=>({
  schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
  run_id:'run',branch_id:'fork',revision_branch_id:owner,saved_revision_id:id,
  season_index:0,season:'2000/2001',week_count:61,
  calendar_status:events.length?'ready':'empty',edition_count:events.length,editions:events
})
describe('Canonical Saved Edition A/B field comparison',()=>{
  it('finds changed, added, removed and unchanged Editions without using opaque fingerprints',()=>{
    const first=saved('old','parent',[
      edition('kept'),edition('changed',{season_week:61,host_city:'Prague'}),
      edition('removed')])
    const second=saved('new','fork',[
      edition('kept'),edition('changed',{season_week:1,host_city:'Brno'}),
      edition('added')])
    const result=compareSavedSeasonEditions('run','fork',0,a,b,first,second)!
    expect(result.branchOwners).toEqual({a:'parent',b:'fork'})
    expect(result.counts).toEqual({added:1,removed:1,changed:1,unchanged:1})
    expect(result.rows.map(r=>[r.eventId,r.status])).toEqual([
      ['added','added'],['changed','changed'],['kept','unchanged'],['removed','removed']
    ])
    expect(result.rows[1].changedFields).toEqual(['season_week','host_city'])
    expect(result.rows[1].a?.season_week).toBe(61)
    expect(result.rows[1].b?.season_week).toBe(1)
    expect(result.rows[3].b).toBeNull()
    expect(result.rows[0].a).toBeNull()
  })
  it('keeps published winner and real entry parameters separate without guessing Match results',()=>{
    const before=saved('old','parent',[edition('cup')])
    const after=saved('new','fork',[edition('cup',{result_published:true,
      champion_player_id:'winner',finalist_player_id:'runner',main_draw_size:16})])
    const r=compareSavedSeasonEditions('run','fork',0,a,b,before,after)!
    expect(r.rows[0].changedFields).toEqual([
      'main_draw_size','result_published','champion_player_id','finalist_player_id'])
    expect(r.counts.changed).toBe(1)
  })
  it('shows honest empty calendars and rejects cross-branch owners and corrupt identities',()=>{
    const left=saved('old','parent',[]),right=saved('new','fork',[])
    const empty=compareSavedSeasonEditions('run','fork',0,a,b,left,right)!
    expect(empty.rows).toEqual([])
    expect(empty.counts.changed).toBe(0)
    expect(compareSavedSeasonEditions('run','fork',0,a,b,
      {...left,revision_branch_id:'fork'},right)).toBeNull()
    expect(compareSavedSeasonEditions('run','other',0,a,b,left,right)).toBeNull()
    expect(compareSavedSeasonEditions('run','fork',50,a,b,left,right)).toBeNull()
    expect(compareSavedSeasonEditions('run','fork',0,a,a,left,left)).toBeNull()
    const source=saved('old','parent',[edition('dup'),edition('dup')])
    expect(compareSavedSeasonEditions('run','fork',0,a,b,source,right)).toBeNull()
    expect(compareSavedSeasonEditions('run','fork',0,a,b,
      saved('old','parent',[edition('wrong',{season_week:62})]),right)).toBeNull()
    expect(compareSavedSeasonEditions('run','fork',0,a,b,
      {...left,calendar_status:'empty',editions:[edition('fake')],edition_count:1},right))
      .toBeNull()
  })
})
