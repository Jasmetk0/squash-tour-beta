import {describe,it,expect} from 'vitest'
import {clock,input,preview} from './calendarInitialPool.fixture'
import {population,reviewed,saveReceipt} from './calendarPopulation.fixture'
import {TURN_PRO_V87_POLICY,lifecyclePolicyFor,validateCalendarPopulation,validateCalendarPopulationReview,
  validateCalendarPopulationSave,type CalendarPopulationRequest} from './calendarPopulation'

const request:CalendarPopulationRequest={command_id:'c1',expected_saved_head:'head-a',expected_draft_version:2,
  expected_package_fingerprint:'a'.repeat(64),generation:input,audit_label:'Admin',audit_reason:'Reviewed population'}
describe('calendar population authority boundary',()=>{
  it('validates only the actual reviewed source, command and time basis',()=>{
    expect(validateCalendarPopulationReview(reviewed(request),request,preview(),'run-a','branch-a',clock)).toEqual(reviewed(request))
    const stale={...reviewed(request),request:{...request,command_id:'other'}}
    expect(()=>validateCalendarPopulationReview(stale,request,preview(),'run-a','branch-a',clock)).toThrow()
    const drift={...reviewed(request),pool_preview:{...preview(),preview_fingerprint:'f'.repeat(64)}}
    expect(()=>validateCalendarPopulationReview(drift,request,preview(),'run-a','branch-a',clock)).toThrow()
  })
  it('accepts the full normalized generation request across independent HTTP JSON responses',()=>{
    const full={...input,schema_version:'run_calendar_initial_pool_request.v2',country_code:null,
      geographic_region:null,travel_region:null,country_quotas:[],naming_policy:'country_serial.v1'}
    const raw={...preview(),request:full}
    const outgoing={...request,generation:raw.request}
    // Every real HTTP response creates new array/object identities.
    const reply=JSON.parse(JSON.stringify({...reviewed(outgoing),pool_preview:raw}))
    expect(validateCalendarPopulationReview(reply,outgoing,raw,'run-a','branch-a',clock)).toEqual(reply)
    reply.pool_preview.request.country_quotas=[{country_code:'CZE',count:1}]
    expect(()=>validateCalendarPopulationReview(reply,outgoing,raw,'run-a','branch-a',clock)).toThrow()
  })
  it('refuses a foreign installed population or a birthday outside the Run calendar',()=>{
    expect(validateCalendarPopulation(population,'run-a','branch-a',clock)).toEqual(population)
    expect(()=>validateCalendarPopulation(population,'run-a','other',clock)).toThrow()
    const bad={...population,state:{...population.state,players:[{...population.state.players[0],birth_year_week:53}]}}
    expect(()=>validateCalendarPopulation(bad,'run-a','branch-a',clock)).toThrow()
  })
  it('requires an exact Saved Revision content and clean matching draft receipt',()=>{
    expect(validateCalendarPopulationSave(saveReceipt,'run-a','branch-a',population.fingerprint)).toEqual(saveReceipt)
    expect(()=>validateCalendarPopulationSave(saveReceipt,'run-a','other',population.fingerprint)).toThrow()
    expect(()=>validateCalendarPopulationSave(saveReceipt,'run-a','branch-a','f'.repeat(64))).toThrow()
  })
})

describe('Master v87 Tour entry rule for new Runs',()=>{
  it('defaults Admin requests to Turn Pro and keeps the historical rule implicit',()=>{
    expect(lifecyclePolicyFor('turn_pro.v87')).toEqual(TURN_PRO_V87_POLICY)
    expect(TURN_PRO_V87_POLICY.tour_entry_rule).toBe('turn_pro.v87')
    expect(lifecyclePolicyFor('first_application')).toBeUndefined()
  })
  it('requires an opening professional count exactly for a v87 review',()=>{
    const base=reviewed(request)
    const v87={...request,lifecycle_policy:TURN_PRO_V87_POLICY}
    const ok=reviewed(v87)
    expect(validateCalendarPopulationReview(ok,v87,preview(),'run-a','branch-a',clock).opening_professional_count).toBe(1)
    expect(()=>validateCalendarPopulationReview({...ok,opening_professional_count:undefined},v87,preview(),'run-a','branch-a',clock)).toThrow()
    expect(()=>validateCalendarPopulationReview({...ok,opening_professional_count:2},v87,preview(),'run-a','branch-a',clock)).toThrow()
    expect(()=>validateCalendarPopulationReview({...base,opening_professional_count:0},request,preview(),'run-a','branch-a',clock)).toThrow()
  })
})
