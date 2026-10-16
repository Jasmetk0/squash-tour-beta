import {act, fireEvent, render, screen, waitFor} from '@testing-library/react'
import {QueryClient, QueryClientProvider} from '@tanstack/react-query'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import {RunCalendarPlayerPreviewPanel} from './RunCalendarPlayerPreviewPanel'
import {clock, preview} from '../api/calendarInitialPool.fixture'

const api=vi.hoisted(() => ({getRunPackageState:vi.fn(),previewRunCalendarPlayerPool:vi.fn()}))
vi.mock('../api/client', () => api)
vi.mock('../utils/apiErrors', () => ({formatApiError:(e:unknown) => String(e)}))
function mount(locale:'cs'|'en'='en') {
  return render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
    <RunCalendarPlayerPreviewPanel runId="run-a" branchId="branch-a" head="head-a" clock={clock} locale={locale}/>
  </QueryClientProvider>)
}
describe('calendar player preview UI', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRunPackageState.mockResolvedValue({fingerprint:'a'.repeat(64),state:{run_id:'run-a',branch_id:'branch-a',
      package_versions:[{package_id:'earth',package_type:'World'}]}})
    api.previewRunCalendarPlayerPool.mockImplementation(async (_r,_b,input) => preview(input.target_pool_size))
  })
  it('calls the actual v2 client, paginates identities and never offers adoption/Save',async () => {
    mount()
    const button=await screen.findByRole('button',{name:'Generate preview'})
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.click(button)
    expect(await screen.findByText('Country 1')).toBeInTheDocument()
    expect(api.previewRunCalendarPlayerPool).toHaveBeenCalledWith('run-a','branch-a',{
      world_package_id:'earth',seed:802,target_pool_size:128,min_age:15,max_age:45})
    expect(screen.queryByText('Country 51')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button',{name:'Next'}))
    expect(screen.getByText('Country 51')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:/save|adopt|confirm/i})).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Seed'),{target:{value:'803'}})
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
  it('discards a delayed response after a condition changes',async () => {
    let finish!:(v:unknown)=>void
    api.previewRunCalendarPlayerPool.mockReturnValue(new Promise(resolve => {finish=resolve}))
    mount()
    const button=await screen.findByRole('button',{name:'Generate preview'})
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.click(button)
    fireEvent.change(screen.getByLabelText('Seed'),{target:{value:'803'}})
    await act(async () => finish(preview(128)))
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
  it('shows Czech controls and refuses malformed numbers or a mismatched server result',async () => {
    mount('cs')
    const button=await screen.findByRole('button',{name:'Generovat náhled'})
    await waitFor(() => expect(button).toBeEnabled())
    fireEvent.change(screen.getByLabelText('Počet hráčů'),{target:{value:'1.5'}})
    expect(button).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Počet hráčů'),{target:{value:'128'}})
    api.previewRunCalendarPlayerPool.mockResolvedValue({...preview(128),branch_id:'foreign'})
    fireEvent.click(button)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })
})
