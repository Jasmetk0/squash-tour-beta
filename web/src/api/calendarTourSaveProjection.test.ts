import {describe,expect,it} from 'vitest'
import {confirmedSavedTourView,type TourSaveReceipt,type TourView} from './calendarTour'

const current=():TourView=>({schema_version:'calendar_tour_inspection.v1',run_id:'r',branch_id:'b',saved_head_revision_id:'old',draft_version:4,
  save_projection_fingerprint:'e'.repeat(64),checkpoint_fingerprint:'a'.repeat(64),tour_fingerprint:'c'.repeat(64),saved:false,sporting_saved:false,
  can_initialize:false,players:[],transition_blockers:[],season_transition_blockers:['season_transition_requires_last_week'],saved_completed_seasons:[],edition_evidence:{},
  state:{week:{calendar:{schema_version:'run_calendar.v1',weeks_per_year:80,season_start_year_week:80,start_year:2030,season_count:3},season_index:0,week:5},editions:[],rankings:[],transitions:[]}})
const receipt=():TourSaveReceipt=>({schema_version:'calendar_tour_save_receipt.v1',run_id:'r',branch_id:'b',saved_revision:{revision_id:'new',run_id:'r',branch_id:'b',content_hash:'f'.repeat(64)},
  working_draft:{status:'clean',change_count:0,draft_version:5,base_saved_revision_id:'new'},
  saved_projection:{schema_version:'calendar_tour_saved_projection.v1',payload_fingerprint:'e'.repeat(64),run_id:'r',branch_id:'b',previous_saved_head_revision_id:'old',saved_head_revision_id:'new',draft_version:5,checkpoint_fingerprint:'a'.repeat(64),tour_fingerprint:'c'.repeat(64)}})

describe('confirmed Saved inspection continuity',()=>{
  it('retains values only after matching the complete payload and clean new revision',()=>{
    const view=current(),saved=receipt(),next=confirmedSavedTourView(view,saved)
    expect(next).toEqual({...view,saved_head_revision_id:'new',draft_version:5,saved:true,sporting_saved:true})
    expect(view.saved).toBe(false)
  })
  it('keeps the independent read for absent, changed or unsupported values',()=>{
    expect(confirmedSavedTourView({...current(),save_projection_fingerprint:null},receipt())).toBeNull()
    expect(confirmedSavedTourView(current(),{...receipt(),saved_projection:null})).toBeNull()
    const changed=receipt();changed.saved_projection!.payload_fingerprint='d'.repeat(64)
    expect(confirmedSavedTourView(current(),changed)).toBeNull()
    expect(confirmedSavedTourView({...current(),saved_completed_seasons:[0]},receipt())).toBeNull()
    const boundary=current();boundary.state!.transitions=[{public_event:{kind:'season_transition_completed'}}]
    expect(confirmedSavedTourView(boundary,receipt())).toBeNull()
  })
  it.each(['branch','parent','revision','dirty draft','checkpoint','version','receipt Run'])('rejects inconsistent %s metadata',field=>{
    const saved=receipt(),p=saved.saved_projection!
    if(field==='branch')p.branch_id='foreign'
    if(field==='parent')p.previous_saved_head_revision_id='foreign'
    if(field==='revision')p.saved_head_revision_id='foreign'
    if(field==='dirty draft')saved.working_draft!.status='dirty'
    if(field==='checkpoint')p.checkpoint_fingerprint='b'.repeat(64)
    if(field==='version')p.draft_version=6
    if(field==='receipt Run')saved.run_id='foreign'
    expect(()=>confirmedSavedTourView(current(),saved)).toThrow()
  })
})
