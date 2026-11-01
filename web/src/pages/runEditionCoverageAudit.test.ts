import { describe,expect,it,vi } from 'vitest'
import type { RunBranch, RunPackageStateResponse } from '../api/types'
import type { RunCalendarProjection, RunCalendarEvent } from '../api/runFirstTournament'
import type { EntryTimingInspection, EntryTimingPreview } from '../api/runEditionEntryTiming'
import { inspectRunEditionCoverage,ENTRY_COVERAGE_MAX_EDITIONS,ENTRY_COVERAGE_CONCURRENCY } from './runEditionCoverageAudit'

const run='run-fax',branch='branch-1',head='revision-1',pkg='calendar-1'
const hash='a'.repeat(64),calHash='b'.repeat(64),contentHash='c'.repeat(64)
const clock={schema_version:'run_calendar.v1' as const,weeks_per_year:61,season_start_year_week:37,start_year:2000,season_count:50}
const week=(w:number)=>({calendar:clock,season_index:0,week:w})
function branches(savedHead=head):{run_branches:RunBranch[]}{
  return {run_branches:[{run_id:run,branch_id:branch,saved_head_revision_id:savedHead,
    display_name:'Timeline 1',status:'active',read_only:false,branch_seed:null,
    forked_from_branch_id:null,forked_from_checkpoint_id:null,head_checkpoint_id:null,
    legacy_simulation_run_id:null,metadata_json:{},is_official:false}]}
}
function state(fingerprint=hash):RunPackageStateResponse{
  return {state:{run_id:run,branch_id:branch},fingerprint}
}
function events(count=3):RunCalendarEvent[]{
  return Array.from({length:count},(_,i)=>({
    event_id:'edition-'+(i+1),event_name:'FAX '+(i+1),
    season:'2000/2001',season_week:i%61+1,template_id:'t',category:'tour',
    tour_level:'World Tour',host_country:'CZE',main_draw_size:32,qualification_draw_size:16
  }))
}
function calendar(rows=events(),fingerprint=calHash):RunCalendarProjection{
  return {run_id:run,branch_id:branch,package_id:pkg,season:'2000/2001',
    run_package_state_fingerprint:hash,fingerprint,content_fingerprint:contentHash,
    calendar:{season:'2000/2001',events:rows,validation_errors:[]}}
}
function missing(id:string):EntryTimingInspection{
  return {run_id:run,branch_id:branch,package_id:pkg,event_id:id,timing:null,
    preflight_status:'missing_content',blockers:[{code:'entry_timing_missing',detail:'Configure Main window'}],
    automatic_eligibility_status:'not_implemented'}
}
function configured(id:string,binding:'missing_prerequisite'|'ready_for_explicit_confirmation'|'bound'='missing_prerequisite'):EntryTimingInspection{
  return {
    schema_version:'run_edition_entry_timing_preview.v1',run_id:run,branch_id:branch,
    package_id:pkg,event_id:id,saved_head_revision_id:head,
    state_fingerprint:hash,edition_fingerprint:'d'.repeat(64),preview_fingerprint:'e'.repeat(64),
    timing:{schema_version:'edition_entry_timing.v1',main_open:week(10),
      main_duration_weeks:2,qualification_duration_weeks:1,
      final_commitment:null,ranking_publication_override:null},
    before:null,
    resolved:{main_open:week(10),main_close:week(11),qualification_open:week(12),
      qualification_close:week(12),final_commitment:week(12),default_ranking_completed_week:week(10),
      ranking_publication_week:week(11),ranking_source:'after_main_closing_minus_one'},
    current_week:null,current_window:null,ranking_snapshot_fingerprint:null,
    ranking_authority_fingerprint:null,ranking_will_be_bound:false,
    ranking_binding_status:binding,configuration_state:'working_draft',
    timing_and_ranking_ready:false,preflight_status:'missing_content',
    automatic_eligibility_status:'not_implemented',can_confirm_configuration:true,blockers:[]
  } satisfies EntryTimingPreview
}
function reader(count=3){
  return {
    branches:vi.fn(async()=>branches()),
    packageState:vi.fn(async()=>state()),
    calendar:vi.fn(async()=>calendar(events(count))),
    timing:vi.fn(async (_run:string,_branch:string,_pkg:string,id:string)=>missing(id))
  }
}
const inspect=(r:ReturnType<typeof reader>)=>inspectRunEditionCoverage(
  r,run,branch,head,pkg,61)

describe('current Working Draft Edition Entry coverage audit',()=>{
  it('scans all Editions and revalidates exact HEAD, package and calendar',async()=>{
    const r=reader(80)
    const report=await inspect(r)
    expect(report.row_count).toBe(80)
    expect(report.rows).toHaveLength(80)
    expect(report.rows[0].event_id).toBe('edition-1')
    expect(report.counts.no_plan).toBe(80)
    expect(report.complete_reads).toBe(true)
    expect(report.all_plans_configured).toBe(false)
    expect(report.automatic_eligibility).toBe('not_implemented')
    expect(report.authorizes_execution).toBe(false)
    expect(report.automatic_save).toBe(false)
    expect(report.evidence_scope).toBe('current_working_draft')
    expect(r.branches).toHaveBeenCalledTimes(2)
    expect(r.packageState).toHaveBeenCalledTimes(2)
    expect(r.calendar).toHaveBeenCalledTimes(2)
    expect(r.timing).toHaveBeenCalledTimes(80)
  })
  it('separates plan configured from bound ranking and sporting eligibility',async()=>{
    const r=reader(3)
    r.timing.mockImplementation(async (_a,_b,_c,id)=>id==='edition-1'
      ?configured(id):id==='edition-2'?configured(id,'ready_for_explicit_confirmation')
        :configured(id,'bound'))
    const result=await inspect(r)
    expect(result.counts.no_plan).toBe(0)
    expect(result.counts.missing_ranking).toBe(1)
    expect(result.counts.configuration_ready).toBe(1)
    expect(result.counts.bound).toBe(1)
    expect(result.all_plans_configured).toBe(true)
    expect(result.authorizes_execution).toBe(false)
  })
  it('keeps a failed GET as unavailable, never silently treating a partial audit as ready',async()=>{
    const r=reader()
    r.timing.mockImplementation(async (_a,_b,_c,id)=>{
      if(id==='edition-2')throw Error('HTTP 409 source changed')
      return configured(id,'bound')
    })
    const result=await inspect(r)
    expect(result.counts.bound).toBe(2)
    expect(result.counts.unavailable).toBe(1)
    expect(result.complete_reads).toBe(false)
    expect(result.all_plans_configured).toBe(false)
    expect(result.rows[1].error).toContain('409')
  })
  it('limits concurrent requests, including 80 reference Editions',async()=>{
    const r=reader(80)
    let active=0,peak=0
    r.timing.mockImplementation(async (_a,_b,_c,id)=>{
      active++;peak=Math.max(peak,active)
      await Promise.resolve()
      await Promise.resolve()
      active--
      return missing(id)
    })
    await inspect(r)
    expect(peak).toBeLessThanOrEqual(ENTRY_COVERAGE_CONCURRENCY)
    expect(peak).toBeGreaterThan(1)
  })
  it('detects Saved HEAD change before and after the bounded scan',async()=>{
    const r=reader()
    r.branches.mockResolvedValueOnce(branches('other-head'))
    await expect(inspect(r)).rejects.toThrow('Saved HEAD changed')
    expect(r.timing).not.toHaveBeenCalled()
    const second=reader()
    second.branches.mockResolvedValueOnce(branches()).mockResolvedValueOnce(branches('new-head'))
    await expect(inspect(second)).rejects.toThrow('Saved HEAD changed')
    expect(second.timing).toHaveBeenCalledTimes(3)
  })
  it('detects live package and calendar changes after reading Editions',async()=>{
    const r=reader()
    r.packageState.mockResolvedValueOnce(state()).mockResolvedValueOnce(state('f'.repeat(64)))
    await expect(inspect(r)).rejects.toThrow('Working Draft changed')
    const c=reader()
    c.calendar.mockResolvedValueOnce(calendar()).mockResolvedValueOnce(calendar(events(),'f'.repeat(64)))
    await expect(inspect(c)).rejects.toThrow('Working Draft changed')
  })
  it('marks a foreign or stale individual Edition GET as unknown instead of trusting it',async()=>{
    const r=reader()
    r.timing.mockImplementation(async (_a,_b,_c,id)=>id==='edition-1'
      ?{...configured(id),saved_head_revision_id:'foreign-head'}:configured(id,'bound'))
    const result=await inspect(r)
    expect(result.counts.unavailable).toBe(1)
    expect(result.counts.bound).toBe(2)
  })
  it('rejects forged calendar events and too-large requests before scanning',async()=>{
    for(const rows of [
      [{...events()[0],season_week:62}],
      [events()[0],events()[0]],
      [{...events()[0],season:'2001/2002'}],
      events(ENTRY_COVERAGE_MAX_EDITIONS+1)
    ]){
      const r=reader()
      r.calendar.mockResolvedValue(calendar(rows))
      await expect(inspect(r)).rejects.toThrow()
      expect(r.timing).not.toHaveBeenCalled()
    }
  })
  it('rejects foreign source hashes, malformed or ambiguous branch inventory',async()=>{
    const a=reader()
    a.calendar.mockResolvedValue(calendar(events(),'not-sha256'))
    await expect(inspect(a)).rejects.toThrow()
    const b=reader()
    b.branches.mockResolvedValue({run_branches:[...branches().run_branches,...branches().run_branches]})
    await expect(inspect(b)).rejects.toThrow('ambiguous')
    const c=reader()
    c.packageState.mockResolvedValue({state:{run_id:'foreign',branch_id:branch},fingerprint:hash})
    await expect(inspect(c)).rejects.toThrow('foreign')
  })
})
