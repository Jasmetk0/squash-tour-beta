/** Mocked HTTP-transport tests, not a production browser/SQLite round-trip. */
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  getRunEditionEntryTiming, previewRunEditionEntryTiming, confirmRunEditionEntryTiming,
  listTournamentRankingPublicationOptions
} from './runEditionEntryTimingClient'
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

  it('preserves HTTP rejection and does not automatically retry a Confirm', async () => {
    const body = JSON.stringify({detail:{code:'stale_review',message:'Review changed'}})
    const spy = vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(body,{status:409}))
    await expect(confirmRunEditionEntryTiming(...args,payload)).rejects.toMatchObject({status:409,message:body})
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

  it('rejects malformed Confirm receipt metadata without claiming a completed Draft', async () => {
    const spy = vi.spyOn(globalThis,'fetch')
      .mockResolvedValueOnce(ok({...receipt, draft_version:-1}))
      .mockResolvedValueOnce(ok({...receipt, already_applied:'false'}))
      .mockResolvedValueOnce(ok({...receipt, ranking_authority_fingerprint:'not-a-hash'}))
      .mockResolvedValueOnce(ok({...receipt, state:null}))
      .mockResolvedValueOnce(ok({...receipt, state:{...receipt.state,branch_id:'foreign'}}))
    for (let index = 0; index < 5; index += 1) {
      await expect(confirmRunEditionEntryTiming(...args,payload)).rejects.toThrow(/receipt does not match/)
    }
    expect(spy).toHaveBeenCalledTimes(5)
  })

  it('rejects corrupt nested preview windows, impossible weeks and invalid blockers before React rendering', async () => {
    const spy = vi.spyOn(globalThis,'fetch')
      .mockResolvedValueOnce(ok({...preview, resolved:undefined}))
      .mockResolvedValueOnce(ok({...preview, resolved:{
        ...preview.resolved,main_close:at(81)
      }}))
      .mockResolvedValueOnce(ok({...preview,blockers:[undefined]}))
    await expect(getRunEditionEntryTiming(...args)).rejects.toThrow(/invalid contract/)
    await expect(getRunEditionEntryTiming(...args)).rejects.toThrow(/invalid contract/)
    await expect(getRunEditionEntryTiming(...args)).rejects.toThrow(/invalid contract/)
    expect(spy).toHaveBeenCalledTimes(3)
  })

  it('rejects malformed status flags, foreign previous Run clocks and invalid window kinds', async () => {
    const foreignClock = {...calendar, start_year: 2040}
    const spy = vi.spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(ok({...preview, ranking_will_be_bound: 'yes'}))
      .mockResolvedValueOnce(ok({...preview, timing_and_ranking_ready: null}))
      .mockResolvedValueOnce(ok({...preview, current_window: 'future_tournament'}))
      .mockResolvedValueOnce(ok({...preview, before:{
        ...timing, main_open:{calendar:foreignClock, season_index:0, week:13}
      }}))
      .mockResolvedValueOnce(ok({...preview, saved_head_revision_id:'  '}))
    for (let index = 0; index < 5; index += 1) {
      await expect(getRunEditionEntryTiming(...args)).rejects.toThrow(/invalid contract/)
    }
    expect(spy).toHaveBeenCalledTimes(5)
  })

  it('rejects preview with a malformed Run clock rather than using an inferred fallback', async () => {
    const spy = vi.spyOn(globalThis,'fetch').mockResolvedValue(
      ok({...preview,timing:{...timing,main_open:{...timing.main_open,
        calendar:{...calendar,weeks_per_year:0}}}}))
    await expect(previewRunEditionEntryTiming(...args,timing)).rejects.toThrow(/preview does not match/)
    expect(spy).toHaveBeenCalledTimes(1)
  })

  it('accepts authentic published ranking options only for the exact Run, Branch and Edition', async () => {
    const options = {run_id:'run/a',branch_id:'branch/b',event_id:'edition/d',
      source:'published_official_rankings.v1',publication_count:1,publications:[{
        ranking_week:{season_index:0,week:14},
        snapshot_fingerprint:hash('f'),ranked_row_count:50,policy_id:'policy',best_n:15
      }]}
    const spy = vi.spyOn(globalThis,'fetch').mockResolvedValue(ok(options))
    await expect(listTournamentRankingPublicationOptions(args[0],args[1],args[3]))
      .resolves.toEqual(options)
    expect(spy).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/admin/runs/run%2Fa/branches/branch%2Fb/tournaments/edition%2Fd/ranking-snapshot-authority/available',
      {headers:{'Content-Type':'application/json'}}
    )
  })

  it('rejects corrupt and duplicated published ranking options before rendering a picker', async () => {
    const item = {ranking_week:{season_index:0,week:14},
      snapshot_fingerprint:hash('f'),ranked_row_count:50,policy_id:'policy',best_n:15}
    const original = {run_id:'run/a',branch_id:'branch/b',event_id:'edition/d',
      source:'published_official_rankings.v1',publication_count:1,publications:[item]}
    const spy = vi.spyOn(globalThis,'fetch')
      .mockResolvedValueOnce(ok({...original,publications:null}))
      .mockResolvedValueOnce(ok({...original,publications:[null]}))
      .mockResolvedValueOnce(ok({...original,publications:[{...item,ranking_week:null}]}))
      .mockResolvedValueOnce(ok({...original,publications:[{...item,snapshot_fingerprint:'bad'}]}))
      .mockResolvedValueOnce(ok({...original,publications:[{...item,ranked_row_count:-1}]}))
      .mockResolvedValueOnce(ok({...original,publications:[{...item,best_n:0}]}))
      .mockResolvedValueOnce(ok({...original,publications:[{...item,policy_id:''}]}))
      .mockResolvedValueOnce(ok({...original,publication_count:2,publications:[item,item]}))
      .mockResolvedValueOnce(ok({...original,branch_id:'foreign'}))
    for (let index = 0; index < 9; index += 1) {
      await expect(listTournamentRankingPublicationOptions(args[0],args[1],args[3]))
        .rejects.toThrow(/do not match the requested tournament scope/)
    }
    expect(spy).toHaveBeenCalledTimes(9)
  })

  it('does not accept a forged confirm receipt kind, missing nested preview, or retargeted Main week', async () => {
    const spy=vi.spyOn(globalThis,'fetch')
      .mockResolvedValueOnce(ok({...receipt,request:{...receipt.request,kind:'other'}}))
      .mockResolvedValueOnce(ok({...receipt,preview:{...preview,resolved:undefined}}))
      .mockResolvedValueOnce(ok({...receipt,preview:{...preview,resolved:{
        ...preview.resolved,main_open:at(12)
      }}}))
    await expect(confirmRunEditionEntryTiming(...args,payload)).rejects.toThrow(/receipt does not match/)
    await expect(confirmRunEditionEntryTiming(...args,payload)).rejects.toThrow(/receipt does not match/)
    await expect(confirmRunEditionEntryTiming(...args,payload)).rejects.toThrow(/receipt does not match/)
    expect(spy).toHaveBeenCalledTimes(3)
  })
})
