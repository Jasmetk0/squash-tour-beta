import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../i18n/LanguageContext'
import { RunsPage } from './RunsPage'
import { RUN_LIST_VIEWS_KEY } from './runListViews'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {},
  listRunContainers: vi.fn(), listRunBranches: vi.fn(), listBranchStates: vi.fn(),
  getGlobalFullSimulationOperations: vi.fn()
}))
vi.mock('../api/client', () => api)

function renderPage() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={['/admin/runs']}><LanguageProvider><RunsPage /></LanguageProvider></MemoryRouter>
  </QueryClientProvider>)
}

describe('canonical Runs inventory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    api.listRunContainers.mockResolvedValue({ run_containers: [
      { run_id: 'run-one', display_name: 'Sandbox One', read_only: false, status: 'working', viewer_branch_id: 'b-viewer' },
      { run_id: 'run-two', display_name: 'Another world', read_only: true, status: 'active' }
    ] })
    api.getGlobalFullSimulationOperations.mockResolvedValue({
      schema_version: 'global_full_simulation_operations.v1',
      visibility: 'durable_receipts_only', operations: [], pending_count: 0,
      legacy_pending_count: 0
    })
    api.listRunBranches.mockResolvedValue({ run_branches: [
      { run_id: 'run-one', branch_id: 'b-alt', display_name: 'Alternative', status: 'active' },
      { run_id: 'run-one', branch_id: 'b-viewer', display_name: 'Viewer timeline', status: 'active' }
    ] })
    api.listBranchStates.mockResolvedValue({ branch_states: [
      { run_id: 'run-one', branch_id: 'b-alt', current_season: 2028, current_week: 27 },
      { run_id: 'run-one', branch_id: 'b-viewer', current_season: null, current_week: null }
    ] })
  })

  it('loads only canonical Runs until a Branch expansion and isolates legacy browsing', async () => {
    renderPage()
    expect(await screen.findByText('Sandbox One')).toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listBranchStates).not.toHaveBeenCalled()
    expect(api.listRunContainers).toHaveBeenCalledTimes(1)
    expect(screen.getByRole('link', { name: 'Starší diagnostika simulačních Runů' })).toHaveAttribute('href', '/admin/legacy-runs')
    expect(screen.getByRole('link', { name: 'Vytvořit prázdný Run' })).toHaveAttribute('href', '/admin/runs/new')
  })

  it('searches canonical names and IDs rather than legacy season fields', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'another')
    expect(screen.queryByText('Sandbox One')).not.toBeInTheDocument()
    expect(screen.getByText('Another world')).toBeInTheDocument()
  })

  it('opens Run Home directly without fetching or expanding its Branches', async () => {
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    const open = within(row).getByRole('link', { name: 'Otevřít Run' })
    expect(open).toHaveAttribute('href', '/admin/runs/run-one')
    expect(api.listRunBranches).not.toHaveBeenCalled()
    await userEvent.click(open)
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-one')
  })

  it('combines search and visibility filters without modifying the stored inventory', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    const visibility = screen.getByRole('combobox', { name: 'Typ Runu' })
    await userEvent.selectOptions(visibility, 'protected')
    expect(screen.queryByText('Sandbox One')).not.toBeInTheDocument()
    expect(screen.getByText('Another world')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'sandbox')
    expect(screen.getByText('Žádný Run neodpovídá hledání.')).toBeInTheDocument()
    await userEvent.selectOptions(visibility, 'editable')
    expect(screen.getByText('Sandbox One')).toBeInTheDocument()
    expect(screen.queryByText('Another world')).not.toBeInTheDocument()
    expect(screen.getByText('Zobrazeno: 1 / 2')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Zrušit filtry' }))
    expect(screen.getByText('Sandbox One')).toBeInTheDocument()
    expect(screen.getByText('Another world')).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno: 2 / 2')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Hledat Run' })).toHaveValue('')
    expect(visibility).toHaveValue('all')
  })

  it('refreshes the Run inventory only when explicitly asked', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    expect(api.listRunContainers).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Obnovit seznam Runů' }))
    await waitFor(() => expect(api.listRunContainers).toHaveBeenCalledTimes(2))
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })

  it.each([null, {}, [null], [{run_id: 'run-one', branch_id: ' '}], [{run_id: 'run-one'}]])(
    'rejects malformed Branch inventory without crashing or claiming no Branches: %j', async run_branches => {
      api.listRunBranches.mockResolvedValueOnce({run_branches})
      renderPage()
      const row = (await screen.findByText('Sandbox One')).closest('li')!
      await userEvent.click(within(row).getByRole('button', {name: 'Větve +'}))
      expect(await within(row).findByRole('alert')).toHaveTextContent('Nekonzistentní identita inventáře')
      expect(within(row).queryByText('Run nemá dostupné větve.')).not.toBeInTheDocument()
      expect(within(row).queryByText('Alternative')).not.toBeInTheDocument()
    }
  )

  it('links the chosen actual Branch, preserving unavailable time and Viewer selection', async () => {
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Větve +' }))
    const alternative = await within(row).findByText('Alternative')
    const target = alternative.closest('.runs-canonical-branch') as HTMLElement
    expect(within(target).getByText('2028/29 · W27')).toBeInTheDocument()
    expect(within(target).getByRole('link', { name: 'Otevřít' })).toHaveAttribute('href', '/admin/runs/run-one?branch=b-alt')
    const viewer = within(row).getByText('Viewer timeline').closest('.runs-canonical-branch') as HTMLElement
    expect(within(viewer).getByText('Čas není dostupný')).toBeInTheDocument()
    expect(within(viewer).getByText('Zobrazuje Viewer')).toBeInTheDocument()
    await userEvent.click(within(target).getByRole('link', { name: 'Otevřít' }))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-one')
  })
  it('shows exact stored parents across Runs without inventing live worker activity', async () => {
    api.getGlobalFullSimulationOperations.mockResolvedValue({
      schema_version: 'global_full_simulation_operations.v1',
      visibility: 'durable_receipts_only',
      pending_count: 2, legacy_pending_count: 1,
      operations: [
        {
          run_id: 'run-one', run_name: 'Sandbox One',
          run_status: 'working', run_read_only: false,
          branch_id: 'b-alt', branch_name: 'Alternative',
          branch_status: 'active', branch_read_only: false,
          command_id: 'parent-a', control_state: 'paused',
          start_week: {season_index: 2, week: 6},
          final_week: {season_index: 49, week: 61},
          completed_season_count: 5, final_completed_week_count: 0,
          review_fingerprint: 'a'.repeat(64), worker_activity: 'unknown'
        },
        {
          run_id: 'run-two', run_name: 'Another world',
          run_status: 'working', run_read_only: true,
          branch_id: 'b-other', branch_name: 'Alternate timeline',
          branch_status: 'active', branch_read_only: false,
          command_id: 'parent-b', control_state: 'running',
          start_week: {season_index: 6, week: 10},
          final_week: {season_index: 49, week: 61},
          completed_season_count: 3, final_completed_week_count: 0,
          review_fingerprint: 'b'.repeat(64), worker_activity: 'unknown'
        }
      ]
    })
    renderPage()
    const list = await screen.findByRole('list', {name: 'Rozpracované Full Simulation'})
    expect(within(list).getByText('Sandbox One · Alternative')).toBeInTheDocument()
    expect(within(list).getByText('Another world · Alternate timeline')).toBeInTheDocument()
    expect(within(list).getByText('Pozastaveno · Aktivita procesu nepotvrzena')).toBeInTheDocument()
    expect(within(list).getByText('Povoleno – proces neověřen · Aktivita procesu nepotvrzena')).toBeInTheDocument()
    const links = within(list).getAllByRole('link', {name: 'Otevřít ovládání'})
    expect(links[0]).toHaveAttribute('href', '/admin/runs/run-one/simulate?branch=b-alt')
    expect(links[1]).toHaveAttribute('href', '/admin/runs/run-two/simulate?branch=b-other')
    expect(screen.getByText(/Starší záznamy bez ověřitelného příkazu k obnovení: 1/)).toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listBranchStates).not.toHaveBeenCalled()
  })

  it('keeps Runs accessible when global operation receipts are unavailable', async () => {
    api.getGlobalFullSimulationOperations.mockRejectedValue(new Error('Read-only conflict'))
    renderPage()
    expect(await screen.findByText('Sandbox One')).toBeInTheDocument()
    expect(await screen.findByRole('alert')).toHaveTextContent('Přehled simulací není dostupný')
    expect(screen.getByRole('link', {name: 'Vytvořit prázdný Run'})).toBeInTheDocument()
  })

  it('rejects foreign or mismatched run_id in Branch responses and does not show empty branches status', async () => {
    api.listRunBranches.mockResolvedValue({ run_branches: [
      { run_id: 'other-run', branch_id: 'b-alt', display_name: 'Alternative', status: 'active' }
    ] })
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Větve +' }))
    const alert = await within(row).findByRole('alert')
    expect(alert).toHaveTextContent('Nekonzistentní identita inventáře')
    expect(within(row).queryByText('Run nemá dostupné větve.')).not.toBeInTheDocument()
  })

  it('rejects duplicate branch_id in Branch responses', async () => {
    api.listRunBranches.mockResolvedValue({ run_branches: [
      { run_id: 'run-one', branch_id: 'b-dup', display_name: 'First', status: 'active' },
      { run_id: 'run-one', branch_id: 'b-dup', display_name: 'Second', status: 'active' }
    ] })
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Větve +' }))
    const alert = await within(row).findByRole('alert')
    expect(alert).toHaveTextContent('Nekonzistentní identita inventáře')
  })

  it('hides time data and shows error if state response contains mismatches or duplicates', async () => {
    api.listBranchStates.mockResolvedValue({ branch_states: [
      { run_id: 'run-one', branch_id: 'b-alt', current_season: 2028, current_week: 27 },
      { run_id: 'other-run', branch_id: 'b-alt', current_season: 2029, current_week: 1 }
    ] })
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Větve +' }))
    const alert = await within(row).findByRole('alert')
    expect(alert).toHaveTextContent('Čas není dostupný: Nekonzistentní identita inventáře')
    const branch = await within(row).findByText('Alternative')
    const container = branch.closest('.runs-canonical-branch') as HTMLElement
    expect(within(container).getByText('Čas není dostupný')).toBeInTheDocument()
    expect(within(container).queryByText(/2028/)).not.toBeInTheDocument()
  })

  it('shows valid branches and states when the inventory is fully consistent', async () => {
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Větve +' }))
    const target = await within(row).findByText('Alternative')
    expect(target).toBeInTheDocument()
    const container = target.closest('.runs-canonical-branch') as HTMLElement
    expect(within(container).getByText('2028/29 · W27')).toBeInTheDocument()
    expect(within(row).queryByRole('alert')).not.toBeInTheDocument()
    expect(within(row).queryByText('Nekonzistentní identita inventáře')).not.toBeInTheDocument()
  })

  it('shows loading state while lazy fetching Branches', async () => {
    let resolveBranches: any
    api.listRunBranches.mockReturnValue(new Promise(resolve => resolveBranches = resolve))
    renderPage()
    const row = (await screen.findByText('Sandbox One')).closest('li')!
    await userEvent.click(within(row).getByRole('button', { name: 'Větve +' }))
    expect(within(row).getByRole('status')).toHaveTextContent('Načítám uložené Runy…')
    resolveBranches({ run_branches: [] })
    await waitFor(() => {
      expect(within(row).queryByRole('status')).not.toBeInTheDocument()
    })
    expect(within(row).getByText('Run nemá dostupné větve.')).toBeInTheDocument()
  })

  it('saves named filters, survives remount and reapplies them to fresh Runs without auto-overwrite', async () => {
    api.listRunContainers.mockResolvedValue({ run_containers: [
      { run_id: 'test-editable', display_name: 'test working', read_only: false, status: 'working' },
      { run_id: 'test-protected', display_name: 'test protected', read_only: true, status: 'active' }
    ] })
    const page = renderPage()
    await screen.findByText('test working')
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'test')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Typ Runu' }), 'editable')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Moje testy')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    const stored = localStorage.getItem(RUN_LIST_VIEWS_KEY)
    expect(stored).toContain('run_list_views.v1')
    expect(JSON.parse(stored!).items).toEqual([
      { name: 'Moje testy', query: 'test', visibility: 'editable', hidden: false }
    ])
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Typ Runu' }), 'protected')
    expect(screen.getByText('Filtry byly změněny. Uložený pohled zůstává beze změny.')).toBeInTheDocument()
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toBe(stored)
    page.unmount()
    renderPage()
    await screen.findByText('test working')
    expect(screen.getByRole('searchbox', { name: 'Hledat Run' })).toHaveValue('')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Uložený pohled' }), 'Moje testy')
    expect(screen.getByRole('searchbox', { name: 'Hledat Run' })).toHaveValue('test')
    expect(screen.getByRole('combobox', { name: 'Typ Runu' })).toHaveValue('editable')
    expect(screen.getByText('test working')).toBeInTheDocument()
    expect(screen.queryByText('test protected')).not.toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listBranchStates).not.toHaveBeenCalled()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
  })

  it('requires explicit update, and rejects a duplicate name instead of silently replacing its filters', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Focus')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    const original = localStorage.getItem(RUN_LIST_VIEWS_KEY)
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Typ Runu' }), 'protected')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'focus')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Pohled se stejným názvem již existuje')
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toBe(original)
    await userEvent.click(screen.getByRole('button', { name: 'Výslovně aktualizovat pohled' }))
    expect(JSON.parse(localStorage.getItem(RUN_LIST_VIEWS_KEY)!).items[0].visibility).toBe('protected')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Uložený pohled' }), '')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Typ Runu' }), 'all')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Uložený pohled' }), 'Focus')
    expect(screen.getByRole('combobox', { name: 'Typ Runu' })).toHaveValue('protected')
  })

  it('hides a view only from quick selection and restores it from the manager after remount', async () => {
    const page = renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Private view')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    await userEvent.click(screen.getByRole('button', { name: 'Spravovat pohledy' }))
    await userEvent.click(screen.getByRole('button', { name: 'Skrýt: Private view' }))
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).not.toHaveTextContent('Private view')
    expect(screen.getByText('Private view · Skrytý')).toBeInTheDocument()
    page.unmount()
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.click(screen.getByRole('button', { name: 'Spravovat pohledy' }))
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).not.toHaveTextContent('Private view')
    await userEvent.click(screen.getByRole('button', { name: 'Obnovit: Private view' }))
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Uložený pohled' }), 'Private view')
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).toHaveValue('Private view')
  })

  it.each([
    ['{broken', 'poškozené'],
    [JSON.stringify({ schema_version: 'run_list_views.v99', items: [] }), 'nepodporovanou verzi'],
    [JSON.stringify({ schema_version: 'run_list_views.v1', items: [{ name: 'Unsafe', query: '', visibility: 'anything', hidden: false }] }), 'poškozené']
  ])('keeps damaged/unsupported preferences intact and basic navigation usable: %s', async (raw, note) => {
    localStorage.setItem(RUN_LIST_VIEWS_KEY, raw)
    renderPage()
    expect(await screen.findByText('Sandbox One')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(note)
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'another')
    expect(screen.getByText('Another world')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít Run' })).toHaveAttribute('href', '/admin/runs/run-two')
    expect(screen.getByRole('button', { name: 'Uložit nový pohled' })).toBeDisabled()
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toBe(raw)
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })

  it('keeps the inventory usable when browser storage throws on read or write', async () => {
    const readError = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked') })
    const page = renderPage()
    expect(await screen.findByText('Sandbox One')).toBeInTheDocument()
    expect(screen.getByText('Úložiště prohlížeče není dostupné. Ukládání pohledů je vypnuté.')).toBeInTheDocument()
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'another')
    expect(screen.getByText('Another world')).toBeInTheDocument()
    page.unmount()
    readError.mockRestore()
    const writeError = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota') })
    try {
      renderPage()
      await screen.findByText('Sandbox One')
      await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Cannot persist')
      await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
      expect(screen.getByRole('alert')).toHaveTextContent('Nastavení se nepodařilo uložit')
      expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).not.toHaveTextContent('Cannot persist')
    } finally {
      writeError.mockRestore()
    }
  })

  it('supports English labels while preserving the user-authored view name', async () => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('textbox', { name: 'New view name' }), 'Moje testy')
    await userEvent.click(screen.getByRole('button', { name: 'Save new view' }))
    expect(screen.getByRole('combobox', { name: 'Saved view' })).toHaveValue('Moje testy')
    expect(screen.getByText('Saved only in this browser. Stores list filters, never Runs.')).toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })

  it('applies saved search to the CURRENT refreshed inventory, not stored Run copies', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'Sandbox')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Current only')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    api.listRunContainers.mockResolvedValue({ run_containers: [
      { run_id: 'run-one', display_name: 'Renamed now', read_only: false, status: 'working' }
    ] })
    await userEvent.click(screen.getByRole('button', { name: 'Obnovit seznam Runů' }))
    await waitFor(() => expect(screen.getByText('Žádný Run neodpovídá hledání.')).toBeInTheDocument())
    expect(screen.queryByText('Sandbox One')).not.toBeInTheDocument()
    expect(JSON.parse(localStorage.getItem(RUN_LIST_VIEWS_KEY)!).items[0]).toEqual({
      name: 'Current only', query: 'Sandbox', visibility: 'all', hidden: false
    })
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })

  it('refuses a stale-tab update without silently overwriting another tab', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Shared')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Typ Runu' }), 'protected')
    const external = JSON.stringify({ schema_version: 'run_list_views.v1', items: [
      { name: 'Shared', query: 'saved elsewhere', visibility: 'editable', hidden: false }
    ] })
    // Simulate a write in another tab that arrived just before our click,
    // even if the StorageEvent has not yet been delivered.
    localStorage.setItem(RUN_LIST_VIEWS_KEY, external)
    await userEvent.click(screen.getByRole('button', { name: 'Výslovně aktualizovat pohled' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Uložené pohledy se mezitím změnily')
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toBe(external)
    expect(screen.getByRole('combobox', { name: 'Typ Runu' })).toHaveValue('protected')
    expect(screen.getByRole('button', { name: 'Výslovně aktualizovat pohled' })).toBeEnabled()
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Uložený pohled' }), '')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Uložený pohled' }), 'Shared')
    expect(screen.getByRole('searchbox', { name: 'Hledat Run' })).toHaveValue('saved elsewhere')
    expect(screen.getByRole('combobox', { name: 'Typ Runu' })).toHaveValue('editable')
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listBranchStates).not.toHaveBeenCalled()
  })

  it('reflects StorageEvent changes in the selector without changing current filters or opening a Run', async () => {
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('searchbox', { name: 'Hledat Run' }), 'Sandbox')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Old')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    const external = JSON.stringify({ schema_version: 'run_list_views.v1', items: [
      { name: 'Old', query: 'Elsewhere', visibility: 'protected', hidden: true },
      { name: 'From tab two', query: 'another', visibility: 'editable', hidden: false }
    ] })
    act(() => {
      localStorage.setItem(RUN_LIST_VIEWS_KEY, external)
      window.dispatchEvent(new StorageEvent('storage', { key: RUN_LIST_VIEWS_KEY }))
    })
    expect(screen.getByRole('searchbox', { name: 'Hledat Run' })).toHaveValue('Sandbox')
    expect(screen.getByRole('combobox', { name: 'Typ Runu' })).toHaveValue('all')
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).not.toHaveTextContent('Old')
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).toHaveTextContent('From tab two')
    expect(screen.getByText('Uložené pohledy se změnily v jiném panelu. Filtry zůstaly beze změny; pro použití vyber pohled znovu.')).toBeInTheDocument()
    expect(api.listRunBranches).not.toHaveBeenCalled()
    expect(api.listBranchStates).not.toHaveBeenCalled()
    expect(localStorage.getItem('beta_engine:last_run_id')).toBeNull()
  })

  it('can retry browser preference loading after temporary unavailable storage', async () => {
    const failure = vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => { throw new Error('blocked') })
    try {
      renderPage()
      expect(await screen.findByText('Sandbox One')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Uložit nový pohled' })).toBeDisabled()
    } finally {
      failure.mockRestore()
    }
    await userEvent.click(screen.getByRole('button', { name: 'Znovu načíst uložené pohledy' }))
    expect(screen.getByRole('button', { name: 'Uložit nový pohled' })).toBeEnabled()
    expect(screen.queryByText('Úložiště prohlížeče není dostupné. Ukládání pohledů je vypnuté.')).not.toBeInTheDocument()
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'Recovered')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    expect(JSON.parse(localStorage.getItem(RUN_LIST_VIEWS_KEY)!).items[0].name).toBe('Recovered')
  })

  it('keeps a full 24-view store unchanged when an additional view is requested', async () => {
    const fullStore = JSON.stringify({
      schema_version: 'run_list_views.v1',
      items: Array.from({ length: 24 }, (_, i) => ({
        name: 'View ' + String(i + 1), query: '', visibility: 'all', hidden: false
      }))
    })
    localStorage.setItem(RUN_LIST_VIEWS_KEY, fullStore)
    renderPage()
    await screen.findByText('Sandbox One')
    await userEvent.type(screen.getByRole('textbox', { name: 'Název nového pohledu' }), 'One too many')
    await userEvent.click(screen.getByRole('button', { name: 'Uložit nový pohled' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Byl dosažen limit 24 pohledů')
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toBe(fullStore)
  })

  it('supports saving with the Enter key, and retaining preferences with empty or unavailable inventory', async () => {
    api.listRunContainers.mockResolvedValueOnce({ run_containers: [] })
    const page = renderPage()
    expect(await screen.findByText('Zatím žádné uložené Runy.')).toBeInTheDocument()
    const input = screen.getByRole('textbox', { name: 'Název nového pohledu' })
    input.focus()
    await userEvent.keyboard('Keyboard saved')
    const saveButton = screen.getByRole('button', { name: 'Uložit nový pohled' })
    saveButton.focus()
    await userEvent.keyboard('{Enter}')
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).toHaveValue('Keyboard saved')
    expect(localStorage.getItem(RUN_LIST_VIEWS_KEY)).toContain('Keyboard saved')
    page.unmount()
    api.listRunContainers.mockRejectedValueOnce(new Error('offline'))
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent('Přehled Runů není dostupný')
    expect(screen.getByRole('combobox', { name: 'Uložený pohled' })).toHaveTextContent('Keyboard saved')
    expect(screen.getByRole('link', { name: 'Vytvořit prázdný Run' })).toHaveAttribute('href', '/admin/runs/new')
    expect(api.listRunBranches).not.toHaveBeenCalled()
  })

})
