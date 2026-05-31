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
      ['/viewer/tour', 'Season Hub needs a selected Viewer run.'],
      ['/viewer/tour/current-week', 'Current Week needs a selected Viewer run.'],
      ['/viewer/tour/tournaments', 'Tournament archive needs a selected Viewer run.'],
      ['/viewer/tournaments', 'Tournament archive needs a selected Viewer run.'],
      ['/viewer/players', 'Select a Viewer run to view MSA Players.'],
      ['/viewer/countries', 'Select a Viewer run to view MSA Countries.'],
      ['/viewer/history', 'Select a Viewer run to view MSA History.'],
      ['/viewer/records', 'Records need connected active-run data and dedicated read models before record tables can be shown.'],
      ['/viewer/stats', 'Stats need connected active-run data and dedicated read models before leaderboards can be shown.'],
      ['/viewer/h2h', 'H2H needs a selected Viewer run and match history read model.'],
      ['/viewer/predictions', 'Predictions need connected active-run data and a deterministic prediction read model.'],
      ['/viewer/predictions/match-predictor', 'Predictions need connected active-run data and a deterministic prediction read model.'],
      ['/viewer/search', 'Search needs a selected Viewer run or connected global search index.']
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
    expect(screen.getByText('Active run calendar is unavailable until a Viewer run is selected.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open active run calendar' })).not.toBeInTheDocument()
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
    expect(screen.getByText('Direct H2H records need a match history read model.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-1i-run/players')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/phase-1i-run/tournaments')
    expect(screen.queryByText(/wins/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/h2h/rivalries')
    expect(await screen.findByText('Real rivalry rankings require a match-history read model.')).toBeInTheDocument()
    expect(screen.getByText('No rivalry list is shown until direct match records are available.')).toBeInTheDocument()
    expect(screen.getAllByText('phase-1i-run').length).toBeGreaterThan(0)
    expect(screen.queryByText(/Top rivalry/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/h2h/most-played')
    expect(await screen.findByText('Most-played matchups require a match-history read model.')).toBeInTheDocument()
    expect(screen.getByText('No matchup list is shown until completed match counts are available.')).toBeInTheDocument()
    expect(screen.queryByText(/matchup record/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/h2h/finals-rivalries')
    expect(await screen.findByText('Finals rivalries require a match-history read model with final-round context.')).toBeInTheDocument()
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
      expect(screen.getByText('Win probabilities are not connected yet.')).toBeInTheDocument()
      expect(screen.getByText('Fair odds are not connected yet.')).toBeInTheDocument()
      expect(screen.getByText('Bookmaker margin model is not connected yet.')).toBeInTheDocument()
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
    expect(screen.getByText('Global search index is not connected yet.')).toBeInTheDocument()
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
    expect(screen.getByRole('link', { name: 'Open active run calendar' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Open active run finals' })).toHaveAttribute('href', '/viewer/runs/run-a/finals')
    expectNoForbiddenViewerActions()
  })

  it('shows active-run Current Week events matching the selected Viewer week', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2030, seed: 99, next_event_index: 1, total_events: 3, completed_event_ids: [] },
      season_state: {
        season: 2030,
        next_event_index: 1,
        completed_event_ids: [],
        ordered_events: [
          { event_id: 'E9', season: 2030, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-9' },
          { event_id: 'E10', season: 2030, week: 10, tour: 'ELITE', category: 'BRONZE', template_id: 'TEMP-10' }
        ]
      }
    })

    renderAppAt('/viewer/tour/current-week')

    expect(await screen.findByRole('heading', { name: 'Current Week' })).toBeInTheDocument()
    const panel = await screen.findByLabelText('Current Week active run summary')
    expect(panel).toHaveTextContent('Season 2004/05 · W10')
    expect(panel).toHaveTextContent('run-a')
    expect(panel).toHaveTextContent('E10')
    expect(panel).toHaveTextContent('BRONZE')
    expect(panel).toHaveTextContent('ELITE')
    expect(panel).toHaveTextContent('TEMP-10')
    expect(panel).not.toHaveTextContent('E9')
    expect(screen.getByRole('link', { name: 'Open active run calendar' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
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
    expect(screen.getByRole('link', { name: 'Open active run calendar' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
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
    expect(await screen.findByText('No tournament metadata is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/tour/current-week')
    expect(await screen.findByText('No events are available for the selected Viewer week.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows top-level History metadata without redirecting to the run-scoped page', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    api.getRunActivity.mockResolvedValue({
      run_id: 'run-a',
      items: [
        { kind: 'event', sequence: 1, label: 'E1 completed', season: 2030, week: 2, event_id: 'E1', snapshot_sequence: null, source_event_id: null, related_run_id: null },
        { kind: 'ranking_snapshot', sequence: 2, label: 'Ranking snapshot stored', season: 2030, week: 2, event_id: null, snapshot_sequence: 4, source_event_id: 'E1', related_run_id: null }
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
    expect(panel).toHaveTextContent('Ranking snapshot stored · Season 2030 · W2')
    expect(panel).toHaveTextContent('Event count')
    expect(panel).toHaveTextContent('1')
    expect(panel).toHaveTextContent('Ranking snapshot count')
    expect(panel).toHaveTextContent('Race snapshot count')
    expect(screen.getByRole('link', { name: 'Open active run history' })).toHaveAttribute('href', '/viewer/runs/run-a/history')
    expect(screen.queryByRole('navigation', { name: 'Viewer active run quick links' })).not.toBeInTheDocument()
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
    expect(await screen.findByText('No activity metadata is available for this run yet.')).toBeInTheDocument()
    expect(within(screen.getByRole('main')).queryByText(/Most title leader/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/records')
    expect(await screen.findByText('No record or statistical leaders are shown here until dedicated read models exist.')).toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveTextContent('Title Leaders: needs dedicated records read model.')
    expect(within(screen.getByRole('main')).queryByText('Most titles')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/stats')
    expect(await screen.findByText('No record or statistical leaders are shown here until dedicated read models exist.')).toBeInTheDocument()
    expect(screen.getByRole('main')).toHaveTextContent('Player Stats: needs dedicated player statistics read model.')
    expect(within(screen.getByRole('main')).queryByText('GOAT')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows active-run top-level Players Hub metadata without redirecting to the run-scoped page', async () => {
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

    expect(await screen.findByRole('heading', { name: 'Players Hub' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Run Players Explorer' })).not.toBeInTheDocument()
    const panel = await screen.findByLabelText('Players Hub active run summary')
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
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/run-a/players')
    expect(api.listRunPlayers).toHaveBeenCalledWith('run-a', { limit: 5, offset: 0 })
    expectNoForbiddenViewerActions()
  })

  it('shows active-run top-level Countries Hub metadata without redirecting to the run-scoped page', async () => {
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

    expect(await screen.findByRole('heading', { name: 'Countries Hub' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Run Nations Dashboard' })).not.toBeInTheDocument()
    const panel = await screen.findByLabelText('Countries Hub active run summary')
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
    expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/run-a/countries')
    expect(api.listRunNations).toHaveBeenCalledWith('run-a', { limit: 5, offset: 0 })
    expectNoForbiddenViewerActions()
  })

  it('shows empty states on active-run top-level Players and Countries hubs without metadata', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')

    renderAppAt('/viewer/players')
    expect(await screen.findByText('No player metadata is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/run-a/players')
    expectNoForbiddenViewerActions()

    cleanup()
    localStorage.setItem('beta_engine:viewer_active_run_id', 'run-a')
    renderAppAt('/viewer/countries')
    expect(await screen.findByText('No country metadata is available for this run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/run-a/countries')
    expectNoForbiddenViewerActions()
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
