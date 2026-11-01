import { fireEvent,render,screen,waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach,describe,expect,it,vi } from 'vitest'
import { LanguageProvider } from '../i18n/LanguageContext'
import { RunEditionCoveragePanel } from './RunEditionCoveragePanel'

const mocks=vi.hoisted(()=>({
  getRunPackageState:vi.fn(),getRunOwnedCalendar:vi.fn(),
  listRunBranches:vi.fn(),getRunEditionEntryTiming:vi.fn()
}))
vi.mock('../api/client',()=>({
  getRunPackageState:mocks.getRunPackageState,
  getRunOwnedCalendar:mocks.getRunOwnedCalendar,
  listRunBranches:mocks.listRunBranches
}))
vi.mock('../api/runEditionEntryTimingClient',()=>({
  getRunEditionEntryTiming:mocks.getRunEditionEntryTiming
}))

const run='run-one',branch='timeline-one',head='saved-one',pkg='cal-one'
const hash='a'.repeat(64),cHash='b'.repeat(64),otherHash='c'.repeat(64)
const packageState=()=>({fingerprint:hash,state:{
  run_id:run,branch_id:branch,
  package_versions:[{package_id:pkg,package_type:'Calendar'}]
}})
const calendar=()=>({
  run_id:run,branch_id:branch,package_id:pkg,season:'2000/2001',
  run_package_state_fingerprint:hash,fingerprint:cHash,content_fingerprint:otherHash,
  calendar:{season:'2000/2001',validation_errors:[],events:[
    {event_id:'edition-a',event_name:'Aster Open',season:'2000/2001',season_week:14,
      template_id:'t',category:'World',tour_level:'World Tour',
      host_country:'CZE',main_draw_size:32,qualification_draw_size:16}
  ]}
})
const branches=()=>({run_branches:[{run_id:run,branch_id:branch,saved_head_revision_id:head,
  display_name:'Timeline 1',status:'active',read_only:false}]})
const entry=(id:string)=>({
  run_id:run,branch_id:branch,package_id:pkg,event_id:id,timing:null,
  preflight_status:'missing_content',
  automatic_eligibility_status:'not_implemented',
  blockers:[{code:'entry_timing_missing',detail:'Choose Main window'}]
})
function mount(locale:'cs'|'en'='cs'){
  localStorage.setItem('squash-engine-language-v1',locale)
  return render(<MemoryRouter><LanguageProvider><RunEditionCoveragePanel
    runId={run} branchId={branch} head={head} weeksPerYear={61}
  /></LanguageProvider></MemoryRouter>)
}
async function inspect(){
  fireEvent.click(screen.getByRole('button',{name:'Načíst Calendar Packages'}))
  expect(await screen.findByLabelText('Kalendářový balíček')).toBeVisible()
  fireEvent.change(screen.getByLabelText('Kalendářový balíček'),{target:{value:pkg}})
  fireEvent.click(screen.getByRole('button',{name:'Prověřit Editions'}))
}
describe('bulk Run-owned Entry timing UI',()=>{
  beforeEach(()=>{
    vi.clearAllMocks();localStorage.clear()
    mocks.getRunPackageState.mockResolvedValue(packageState())
    mocks.listRunBranches.mockResolvedValue(branches())
    mocks.getRunOwnedCalendar.mockResolvedValue(calendar())
    mocks.getRunEditionEntryTiming.mockImplementation(async (_r:string,_b:string,_p:string,id:string)=>entry(id))
  })
  it('is fully idle until explicit package loading and explicit audit',async()=>{
    mount()
    expect(screen.getByText('Hromadná kontrola Entry přípravy')).toBeInTheDocument()
    expect(mocks.getRunOwnedCalendar).not.toHaveBeenCalled()
    expect(mocks.getRunEditionEntryTiming).not.toHaveBeenCalled()
    await inspect()
    expect(await screen.findByText('Aster Open')).toBeVisible()
    expect(screen.getByText(/Část GET selhala/)).not.toBeInTheDocument()
    expect(screen.getByText(/Všechny GET dokončeny/)).toBeInTheDocument()
    expect(mocks.getRunEditionEntryTiming).toHaveBeenCalledWith(run,branch,pkg,'edition-a')
    expect(screen.getByRole('link',{name:'Otevřít Entry detail'}))
      .toHaveAttribute('href','/admin/runs/run-one/calendar/edition-a?branch=timeline-one&calendar=cal-one')
  })
  it('supports English labels and does not falsely approve player eligibility',async()=>{
    mount('en')
    expect(screen.getByRole('button',{name:'Load Calendar Packages'})).toBeVisible()
    fireEvent.click(screen.getByRole('button',{name:'Load Calendar Packages'}))
    expect(await screen.findByLabelText('Calendar Package')).toBeVisible()
    fireEvent.change(screen.getByLabelText('Calendar Package'),{target:{value:pkg}})
    fireEvent.click(screen.getByRole('button',{name:'Inspect Editions'}))
    expect(await screen.findByText('Aster Open')).toBeVisible()
    expect(screen.getByText(/does not prove player eligibility/)).toBeVisible()
  })
  it('marks a failed individual GET as unavailable with a visible warning',async()=>{
    mocks.getRunEditionEntryTiming.mockRejectedValue(Error('HTTP 409'))
    mount()
    await inspect()
    expect(await screen.findByText('Aster Open')).toBeVisible()
    expect(screen.getByRole('alert')).toHaveTextContent('Některé informace nelze ověřit')
    expect(screen.getByText('HTTP 409')).toBeVisible()
    expect(screen.getByText(/Část GET selhala/)).toBeInTheDocument()
  })
  it('refuses stale Calendar State even if individual GETs returned',async()=>{
    mocks.getRunPackageState.mockResolvedValueOnce(packageState())
      .mockResolvedValueOnce(packageState())
      .mockResolvedValueOnce({...packageState(),fingerprint:'d'.repeat(64)})
    mount()
    await inspect()
    expect(await screen.findByRole('alert')).toHaveTextContent('Zdroj se změnil')
    expect(screen.queryByText('Aster Open')).not.toBeInTheDocument()
  })
  it('clears old rows on a repeated audit that fails before any source is trusted',async()=>{
    mount()
    await inspect()
    expect(await screen.findByText('Aster Open')).toBeVisible()
    mocks.listRunBranches.mockRejectedValue(Error('Source no longer available'))
    fireEvent.click(screen.getByRole('button',{name:'Prověřit znovu'}))
    await waitFor(()=>expect(screen.queryByText('Aster Open')).not.toBeInTheDocument())
    expect(await screen.findByRole('alert')).toHaveTextContent('Source no longer available')
  })
})
