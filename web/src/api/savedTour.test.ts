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
})
