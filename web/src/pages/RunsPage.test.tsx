import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../i18n/LanguageContext'
import { RunsPage } from './RunsPage'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn(), listRunBranches: vi.fn(), listBranchStates: vi.fn()
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
})
