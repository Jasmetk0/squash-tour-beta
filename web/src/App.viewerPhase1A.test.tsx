import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
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
  getRunStatusSummary: vi.fn(),
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
  api.getRunStatusSummary.mockResolvedValue({
    run_id: 'run-a',
    season: 2029,
    seed: 7,
    progress: { next_event_index: 0, total_events: 1, completed_event_count: 0 },
    finals: { qualification_available: false, result_available: false },
    rollover: null,
    source: { source_type: 'fresh_seed', parent_run_id: null },
    lineage: { child_run_count: 0 },
    history_counts: { events: 0, ranking_snapshots: 0, race_snapshots: 0 }
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
  api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2029, qualification: null, result: null })
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

describe('Viewer Phase 1B/1C/1D routes and safety', () => {
  it('renders premium MSA homepage scaffold sections without active-run authoritative data', async () => {
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
    expect(screen.getByText(/Active run data is unavailable until a Viewer run is selected/)).toBeInTheDocument()
    expect(screen.getByText('Prediction analytics are not connected yet.')).toBeInTheDocument()
    expect(screen.queryByText('Paris can reclaim No.1 this week.')).not.toBeInTheDocument()
    expect(screen.queryByText('Macky needs a semifinal to protect his Race lead.')).not.toBeInTheDocument()
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
      ['/viewer/rankings/race', 'Select a Viewer run to view Race to Finals.'],
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

  it('shows active run status, safe links, and small real summaries on the Viewer homepage', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      seed: 99,
      progress: { next_event_index: 1, total_events: 4, completed_event_count: 1 },
      finals: { qualification_available: true, result_available: false },
      rollover: null,
      source: { source_type: 'rollover_bootstrap', parent_run_id: 'run-parent' },
      lineage: { child_run_count: 0 },
      history_counts: { events: 1, ranking_snapshots: 2, race_snapshots: 1 }
    })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 1, total_events: 4, completed_event_ids: ['E1'] },
      season_state: {
        season: 2030,
        next_event_index: 1,
        completed_event_ids: ['E1'],
        ordered_events: [
          { event_id: 'E1', season: 2030, week: 2, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' },
          { event_id: 'E2', season: 2030, week: 5, tour: 'WORLD', category: 'DIAMOND', template_id: 'TEMP-B' },
          { event_id: 'E3', season: 2030, week: 5, tour: 'ELITE', category: 'BRONZE', template_id: 'TEMP-C' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [{ event_sequence: 1, event_id: 'E1', season: 2030, week: 2, template_id: 'TEMP-A', tournament_result: {} }] })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [{ snapshot_sequence: 1, snapshot_kind: 'ranking', source_event_id: 'E1', payload: {} }, { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'E2', payload: {} }] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [{ snapshot_sequence: 3, snapshot_kind: 'race', source_event_id: 'E2', payload: {} }] })
    api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [{ kind: 'event', sequence: 1, label: 'E1 completed', season: 2030, week: 2, event_id: 'E1', snapshot_sequence: null, source_event_id: null, related_run_id: null }] })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2030, qualification: { run_id: 'run-a', season: 2030, source_as_of_season: 2030, source_as_of_week: 40, qualification: {} }, result: null })
    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: 'Active run data is available' })).toBeInTheDocument()
    const statusPanel = screen.getByLabelText('Active Viewer run status')
    await waitFor(() => expect(statusPanel).toHaveTextContent('Using Viewer run'))
    expect(statusPanel).toHaveTextContent('run-a')
    expect(statusPanel).toHaveTextContent('2030')
    expect(statusPanel).toHaveTextContent('99')
    expect(statusPanel).toHaveTextContent('1/4 events complete')
    expect(statusPanel).toHaveTextContent('Qualification available')
    expect(statusPanel).toHaveTextContent('rollover_bootstrap from run-parent')
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
    expect(screen.getByText(/Next scheduled event:/)).toHaveTextContent('E2')
    expect(screen.getByText(/DIAMOND/)).toHaveTextContent('W5')
    expect(screen.getByText(/E3 · BRONZE · W5/)).toBeInTheDocument()
    expect(screen.getByText(/Latest ranking snapshot #2 from E2/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByText(/Latest race snapshot #3 from E2/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByText(/1 activity items · Latest: E1 completed/)).toBeInTheDocument()
    expect(screen.getByText('Prediction analytics are not connected yet.')).toBeInTheDocument()
  })

  it('shows a sports-facing unavailable state when active-run homepage APIs fail', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRun.mockRejectedValueOnce(new Error('run unavailable'))
    api.getRunStatusSummary.mockRejectedValueOnce(new Error('status unavailable'))
    api.listEvents.mockRejectedValueOnce(new Error('events unavailable'))
    api.listRankingSnapshots.mockRejectedValueOnce(new Error('ranking unavailable'))
    api.listRaceSnapshots.mockRejectedValueOnce(new Error('race unavailable'))
    api.getRunActivity.mockRejectedValueOnce(new Error('activity unavailable'))
    api.getFinalsSummary.mockRejectedValueOnce(new Error('finals unavailable'))

    renderAppAt('/viewer')

    expect(await screen.findByText(/Active run summary is temporarily unavailable/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Featured Tournament Hero' })).toBeInTheDocument()
    expect(screen.getByText('No current event summary available yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows top-level rankings snapshot metadata when an active run has ranking snapshots', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'TOURNAMENT', source_event_id: 'E1', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} }
      ]
    })

    renderAppAt('/viewer/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('MSA Rankings active run snapshot summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Ranking snapshot count')
    expect(panel).toHaveTextContent('2')
    expect(panel).toHaveTextContent('Latest snapshot sequence')
    expect(panel).toHaveTextContent('8')
    expect(panel).toHaveTextContent('Latest source event ID')
    expect(panel).toHaveTextContent('E3')
    expect(panel).toHaveTextContent('Latest snapshot kind')
    expect(panel).toHaveTextContent('WEEK')
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'View latest ranking snapshot' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/8')
    expectNoForbiddenViewerActions()
  })

  it('shows top-level race snapshot metadata when an active run has race snapshots', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [
        { snapshot_sequence: 2, snapshot_kind: 'TOURNAMENT', source_event_id: 'E1', payload: {} },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: {} }
      ]
    })

    renderAppAt('/viewer/rankings/race')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('Race to Finals active run snapshot summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Race snapshot count')
    expect(panel).toHaveTextContent('2')
    expect(panel).toHaveTextContent('Latest snapshot sequence')
    expect(panel).toHaveTextContent('9')
    expect(panel).toHaveTextContent('Latest source event ID')
    expect(panel).toHaveTextContent('E4')
    expect(panel).toHaveTextContent('Latest snapshot kind')
    expect(panel).toHaveTextContent('WEEK')
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByRole('link', { name: 'View latest race snapshot' })).toHaveAttribute('href', '/viewer/runs/run-a/race/9')
    expectNoForbiddenViewerActions()
  })

  it('shows top-level rankings and race empty snapshot states for active runs without snapshots', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/rankings')
    expect(await screen.findByText('No ranking snapshots are available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.queryByRole('link', { name: 'View latest ranking snapshot' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/rankings/race')
    expect(await screen.findByText('No race snapshots are available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.queryByRole('link', { name: 'View latest race snapshot' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('bridges other active-run top-level Viewer pages to run-scoped read-only routes', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    const bridgedRoutes = [
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

  it('preserves the real run-scoped Viewer ranking and race snapshot pages', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/runs/run-a/rankings')
    expect(await screen.findByRole('heading', { name: 'Ranking snapshots' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/runs/run-a/race')
    expect(await screen.findByRole('heading', { name: 'Race snapshots' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
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
      '/viewer/rankings/race',
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
