import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Link, MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { acknowledgeSavedRunForm, RunNavigationSafeguard } from './RunNavigationSafeguard'

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

describe('Run dirty navigation evidence',()=>{
  beforeEach(()=>{
    vi.restoreAllMocks();vi.clearAllMocks()
    context.branch={run_id:'run-a',branch_id:'branch-a',saved_head_revision_id:'head-a'}
    api.getBranchWorkingDraft.mockResolvedValue(clean)
    vi.spyOn(window,'confirm').mockReturnValue(true)
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
