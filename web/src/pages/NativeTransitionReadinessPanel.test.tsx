import {act,fireEvent,render,screen} from '@testing-library/react'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import type {TourView} from '../api/calendarTour'
import {validateNativeTransitionReadiness,type NativeTransitionReadiness} from '../api/nativeTransitionReadiness'
import {NativeTransitionReadinessPanel} from './NativeTransitionReadinessPanel'

const api=vi.hoisted(()=>({inspectCalendarTourTransitionReadiness:vi.fn()}))
vi.mock('../api/client',()=>({...api,ApiError:class ApiError extends Error {status=409}}))
const clock={schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:1,start_year:2030,season_count:3}
const view=(run='r'):TourView=>({schema_version:'calendar_tour_inspection.v1',run_id:run,branch_id:'b',saved_head_revision_id:'head',draft_version:1,checkpoint_fingerprint:'a'.repeat(64),tour_fingerprint:'b'.repeat(64),saved:true,can_initialize:false,players:[],transition_blockers:[],season_transition_blockers:[],saved_completed_seasons:[],edition_evidence:{},run_calendar:clock,state:{week:{calendar:clock,season_index:0,week:2},editions:[],rankings:[],transitions:[]}})
const report=(v=view()):NativeTransitionReadiness=>({schema_version:'native_tour_transition_readiness.v1',run_id:v.run_id,branch_id:v.branch_id,saved_head_revision_id:v.saved_head_revision_id,checkpoint_fingerprint:v.checkpoint_fingerprint!,tour_fingerprint:v.tour_fingerprint!,run_calendar:clock,completed_week:v.state!.week,target_week:{calendar:clock,season_index:0,week:3},action:'transition',can_preview_transition:true,blockers:[],source_problems:[],due:[{player_id:'born',display_name:'New Athlete',country_code:'CZE'}],due_count:1,admitted_population_count:0,current_scope:'configured_tour',target_scope:'native_natural_transitions',post_birth_competition_supported:false,source_epoch_changes_supported:false,command_preview_required:true,explicit_confirmation_required:true,manual_save_required:true,simulation_started:false,readiness_fingerprint:'f'.repeat(64)})
const panel=(v=view(),disabled=false)=><LanguageProvider><NativeTransitionReadinessPanel view={v} disabled={disabled}/></LanguageProvider>

describe('native capability (HTTP mocked; no execution authority)',()=>{
  beforeEach(()=>{vi.clearAllMocks();localStorage.setItem('squash-engine-language-v1','en');api.inspectCalendarTourTransitionReadiness.mockResolvedValue(report())})
  it('fetches only on explicit request, explains limits and never offers Execute or Save',async()=>{
    render(panel())
    expect(api.inspectCalendarTourTransitionReadiness).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button',{name:'Check transition capability'}))
    const result=await screen.findByLabelText('Verified transition readiness result')
    expect(result).toHaveTextContent('New Athlete')
    expect(result).toHaveTextContent('S1/W3')
    expect(result).toHaveTextContent('only natural transitions')
    expect(screen.queryByRole('button',{name:/Execute|Save/})).not.toBeInTheDocument()
  })
  it('validates the versioned native competition capability and rejects invented scope (component)',()=>{
    const v={...view(),state:{...view().state!,schema_version:'calendar_tour_authority.v4'}}
    const modern:NativeTransitionReadiness={...report(v),schema_version:'native_tour_transition_readiness.v2',current_scope:'native_competition',target_scope:'native_competition',post_birth_competition_supported:true}
    expect(validateNativeTransitionReadiness(modern,v)).toBe(modern)
    expect(()=>validateNativeTransitionReadiness({...modern,post_birth_competition_supported:false},v)).toThrow()
    expect(()=>validateNativeTransitionReadiness({...modern,current_scope:'configured_tour'},v)).toThrow()
  })
  it.each(['saved_head_revision_id','checkpoint_fingerprint','tour_fingerprint','run_id','branch_id'] as const)('rejects changed %s',key=>{
    expect(()=>validateNativeTransitionReadiness({...report(),[key]:'foreign'},view())).toThrow()
  })
  it('rejects altered target clocks and a false capability claim',()=>{
    const changed=report();changed.target_week={...changed.target_week!,calendar:{...clock,season_count:4}}
    expect(()=>validateNativeTransitionReadiness(changed,view())).toThrow()
    expect(()=>validateNativeTransitionReadiness({...report(),simulation_started:true},view())).toThrow()
    expect(()=>validateNativeTransitionReadiness({...report(),blockers:['manual_save_required']},view())).toThrow()
  })
  it('drops a delayed response across Run A→B→A and aborts its transport',async()=>{
    let resolve!:(v:NativeTransitionReadiness)=>void
    api.inspectCalendarTourTransitionReadiness.mockReturnValueOnce(new Promise(r=>{resolve=r}))
    const page=render(panel())
    fireEvent.click(screen.getByRole('button',{name:'Check transition capability'}))
    const signal=api.inspectCalendarTourTransitionReadiness.mock.calls[0][2] as AbortSignal
    page.rerender(panel(view('other')));page.rerender(panel())
    expect(signal.aborted).toBe(true)
    await act(async()=>resolve(report()))
    expect(screen.queryByLabelText('Verified transition readiness result')).not.toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Check transition capability'})).toBeEnabled()
  })
  it('does not revive an old completed result after a mutating parent action',async()=>{
    const page=render(panel())
    fireEvent.click(screen.getByRole('button',{name:'Check transition capability'}))
    await screen.findByLabelText('Verified transition readiness result')
    page.rerender(panel(view(),true));page.rerender(panel())
    expect(screen.queryByLabelText('Verified transition readiness result')).not.toBeInTheDocument()
  })
  it('renders the manual Save blocker and Czech labels',async()=>{
    localStorage.setItem('squash-engine-language-v1','cs')
    api.inspectCalendarTourTransitionReadiness.mockResolvedValue({...report(),can_preview_transition:false,blockers:['manual_save_required']})
    render(panel())
    fireEvent.click(screen.getByRole('button',{name:'Ověřit možnosti přechodu'}))
    const result=await screen.findByLabelText('Verified transition readiness result')
    expect(result).toHaveTextContent('Nejprve proveďte ruční Save.')
  })
})
