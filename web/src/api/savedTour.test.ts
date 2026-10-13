import {describe,it,expect} from 'vitest'
import {matchesSavedTourContext,validSavedTourCalendar,validSavedTourEdition} from './savedTour'
import type {SavedTourCalendar,SavedTourEdition,SavedTourEvent} from './savedTour'
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
  it('validates explicit Run/selected Branch/revision/season and original ancestry owner',()=>{
    expect(validSavedTourCalendar(calendar,'r','b','rev',2)).toBe(true)
    expect(matchesSavedTourContext(edition,'r','b','rev',2)).toBe(true)
    expect(validSavedTourCalendar(calendar,'other','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar(calendar,'r','other','rev',2)).toBe(false)
    expect(validSavedTourCalendar(calendar,'r','b','stale',2)).toBe(false)
    expect(validSavedTourCalendar(calendar,'r','b','rev',0)).toBe(false)
    expect(validSavedTourCalendar({...calendar,revision_branch_id:''},'r','b','rev',2)).toBe(false)
  })
  it('rejects duplicates, invalid weeks and cross-season source rows',()=>{
    expect(validSavedTourCalendar({...calendar,editions:[event,event],edition_count:2},'r','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar({...calendar,editions:[{...event,season_week:62}]},'r','b','rev',2)).toBe(false)
    expect(validSavedTourCalendar({...calendar,editions:[{...event,season:'2000/2001'}]},'r','b','rev',2)).toBe(false)
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
