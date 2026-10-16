import {describe, expect, it} from 'vitest'
import {validateCalendarPoolPreview} from './calendarInitialPool'
import {clock, input, preview} from './calendarInitialPool.fixture'

const check = (v: unknown) => validateCalendarPoolPreview(v, 'run-a','branch-a','head-a','a'.repeat(64),clock,input)
describe('calendar player preview boundary', () => {
  it('accepts only matching server source and correct W52 age identities', () => {
    expect(check(preview())).toEqual(preview())
    for (const update of [{branch_id:'foreign'}, {calendar_saved_revision_id:'older'},
      {run_package_state_fingerprint:'c'.repeat(64)}, {run_calendar:{...clock,weeks_per_year:61}},
      {preview_only:false}, {adoption_supported:true}, {limitations:[]},
      {request:{...input,seed:803}}, {result:{players:[]}}]) {
      expect(() => check({...preview(),...update})).toThrow()
    }
  })
  it('rejects a foreign scale, impossible birthday, wrong age and duplicate identities', () => {
    for (const update of [{birth_year_week:53}, {current_age_years:19},
      {schema_version:'initial_pool_player.v1'}, {time_basis:{...clock,weeks_per_year:61}},
      {birth_year:2015,birth_year_week:35,age_at_generation:15,current_age_years:15}]) {
      const v=preview(); Object.assign(v.result.players[0],update)
      expect(() => check(v)).toThrow()
    }
    const v=preview(2); v.result.players[1]=v.result.players[0]
    expect(() => validateCalendarPoolPreview(v,'run-a','branch-a','head-a','a'.repeat(64),clock,{...input,target_pool_size:2})).toThrow()
  })
})
