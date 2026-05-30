import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

const api = vi.hoisted(() => ({
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listRuns: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getRun: vi.fn(),
  listEvents: vi.fn(),
  getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRunPlayers: vi.fn(),
  getRunPlayerDetail: vi.fn(),
  listRunNations: vi.fn(),
  getRunNationDetail: vi.fn(),
  getRunActivity: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn(),
  getFinalsSummary: vi.fn()
}))

vi.mock('./api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api/client')>()
  return {
    ...actual,
    ...api
  }
})

function resetApiMocks(): void {
  api.getCountriesMetadata.mockResolvedValue({ country_count: 0 })
  api.getTournamentTemplatesMetadata.mockResolvedValue({ template_count: 0 })
  api.listRuns.mockResolvedValue({ runs: [] })
  api.getViewerRankingTable.mockRejectedValue(new Error('Viewer read model unavailable in test'))
  api.getRun.mockResolvedValue({
    run: { run_id: 'run-a', season: 2029, seed: 7, next_event_index: 0, total_events: 1, completed_event_ids: [] },
    season_state: {
      season: 2029,
      next_event_index: 0,
      completed_event_ids: [],
      ordered_events: [{ event_id: 'E1', season: 2029, week: 2, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' }]
    }
  })
  api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [] })
  api.getEvent.mockResolvedValue({ run_id: 'run-a', event_id: 'E1', event: null })
  api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
  api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
  api.listRunPlayers.mockResolvedValue({ run_id: 'run-a', players: [], total: 0, limit: 200, offset: 0 })
  api.getRunPlayerDetail.mockResolvedValue({ player: null })
  api.listRunNations.mockResolvedValue({ run_id: 'run-a', nations: [], total: 0, limit: 300, offset: 0 })
  api.getRunNationDetail.mockResolvedValue({ nation: null })
  api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [] })
  api.getFinalsQualification.mockResolvedValue({ run_id: 'run-a', qualification: null })
  api.getFinalsResult.mockResolvedValue({ run_id: 'run-a', result: null })
  api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', qualification: null, result: null })
}

function renderAppAt(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function interactiveLabels(): string[] {
  return [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')].map((element) => element.textContent?.trim() ?? '')
}

function expectNoForbiddenViewerActions(): void {
  const forbidden = /^(Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)$/i
  expect(interactiveLabels().filter((label) => forbidden.test(label))).toEqual([])
}

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

beforeEach(() => {
  localStorage.removeItem('beta_engine:viewer_active_run_id')
  resetApiMocks()
})

describe('Viewer Phase 1B/1C routes and safety', () => {
  it('renders premium MSA homepage scaffold sections without authoritative data', async () => {
    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: /MSA Squash/, level: 2 })).toBeInTheDocument()
    for (const section of [
      'Featured Tournament Hero',
      'Other Tournaments This Week',
      'Top 10 Rankings',
      'Race to Finals',
      'Featured Matches',
      'Predictions & Upset Watch',
      'Storylines'
    ]) {
      expect(screen.getByRole('heading', { name: section })).toBeInTheDocument()
    }
    expect(screen.getAllByText('No authoritative data is shown in this Phase 1C shell.')).toHaveLength(7)
  })

  it('updates local Viewer context with Jump to Week', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer/tour/calendar')

    expect(await screen.findByRole('button', { name: 'Season 2004/05 · W10' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Jump to W24' }))
    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
  })

  it('shows sports-facing empty states on top-level Viewer pages when no active run is selected', async () => {
    localStorage.removeItem('beta_engine:viewer_active_run_id')
    const emptyStateRoutes = [
      ['/viewer/rankings', 'Select a Viewer run to view MSA Rankings.'],
      ['/viewer/players', 'Select a Viewer run to view MSA Players.'],
      ['/viewer/countries', 'Select a Viewer run to view MSA Countries.'],
      ['/viewer/history', 'Select a Viewer run to view MSA History.']
    ] as const

    for (const [route, message] of emptyStateRoutes) {
      cleanup()
      renderAppAt(route)
      expect(await screen.findByText(message)).toBeInTheDocument()
      expect(screen.queryByText(/debug/i)).not.toBeInTheDocument()
    }
  })

  it('shows active run status and run-scoped read-only links on the Viewer homepage', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: 'Active run data is available' })).toBeInTheDocument()
    expect(screen.getByText(/Using Viewer run/)).toHaveTextContent('run-a')
    const statusPanel = screen.getByLabelText('Active Viewer run status')
    for (const [name, href] of [
      ['Active Run Rankings', '/viewer/runs/run-a/rankings'],
      ['Active Run Race', '/viewer/runs/run-a/race'],
      ['Active Run Tournaments', '/viewer/runs/run-a/tournaments'],
      ['Active Run Calendar', '/viewer/runs/run-a/calendar'],
      ['Active Run Players', '/viewer/runs/run-a/players'],
      ['Active Run Countries', '/viewer/runs/run-a/countries'],
      ['Active Run History', '/viewer/runs/run-a/history'],
      ['Active Run Finals', '/viewer/runs/run-a/finals']
    ] as const) {
      expect(within(statusPanel).getByRole('link', { name })).toHaveAttribute('href', href)
    }
  })

  it('bridges active-run top-level Viewer pages to run-scoped read-only routes', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    const bridgedRoutes = [
      ['/viewer/rankings', 'Ranking snapshots'],
      ['/viewer/rankings/race', 'Race snapshots'],
      ['/viewer/tour/tournaments', 'Events history'],
      ['/viewer/tournaments', 'Events history'],
      ['/viewer/players', 'Run Players Explorer'],
      ['/viewer/countries', 'Run Nations Dashboard'],
      ['/viewer/history', 'Run activity']
    ] as const

    for (const [route, heading] of bridgedRoutes) {
      cleanup()
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
      expectNoForbiddenViewerActions()
    }
  })

  it('offers the active run calendar link while preserving the top-level calendar Jump to Week primitive', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/tour/calendar')

    expect(await screen.findByRole('button', { name: 'Jump to W24' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run calendar' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
  })

  it('does not render forbidden mutating Viewer buttons or links on top-level shell pages', async () => {
    const routes = [
      '/viewer',
      '/viewer/rankings',
      '/viewer/tournaments',
      '/viewer/players',
      '/viewer/countries',
      '/viewer/history',
      '/viewer/records',
      '/viewer/tour',
      '/viewer/tour/calendar',
      '/viewer/tour/tournaments',
      '/viewer/h2h',
      '/viewer/stats',
      '/viewer/predictions',
      '/viewer/search'
    ]

    for (const route of routes) {
      cleanup()
      renderAppAt(route)
      expect(await screen.findByTestId('viewer-primary-nav')).toBeInTheDocument()
      expectNoForbiddenViewerActions()
    }
  })

  it('preserves the real run-scoped Viewer season calendar page', async () => {
    renderAppAt('/viewer/runs/run-a/calendar')

    expect(await screen.findByRole('heading', { name: 'Season calendar' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ordered season calendar' })).toBeInTheDocument()
    expect(await screen.findByRole('list', { name: 'Season calendar ordered list' })).toHaveTextContent('E1')
    expect(screen.queryByText('Sample calendar card for future read-only weekly event browsing.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Jump to W24' })).not.toBeInTheDocument()
  })

  it('preserves the real run-scoped Viewer tournaments/events page', async () => {
    renderAppAt('/viewer/runs/run-a/tournaments')

    expect(await screen.findByRole('heading', { name: 'Events history' })).toBeInTheDocument()
    expect(screen.getByText(/Browse persisted event history/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer players page', async () => {
    renderAppAt('/viewer/runs/run-a/players')

    expect(await screen.findByRole('heading', { name: 'Run Players Explorer' })).toBeInTheDocument()
    expect(screen.getByText('Read-only player pool explorer for the selected run.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer countries/nations page', async () => {
    renderAppAt('/viewer/runs/run-a/countries')

    expect(await screen.findByRole('heading', { name: 'Run Nations Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Country strength diagnostics over the current run player pool.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer history/activity page', async () => {
    renderAppAt('/viewer/runs/run-a/history')

    expect(await screen.findByRole('heading', { name: 'Run activity' })).toBeInTheDocument()
    expect(screen.getByText(/Deterministic run-level feed browser/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders read-only Viewer Finals without simulation action', async () => {
    renderAppAt('/viewer/runs/run-a/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders read-only Viewer planned event detail without commissioner controls', async () => {
    renderAppAt('/viewer/runs/run-a/calendar/event-a')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    const controls = interactiveLabels().join(' ')
    expect(controls).not.toMatch(/wildcard|withdrawal|late replacement/i)
    expectNoForbiddenViewerActions()
  })

  it('routes shared shortcuts to same pages/components', async () => {
    renderAppAt('/viewer/countries/ranking')
    expect(await screen.findByRole('heading', { name: 'Country Ranking' })).toBeInTheDocument()

    cleanup()
    renderAppAt('/viewer/players/compare')
    expect(await screen.findByRole('heading', { name: 'Player Comparison' })).toBeInTheDocument()

    cleanup()
    renderAppAt('/viewer/predictions/match-predictor')
    expect(await screen.findByRole('heading', { name: 'Match Predictor' })).toBeInTheDocument()
  })

  it('keeps context-aware mode switcher mappings on equivalent Viewer and Admin routes', async () => {
    const mappings = [
      ['/viewer/players', '/admin/players'],
      ['/admin/players', '/viewer/players'],
      ['/viewer/countries', '/admin/world/countries'],
      ['/admin/world/countries', '/viewer/countries'],
      ['/viewer/tour', '/admin/tour-seasons'],
      ['/admin/tour-seasons', '/viewer/tour'],
      ['/viewer/runs/run-a/calendar', '/admin/runs/run-a/calendar'],
      ['/admin/runs/run-a/calendar', '/viewer/runs/run-a/calendar'],
      ['/viewer/runs/run-a/players', '/admin/runs/run-a/players'],
      ['/admin/runs/run-a/players', '/viewer/runs/run-a/players']
    ]

    for (const [route, expectedHref] of mappings) {
      cleanup()
      renderAppAt(route)
      const switcher = await screen.findByLabelText('Mode switcher')
      const targetName = expectedHref.startsWith('/admin') ? 'Admin / Engine' : 'Viewer / MSA'
      expect(within(switcher).getByRole('link', { name: targetName })).toHaveAttribute('href', expectedHref)
    }
  })

  it('Admin routes still render', async () => {
    renderAppAt('/admin')

    expect(await screen.findByRole('heading', { name: 'Admin Engine Dashboard' })).toBeInTheDocument()
    const adminNav = screen.getByRole('navigation', { name: 'Admin / Engine Mode navigation' })
    expect(within(adminNav).getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(within(adminNav).getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
  })
})
