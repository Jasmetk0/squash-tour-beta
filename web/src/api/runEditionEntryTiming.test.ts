/** Mocked HTTP-transport tests, not a production browser/SQLite round-trip. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getRunEditionEntryTiming, previewRunEditionEntryTiming, confirmRunEditionEntryTiming
} from './client'
import type {
  EditionEntryTiming, EntryTimingPreview, EntryTimingReceipt
} from './runEditionEntryTiming'

const hash = (v: string) => v.repeat(64)
const calendar = {
  schema_version: 'run_calendar.v1' as const,
  weeks_per_year: 80, season_start_year_week: 37, start_year: 2030, season_count: 5
}
const at = (week: number) => ({ calendar, season_index: 0, week })
const timing: EditionEntryTiming = {
  schema_version: 'edition_entry_timing.v1', main_open: at(13),
  main_duration_weeks: 2, qualification_duration_weeks: 1,
  final_commitment: null, ranking_publication_override: null
}
const missing = {
  run_id: 'run/a', branch_id:'branch/b', package_id:'calendar/c', event_id:'edition/d',
  timing: null, preflight_status:'missing_content',
  blockers: [{code:'entry_timing_missing', detail:'Main opening required'}],
  automatic_eligibility_status:'not_implemented'
}
const preview: EntryTimingPreview = {
  schema_version: 'run_edition_entry_timing_preview.v1',
  run_id: 'run/a', branch_id: 'branch/b', package_id:'calendar/c', event_id:'edition/d',
  saved_head_revision_id:'revision',draft_version:1,
  state_fingerprint:hash('a'), edition_fingerprint:hash('b'),
  timing, before:null,
  resolved: {
    main_open:at(13),main_close:at(14),qualification_open:at(15),
    qualification_close:at(15),final_commitment:at(15),
    default_ranking_completed_week:at(13),ranking_publication_week:at(14),
    ranking_source:'after_main_closing_minus_one'
  },
  current_week:null,current_window:null,
  ranking_snapshot_fingerprint:null,ranking_authority_fingerprint:null,
  ranking_will_be_bound:false,ranking_binding_status:'missing_prerequisite',
  configuration_state:'working_draft',timing_and_ranking_ready:false,
  preflight_status:'missing_content',automatic_eligibility_status:'not_implemented',
  can_confirm_configuration:true,
  blockers:[{code:'ranking_publication_missing',detail:'Exact publication missing'}],
  preview_fingerprint:hash('c')
}
const payload = {
  timing, command_id:'timing-test-command', expected_preview_fingerprint:hash('c'),
  operator_label:'Operator',audit_reason:'Explicit review'
}
const receipt: EntryTimingReceipt = {
  command_id:payload.command_id,request_fingerprint:hash('d'),
  request:{
    kind:'run_edition_entry_timing.v1',
    run_id:'run/a',branch_id:'branch/b',package_id:'calendar/c',event_id:'edition/d',
    ...payload
  },
  preview,draft_version:2,state_fingerprint:hash('e'),
  state:{run_id:'run/a',branch_id:'branch/b'},
  ranking_authority_fingerprint:null,already_applied:false,receipt_fingerprint:hash('f')
}
const root = 'http://127.0.0.1:8000/admin/runs/run%2Fa/branches/branch%2Fb/packages/calendar/calendar%2Fc/editions/edition%2Fd/entry-timing'
const args = ['run/a','branch/b','calendar/c','edition/d'] as const
const ok = (body: unknown) =>
  new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}})

describe('Run Edition Entry timing HTTP client — mocked transport', () => {
  afterEach(() => vi.restoreAllMocks())

  it('GET uses only exact encoded Run/Branch/Package/Edition and does not fabricate missing timing', async () => {
    const spy=vi.spyOn(globalThis,'fetch').mockResolvedValue(ok(missing))
    const result=await getRunEditionEntryTiming(...args)
    expect(result.timing).toBeNull()
    expect(spy).toHaveBeenCalledWith(root,{headers:{'Content-Type':'application/json'}})
  })

  it('preview sends only timing, including truly null optional override and no Save', async () => {
    const spy=vi.spyOn(globalThis,'fetch').mockResolvedValue(ok(preview))
    await expect(previewRunEditionEntryTiming(...args,timing)).resolves.toEqual(preview)
    expect(spy).toHaveBeenCalledWith(root+'/preview',{
      method:'POST',body:JSON.stringify({timing}),
      headers:{'Content-Type':'application/json'}
    })
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('confirm transmits the exact fingerprint, command ID and unchanged audit payload', async () => {
    const spy=vi.spyOn(globalThis,'fetch').mockResolvedValue(ok(receipt))
    await expect(confirmRunEditionEntryTiming(...args,payload)).resolves.toEqual(receipt)
    expect(spy).toHaveBeenCalledWith(root+'/confirm',{
      method:'POST',body:JSON.stringify(payload),
      headers:{'Content-Type':'application/json'}
    })
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('rejects foreign inspection, wrong preview configuration, and retargeted confirm receipt', async () => {
    const spy=vi.spyOn(globalThis,'fetch')
      .mockResolvedValueOnce(ok({...missing,branch_id:'foreign'}))
      .mockResolvedValueOnce(ok({...preview,timing:{...timing,main_duration_weeks:9}}))
      .mockResolvedValueOnce(ok({...receipt,command_id:'other-command'}))
    await expect(getRunEditionEntryTiming(...args)).rejects.toThrow(/foreign scope/)
    await expect(previewRunEditionEntryTiming(...args,timing)).rejects.toThrow(/preview does not match/)
    await expect(confirmRunEditionEntryTiming(...args,payload)).rejects.toThrow(/receipt does not match/)
    expect(spy).toHaveBeenCalledTimes(3)
  })
})
