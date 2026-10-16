import {act,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {RunCalendarPopulationControls} from './RunCalendarPopulationControls'
import {clock,preview} from '../api/calendarInitialPool.fixture'
import {population,reviewed,saveProof,saveReceipt} from '../api/calendarPopulation.fixture'
const api=vi.hoisted(()=>({getRunCalendarPopulation:vi.fn(),getBranchWorkingDraft:vi.fn(),
  reviewRunCalendarPopulation:vi.fn(),confirmRunCalendarPopulation:vi.fn(),previewRunInitialWorldSave:vi.fn(),saveRunOwnedInitialWorld:vi.fn()}))
vi.mock('../api/client',()=>api)
vi.mock('../utils/apiErrors',()=>({formatApiError:(e:unknown)=>String(e)}))
vi.mock('./RunNavigationSafeguard',()=>({acknowledgeSavedRunForm:vi.fn()}))
const installed=vi.fn()
function mount(pool=preview(),locale:'cs'|'en'='en'){
  const client=new QueryClient({defaultOptions:{queries:{retry:false}}})
  const element=(p=pool)=><QueryClientProvider client={client}><MemoryRouter>
    <RunCalendarPopulationControls runId="run-a" branchId="branch-a" head="head-a" clock={clock}
      packageFingerprint={'a'.repeat(64)} pool={p} locale={locale} onInstalled={installed}/>
  </MemoryRouter></QueryClientProvider>
  const view=render(element())
  return {...view,changePool:(p:typeof pool)=>view.rerender(element(p))}
}
describe('reviewed population adoption and explicit Save',()=>{
  beforeEach(()=>{
    vi.clearAllMocks()
    api.getRunCalendarPopulation.mockResolvedValue(null)
    api.getBranchWorkingDraft.mockResolvedValue({run_id:'run-a',branch_id:'branch-a',base_saved_revision_id:'head-a',draft_version:2,status:'clean'})
    api.reviewRunCalendarPopulation.mockImplementation(async(_r,_b,request)=>reviewed(request))
    api.confirmRunCalendarPopulation.mockImplementation(async()=>{api.getRunCalendarPopulation.mockResolvedValue(population);return population})
    api.previewRunInitialWorldSave.mockResolvedValue(saveProof)
    api.saveRunOwnedInitialWorld.mockResolvedValue(saveReceipt)
  })
  async function review(){
    const button=await screen.findByRole('button',{name:'Review adding players'})
    await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button)
    return screen.findByRole('button',{name:'Add players to Run'})
  }
  it('requires separate confirmation, then manual Save, and never autosaves',async()=>{
    mount()
    const confirm=await review()
    expect(confirm).toBeDisabled()
    expect(api.confirmRunCalendarPopulation).not.toHaveBeenCalled()
    fireEvent.click(screen.getByLabelText('Confirm population adoption'));fireEvent.click(confirm)
    const save=await screen.findByRole('button',{name:'Save players'})
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(save).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm population Save'))
    await waitFor(()=>expect(save).toBeEnabled());fireEvent.click(save)
    await waitFor(()=>expect(api.saveRunOwnedInitialWorld).toHaveBeenCalledTimes(1))
    expect(api.saveRunOwnedInitialWorld).toHaveBeenCalledWith('run-a','branch-a',2,population.fingerprint)
    const payload=api.reviewRunCalendarPopulation.mock.calls[0][2]
    expect(api.confirmRunCalendarPopulation).toHaveBeenCalledWith('run-a','branch-a',payload,population.fingerprint)
  })
  it('revokes review and consent when a new preview arrives',async()=>{
    const view=mount();await review()
    fireEvent.click(screen.getByLabelText('Confirm population adoption'))
    view.changePool({...preview(),preview_fingerprint:'e'.repeat(64)})
    expect(screen.queryByRole('button',{name:'Add players to Run'})).not.toBeInTheDocument()
    expect(api.confirmRunCalendarPopulation).not.toHaveBeenCalled()
  })
  it('discards an old async review after its source preview changes',async()=>{
    let finish!:(value:unknown)=>void
    api.reviewRunCalendarPopulation.mockReturnValue(new Promise(resolve=>{finish=resolve}))
    const view=mount();const button=await screen.findByRole('button',{name:'Review adding players'})
    await waitFor(()=>expect(button).toBeEnabled());fireEvent.click(button)
    await waitFor(()=>expect(api.reviewRunCalendarPopulation).toHaveBeenCalledTimes(1))
    const payload=api.reviewRunCalendarPopulation.mock.calls[0][2]
    view.changePool({...preview(),preview_fingerprint:'e'.repeat(64)})
    await act(async()=>finish(reviewed(payload)))
    expect(screen.queryByRole('button',{name:'Add players to Run'})).not.toBeInTheDocument()
  })
  it('reopens the existing population in Czech without a replacement action',async()=>{
    api.getRunCalendarPopulation.mockResolvedValue(population)
    mount(preview(),'cs')
    expect(await screen.findByText('Hráči přidaní do Runu')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Zkontrolovat přidání hráčů'})).not.toBeInTheDocument()
    expect(api.confirmRunCalendarPopulation).not.toHaveBeenCalled()
  })
  it('does not accept a Save receipt or offer Save for a stale proof',async()=>{
    api.getRunCalendarPopulation.mockResolvedValue(population)
    api.previewRunInitialWorldSave.mockResolvedValue({...saveProof,saved_head_revision_id:'older'})
    mount()
    expect(await screen.findByText('Players added to this Run')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Save players'})).not.toBeInTheDocument()
  })
  it('freezes server-resolved policy and requires consent again for an exact failed-request retry',async()=>{
    const policy={policy_id:'calendar-default.v2',automatic_retirement_age:46,provenance:'Resolved server policy'}
    api.reviewRunCalendarPopulation.mockImplementation(async(_r,_b,payload)=>reviewed({...payload,lifecycle_policy:policy}))
    api.confirmRunCalendarPopulation.mockRejectedValueOnce(Error('Connection lost'))
    mount();let confirm=await review()
    fireEvent.click(screen.getByLabelText('Confirm population adoption'));fireEvent.click(confirm)
    expect(await screen.findByRole('alert')).toHaveTextContent('Connection lost')
    await waitFor(()=>expect(api.confirmRunCalendarPopulation).toHaveBeenCalledTimes(1))
    confirm=screen.getByRole('button',{name:'Add players to Run'})
    expect(confirm).toBeDisabled()
    fireEvent.click(screen.getByLabelText('Confirm population adoption'))
    await waitFor(()=>expect(confirm).toBeEnabled());fireEvent.click(confirm)
    await waitFor(()=>expect(api.confirmRunCalendarPopulation).toHaveBeenCalledTimes(2))
    expect(api.confirmRunCalendarPopulation.mock.calls[0]).toEqual(api.confirmRunCalendarPopulation.mock.calls[1])
    expect(api.confirmRunCalendarPopulation.mock.calls[1][2].lifecycle_policy).toEqual(policy)
    expect(api.reviewRunCalendarPopulation).toHaveBeenCalledTimes(1)
  })
})
