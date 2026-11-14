import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { createMemoryRouter, Link, MemoryRouter, RouterProvider, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { acknowledgeSavedRunForm, RunNavigationSafeguard } from './RunNavigationSafeguard'
import { useReaderParams } from './readerUrlState'

const context = vi.hoisted(() => ({
  branch: { run_id: 'run-a', branch_id: 'branch-a', saved_head_revision_id: 'head-a' }
}))
const api = vi.hoisted(() => ({getBranchWorkingDraft:vi.fn()}))
vi.mock('../api/client',()=>api)
vi.mock('../admin/AdminBranchContext',()=>({
  useAdminBranch:()=>({selectedBranch:context.branch})
}))

const clean = {
  run_id:'run-a', branch_id:'branch-a', base_saved_revision_id:'head-a',
  draft_version:0, status:'clean'
}
function setup() {
  const cache = new QueryClient({defaultOptions:{queries:{retry:false,gcTime:0}}})
  const content = () => <QueryClientProvider client={cache}>
    <MemoryRouter initialEntries={['/admin/runs/run-a']}>
      <div className="app-shell--admin">
        <RunNavigationSafeguard runId="run-a" />
        <nav><Link to="/admin/runs">All Runs</Link><Link to="/admin/runs/run-a/manage">Manage Run</Link></nav>
        <main>
          <label>Filter <input data-run-navigation-readonly aria-label="Filter search" /></label>
          <label>Age <input data-run-navigation-readonly type="number" aria-label="Filter age" /></label>
          <label>Season <select data-run-navigation-readonly aria-label="Filter season">
            <option value="">All</option><option value="1">One</option>
          </select></label>
          <label>Audit reason <input aria-label="Audit reason" defaultValue="initial" /></label>
          <label>Approve <input aria-label="Approve" type="checkbox" /></label>
        </main>
      </div>
    </MemoryRouter>
  </QueryClientProvider>
  const view=render(content())
  return {cache,view,refresh:()=>view.rerender(content()),
    shell:()=>document.querySelector('.app-shell--admin')!}
}
async function loaded() {
  await waitFor(()=>expect(api.getBranchWorkingDraft).toHaveBeenCalled())
}
function edit(value:string) {
  const field=screen.getByRole('textbox',{name:'Audit reason'})
  fireEvent.focusIn(field)
  fireEvent.change(field,{target:{value}})
}

function GuardedReader(): JSX.Element {
  const reader = useReaderParams('career', 'run-a:branch-a:head-a:P1')
  const location = useLocation()
  const navigate = useNavigate()
  return <div className="app-shell--admin">
    <RunNavigationSafeguard runId="run-a" />
    <main>
      <input aria-label="Audit reason" defaultValue="initial" />
      <section data-run-navigation-readonly>
        <input aria-label="Reader search" value={reader.get('search')}
          onChange={event => reader.set({ search: event.target.value }, true)} />
        <button onClick={() => reader.set({ page: '2' })}>Reader page</button>
        <button onClick={() => reader.reset()}>Reset reader</button>
      </section>
      <output aria-label="Location">{location.pathname + location.search + location.hash}</output>
      <button onClick={() => navigate(-1)}>Back</button>
      <button onClick={() => navigate(1)}>Forward</button>
      <button onClick={() => navigate('?branch=other&career_page=3#timeline')}>Other Branch</button>
      <button onClick={() => navigate('?branch=branch-a&tab=health&career_page=3#timeline')}>Other tab</button>
      <button onClick={() => navigate('?branch=branch-a&tab=career#other')}>Other anchor</button>
    </main>
  </div>
}

describe('Run dirty navigation evidence',()=>{
  beforeEach(()=>{
    vi.restoreAllMocks();vi.clearAllMocks()
    context.branch={run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a'}
    api.getBranchWorkingDraft.mockResolvedValue(clean)
    vi.spyOn(window,'confirm').mockReturnValue(true)
  })

  it.each(['local form', 'server Working Draft'])('preserves %s through real reader controls and history with an anchor', async source => {
    if (source === 'server Working Draft') api.getBranchWorkingDraft.mockResolvedValue({ ...clean, status: 'dirty' })
    const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
    const router = createMemoryRouter([{ path: '*', element: <GuardedReader /> }], {
      initialEntries: ['/admin/runs/run-a/player/P1?branch=branch-a&tab=career#timeline']
    })
    render(<QueryClientProvider client={cache}><RouterProvider router={router} /></QueryClientProvider>)
    await loaded()
    vi.mocked(window.confirm).mockReturnValue(false)
    const field = screen.getByRole('textbox', { name: 'Audit reason' })
    if (source === 'local form') edit('keep my unsaved reason')
    const shell = document.querySelector('.app-shell--admin')!
    await waitFor(() => expect(shell).toHaveAttribute('data-run-form-edited', 'true'))
    fireEvent.change(screen.getByLabelText('Reader search'), { target: { value: 'title' } })
    fireEvent.click(screen.getByRole('button', { name: 'Reader page' }))
    await waitFor(() => expect(screen.getByLabelText('Location')).toHaveTextContent('career_page=2'))
    fireEvent.click(screen.getByRole('button', { name: 'Back' }))
    await waitFor(() => expect(screen.getByLabelText('Location')).not.toHaveTextContent('career_page=2'))
    fireEvent.click(screen.getByRole('button', { name: 'Forward' }))
    await waitFor(() => expect(screen.getByLabelText('Location')).toHaveTextContent('career_page=2'))
    fireEvent.click(screen.getByRole('button', { name: 'Reset reader' }))
    expect(screen.getByLabelText('Location')).toHaveTextContent('branch=branch-a&tab=career#timeline')
    expect(window.confirm).not.toHaveBeenCalled()
    for (const [index, action] of ['Other Branch', 'Other tab', 'Other anchor'].entries()) {
      fireEvent.click(screen.getByRole('button', { name: action }))
      await waitFor(() => expect(window.confirm).toHaveBeenCalledTimes(index + 1))
      expect(screen.getByLabelText('Location')).toHaveTextContent('branch=branch-a&tab=career#timeline')
    }
    expect(screen.getByRole('textbox', { name: 'Audit reason' })).toBe(field)
    expect(field).toHaveValue(source === 'local form' ? 'keep my unsaved reason' : 'initial')
    expect(shell).toHaveAttribute('data-run-form-edited', 'true')
  })

  it('does not prompt when leaving an unchanged Run',async()=>{
    setup();await loaded()
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).not.toHaveBeenCalled()
  })

  it('treats search, number, and select filters as read-only exploration',async()=>{
    const view=setup();await loaded()
    fireEvent.change(screen.getByRole('textbox',{name:'Filter search'}),{target:{value:'CZE'}})
    fireEvent.change(screen.getByRole('spinbutton',{name:'Filter age'}),{target:{value:'22'}})
    fireEvent.change(screen.getByRole('combobox',{name:'Filter season'}),{target:{value:'1'}})
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).not.toHaveBeenCalled()
  })

  it('protects edited forms, supports cancelling both internal and exit links',async()=>{
    const view=setup();await loaded()
    vi.mocked(window.confirm).mockReturnValue(false)
    edit('pending change')
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    fireEvent.click(screen.getByRole('link',{name:'Manage Run'}))
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).toHaveBeenCalledTimes(2)
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('unsaved Working Draft'))
  })

  it('reverting to the starting value clears the warning',async()=>{
    const view=setup();await loaded()
    edit('different')
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    edit('initial')
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).not.toHaveBeenCalled()
  })

  it('requires a matching successful Save before clearing local form edits',async()=>{
    const view=setup();await loaded()
    edit('pending change')
    act(()=>acknowledgeSavedRunForm('other-run','branch-a'))
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    act(()=>acknowledgeSavedRunForm('run-a','different-branch'))
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    act(()=>acknowledgeSavedRunForm('run-a','branch-a'))
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).not.toHaveBeenCalled()
  })

  it('re-bases an edited form on its newly saved value instead of the pre-Save default',async()=>{
    const view=setup();await loaded()
    edit('saved revision')
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    act(()=>acknowledgeSavedRunForm('run-a','branch-a'))
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
    // Returning to the OLD value is a real unsaved edit after the Save.
    edit('initial')
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    vi.mocked(window.confirm).mockReturnValue(false)
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).toHaveBeenCalledOnce()
    // Returning to the NEW persisted value must clear the warning.
    edit('saved revision')
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).toHaveBeenCalledTimes(1)
  })

  it('re-bases checkbox state after Save and still tracks later unsaved toggles',async()=>{
    const view=setup();await loaded()
    const checkbox=screen.getByRole('checkbox',{name:'Approve'})
    fireEvent.click(checkbox)
    expect(checkbox).toBeChecked()
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    act(()=>acknowledgeSavedRunForm('run-a','branch-a'))
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
    fireEvent.click(checkbox)
    expect(checkbox).not.toBeChecked()
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    fireEvent.click(checkbox)
    expect(checkbox).toBeChecked()
    expect(view.shell()).not.toHaveAttribute('data-run-form-edited')
  })

  it('preserves server-authoritative dirty Working Draft after local form Save acknowledgement',async()=>{
    const view=setup();await loaded()
    act(()=>view.cache.setQueryData(['package-working-draft','run-a','branch-a'],{...clean,status:'dirty',draft_version:1}))
    await waitFor(()=>expect(view.shell()).toHaveAttribute('data-run-form-edited','true'))
    act(()=>acknowledgeSavedRunForm('run-a','branch-a'))
    expect(view.shell()).toHaveAttribute('data-run-form-edited','true')
    act(()=>view.cache.setQueryData(['package-working-draft','run-a','branch-a'],{...clean,status:'clean',draft_version:2}))
    await waitFor(()=>expect(view.shell()).not.toHaveAttribute('data-run-form-edited'))
    fireEvent.click(screen.getByRole('link',{name:'All Runs'}))
    expect(window.confirm).not.toHaveBeenCalled()
  })

  it('prompts on beforeunload only with actual unsaved evidence',async()=>{
    setup();await loaded()
    const cleanExit = new Event('beforeunload',{cancelable:true})
    window.dispatchEvent(cleanExit)
    expect(cleanExit.defaultPrevented).toBe(false)
    edit('dirty')
    const dirtyExit = new Event('beforeunload',{cancelable:true})
    window.dispatchEvent(dirtyExit)
    expect(dirtyExit.defaultPrevented).toBe(true)
  })

  it('does not allow a saved-head from a different revision to mark the wrong Branch dirty',async()=>{
    const view=setup();await loaded()
    act(()=>view.cache.setQueryData(['package-working-draft','run-a','branch-a'],{
      ...clean,base_saved_revision_id:'different-head',status:'dirty'
    }))
    await waitFor(()=>expect(view.shell()).not.toHaveAttribute('data-run-form-edited'))
  })
})
