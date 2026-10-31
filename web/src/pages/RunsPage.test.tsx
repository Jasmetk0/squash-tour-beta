import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../i18n/LanguageContext'
import { RunsPage } from './RunsPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {},
  listRunContainers: vi.fn(), listRunBranches: vi.fn(), listBranchStates: vi.fn(),
  getGlobalFullSimulationOperations: vi.fn()
}))
vi.mock('../api/client', () => api)

function renderPage(): void {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
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

})
