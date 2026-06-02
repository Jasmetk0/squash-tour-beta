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
  getFinalsSummary: vi.fn(),
  getRankingSnapshot: vi.fn(),
  getRaceSnapshot: vi.fn()
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
  api.getRankingSnapshot.mockResolvedValue({ snapshot_sequence: 4, snapshot_kind: 'ranking', source_event_id: 'E1', payload: {} })
  api.getRaceSnapshot.mockResolvedValue({ snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'E1', payload: {} })
}


function topRankingRows(count: number): Array<Record<string, unknown>> {
  return Array.from({ length: count }, (_, index) => ({
    position: index + 1,
    player: { id: `P${index + 1}`, name: index === 0 ? 'Nour El Sherbini' : `Top Player ${index + 1}`, country_code: index === 0 ? 'EG' : 'US' },
    total_points: 1000 - index,
    events_counted: index === 0 ? 9 : 7,
    previous_rank: index === 0 ? 2 : index + 1
  }))
}

function topRaceRows(count: number): Array<Record<string, unknown>> {
  return Array.from({ length: count }, (_, index) => ({
    rank: index + 1,
    player: { id: `R${index + 1}`, name: index === 0 ? 'Paul Coll' : `Race Top Player ${index + 1}`, country_code: index === 0 ? 'NZ' : 'EG' },
    points: 7000 - index,
    events_counted: index === 0 ? 8 : 6,
    qualification_status: index === 0 ? 'Qualified' : 'Chasing',
    next_max_points: index === 0 ? 1500 : 1000
  }))
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
  localStorage.removeItem('beta_engine:viewer_context')
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
    expect(screen.getAllByText('No data is available for this run yet.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('This preview is not connected for this data shape yet.').length).toBeGreaterThan(0)
    expect(screen.queryByText('Paris can reclaim No.1 this week.')).not.toBeInTheDocument()
    expect(screen.queryByText('Macky needs a semifinal to protect his Race lead.')).not.toBeInTheDocument()
  })

  it('renders the active run picker with available runs and no active run state', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        { run_id: 'run-a', season: 2030, seed: 9, progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 },
        { run_id: 'run-b', season: 2031, seed: 11, progress: { next_event_index: 1, total_events: 5, completed_event_count: 1 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 }
      ]
    })

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active run picker')
    expect(picker).toHaveTextContent('No active run selected')
    expect(await within(picker).findByRole('option', { name: /run-a — season 2030, seed 9/ })).toBeInTheDocument()
    expect(within(picker).getByRole('option', { name: /run-b — season 2031, seed 11/ })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('stores selected active run locally and updates homepage active-run links', async () => {
    const user = userEvent.setup()
    api.listRuns.mockResolvedValue({
      runs: [
        { run_id: 'run-a', season: 2030, seed: 9, progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 },
        { run_id: 'run-b', season: 2031, seed: 11, progress: { next_event_index: 1, total_events: 5, completed_event_count: 1 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 }
      ]
    })

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active run picker')
    await within(picker).findByRole('option', { name: /run-b — season 2031, seed 11/ })
    await user.selectOptions(within(picker).getByLabelText('Available runs'), 'run-b')
    await user.click(within(picker).getByRole('button', { name: 'Set active run' }))

    await waitFor(() => expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-b')
    await waitFor(() => expect(within(picker).getByText('run-b')).toBeInTheDocument())
    expect(await screen.findByRole('link', { name: 'Active Run Rankings' })).toHaveAttribute('href', '/viewer/runs/run-b/rankings')
    expect(screen.getByRole('link', { name: 'Active Run Calendar' })).toHaveAttribute('href', '/viewer/runs/run-b/calendar')
    expect(screen.queryAllByLabelText('Viewer active run quick links')).toHaveLength(0)
    expectNoForbiddenViewerActions()
  })

  it('shows an empty state when the active run picker has no runs', async () => {
    api.listRuns.mockResolvedValue({ runs: [] })

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active run picker')
    expect(await within(picker).findByText('No runs are available yet.')).toBeInTheDocument()
    expect(within(picker).getByRole('button', { name: 'Set active run' })).toBeDisabled()
    expectNoForbiddenViewerActions()
  })

  it('shows an unavailable state when the active run picker cannot load runs', async () => {
    api.listRuns.mockRejectedValue(new Error('runs unavailable'))

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active run picker')
    expect(await within(picker).findByText('Run list is unavailable.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('updates and persists local Viewer context from the selector controls', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer/tour/current-week')

    const selector = await screen.findByRole('button', { name: 'Season 2004/05 · W10' })
    await user.click(selector)
    const weekInput = screen.getByLabelText('Selected week')
    await user.clear(weekInput)
    await user.type(weekInput, '24')
    await user.click(screen.getByRole('button', { name: 'Set Viewer Week' }))

    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
    expect(localStorage.getItem('beta_engine:viewer_context')).toContain('24')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()

    cleanup()
    renderAppAt('/viewer/tour/current-week')
    expect(await screen.findByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
  })

  it('updates local Viewer context with Jump to Week and stores the shared context', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer/tour/calendar')

    expect(await screen.findByRole('button', { name: 'Season 2004/05 · W10' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Jump to W24' }))
    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
    expect(localStorage.getItem('beta_engine:viewer_context')).toContain('24')
  })

  it('navigates the topbar search input to the query shell without fake results', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer')

    const searchInput = await screen.findByRole('textbox', { name: 'Search players, countries, tournaments' })
    await user.type(searchInput, 'Paris{Enter}')

    expect(await screen.findByRole('heading', { name: 'Search' })).toBeInTheDocument()
    expect(screen.getByText('Search query: Paris')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Read-only Viewer search shell')[0]).toHaveValue('Paris')
    expect(screen.getByText('Full search result sets are not shown yet; this page only reflects the local query from the URL.')).toBeInTheDocument()
    expect(screen.queryByText(/Paris can reclaim/i)).not.toBeInTheDocument()
  })

  it('navigates an empty topbar search submit to the search shell without a query string', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer')

    const searchInput = await screen.findByRole('textbox', { name: 'Search players, countries, tournaments' })
    await user.click(searchInput)
    await user.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { name: 'Search' })).toBeInTheDocument()
    expect(screen.getAllByLabelText('Read-only Viewer search shell')[0]).toHaveValue('')
    expect(screen.queryByText(/Search query:/)).not.toBeInTheDocument()
    expect(screen.getAllByText('No data is available for this run yet.').length).toBeGreaterThan(0)
  })

  it('shows sports-facing empty states on top-level Viewer pages when no active run is selected', async () => {
    localStorage.removeItem('beta_engine:viewer_active_run_id')
    const emptyStateRoutes = [
      ['/viewer/rankings', 'No data is available for this run yet.'],
      ['/viewer/rankings/race', 'No data is available for this run yet.'],
      ['/viewer/tour', 'No data is available for this run yet.'],
      ['/viewer/tour/current-week', 'No data is available for this run yet.'],
      ['/viewer/tour/tournaments', 'No data is available for this run yet.'],
      ['/viewer/tournaments', 'No data is available for this run yet.'],
      ['/viewer/players', 'No data is available for this run yet.'],
      ['/viewer/countries', 'No data is available for this run yet.'],
      ['/viewer/history', 'No data is available for this run yet.'],
      ['/viewer/records', 'This preview is not connected for this data shape yet.'],
      ['/viewer/stats', 'This preview is not connected for this data shape yet.'],
      ['/viewer/h2h', 'No data is available for this run yet.'],
      ['/viewer/predictions', 'This preview is not connected for this data shape yet.'],
      ['/viewer/predictions/match-predictor', 'This preview is not connected for this data shape yet.'],
      ['/viewer/search', 'No data is available for this run yet.']
    ] as const

    for (const [route, message] of emptyStateRoutes) {
      cleanup()
      renderAppAt(route)
      expect(await screen.findByText(message)).toBeInTheDocument()
      expect(screen.queryByText(/debug/i)).not.toBeInTheDocument()
    }

    cleanup()
    renderAppAt('/viewer/tour/calendar')
    expect(await screen.findByRole('button', { name: 'Jump to W24' })).toBeInTheDocument()
    expect(screen.getAllByText('No data is available for this run yet.').length).toBeGreaterThan(0)
    expect(screen.queryByRole('link', { name: 'Open active run schedule' })).not.toBeInTheDocument()
  })

  it('shows conservative active-run H2H landing and subroute deferred states', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'phase-1i-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-1i-run',
      total: 8,
      limit: 5,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'AAA', age: 24, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 80, movement: 81, physical: 82, mental: 83, overall: 84 },
        { player_id: 'P2', name: 'Player Two', country_code: 'BBB', age: 26, source_type: 'planner_generated', override_id: null, quality_band: 'B', is_top_band: false, origin_source_type: 'planner_generated', origin_quality_band: 'B', origin_override_id: null, origin_season: 2030, technique: 70, movement: 71, physical: 72, mental: 73, overall: 74 }
      ]
    })

    renderAppAt('/viewer/h2h')
    expect(await screen.findByRole('heading', { name: 'H2H Explorer', level: 2 })).toBeInTheDocument()
    expect(await screen.findByLabelText('H2H Explorer active run summary')).toHaveTextContent('phase-1i-run')
    expect(screen.getByText('Player One')).toBeInTheDocument()
    expect(screen.getAllByText('This preview is not connected for this data shape yet.').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-1i-run/players')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/phase-1i-run/tournaments')
    expect(screen.queryByText(/wins/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/h2h/rivalries')
    expect((await screen.findAllByText('This preview is not connected for this data shape yet.')).length).toBeGreaterThan(0)
    expect(screen.getByText('No rivalry list is shown until direct match records are available.')).toBeInTheDocument()
    expect(screen.getAllByText('phase-1i-run').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Top rivalry/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/h2h/most-played')
    expect((await screen.findAllByText('This preview is not connected for this data shape yet.')).length).toBeGreaterThan(0)
    expect(screen.getByText('No matchup list is shown until completed match counts are available.')).toBeInTheDocument()
    expect(screen.queryByText(/matchup record/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/h2h/finals-rivalries')
    expect((await screen.findAllByText('This preview is not connected for this data shape yet.')).length).toBeGreaterThan(0)
    expect(screen.getByText('No finals rivalry list is shown until final-round match records are available.')).toBeInTheDocument()
    expect(screen.queryByText(/finals record/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows conservative Match Predictor landing for predictions shortcut routes', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'phase-1i-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-1i-run',
      total: 6,
      limit: 5,
      offset: 0,
      players: [
        { player_id: 'P3', name: 'Player Three', country_code: 'CCC', age: 23, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 82, movement: 83, physical: 84, mental: 85, overall: 86 }
      ]
    })

    for (const route of ['/viewer/predictions', '/viewer/predictions/match-predictor']) {
      cleanup()
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: 'Match Predictor', level: 2 })).toBeInTheDocument()
      expect(await screen.findByLabelText('Match Predictor active run summary')).toHaveTextContent('phase-1i-run')
      expect(screen.getByText('Player Three')).toBeInTheDocument()
      expect(screen.getAllByText('This preview is not connected for this data shape yet.')).toHaveLength(3)
      expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-1i-run/players')
      expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/phase-1i-run/tournaments')
      expect(screen.queryByText(/%/)).not.toBeInTheDocument()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows conservative active-run Search landing with metadata samples only', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'phase-1i-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-1i-run',
      total: 2,
      limit: 5,
      offset: 0,
      players: [
        { player_id: 'P4', name: 'Searchable Player', country_code: 'DDD', age: 28, source_type: 'planner_generated', override_id: null, quality_band: 'B', is_top_band: false, origin_source_type: 'planner_generated', origin_quality_band: 'B', origin_override_id: null, origin_season: 2030, technique: 75, movement: 76, physical: 77, mental: 78, overall: 79 }
      ]
    })
    api.listRunNations.mockResolvedValue({
      run_id: 'phase-1i-run',
      total: 1,
      limit: 5,
      offset: 0,
      nations: [{ country_code: 'DDD', country_name: 'Delta', total_players: 2, average_overall: 79, average_age: 28, top_band_count: 0, manual_override_count: 0, planner_generated_count: 2, rollover_carried_count: 0, top_player_id: 'P4', top_player_name: 'Searchable Player', top_player_overall: 79 }]
    })
    api.getRun.mockResolvedValue({
      run: { run_id: 'phase-1i-run', season: 2030, seed: 7, next_event_index: 0, total_events: 1, completed_event_ids: [] },
      season_state: {
        season: 2030,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [{ event_id: 'EVT-1', season: 2030, week: 12, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-1' }]
      }
    })

    renderAppAt('/viewer/search')
    expect(await screen.findByRole('heading', { name: 'Search', level: 2 })).toBeInTheDocument()
    const summary = await screen.findByLabelText('Search active run metadata summary')
    expect(summary).toHaveTextContent('phase-1i-run')
    expect(screen.getByLabelText('Read-only Viewer search shell')).toBeInTheDocument()
    expect(screen.getAllByText('This preview is not connected for this data shape yet.').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Searchable Player').length).toBeGreaterThan(0)
    expect(screen.getByText('Delta')).toBeInTheDocument()
    expect(screen.getByText('EVT-1 · W12 · GOLD · WORLD')).toBeInTheDocument()
    expect(screen.queryByText(/Complete search results/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
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
    expect(screen.getByRole('link', { name: 'E3' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar/E3')
    expect(screen.getAllByRole('link', { name: 'W5' }).some((link) => link.getAttribute('href') === '/viewer/runs/run-a/weeks/5')).toBe(true)
    expect(screen.getByRole('link', { name: '#2' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/2')
    expect(screen.getAllByText(/from E2/).length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: '#3' })).toHaveAttribute('href', '/viewer/runs/run-a/race/3')
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByRole('main')).toHaveTextContent('1 activity items · Latest: E1 completed')
    expect(screen.getAllByRole('link', { name: 'E1' }).some((link) => link.getAttribute('href') === '/viewer/runs/run-a/calendar/E1')).toBe(true)
    expect(screen.getByRole('link', { name: 'Open active run history' })).toHaveAttribute('href', '/viewer/runs/run-a/history')
    expect(screen.getAllByText('This preview is not connected for this data shape yet.').length).toBeGreaterThan(0)
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
    expect(screen.getAllByText('No data is available for this run yet.').length).toBeGreaterThan(0)
    expectNoForbiddenViewerActions()
  })

  it('shows top-level rankings snapshot metadata when an active run has ranking snapshots', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'TOURNAMENT', source_event_id: 'E1', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: { standings: { rows: topRankingRows(11) } } }
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
    expect(screen.getByRole('heading', { name: 'Top 10 Ranking Preview' })).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Latest Top 10 ranking preview table' })
    expect(within(table).getByRole('link', { name: 'Nour El Sherbini' })).toHaveAttribute(
      'href',
      '/viewer/runs/run-a/players/P1/career'
    )
    expect(within(table).getByRole('link', { name: 'EG' })).toHaveAttribute('href', '/viewer/runs/run-a/countries/EG')
    expect(within(table).getByText('1000')).toBeInTheDocument()
    expect(within(table).getAllByText('9').length).toBeGreaterThan(0)
    expect(within(table).getAllByText('Previous 2').length).toBeGreaterThan(0)
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    expect(screen.queryByText('Top Player 11')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'View latest ranking snapshot' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/8')
    expectNoForbiddenViewerActions()
  })

  it('shows top-level race snapshot metadata and preview when an active run has parseable race snapshots', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'run-a',
      snapshots: [
        { snapshot_sequence: 2, snapshot_kind: 'TOURNAMENT', source_event_id: 'E1', payload: {} },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: { race_table: { rows: topRaceRows(11) } } }
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
    expect(screen.getByRole('heading', { name: 'Top 10 Race Preview' })).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Latest Top 10 race preview table' })
    expect(within(table).getByRole('link', { name: 'Paul Coll' })).toHaveAttribute(
      'href',
      '/viewer/runs/run-a/players/R1/career'
    )
    expect(within(table).getByRole('link', { name: 'NZ' })).toHaveAttribute('href', '/viewer/runs/run-a/countries/NZ')
    expect(within(table).getByText('7000')).toBeInTheDocument()
    expect(within(table).getAllByText('8').length).toBeGreaterThan(0)
    expect(within(table).getByText('Qualified')).toBeInTheDocument()
    expect(within(table).getByText('1500')).toBeInTheDocument()
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    expect(screen.queryByText('Race Top Player 11')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByRole('link', { name: 'View latest race snapshot' })).toHaveAttribute('href', '/viewer/runs/run-a/race/9')
    expectNoForbiddenViewerActions()
  })

  it('shows top-level rankings and race empty snapshot states for active runs without snapshots', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/rankings')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.queryByRole('link', { name: 'View latest ranking snapshot' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/rankings/race')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.queryByRole('link', { name: 'View latest race snapshot' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows top-level Season Hub metadata when an active Viewer run exists', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      seed: 99,
      progress: { next_event_index: 1, total_events: 4, completed_event_count: 1 },
      finals: { qualification_available: true, result_available: false },
      rollover: null,
      source: { source_type: 'fresh_seed', parent_run_id: null },
      lineage: { child_run_count: 0 },
      history_counts: { events: 1, ranking_snapshots: 0, race_snapshots: 0 }
    })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 1, total_events: 4, completed_event_ids: ['E1'] },
      season_state: {
        season: 2030,
        next_event_index: 1,
        completed_event_ids: ['E1'],
        ordered_events: [
          { event_id: 'E1', season: 2030, week: 2, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' },
          { event_id: 'E2', season: 2030, week: 10, tour: 'WORLD', category: 'DIAMOND', template_id: 'TEMP-B' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [{ event_sequence: 1, event_id: 'E1', season: 2030, week: 2, template_id: 'TEMP-A', tournament_result: {} }] })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2030, qualification: { run_id: 'run-a', season: 2030, source_as_of_season: 2030, source_as_of_week: 40, qualification: {} }, result: null })

    renderAppAt('/viewer/tour')

    expect(await screen.findByRole('heading', { name: 'Season Hub' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('Season Hub active run summary')
    await waitFor(() => expect(panel).toHaveTextContent('run-a'))
    expect(panel).toHaveTextContent('2030')
    expect(panel).toHaveTextContent('1/4 events complete')
    expect(panel).toHaveTextContent('Next event index')
    expect(panel).toHaveTextContent('E2 · W10 · DIAMOND · WORLD · TEMP-B')
    expect(panel).toHaveTextContent('E1 · W2 · GOLD · WORLD · TEMP-A')
    expect(panel).toHaveTextContent('Finals qualification available')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')
    expect(screen.getByRole('link', { name: 'Open active run schedule' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Open active run finals' })).toHaveAttribute('href', '/viewer/runs/run-a/finals')
    expectNoForbiddenViewerActions()
  })

  it('shows active-run Current Week events matching the selected Viewer week', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    localStorage.setItem('beta_engine:viewer_context', JSON.stringify({ selectedSeason: '2004/05', selectedWeek: 24 }))
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 1, total_events: 3, completed_event_ids: [] },
      season_state: {
        season: 2030,
        next_event_index: 1,
        completed_event_ids: [],
        ordered_events: [
          { event_id: 'E9', season: 2030, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-9' },
          { event_id: 'E10', season: 2030, week: 10, tour: 'ELITE', category: 'BRONZE', template_id: 'TEMP-10' },
          { event_id: 'E24', season: 2030, week: 24, tour: 'ELITE', category: 'BRONZE', template_id: 'TEMP-24' }
        ]
      }
    })

    renderAppAt('/viewer/tour/current-week')

    expect(await screen.findByRole('heading', { name: 'Current Week' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('Current Week active run summary')
    expect(panel).toHaveTextContent('Season 2004/05 · W24')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('E24')
    expect(panel).toHaveTextContent('BRONZE')
    expect(panel).toHaveTextContent('ELITE')
    expect(panel).toHaveTextContent('TEMP-24')
    expect(panel).not.toHaveTextContent('E9')
    expect(panel).not.toHaveTextContent('E10')
    expect(screen.getByRole('link', { name: 'Open active run schedule' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expectNoForbiddenViewerActions()
  })

  it.each(['/viewer/tour/tournaments', '/viewer/tournaments'] as const)('shows top-level All Tournaments metadata on %s', async (route) => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 1, total_events: 6, completed_event_ids: ['E1'] },
      season_state: {
        season: 2030,
        next_event_index: 1,
        completed_event_ids: ['E1'],
        ordered_events: [
          { event_id: 'E1', season: 2030, week: 2, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' },
          { event_id: 'E2', season: 2030, week: 10, tour: 'WORLD', category: 'DIAMOND', template_id: 'TEMP-B' },
          { event_id: 'E3', season: 2030, week: 11, tour: 'ELITE', category: 'BRONZE', template_id: 'TEMP-C' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [{ event_sequence: 1, event_id: 'E1', season: 2030, week: 2, template_id: 'TEMP-A', tournament_result: {} }] })

    renderAppAt(route)

    expect(await screen.findByRole('heading', { name: 'All Tournaments' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('All Tournaments active run summary')
    await waitFor(() => expect(panel).toHaveTextContent('run-a'))
    expect(panel).toHaveTextContent('Total ordered calendar events')
    expect(panel).toHaveTextContent('3')
    expect(panel).toHaveTextContent('Persisted event count')
    expect(panel).toHaveTextContent('1')
    expect(panel).toHaveTextContent('E2 · W10 · DIAMOND · WORLD · TEMP-B')
    expect(panel).toHaveTextContent('E1 · W2 · GOLD · WORLD · TEMP-A')
    expect(panel).toHaveTextContent('E3')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')
    expect(screen.getByRole('link', { name: 'Open active run schedule' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expectNoForbiddenViewerActions()
  })

  it('shows active-run top-level tournament and current-week empty states without event metadata', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 0, total_events: 0, completed_event_ids: [] },
      season_state: { season: 2030, next_event_index: 0, completed_event_ids: [], ordered_events: [] }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [] })

    renderAppAt('/viewer/tour/tournaments')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/tour/current-week')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('links top-level History activity, week, tournament, and snapshot metadata safely', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 1, total_events: 3, completed_event_ids: ['E1'] },
      season_state: {
        season: 2030,
        next_event_index: 1,
        completed_event_ids: ['E1'],
        ordered_events: [
          { event_id: 'E1', season: 2030, week: 2, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' },
          { event_id: 'E2', season: 2030, week: 5, tour: 'WORLD', category: 'DIAMOND', template_id: 'TEMP-B' }
        ]
      }
    })
    api.getRunActivity.mockResolvedValue({
      run_id: 'run-a',
      items: [
        { kind: 'event', sequence: 1, label: 'E1 completed', season: 2030, week: 2, event_id: 'E1', snapshot_sequence: null, source_event_id: null, related_run_id: null },
        { kind: 'ranking_snapshot', sequence: 2, label: 'Ranking snapshot stored', season: 2030, week: 2, event_id: 'E1', snapshot_sequence: 4, source_event_id: 'E1', related_run_id: null }
      ]
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      seed: 99,
      progress: { next_event_index: 1, total_events: 4, completed_event_count: 1 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 1, ranking_snapshots: 2, race_snapshots: 1 }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [{ event_sequence: 1, event_id: 'E1', season: 2030, week: 2, template_id: 'TEMP-A', tournament_result: {} }] })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'ranking', source_event_id: 'E1', payload: {} }, { snapshot_sequence: 3, snapshot_kind: 'ranking', source_event_id: 'E0', payload: {} }] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [{ snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'E1', payload: {} }] })

    renderAppAt('/viewer/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('History active run metadata summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Activity item count')
    expect(panel).toHaveTextContent('2')
    expect(panel).toHaveTextContent('Ranking snapshot stored · Season 2030')
    expect(within(panel).getAllByRole('link', { name: 'E1' }).some((link) => link.getAttribute('href') === '/viewer/runs/run-a/calendar/E1')).toBe(true)
    expect(within(panel).getAllByRole('link', { name: 'W2' }).some((link) => link.getAttribute('href') === '/viewer/runs/run-a/weeks/2')).toBe(true)
    expect(within(panel).getByRole('link', { name: 'Tournament detail E1' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments/E1')
    expect(within(panel).getByRole('link', { name: 'Ranking snapshot #4' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/4')
    expect(within(panel).getByRole('link', { name: '#4' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/4')
    expect(within(panel).getByRole('link', { name: '#5' })).toHaveAttribute('href', '/viewer/runs/run-a/race/5')
    expect(panel).toHaveTextContent('Event count')
    expect(panel).toHaveTextContent('1')
    expect(screen.getByRole('link', { name: 'Open active run history' })).toHaveAttribute('href', '/viewer/runs/run-a/history')
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps unmatched History activity event IDs as plain text without broken detail links', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRunActivity.mockResolvedValue({
      run_id: 'run-a',
      items: [{ kind: 'event', sequence: 1, label: 'Missing event noted', season: 2030, week: 7, event_id: 'MISSING-EVENT', snapshot_sequence: null, source_event_id: null, related_run_id: null }]
    })

    renderAppAt('/viewer/history')

    const panel = await screen.findByLabelText('History active run metadata summary')
    await waitFor(() => expect(panel).toHaveTextContent('Missing event noted · Season 2030 · W7 · MISSING-EVENT'))
    expect(within(panel).queryByRole('link', { name: 'MISSING-EVENT' })).not.toBeInTheDocument()
    expect(within(panel).queryByRole('link', { name: 'W7' })).not.toBeInTheDocument()
    expect(within(panel).queryByRole('link', { name: 'Tournament detail MISSING-EVENT' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows active-run Records and Stats metadata with deferred groups and safe links', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      seed: 99,
      progress: { next_event_index: 2, total_events: 4, completed_event_count: 2 },
      finals: { qualification_available: true, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 2, ranking_snapshots: 3, race_snapshots: 2 }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [
      { event_sequence: 1, event_id: 'E1', season: 2030, week: 2, template_id: 'TEMP-A', tournament_result: {} },
      { event_sequence: 2, event_id: 'E2', season: 2030, week: 5, template_id: 'TEMP-B', tournament_result: {} }
    ] })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 1, snapshot_kind: 'ranking', source_event_id: 'E1', payload: {} },
      { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'E2', payload: {} },
      { snapshot_sequence: 3, snapshot_kind: 'ranking', source_event_id: 'E2', payload: {} }
    ] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'run-a', snapshots: [
      { snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'E1', payload: {} },
      { snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'E2', payload: {} }
    ] })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2030, qualification: { run_id: 'run-a', season: 2030, source_as_of_season: 2030, source_as_of_week: 40, qualification: {} }, result: null })

    renderAppAt('/viewer/records')
    expect(await screen.findByRole('heading', { name: 'Records' })).toBeInTheDocument()
    let panel = await screen.findByLabelText('Records active run metadata summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Completed/persisted event count')
    expect(panel).toHaveTextContent('2')
    expect(panel).toHaveTextContent('Ranking snapshot count')
    expect(panel).toHaveTextContent('3')
    expect(panel).toHaveTextContent('Race snapshot count')
    expect(panel).toHaveTextContent('Finals qualification available')
    expect(panel).toHaveTextContent('Title Leaders: needs dedicated records read model.')
    expect(panel).toHaveTextContent('Weeks at No.1: needs dedicated records read model.')
    expect(panel).toHaveTextContent('Biggest Upsets: needs match/prediction read model.')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByRole('link', { name: 'Open active run finals' })).toHaveAttribute('href', '/viewer/runs/run-a/finals')
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/stats')
    expect(await screen.findByRole('heading', { name: 'Stats' })).toBeInTheDocument()
    panel = await screen.findByLabelText('Stats active run metadata summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Completed/persisted event count')
    expect(panel).toHaveTextContent('2')
    expect(panel).toHaveTextContent('Player Stats: needs dedicated player statistics read model.')
    expect(panel).toHaveTextContent('Tournament Stats: needs dedicated tournament statistics read model.')
    expect(panel).toHaveTextContent('Era Rankings: needs dedicated era comparison read model.')
    expectNoForbiddenViewerActions()
  })

  it('shows active-run History Records and Stats empty metadata states without fake leaders', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/history')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(within(screen.getByRole('main')).queryByText(/Most title leader/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/records')
    expect((await screen.findAllByText('This preview is not connected for this data shape yet.')).length).toBeGreaterThan(0)
    expect(screen.getByRole('main')).toHaveTextContent('Title Leaders: needs dedicated records read model.')
    expect(within(screen.getByRole('main')).queryByText('Most titles')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/stats')
    expect((await screen.findAllByText('This preview is not connected for this data shape yet.')).length).toBeGreaterThan(0)
    expect(screen.getByRole('main')).toHaveTextContent('Player Stats: needs dedicated player statistics read model.')
    expect(within(screen.getByRole('main')).queryByText('GOAT')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows active-run top-level Players metadata without redirecting to the run-scoped page', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run-a',
      total: 8,
      limit: 5,
      offset: 0,
      players: [
        {
          player_id: 'EGY-0001',
          name: 'Ali Farag',
          country_code: 'EGY',
          age: 30,
          source_type: 'planner_generated',
          override_id: null,
          quality_band: 'elite_talent',
          is_top_band: true,
          origin_source_type: 'planner_generated',
          origin_quality_band: 'elite_talent',
          origin_override_id: null,
          origin_season: 2030,
          technique: 92,
          movement: 91,
          physical: 88,
          mental: 90,
          overall: 91
        }
      ]
    })

    renderAppAt('/viewer/players')

    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(screen.queryByText('Player filters')).not.toBeInTheDocument()
    const panel = await screen.findByLabelText('Players active run summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Total player count')
    expect(panel).toHaveTextContent('8')
    expect(panel).toHaveTextContent('Returned player count')
    expect(panel).toHaveTextContent('1')
    expect(panel).toHaveTextContent('Ali Farag')
    expect(panel).toHaveTextContent('EGY-0001')
    expect(panel).toHaveTextContent('EGY')
    expect(panel).toHaveTextContent('30')
    expect(panel).toHaveTextContent('Power Rating')
    expect(panel).toHaveTextContent('91')
    expect(within(panel).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/run-a/players/EGY-0001/career')
    expect(within(panel).getByRole('link', { name: 'EGY-0001' })).toHaveAttribute('href', '/viewer/runs/run-a/players/EGY-0001/career')
    expect(within(panel).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/run-a/countries/EGY')
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/run-a/players')
    expect(api.listRunPlayers).toHaveBeenCalledWith('run-a', { limit: 5, offset: 0 })
    expectNoForbiddenViewerActions()
  })

  it('shows active-run top-level Countries metadata without redirecting to the run-scoped page', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRunNations.mockResolvedValue({
      run_id: 'run-a',
      total: 4,
      limit: 5,
      offset: 0,
      nations: [
        {
          country_code: 'EGY',
          country_name: 'Egypt',
          total_players: 12,
          average_overall: 78.4,
          average_age: 25.2,
          top_band_count: 3,
          manual_override_count: 1,
          planner_generated_count: 10,
          rollover_carried_count: 1,
          top_player_id: 'EGY-0001',
          top_player_name: 'Ali Farag',
          top_player_overall: 91
        }
      ]
    })

    renderAppAt('/viewer/countries')

    expect(await screen.findByRole('heading', { name: 'Countries' })).toBeInTheDocument()
    expect(screen.queryByText('Country filters')).not.toBeInTheDocument()
    const panel = await screen.findByLabelText('Countries active run summary')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('Total country count')
    expect(panel).toHaveTextContent('4')
    expect(panel).toHaveTextContent('Returned country count')
    expect(panel).toHaveTextContent('1')
    expect(panel).toHaveTextContent('EGY')
    expect(panel).toHaveTextContent('Egypt')
    expect(panel).toHaveTextContent('12')
    expect(panel).toHaveTextContent('78.4')
    expect(panel).toHaveTextContent('Ali Farag')
    expect(panel).toHaveTextContent('91')
    expect(within(panel).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/run-a/countries/EGY')
    expect(within(panel).getByRole('link', { name: 'Egypt' })).toHaveAttribute('href', '/viewer/runs/run-a/countries/EGY')
    expect(within(panel).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/run-a/players/EGY-0001/career')
    expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/run-a/countries')
    expect(api.listRunNations).toHaveBeenCalledWith('run-a', { limit: 5, offset: 0 })
    expectNoForbiddenViewerActions()
  })


  it('keeps top-level sample player and country fields as plain text when IDs are missing', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run-a',
      total: 1,
      limit: 5,
      offset: 0,
      players: [
        {
          player_id: '',
          name: 'Mystery Player',
          country_code: '',
          age: 22,
          source_type: 'planner_generated',
          override_id: null,
          quality_band: 'prospect',
          is_top_band: false,
          origin_source_type: 'planner_generated',
          origin_quality_band: 'prospect',
          origin_override_id: null,
          origin_season: 2030,
          technique: 70,
          movement: 71,
          physical: 72,
          mental: 73,
          overall: 74
        }
      ]
    })

    renderAppAt('/viewer/players')

    const playersPanel = await screen.findByLabelText('Players active run summary')
    await waitFor(() => expect(playersPanel).toHaveTextContent('Mystery Player'))
    expect(within(playersPanel).queryByRole('link', { name: 'Mystery Player' })).not.toBeInTheDocument()
    expect(within(playersPanel).queryByRole('link', { name: '—' })).not.toBeInTheDocument()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.listRunNations.mockResolvedValue({
      run_id: 'run-a',
      total: 1,
      limit: 5,
      offset: 0,
      nations: [
        {
          country_code: '',
          country_name: 'Unknown Country',
          total_players: 1,
          average_overall: 74,
          average_age: 22,
          top_band_count: 0,
          manual_override_count: 0,
          planner_generated_count: 1,
          rollover_carried_count: 0,
          top_player_id: null,
          top_player_name: 'Mystery Player',
          top_player_overall: 74
        }
      ]
    })

    renderAppAt('/viewer/countries')

    const countriesPanel = await screen.findByLabelText('Countries active run summary')
    await waitFor(() => expect(countriesPanel).toHaveTextContent('Unknown Country'))
    expect(countriesPanel).toHaveTextContent('Mystery Player')
    expect(within(countriesPanel).queryByRole('link', { name: 'Unknown Country' })).not.toBeInTheDocument()
    expect(within(countriesPanel).queryByRole('link', { name: 'Mystery Player' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows empty states on active-run top-level Players and Countries hubs without metadata', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/players')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/run-a/players')
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/countries')
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/run-a/countries')
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer ranking and race snapshot pages', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/runs/run-a/rankings')
    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/runs/run-a/race')
    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('offers the active run calendar link while preserving the top-level calendar Jump to Week primitive', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/tour/calendar')

    expect(await screen.findByRole('button', { name: 'Jump to W24' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run schedule' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
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

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Season timeline' })).toBeInTheDocument()
    expect(await screen.findByRole('list', { name: 'Viewer season calendar events' })).toHaveTextContent('E1')
    expect(screen.queryByText('This section uses existing read-only run data only.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Jump to W24' })).not.toBeInTheDocument()
  })

  it('preserves the real run-scoped Viewer tournaments/events page', async () => {
    renderAppAt('/viewer/runs/run-a/tournaments')

    expect(await screen.findByText('Tournaments', { selector: 'h2' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only tournament schedule and results for the selected run/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer players page', async () => {
    renderAppAt('/viewer/runs/run-a/players')

    expect(await screen.findByRole('heading', { name: 'Players', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('Read-only player profiles for the selected run.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer countries/nations page', async () => {
    renderAppAt('/viewer/runs/run-a/countries')

    expect(await screen.findByRole('heading', { name: 'Countries', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('Read-only country strength overview for the selected run.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer history/activity page', async () => {
    renderAppAt('/viewer/runs/run-a/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByText(/Read-only run activity and season timeline/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders sports-facing Viewer Finals summary from existing Finals summary data only', async () => {
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      qualification: {
        run_id: 'run-a',
        season: 2030,
        source_as_of_season: 2030,
        source_as_of_week: 40,
        qualification: {
          qualified_player_ids: ['P1', 'P2'],
          ranking_snapshot_sequence: 4,
          race_snapshot_sequence: 5,
          cutoff_points: 1200,
          qualification_locked: true
        }
      },
      result: {
        run_id: 'run-a',
        season: 2030,
        event_id: 'E1',
        source_as_of_season: 2030,
        source_as_of_week: 61,
        result: {
          champion_player_id: 'P1',
          runner_up_player_id: 'P2',
          completed_matches_count: 15,
          result_status: 'complete'
        }
      }
    })

    renderAppAt('/viewer/runs/run-a/finals')

    expect(await screen.findByRole('heading', { name: 'Finals Summary' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Finals Summary' }).closest('article')).toHaveTextContent('Active run IDrun-a'))
    const summary = screen.getByRole('heading', { name: 'Finals Summary' }).closest('article')
    expect(summary).toHaveTextContent('Qualification availabilityAvailable')
    expect(summary).toHaveTextContent('Result availabilityAvailable')
    expect(summary).toHaveTextContent('Season2030')
    expect(summary).toHaveTextContent('Source event IDE1')
    expect(summary).toHaveTextContent('Qualification Qualified Player Ids count2')

    const qualification = screen.getByRole('heading', { name: 'Qualification' }).closest('article')
    expect(qualification).toHaveTextContent('Source weekW40')
    expect(qualification).toHaveTextContent('Qualified Player Ids count2')
    expect(qualification).toHaveTextContent('Cutoff Points1200')
    expect(qualification).toHaveTextContent('Qualification LockedYes')
    expect(within(qualification as HTMLElement).getByRole('link', { name: 'Player P1 profile' })).toHaveAttribute('href', '/viewer/runs/run-a/players/P1/career')
    expect(within(qualification as HTMLElement).getByRole('link', { name: 'Ranking snapshot 4' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/4')
    expect(within(qualification as HTMLElement).getByRole('link', { name: 'Race snapshot 5' })).toHaveAttribute('href', '/viewer/runs/run-a/race/5')

    const result = screen.getByRole('heading', { name: 'Result' }).closest('article')
    expect(result).toHaveTextContent('Source weekW61')
    expect(result).toHaveTextContent('Completed Matches Count15')
    expect(result).toHaveTextContent('Result Statuscomplete')
    expect(within(result as HTMLElement).getAllByRole('link', { name: 'Player Profile' })[0]).toHaveAttribute('href', '/viewer/runs/run-a/players/P1/career')
    expect(within(result as HTMLElement).getByRole('link', { name: 'E1' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar/E1')

    expect(screen.getByRole('link', { name: 'Back to Season Hub' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Open rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'Open race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByRole('link', { name: 'Open tournaments' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')

    const technical = screen.getByText('Show technical finals data').closest('details')
    expect(technical).not.toHaveAttribute('open')
    expect(screen.queryByText(/Finals bracket/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/6-11, 11-8/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders Viewer Finals qualification subpage metadata, links, and collapsed technical data', async () => {
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      source_as_of_season: 2030,
      source_as_of_week: 40,
      qualification: {
        qualified_player_ids: ['P1', 'P2'],
        groups: [{ group_id: 'A' }, { group_id: 'B' }],
        ranking_snapshot_sequence: 4,
        race_snapshot_sequence: 5,
        cutoff_points: 1200,
        race_cutoff_rank: 8,
        unrelated_payload: { hidden: 'not shown' }
      }
    })

    renderAppAt('/viewer/runs/run-a/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Qualification Summary' }).closest('article')
    await waitFor(() => expect(summary).toHaveTextContent('Active run IDrun-a'))
    expect(summary).toHaveTextContent('Season2030')
    expect(summary).toHaveTextContent('Source season2030')
    expect(summary).toHaveTextContent('Source weekW40')
    expect(summary).toHaveTextContent('Qualification availabilityAvailable')
    expect(summary).toHaveTextContent('Qualified player count2')
    expect(summary).toHaveTextContent('Group count2')
    expect(summary).toHaveTextContent('Cutoff Points1200')
    expect(summary).toHaveTextContent('Race Cutoff Rank8')
    expect(summary).not.toHaveTextContent('hidden')
    expect(within(summary as HTMLElement).getByRole('link', { name: 'Ranking snapshot 4' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings/4')
    expect(within(summary as HTMLElement).getByRole('link', { name: 'Race snapshot 5' })).toHaveAttribute('href', '/viewer/runs/run-a/race/5')

    const players = screen.getByRole('heading', { name: 'Qualified Players / Links' }).closest('article')
    expect(within(players as HTMLElement).getByRole('link', { name: 'Player P1 profile' })).toHaveAttribute('href', '/viewer/runs/run-a/players/P1/career')
    expect(within(players as HTMLElement).getByRole('link', { name: 'Player P2 profile' })).toHaveAttribute('href', '/viewer/runs/run-a/players/P2/career')
    expect(screen.getByRole('link', { name: 'Back to Finals Summary' })).toHaveAttribute('href', '/viewer/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'Open rankings' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.getByRole('link', { name: 'Open race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.getByRole('link', { name: 'Open tournaments' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')
    expect(screen.getByText('Show technical finals qualification data').closest('details')).not.toHaveAttribute('open')
    expectNoForbiddenViewerActions()
  })

  it('shows deferred state for missing or unrecognized Viewer Finals qualification data', async () => {
    api.getFinalsQualification.mockResolvedValue({ run_id: 'run-a', season: 2030, source_as_of_season: 2030, source_as_of_week: 40, qualification: { nested_unknown: { value: 1 } } })

    renderAppAt('/viewer/runs/run-a/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Qualification Summary' }).closest('article')).toHaveTextContent('This preview is not connected for this data shape yet.'))
    expect(screen.getByText('Show technical finals qualification data').closest('details')).not.toHaveAttribute('open')
    expectNoForbiddenViewerActions()
  })

  it('renders Viewer Finals result subpage metadata, player/source links, and collapsed technical data', async () => {
    api.getFinalsResult.mockResolvedValue({
      run_id: 'run-a',
      season: 2030,
      event_id: 'E1',
      source_as_of_season: 2030,
      source_as_of_week: 61,
      result: {
        champion_player_id: 'P1',
        runner_up_player_id: 'P2',
        completed_matches_count: 15,
        result_status: 'complete',
        court_note: 'show court one'
      }
    })

    renderAppAt('/viewer/runs/run-a/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals Result' })).toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Result Summary' }).closest('article')
    await waitFor(() => expect(summary).toHaveTextContent('Active run IDrun-a'))
    expect(summary).toHaveTextContent('Season2030')
    expect(summary).toHaveTextContent('Source event IDE1')
    expect(summary).toHaveTextContent('Source season2030')
    expect(summary).toHaveTextContent('Source weekW61')
    expect(summary).toHaveTextContent('Completed Matches Count15')
    expect(summary).toHaveTextContent('Result Statuscomplete')
    expect(summary).toHaveTextContent('Champion Player IdP1')
    expect(summary).toHaveTextContent('Runner Up Player IdP2')
    expect(within(summary as HTMLElement).getByRole('link', { name: 'E1' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar/E1')

    const players = screen.getByRole('heading', { name: 'Player Links' }).closest('article')
    expect(within(players as HTMLElement).getByRole('link', { name: 'Player P1 profile' })).toHaveAttribute('href', '/viewer/runs/run-a/players/P1/career')
    expect(within(players as HTMLElement).getByRole('link', { name: 'Player P2 profile' })).toHaveAttribute('href', '/viewer/runs/run-a/players/P2/career')
    const sources = screen.getByRole('heading', { name: 'Source Links' }).closest('article')
    expect(within(sources as HTMLElement).getByRole('link', { name: 'Planned event E1' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar/E1')
    expect(within(sources as HTMLElement).getByRole('link', { name: 'Tournament detail E1' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments/E1')
    expect(screen.getByRole('link', { name: 'Back to Finals Summary' })).toHaveAttribute('href', '/viewer/runs/run-a/finals')
    expect(screen.getByText('Show technical finals result data').closest('details')).not.toHaveAttribute('open')
    expect(screen.queryByText(/Finals bracket/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/6-11, 11-8/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows deferred state for missing or unrecognized Viewer Finals result data', async () => {
    api.getFinalsResult.mockResolvedValue({ run_id: 'run-a', season: 2030, event_id: 'E1', source_as_of_season: 2030, source_as_of_week: 61, result: { nested_unknown: { value: 1 } } })

    renderAppAt('/viewer/runs/run-a/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals Result' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Result Summary' }).closest('article')).toHaveTextContent('This preview is not connected for this data shape yet.'))
    expect(screen.getByText('Show technical finals result data').closest('details')).not.toHaveAttribute('open')
    expectNoForbiddenViewerActions()
  })

  it('shows deferred states when Viewer Finals qualification and result data are missing', async () => {
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2030, qualification: null, result: null })

    renderAppAt('/viewer/runs/run-a/finals')

    expect(await screen.findByRole('heading', { name: 'Finals Summary' })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Qualification' }).closest('article')).toHaveTextContent('This preview is not connected for this data shape yet.'))
    expect(screen.getByRole('heading', { name: 'Result' }).closest('article')).toHaveTextContent('This preview is not connected for this data shape yet.')
    expect(screen.queryByText(/Finals bracket/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/winner/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/runner-up/i)).not.toBeInTheDocument()
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

  it('renders all required Viewer Phase 1K top-level and run-scoped routes without forbidden Viewer actions', async () => {
    const requiredViewerRoutes = [
      '/viewer',
      '/viewer/rankings',
      '/viewer/rankings/race',
      '/viewer/rankings/next-gen',
      '/viewer/rankings/elo',
      '/viewer/rankings/power',
      '/viewer/rankings/form',
      '/viewer/countries/ranking',
      '/viewer/rankings/no1-history',
      '/viewer/tour',
      '/viewer/tour/calendar',
      '/viewer/tour/current-week',
      '/viewer/tour/tournaments',
      '/viewer/tour/matches',
      '/viewer/tour/categories',
      '/viewer/tour/champions',
      '/viewer/tournaments',
      '/viewer/players',
      '/viewer/players/all',
      '/viewer/players/active',
      '/viewer/players/next-gen',
      '/viewer/players/retired',
      '/viewer/players/compare',
      '/viewer/countries',
      '/viewer/countries/all',
      '/viewer/countries/hosting',
      '/viewer/countries/talent-pipeline',
      '/viewer/countries/records',
      '/viewer/h2h',
      '/viewer/h2h/rivalries',
      '/viewer/h2h/most-played',
      '/viewer/h2h/finals-rivalries',
      '/viewer/stats',
      '/viewer/stats/title-leaders',
      '/viewer/stats/no1-weeks',
      '/viewer/stats/streaks',
      '/viewer/stats/upsets',
      '/viewer/stats/best-seasons',
      '/viewer/stats/player-stats',
      '/viewer/stats/tournament-stats',
      '/viewer/stats/country-stats',
      '/viewer/stats/awards',
      '/viewer/stats/hall-of-fame',
      '/viewer/stats/era-rankings',
      '/viewer/records',
      '/viewer/predictions',
      '/viewer/predictions/match-predictor',
      '/viewer/predictions/match-odds',
      '/viewer/predictions/tournament-odds',
      '/viewer/predictions/finals-qualification',
      '/viewer/predictions/season-end-no1',
      '/viewer/predictions/upset-watch',
      '/viewer/predictions/futures',
      '/viewer/search',
      '/viewer/runs/run-a/rankings',
      '/viewer/runs/run-a/rankings/4',
      '/viewer/runs/run-a/race',
      '/viewer/runs/run-a/race/5',
      '/viewer/runs/run-a/tournaments',
      '/viewer/runs/run-a/tournaments/E1',
      '/viewer/runs/run-a/calendar',
      '/viewer/runs/run-a/calendar/E1',
      '/viewer/runs/run-a/weeks/2',
      '/viewer/runs/run-a/players',
      '/viewer/runs/run-a/players/P1/career',
      '/viewer/runs/run-a/countries',
      '/viewer/runs/run-a/history',
      '/viewer/runs/run-a/finals',
      '/viewer/runs/run-a/finals/qualification',
      '/viewer/runs/run-a/finals/result'
    ]

    for (const route of requiredViewerRoutes) {
      cleanup()
      resetApiMocks()
      renderAppAt(route)
      expect(await screen.findByTestId('viewer-primary-nav')).toBeInTheDocument()
      expect(screen.getByRole('main')).not.toHaveTextContent('Choose your mode')
      expect(screen.getByRole('button', { name: 'Season 2004/05 · W10' })).toBeInTheDocument()
      expectNoForbiddenViewerActions()
    }
  }, 20000)

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
