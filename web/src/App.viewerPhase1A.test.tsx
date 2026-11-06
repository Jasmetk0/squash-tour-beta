import appSource from './App.tsx?raw'
import { viewerAppRoutePaths } from './test/viewerAppRouteSource'
import layoutSource from './components/Layout.tsx?raw'
import viewerRunSelectorSource from './components/ViewerRunSelector.tsx?raw'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import type { ViewerPlayers, ViewerPlayer, ViewerCountries, ViewerCountry } from './api/types'
import { calendarEvent, historyEvent, savedCalendar, savedHistory, savedRankings, savedRace, rankingPublication, racePublication } from './test/viewerCalendarFixtures'
import { getModeSwitcherTarget } from './viewer/modeSwitcherRoutes'
import { viewerDropdowns } from './viewer/viewerNavigation'
import {
  viewerCountriesPath,
  viewerCountryProfilePath,
  viewerFinalsPath,
  viewerFinalsQualificationPath,
  viewerFinalsResultPath,
  viewerHistoryPath,
  viewerHomePath,
  viewerPlayerProfilePath,
  viewerPlayersPath,
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTopCountriesPath,
  viewerTopCountryRankingPath,
  viewerTopH2HPath,
  viewerTopHistoryPath,
  viewerTopPlayersPath,
  viewerTopPredictionsPath,
  viewerTopRacePath,
  viewerTopRankingsPath,
  viewerTopRecordsPath,
  viewerTopSearchPath,
  viewerTopStatsPath,
  viewerTopTourCalendarPath,
  viewerTopTourCurrentWeekPath,
  viewerTopTourPath,
  viewerTopTournamentsPath,
  viewerTopTourTournamentsPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
  viewerWeekDetailPath
} from './viewer/viewerRoutes'

const api = vi.hoisted(() => ({
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listRuns: vi.fn(),
  listRunContainers: vi.fn(),
  getViewerOfficialRunContext: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerPlayers: vi.fn(),
  getViewerCountries: vi.fn(),
  getViewerVisibleProspects: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getViewerOfficialRanking: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerTournamentResult: vi.fn(),
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
  api.listRunContainers.mockImplementation(async () => {
    const response = await api.listRuns()
    return {
      run_containers: (response?.runs ?? []).map((run: Record<string, unknown>) => ({
        run_id: String(run.run_id ?? ''),
        display_name: `${String(run.run_id ?? '')} — season ${String(run.season ?? '—')}, seed ${String(run.seed ?? '—')}`,
        storage_kind: 'custom_local',
        read_only: false,
        world_id: 'test-world',
        world_package_fingerprint: null,
        config_version: null,
        config_fingerprint: null,
        global_seed: typeof run.seed === 'number' ? run.seed : 0,
        timeline_start_season: typeof run.season === 'number' ? run.season : 2000,
        timeline_end_season: typeof run.season === 'number' ? run.season : 2049,
        viewer_branch_id: 'viewer',
        official_branch_id: `${String(run.run_id ?? '')}-official`,
        status: 'active',
        metadata_json: {},
        mapped_simulation_run_count: 1
      }))
    }
  })
  api.getViewerOfficialRunContext.mockImplementation(async (productRunId: string) => ({
    product_run_id: productRunId,
    product_run_display_name: productRunId,
    product_run_status: 'active',
    product_run_storage_kind: 'custom_local',
    product_run_read_only: false,
    official_branch_id: `${productRunId}-official`,
    official_branch_display_name: 'Official',
    official_branch_status: 'active',
    official_branch_read_only: false,
    official_branch_seed: 7,
    legacy_simulation_run_id: productRunId,
    head_checkpoint_id: 'checkpoint',
    head_checkpoint_kind: 'week',
    current_season: 2029,
    current_week: 1,
    current_event_id: null,
    current_event_sequence: null,
    resolution_version: 'viewer_official_branch_v1'
  }))
  api.getViewerRunCalendar.mockImplementation(async (run: string) => ({
    ...savedCalendar([calendarEvent({ event_id: 'E1', event_name: 'Canonical Event E1', season: '2029/30', season_week: 2 })], run),
    viewer_branch_id: `${run}-official`,
  }))
  api.getViewerPlayers.mockImplementation(async (run: string) => publicRoster(run))
  api.getViewerCountries.mockImplementation(async (run: string) => publicCountries(run))
  api.getViewerVisibleProspects.mockResolvedValue({
    schema_version: 'visible_pre_tour_prospects.v1',
    run_id: 'run-a',
    branch_id: 'run-a-official',
    week: { season_index: 29, week: 1 },
    lifecycle_fingerprint: 'a'.repeat(64),
    total: 0,
    limit: 50,
    offset: 0,
    prospects: []
  })
  api.getViewerRankingTable.mockRejectedValue(new Error('Viewer read model unavailable in test'))
  api.getViewerOfficialRanking.mockImplementation(async (productRunId: string) => ({
    schema_version: 'viewer_official_ranking.v1',
    product_run_id: productRunId,
    viewer_branch_id: `${productRunId}-official`,
    season_index: 29,
    week: 1,
    week_ordinal: 1769,
    snapshot_fingerprint: 'a'.repeat(64),
    policy_id: 'best-15',
    best_n: 15,
    row_count: 0,
    rows: []
  }))
  api.getViewerFinalsRace.mockImplementation(async (productRunId: string) => ({
    schema_version: 'viewer_finals_race_history.v1',
    product_run_id: productRunId,
    viewer_branch_id: `${productRunId}-official`,
    latest_target_season_index: null,
    publications: []
  }))
  api.getViewerTournamentHistory.mockImplementation(async (productRunId: string) => ({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: productRunId,
    viewer_branch_id: `${productRunId}-official`,
    tournament_count: 1,
    published_result_count: 0,
    tournaments: [{
      event_id: 'E1',
      season: '2029/30',
      season_week: 2,
      event_name: 'Canonical Event E1',
      template_id: 'TEMP-A',
      category: 'GOLD',
      tour_level: 'WORLD_TOUR',
      host_country: 'CZE',
      host_city: 'Prague',
      region: 'EUROPE',
      main_draw_size: 16,
      qualification_draw_size: 8,
      seeds_count: 4,
      qualifier_spots: 4,
      wild_cards: 2,
      byes: 0,
      ranking_status: 'ranked',
      result_published: false,
      champion_player_id: null,
      finalist_player_id: null
    }]
  }))
  api.listViewerOfficialRankingHistory.mockImplementation(async (productRunId: string) => ({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: productRunId,
    viewer_branch_id: `${productRunId}-official`,
    public_head_ordinal: 1769,
    publication_count: 1,
    publications: [{
      season_index: 29,
      week: 1,
      week_ordinal: 1769,
      snapshot_fingerprint: 'a'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 0
    }]
  }))
  api.getViewerTournamentResult.mockResolvedValue({
    schema_version: 'viewer_tournament_result.v1',
    product_run_id: 'run-a',
    viewer_branch_id: 'run-a-official',
    event_id: 'WTF-2030',
    completed_season_index: 30,
    completed_week: 41,
    champion_player_id: 'P1',
    finalist_player_id: 'P2',
    qualification_winner_ids: [],
    players: [],
    matches: []
  })
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


// Explicit canonical component fixtures, never a compatibility adapter to legacy reads.
function publicPlayer(id = 'P1', name = 'Player One', country = 'EGY', age = 24, ovr: number | null = 120): ViewerPlayer {
  return { player_id: id, name, country_code: country, age, current_ovr: ovr,
    status: 'active', identity_source: 'initial_world', tour_entry_season_index: null,
    tour_entry_week: null, potential_ovr: null, current_form: null,
    match_sharpness: null, long_term_fatigue: null }
}
function publicRoster(run: string, players: ViewerPlayer[] = []): ViewerPlayers {
  return { schema_version: 'viewer_players.v1', product_run_id: run, viewer_branch_id: `${run}-official`,
    season_index: 29, week: 1, player_count: players.length,
    active_player_count: players.filter(p => p.status === 'active').length,
    retired_player_count: players.filter(p => p.status === 'retired').length, players }
}
function publicCountries(run: string, countries: ViewerCountry[] = []): ViewerCountries {
  return { schema_version: 'viewer_countries.v1', product_run_id: run, viewer_branch_id: `${run}-official`,
    season_index: 29, week: 1, country_count: countries.length, countries }
}
function publicCountry(): ViewerCountry {
  return { country_code: 'EGY', player_count: 1, active_player_count: 1, retired_player_count: 0,
    average_current_ovr: 120, top_player_id: 'P1', top_player_name: 'Player One', top_player_current_ovr: 120 }
}
function mockCanonicalMetadata(run: string): void {
  const event = calendarEvent({ event_id: 'EVENT-LATEST', event_name: 'Published Open', season: '2029/2030', season_week: 1, status: 'completed' })
  api.getViewerRunCalendar.mockResolvedValue({ ...savedCalendar([event], run), viewer_branch_id: `${run}-official` })
  api.getViewerTournamentHistory.mockResolvedValue({ ...savedHistory([historyEvent(event, { result_published: true, champion_player_id: 'P1', finalist_player_id: 'P2' })], run), viewer_branch_id: `${run}-official` })
  const ranking = { ...rankingPublication(1), season_index: 29, week_ordinal: 1769 }
  api.listViewerOfficialRankingHistory.mockResolvedValue({ ...savedRankings([ranking]), product_run_id: run, viewer_branch_id: `${run}-official`, public_head_ordinal: 1769 })
  const race = { ...racePublication(1), product_run_id: run, viewer_branch_id: `${run}-official`, target_season_index: 29, cutoff_season_index: 29 }
  api.getViewerFinalsRace.mockResolvedValue({ ...savedRace([race]), product_run_id: run, viewer_branch_id: `${run}-official`, latest_target_season_index: 29 })
}
async function expectNoSelectedRunNotice(): Promise<void> {
  expect((await screen.findAllByText(/^(?:No Product Run is selected(?: yet)?\.|Select a Product Run first\.|No data is available for this run yet\.|Select a Product Run and enter a search query\.|No Product Run search context is available yet\.)$/)).length).toBeGreaterThan(0)
}
async function chooseViewerWeek(user: ReturnType<typeof userEvent.setup>, week: number): Promise<void> {
  await user.click(await screen.findByRole('button', { name: 'Season 2004/05 · W10' }))
  const input = screen.getByLabelText('Selected week')
  await user.clear(input); await user.type(input, String(week))
  await user.click(screen.getByRole('button', { name: 'Set Viewer Week' }))
}
function expectNoLegacyMetadataReads(): void {
  for (const reader of [api.getRunStatusSummary, api.listEvents, api.listRankingSnapshots, api.listRaceSnapshots, api.getRunActivity, api.getFinalsSummary]) expect(reader).not.toHaveBeenCalled()
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

function setTestActiveRun(runId: string): void {
  localStorage.setItem('beta_engine:viewer_active_run_id', runId)
  localStorage.setItem('beta_engine:viewer_active_product_run_id', runId)
}

function clearTestActiveRun(): void {
  localStorage.removeItem('beta_engine:viewer_active_run_id')
  localStorage.removeItem('beta_engine:viewer_active_product_run_id')
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
  localStorage.setItem('squash-engine-language-v1', 'en')
  clearTestActiveRun()
  localStorage.removeItem('beta_engine:viewer_context')
  resetApiMocks()
})

describe('Viewer Phase 3AQ completion audit', () => {
  it('keeps Viewer routes free of direct generic ViewerShellPage placeholders', () => {
    const directViewerShellRoutes = [...appSource.matchAll(/<Route\s+path="(viewer[^"]*)"\s+element=\{<ViewerShellPage\s+title="([^"]*)"\s*\/>\}/g)]
      .map((match) => ({ path: match[1], title: match[2] }))

    expect(directViewerShellRoutes).toEqual([])
  })
})

describe('Viewer Phase 4I run-scoped inline route cleanup audit', () => {
  it('keeps obvious run-scoped Viewer link construction on shared helpers in inspected Viewer sources', () => {
    const inspectedSources = [appSource, layoutSource, viewerRunSelectorSource]
    const obviousInlineRunScopedPatterns = [
      /`\/viewer\/runs\/\$\{[^`]+`/,
      /['"]\/viewer\/runs\/\$\{[^'"]+['"]/
    ]

    expect(
      inspectedSources.flatMap((source) => obviousInlineRunScopedPatterns.flatMap((pattern) => source.match(pattern) ?? []))
    ).toEqual([])
  })
})

describe('Viewer Phase 4H run-scoped route helper audit', () => {
  it('keeps run-scoped Viewer helpers aligned with App route patterns and encodes dynamic segments', () => {
    const runId = 'run alpha'
    const eventId = 'EV/01'
    const playerId = 'P/1'
    const countryCode = 'GB & IE'

    expect({
      calendar: viewerSeasonCalendarPath(runId),
      plannedEvent: viewerPlannedEventPath(runId, eventId),
      week: viewerWeekDetailPath(runId, 7),
      tournaments: viewerTournamentsPath(runId),
      tournamentDetail: viewerTournamentDetailPath(runId, eventId),
      players: viewerPlayersPath(runId),
      playerProfile: viewerPlayerProfilePath(runId, playerId),
      countries: viewerCountriesPath(runId),
      countryProfile: viewerCountryProfilePath(runId, countryCode),
      rankings: viewerRankingsPath(runId),
      rankingSnapshot: viewerRankingSnapshotPath(runId, 12),
      race: viewerRacePath(runId),
      raceSnapshot: viewerRaceSnapshotPath(runId, 12),
      history: viewerHistoryPath(runId),
      finals: viewerFinalsPath(runId),
      finalsQualification: viewerFinalsQualificationPath(runId),
      finalsResult: viewerFinalsResultPath(runId)
    }).toEqual({
      calendar: '/viewer/runs/run%20alpha/calendar',
      plannedEvent: '/viewer/runs/run%20alpha/calendar/EV%2F01',
      week: '/viewer/runs/run%20alpha/weeks/7',
      tournaments: '/viewer/runs/run%20alpha/tournaments',
      tournamentDetail: '/viewer/runs/run%20alpha/tournaments/EV%2F01',
      players: '/viewer/runs/run%20alpha/players',
      playerProfile: '/viewer/runs/run%20alpha/players/P%2F1/career',
      countries: '/viewer/runs/run%20alpha/countries',
      countryProfile: '/viewer/runs/run%20alpha/countries/GB%20%26%20IE',
      rankings: '/viewer/runs/run%20alpha/rankings',
      rankingSnapshot: '/viewer/runs/run%20alpha/rankings/12',
      race: '/viewer/runs/run%20alpha/race',
      raceSnapshot: '/viewer/runs/run%20alpha/race/12',
      history: '/viewer/runs/run%20alpha/history',
      finals: '/viewer/runs/run%20alpha/finals',
      finalsQualification: '/viewer/runs/run%20alpha/finals/qualification',
      finalsResult: '/viewer/runs/run%20alpha/finals/result'
    })

    const appRoutes = viewerAppRoutePaths(appSource)
    for (const routePattern of [
      '/viewer/runs/:runId/rankings',
      '/viewer/runs/:runId/rankings/:snapshotSequence',
      '/viewer/runs/:runId/race',
      '/viewer/runs/:runId/race/:snapshotSequence',
      '/viewer/runs/:runId/tournaments',
      '/viewer/runs/:runId/tournaments/:eventId',
      '/viewer/runs/:runId/calendar',
      '/viewer/runs/:runId/calendar/:eventId',
      '/viewer/runs/:runId/weeks/:week',
      '/viewer/runs/:runId/players',
      '/viewer/runs/:runId/players/:playerId/career',
      '/viewer/runs/:runId/countries',
      '/viewer/runs/:runId/countries/:countryCode',
      '/viewer/runs/:runId/history',
      '/viewer/runs/:runId/finals',
      '/viewer/runs/:runId/finals/qualification',
      '/viewer/runs/:runId/finals/result'
    ]) {
      expect(appRoutes).toContain(routePattern)
    }
  })
})

describe('Viewer Phase 4B navigation canonicalization', () => {
  it('exposes expected top-level Viewer route helper paths', () => {
    expect({
      home: viewerHomePath(),
      rankings: viewerTopRankingsPath(),
      race: viewerTopRacePath(),
      tour: viewerTopTourPath(),
      tourCalendar: viewerTopTourCalendarPath(),
      tourCurrentWeek: viewerTopTourCurrentWeekPath(),
      tourTournaments: viewerTopTourTournamentsPath(),
      tournaments: viewerTopTournamentsPath(),
      players: viewerTopPlayersPath(),
      countries: viewerTopCountriesPath(),
      countryRanking: viewerTopCountryRankingPath(),
      stats: viewerTopStatsPath(),
      records: viewerTopRecordsPath(),
      predictions: viewerTopPredictionsPath(),
      search: viewerTopSearchPath(),
      history: viewerTopHistoryPath(),
      h2h: viewerTopH2HPath()
    }).toEqual({
      home: '/viewer',
      rankings: '/viewer/rankings',
      race: '/viewer/rankings/race',
      tour: '/viewer/tour',
      tourCalendar: '/viewer/tour/calendar',
      tourCurrentWeek: '/viewer/tour/current-week',
      tourTournaments: '/viewer/tour/tournaments',
      tournaments: '/viewer/tournaments',
      players: '/viewer/players',
      countries: '/viewer/countries',
      countryRanking: '/viewer/countries/ranking',
      stats: '/viewer/stats',
      records: '/viewer/records',
      predictions: '/viewer/predictions',
      search: '/viewer/search',
      history: '/viewer/history',
      h2h: '/viewer/h2h'
    })
  })

  it('keeps Viewer nav Records and Country Ranking ownership canonical', () => {
    const navItems = viewerDropdowns.flatMap((dropdown) => dropdown.items.map((item) => ({ ...item, owner: dropdown.label })))
    const recordsItems = navItems.filter((item) => /Records/.test(item.label))
    expect(recordsItems).toEqual(expect.arrayContaining([expect.objectContaining({ label: 'Records', to: '/viewer/records', owner: 'Stats' })]))
    expect(recordsItems).not.toEqual(expect.arrayContaining([expect.objectContaining({ label: 'Records', to: '/viewer/stats' })]))
    expect(navItems).toEqual(expect.arrayContaining([expect.objectContaining({ label: 'Stats Hub', to: '/viewer/stats', owner: 'Stats' })]))

    const countryRankingOwners = navItems.filter((item) => item.to === '/viewer/countries/ranking').map((item) => item.owner)
    expect(countryRankingOwners).toEqual(['Countries'])
  })

  it('renders canonicalized Viewer routes and tournament alias without forbidden Viewer actions', async () => {
    const routes = [
      ['/viewer/records', 'Records'],
      ['/viewer/stats', 'Stats'],
      ['/viewer/countries/ranking', 'Country Ranking'],
      ['/viewer/tour/tournaments', 'All Tournaments'],
      ['/viewer/tournaments', 'All Tournaments']
    ] as const

    for (const [route, heading] of routes) {
      cleanup()
      resetApiMocks()
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: heading, level: 2 })).toBeInTheDocument()
      expectNoForbiddenViewerActions()
    }
  })
})

describe('Viewer Phase 1B/1C/1D routes and safety', () => {
  it('renders premium MSA homepage scaffold sections without active-run authoritative data', async () => {
    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: /MSA Squash/, level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')
    for (const section of [
      'Latest Completed Tournament',
      'Season Schedule',
      'Official Ranking Publications',
      'World Tour Finals Race',
      'Featured Matches',
      'Predictions & Upset Watch',
      'Viewer hub links',
      'What this hub does not infer',
      'History'
    ]) {
      expect(screen.getByRole('heading', { name: section })).toBeInTheDocument()
    }
    expect(screen.getByText(/No active Viewer run selected/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('renders the active run picker with available runs and no active run state', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        { run_id: 'run-a', season: 2030, seed: 9, progress: { next_event_index: 0, total_events: 4, completed_event_count: 0 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 },
        { run_id: 'run-b', season: 2031, seed: 11, progress: { next_event_index: 1, total_events: 5, completed_event_count: 1 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 }
      ]
    })

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active Product Run picker')
    expect(picker).toHaveTextContent('No active run selected')
    expect(within(picker).getByRole('link', { name: 'Browse all runs' })).toHaveAttribute('href', '/viewer/runs')
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

    const picker = await screen.findByLabelText('Active Product Run picker')
    await within(picker).findByRole('option', { name: /run-b — season 2031, seed 11/ })
    await user.selectOptions(within(picker).getByLabelText('Available Product Runs'), 'run-b')
    await user.click(within(picker).getByRole('button', { name: 'Set active run' }))

    await waitFor(() => expect(localStorage.getItem('beta_engine:viewer_active_run_id')).toBe('run-b'))
    expect(localStorage.getItem('beta_engine:last_run_id')).toBe('run-b')
    await waitFor(() => expect(within(picker).getAllByText('run-b').length).toBeGreaterThan(0))
    expect(await screen.findByRole('link', { name: 'Active Run Rankings' })).toHaveAttribute('href', '/viewer/runs/run-b/rankings')
    expect(screen.getByRole('link', { name: 'Active Run Calendar' })).toHaveAttribute('href', '/viewer/runs/run-b/calendar')
    expect(screen.queryAllByLabelText('Viewer active run quick links')).toHaveLength(0)
    expectNoForbiddenViewerActions()
  })

  it('shows an empty state when the active run picker has no runs', async () => {
    api.listRuns.mockResolvedValue({ runs: [] })

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active Product Run picker')
    expect(await within(picker).findByText('No Product Runs are available yet.')).toBeInTheDocument()
    expect(within(picker).getByRole('button', { name: 'Set active run' })).toBeDisabled()
    expectNoForbiddenViewerActions()
  })

  it('shows an unavailable state when the active run picker cannot load runs', async () => {
    api.listRuns.mockRejectedValue(new Error('runs unavailable'))

    renderAppAt('/viewer')

    const picker = await screen.findByLabelText('Active Product Run picker')
    expect(await within(picker).findByText('runs unavailable')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders the Viewer Run Browser with available run metadata and safe links', async () => {
    api.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'browser-run-a',
          season: 2032,
          seed: 21,
          progress: { next_event_index: 2, total_events: 9, completed_event_count: 2 },
          source_type: 'fresh_seed',
          parent_run_id: null,
          child_run_count: 0,
          created_at: '2032-01-01T00:00:00Z',
          updated_at: '2032-01-02T00:00:00Z',
          payload: { hidden: 'raw payload should not render' }
        },
        {
          run_id: 'browser-run-b',
          season: 2033,
          seed: 34,
          progress: { next_event_index: 4, total_events: 12, completed_event_count: 4 },
          source_type: 'rollover_bootstrap',
          parent_run_id: 'browser-run-a',
          child_run_count: 0
        }
      ]
    })

    renderAppAt('/viewer/runs')

    expect(await screen.findByRole('heading', { name: 'Run Browser', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Available runs' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Active run' })).toBeInTheDocument()

    const runCard = await screen.findByLabelText('Run browser-run-a')
    expect(runCard).toHaveTextContent('browser-run-a')
    expect(runCard).toHaveTextContent('Product Run ID')
    expect(runCard).toHaveTextContent('Status')
    expect(runCard).toHaveTextContent('active')
    expect(runCard).toHaveTextContent('Storage kind')
    expect(runCard).toHaveTextContent('custom_local')
    expect(runCard).toHaveTextContent('Read-only')
    expect(runCard).toHaveTextContent('false')
    expect(runCard).toHaveTextContent('World ID')
    expect(runCard).toHaveTextContent('test-world')
    expect(runCard).toHaveTextContent('Timeline')
    expect(runCard).toHaveTextContent('2032–2032')
    expect(runCard).toHaveTextContent('Official Branch ID')
    expect(runCard).toHaveTextContent('browser-run-a-official')
    expect(runCard).toHaveTextContent('Mapped SimulationRuns')
    expect(runCard).toHaveTextContent('1')

    expect(screen.getByLabelText('Run browser-run-b')).toHaveTextContent('browser-run-b-official')

    const expectedLinks = [
      ['Season calendar', '/viewer/runs/browser-run-a/calendar'],
      ['Tournaments', '/viewer/runs/browser-run-a/tournaments'],
      ['Rankings', '/viewer/runs/browser-run-a/rankings'],
      ['Race', '/viewer/runs/browser-run-a/race'],
      ['Players', '/viewer/runs/browser-run-a/players'],
      ['Countries', '/viewer/runs/browser-run-a/countries'],
      ['History', '/viewer/runs/browser-run-a/history'],
      ['Finals', '/viewer/runs/browser-run-a/finals']
    ]
    for (const [name, href] of expectedLinks) {
      expect(within(runCard).getByRole('link', { name })).toHaveAttribute('href', href)
    }
    expect(screen.queryByText('raw payload should not render')).not.toBeInTheDocument()
    expect(screen.queryByText(/hidden/)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows active Viewer run status on the Run Browser when local storage is set', async () => {
    setTestActiveRun('browser-run-active')
    api.listRuns.mockResolvedValue({
      runs: [
        { run_id: 'browser-run-active', season: 2034, seed: 55, progress: { next_event_index: 1, total_events: 6, completed_event_count: 1 }, source_type: 'fresh_seed', parent_run_id: null, child_run_count: 0 }
      ]
    })

    renderAppAt('/viewer/runs')

    const activeRunPanel = await screen.findByLabelText('Run Browser active run')
    expect(activeRunPanel).toHaveTextContent('Current active Viewer run id: browser-run-active')
    expectNoForbiddenViewerActions()
  })

  it('shows the no-data state when the Run Browser has no runs', async () => {
    api.listRuns.mockResolvedValue({ runs: [] })

    renderAppAt('/viewer/runs')

    expect(await screen.findByText('No Viewer runs are available yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows a temporary unavailable state when the Run Browser cannot load run metadata', async () => {
    api.listRuns.mockRejectedValue(new Error('runs unavailable'))

    renderAppAt('/viewer/runs')

    expect(await screen.findByText('Run metadata is temporarily unavailable.')).toBeInTheDocument()
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
    await expectNoSelectedRunNotice()

    cleanup()
    renderAppAt('/viewer/tour/current-week')
    expect(await screen.findByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
  })

  it('updates local Viewer week through the real calendar context selector', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer/tour/calendar')
    await chooseViewerWeek(user, 24)
    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
    expect(localStorage.getItem('beta_engine:viewer_context')).toContain('24')
    expectNoLegacyMetadataReads()
    expectNoForbiddenViewerActions()
  })

  it('navigates the topbar search input to canonical q search results without fake results', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer')

    const searchInput = await screen.findByRole('textbox', { name: 'Search players, countries, tournaments' })
    await user.type(searchInput, 'Paris{Enter}')

    expect(await screen.findByRole('heading', { name: 'Search', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('Search: Paris')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Read-only Viewer search shell')[0]).toHaveValue('Paris')
    await expectNoSelectedRunNotice()
    expect(screen.queryByText(/Paris can reclaim/i)).not.toBeInTheDocument()
  })

  it('navigates an empty topbar search submit to the search shell without a query string', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer')

    const searchInput = await screen.findByRole('textbox', { name: 'Search players, countries, tournaments' })
    await user.click(searchInput)
    await user.keyboard('{Enter}')

    expect(await screen.findByRole('heading', { name: 'Search', level: 2 })).toBeInTheDocument()
    expect(screen.getAllByLabelText('Read-only Viewer search shell')[0]).toHaveValue('')
    expect(screen.queryByText(/Search query:/)).not.toBeInTheDocument()
    await expectNoSelectedRunNotice()
  })

  it('shows sports-facing empty states on top-level Viewer pages when no active run is selected', async () => {
    for (const route of ['/viewer/rankings', '/viewer/rankings/race', '/viewer/tour', '/viewer/tour/current-week', '/viewer/tour/tournaments', '/viewer/tour/matches', '/viewer/tour/categories', '/viewer/tour/champions', '/viewer/tournaments', '/viewer/players', '/viewer/countries', '/viewer/history', '/viewer/records', '/viewer/stats']) {
      cleanup(); clearTestActiveRun(); renderAppAt(route)
      await expectNoSelectedRunNotice()
      expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
      expect(api.getViewerPlayers).not.toHaveBeenCalled()
      expect(api.getViewerCountries).not.toHaveBeenCalled()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows no-data state on H2H when no active run is selected', async () => {
    clearTestActiveRun()

    renderAppAt('/viewer/h2h')

    expect(await screen.findByRole('heading', { name: 'Player Comparison', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows deferred H2H state and sample player links without player params', async () => {
    setTestActiveRun('phase-3ab-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ab-run',
      total: 2,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'AAA', age: 24, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 80, movement: 81, physical: 82, mental: 83, overall: 84 },
        { player_id: 'P2', name: 'Player Two', country_code: 'BBB', age: 26, source_type: 'planner_generated', override_id: null, quality_band: 'B', is_top_band: false, origin_source_type: 'planner_generated', origin_quality_band: 'B', origin_override_id: null, origin_season: 2030, technique: 70, movement: 71, physical: 72, mental: 73, overall: 74 }
      ]
    })

    renderAppAt('/viewer/h2h')

    expect(await screen.findByRole('heading', { name: 'Player Comparison', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/players/P1/career')
    expect(screen.getByRole('link', { name: 'P1' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/players/P1/career')
    expect(screen.getByRole('link', { name: 'AAA' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/countries/AAA')
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/players')
    expect(screen.getByRole('link', { name: 'Open Viewer search' })).toHaveAttribute('href', '/viewer/search')
    expectNoForbiddenViewerActions()
  })

  it('shows matched H2H player cards, links, and numeric differences without fake outcomes', async () => {
    setTestActiveRun('phase-3ab-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ab-run',
      total: 2,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'AAA', age: 24, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 80, movement: 81, physical: 82, mental: 83, overall: 84 },
        { player_id: 'P2', name: 'Player Two', country_code: 'BBB', age: 26, source_type: 'planner_generated', override_id: null, quality_band: 'B', is_top_band: false, origin_source_type: 'planner_generated', origin_quality_band: 'B', origin_override_id: null, origin_season: 2030, technique: 70, movement: 71, physical: 72, mental: 73, overall: 74 }
      ]
    })

    api.listRunPlayers.mockResolvedValue({ run_id: 'phase-3ab-run', players: [], total: 0, limit: 50, offset: 0 })
    api.getRunPlayerDetail.mockImplementation(async (_run: string, id: string) => ({
      player_id: id, name: id === 'P1' ? 'Player One' : 'Player Two',
      country_code: id === 'P1' ? 'AAA' : 'BBB', age: id === 'P1' ? 24 : 26,
      overall: id === 'P1' ? 84 : 74, technique: id === 'P1' ? 80 : 70,
      movement: id === 'P1' ? 81 : 71, physical: id === 'P1' ? 82 : 72,
      mental: id === 'P1' ? 83 : 73, source_type: 'planner_generated',
      quality_band: id === 'P1' ? 'A' : 'B', is_top_band: id === 'P1',
    }))

    renderAppAt('/viewer/h2h?playerA=P1&playerB=P2')

    expect(await screen.findByRole('heading', { name: 'Player Comparison', level: 2 })).toBeInTheDocument()
    const playerACard = screen.getByRole('heading', { name: 'Player A' }).closest('article')
    const playerBCard = screen.getByRole('heading', { name: 'Player B' }).closest('article')
    await waitFor(() => expect(playerACard).toHaveTextContent('Player One'))
    expect(playerACard).toHaveTextContent('Power Rating84')
    expect(playerACard).toHaveTextContent('Technique80')
    expect(playerACard).toHaveTextContent('Movement81')
    expect(playerACard).toHaveTextContent('Physical82')
    expect(playerACard).toHaveTextContent('Mental83')
    expect(playerACard).toHaveTextContent('Quality bandA')
    expect(playerBCard).toHaveTextContent('Player Two')
    expect(screen.getByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/players/P1/career')
    expect(screen.getByRole('link', { name: 'P2' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/players/P2/career')
    expect(screen.getByRole('link', { name: 'AAA' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/countries/AAA')
    expect(screen.getByRole('link', { name: 'BBB' })).toHaveAttribute('href', '/viewer/runs/phase-3ab-run/countries/BBB')

    const summary = screen.getByRole('heading', { name: 'Comparison Summary' }).closest('article')
    expect(summary).toHaveTextContent('Power Rating difference+10')
    expect(summary).toHaveTextContent('Technique difference+10')
    expect(summary).toHaveTextContent('Movement difference+10')
    expect(summary).toHaveTextContent('Physical difference+10')
    expect(summary).toHaveTextContent('Mental difference+10')
    expect(summary).toHaveTextContent('Age difference-2')
    expect(screen.queryByText(/3-1 H2H|win probability|predicted winner|betting odds|rivalry history|match result/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/source_type|origin_source_type|override_id/i)).not.toBeInTheDocument()
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('phase-3ab-run', 'P1')
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('phase-3ab-run', 'P2')
    expectNoForbiddenViewerActions()
  })

  it('shows safe missing state for unavailable comparison player ids', async () => {
    setTestActiveRun('phase-3ab-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ab-run',
      total: 1,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'AAA', age: 24, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 80, movement: 81, physical: 82, mental: 83, overall: 84 }
      ]
    })

    renderAppAt('/viewer/h2h?playerA=P1&playerB=P404')

    await waitFor(() => expect(screen.queryByText('Loading active run player metadata…')).not.toBeInTheDocument())
    expect(screen.getAllByText('Player data is not available for this run yet.').length).toBeGreaterThan(0)
    expect(screen.queryByText(/predicted winner|win probability|match result/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps player compare route consistent with H2H comparison behavior', async () => {
    setTestActiveRun('phase-3ab-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ab-run',
      total: 2,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'AAA', age: 24, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 80, movement: 81, physical: 82, mental: 83, overall: 84 },
        { player_id: 'P2', name: 'Player Two', country_code: 'BBB', age: 26, source_type: 'planner_generated', override_id: null, quality_band: 'B', is_top_band: false, origin_source_type: 'planner_generated', origin_quality_band: 'B', origin_override_id: null, origin_season: 2030, technique: 70, movement: 71, physical: 72, mental: 73, overall: 74 }
      ]
    })

    api.listRunPlayers.mockResolvedValue({ run_id: 'phase-3ab-run', players: [], total: 0, limit: 50, offset: 0 })
    api.getRunPlayerDetail.mockImplementation(async (_run: string, id: string) => ({
      player_id: id, name: id === 'P1' ? 'Player One' : 'Player Two',
      country_code: id === 'P1' ? 'AAA' : 'BBB', age: id === 'P1' ? 24 : 26,
      overall: id === 'P1' ? 84 : 74, technique: id === 'P1' ? 80 : 70,
      movement: id === 'P1' ? 81 : 71, physical: id === 'P1' ? 82 : 72,
      mental: id === 'P1' ? 83 : 73, source_type: 'planner_generated',
      quality_band: id === 'P1' ? 'A' : 'B', is_top_band: id === 'P1',
    }))

    renderAppAt('/viewer/players/compare?playerA=P1&playerB=P2')

    expect(await screen.findByRole('heading', { name: 'Player Comparison', level: 2 })).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Player A' }).closest('article')).toHaveTextContent('Player One'))
    expect(screen.getByRole('heading', { name: 'Player B' }).closest('article')).toHaveTextContent('Player Two')
    expect(screen.getByRole('heading', { name: 'Comparison Summary' }).closest('article')).toHaveTextContent('Power Rating difference+10')
    expect(screen.queryByText(/3-1 H2H|win probability|predicted winner|betting odds|rivalry history|match result/i)).not.toBeInTheDocument()
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('phase-3ab-run', 'P1')
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('phase-3ab-run', 'P2')
    expectNoForbiddenViewerActions()
  })

  it('keeps H2H subroutes as conservative active-run metadata pages', async () => {
    for (const [route, title] of [['/viewer/h2h/rivalries', 'Rivalries'], ['/viewer/h2h/most-played', 'Most Played Matchups'], ['/viewer/h2h/finals-rivalries', 'Finals Rivalries']]) {
      cleanup(); resetApiMocks(); setTestActiveRun('h2h run'); mockCanonicalMetadata('h2h run')
      api.getViewerPlayers.mockResolvedValue(publicRoster('h2h run', [publicPlayer()]))
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(await screen.findByRole('link', { name: 'Published Open' })).toHaveAttribute('href', '/viewer/runs/h2h%20run/tournaments/EVENT-LATEST')
      expect(screen.getByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/h2h%20run/players/P1/career')
      expectNoLegacyMetadataReads(); expect(api.listRunPlayers).not.toHaveBeenCalled()
      expect(document.body).not.toHaveTextContent(/3-1 H2H|win probability|predicted winner|raw_secret/)
      expectNoForbiddenViewerActions()
    }
  })


  it('shows Match Predictor no-data state when no active run is selected', async () => {
    clearTestActiveRun()

    renderAppAt('/viewer/predictions')

    expect(await screen.findByRole('heading', { name: 'Match Predictor', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.listRunPlayers).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows Match Predictor deferred inputs and sample player profile links without player params', async () => {
    setTestActiveRun('phase-3ac-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ac-run',
      total: 2,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'EGY', age: 28, source_type: 'planner_generated', override_id: null, quality_band: 'Elite', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'Elite', origin_override_id: null, origin_season: 2030, technique: 90, movement: 91, physical: 88, mental: 92, overall: 95 },
        { player_id: 'P2', name: 'Player Two', country_code: 'NZL', age: 31, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 86, movement: 84, physical: 89, mental: 85, overall: 90 }
      ]
    })

    renderAppAt('/viewer/predictions')

    expect(await screen.findByRole('heading', { name: 'Match Predictor', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Predictor Inputs' })).toBeInTheDocument()
    expect(screen.getAllByText('This preview is not connected for this data shape yet.').length).toBeGreaterThan(0)
    expect(await screen.findByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/players/P1/career')
    expect(await screen.findByRole('link', { name: 'P1' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/players/P1/career')
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/players')
    expect(screen.getByRole('link', { name: 'Open Viewer search' })).toHaveAttribute('href', '/viewer/search')
    expect(screen.getByRole('link', { name: 'Open H2H comparison' })).toHaveAttribute('href', '/viewer/h2h')
    expect(api.listRunPlayers).toHaveBeenCalledWith('phase-3ac-run', { limit: 50, offset: 0 })
    expectNoForbiddenViewerActions()
  })

  it('shows Match Predictor selected player cards, links, numeric input differences, and deferred outputs', async () => {
    setTestActiveRun('phase-3ac-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ac-run',
      total: 2,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'EGY', age: 28, source_type: 'planner_generated', override_id: null, quality_band: 'Elite', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'Elite', origin_override_id: null, origin_season: 2030, technique: 90, movement: 91, physical: 88, mental: 92, overall: 95 },
        { player_id: 'P2', name: 'Player Two', country_code: 'NZL', age: 31, source_type: 'planner_generated', override_id: null, quality_band: 'A', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'A', origin_override_id: null, origin_season: 2030, technique: 86, movement: 84, physical: 89, mental: 85, overall: 90 }
      ]
    })

    renderAppAt('/viewer/predictions?playerA=P1&playerB=P2')

    expect(await screen.findByRole('heading', { name: 'Match Predictor', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Player A' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Player B' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Input Comparison' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/players/P1/career')
    expect(await screen.findByRole('link', { name: 'P2' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/players/P2/career')
    expect(await screen.findByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/countries/EGY')
    expect(await screen.findByRole('link', { name: 'NZL' })).toHaveAttribute('href', '/viewer/runs/phase-3ac-run/countries/NZL')
    const comparison = await screen.findByLabelText('Input Comparison differences')
    expect(comparison).toHaveTextContent('Power Rating difference+5')
    expect(comparison).toHaveTextContent('Technique difference+4')
    expect(comparison).toHaveTextContent('Movement difference+7')
    expect(comparison).toHaveTextContent('Physical difference-1')
    expect(comparison).toHaveTextContent('Mental difference+7')
    expect(comparison).toHaveTextContent('Age difference-3')
    expect(screen.getByRole('link', { name: 'Open H2H comparison' })).toHaveAttribute('href', '/viewer/h2h?playerA=P1&playerB=P2')
    expect(screen.getByText('No prediction is shown until a real prediction read model exists.')).toBeInTheDocument()
    expect(screen.getByText('No odds are shown until a real odds read model exists.')).toBeInTheDocument()
    expect(document.body).not.toHaveTextContent(/predicted winner|win probability|upset chance|H2H record|match result|betting odds|3-1 H2H|"source_type"|planner_generated/i)
    expect(document.body).not.toHaveTextContent(/[0-9]+%|[0-9]+\.[0-9]+/)
    expectNoForbiddenViewerActions()
  })

  it('shows Match Predictor safe missing-player state and keeps shortcut routes consistent', async () => {
    setTestActiveRun('phase-3ac-run')
    api.listRunPlayers.mockResolvedValue({
      run_id: 'phase-3ac-run',
      total: 1,
      limit: 50,
      offset: 0,
      players: [
        { player_id: 'P1', name: 'Player One', country_code: 'EGY', age: 28, source_type: 'planner_generated', override_id: null, quality_band: 'Elite', is_top_band: true, origin_source_type: 'planner_generated', origin_quality_band: 'Elite', origin_override_id: null, origin_season: 2030, technique: 90, movement: 91, physical: 88, mental: 92, overall: 95 }
      ]
    })

    renderAppAt('/viewer/predictions/match-predictor?playerA=P1&playerB=P404')

    expect(await screen.findByRole('heading', { name: 'Match Predictor', level: 2 })).toBeInTheDocument()
    expect(screen.getAllByText('Player data is not available for this run yet.').length).toBeGreaterThan(0)
    expect(screen.getByText('No prediction is shown until a real prediction read model exists.')).toBeInTheDocument()
    expect(document.body).not.toHaveTextContent(/predicted winner|win probability|upset chance|H2H record|match result|betting odds|3-1 H2H|"players"/i)
    expectNoForbiddenViewerActions()
  })

  it('renders deferred prediction subpages with no active run empty state', async () => {
    const routes = [
      ['/viewer/predictions/match-odds', 'Match Odds'],
      ['/viewer/predictions/tournament-odds', 'Tournament Odds'],
      ['/viewer/predictions/finals-qualification', 'Finals Qualification'],
      ['/viewer/predictions/season-end-no1', 'Season-End No.1'],
      ['/viewer/predictions/upset-watch', 'Upset Watch'],
      ['/viewer/predictions/futures', 'Futures']
    ] as const

    for (const [route, title] of routes) {
      cleanup()
      resetApiMocks()
      clearTestActiveRun()
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      await expectNoSelectedRunNotice()
      expect(api.getRunStatusSummary).not.toHaveBeenCalled()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows conservative active-run metadata and links on deferred prediction subpages', async () => {
    for (const route of ['/viewer/predictions/match-odds', '/viewer/predictions/tournament-odds', '/viewer/predictions/finals-qualification', '/viewer/predictions/season-end-no1', '/viewer/predictions/upset-watch', '/viewer/predictions/futures']) {
      cleanup(); resetApiMocks(); setTestActiveRun('prediction run'); mockCanonicalMetadata('prediction run')
      renderAppAt(route)
      expect(await screen.findByRole('link', { name: 'Published Open' })).toHaveAttribute('href', '/viewer/runs/prediction%20run/tournaments/EVENT-LATEST')
      expect(screen.getByRole('link', { name: 'Season 29 W1 · #1769' })).toHaveAttribute('href', '/viewer/runs/prediction%20run/rankings/1769')
      expectNoLegacyMetadataReads()
      expect(document.body).not.toHaveTextContent(/predicted winner|win probability|raw_secret|invented odds/)
      expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run Search player results with profile and country links', async () => {
    setTestActiveRun('search run')
    api.getViewerPlayers.mockResolvedValue(publicRoster('search run', [publicPlayer('ALI-1', 'Ali Farag', 'EGY', 34, 190)]))
    renderAppAt('/viewer/search?q=ali')
    expect(await screen.findByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/search%20run/players/ALI-1/career')
    expect(screen.getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/search%20run/countries/EGY')
    expect(api.getViewerPlayers).toHaveBeenCalledWith('search run')
    expect(api.listRunPlayers).not.toHaveBeenCalled()
    expect(document.body).not.toHaveTextContent(/potential_ovr|planner_generated|raw_secret/)
    expectNoForbiddenViewerActions()
  })

  it('shows active-run Search country results with country and top-player links', async () => {
    setTestActiveRun('search run')
    api.getViewerCountries.mockResolvedValue(publicCountries('search run', [publicCountry()]))
    renderAppAt('/viewer/search?q=egy')
    const countries = within(await screen.findByLabelText('Countries'))
    expect((await countries.findAllByRole('link', { name: 'EGY' }))[0]).toHaveAttribute('href', '/viewer/runs/search%20run/countries/EGY')
    expect(countries.getByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/search%20run/players/P1/career')
    expect(api.getViewerCountries).toHaveBeenCalledWith('search run')
    expect(api.listRunNations).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows active-run Search tournament results with planned, week, and detail links', async () => {
    setTestActiveRun('search run')
    const event = calendarEvent({ event_id: 'GOLD-1', event_name: 'Gold Open', template_id: 'TEMP-GOLD', category: 'GOLD', season_week: 12 })
    api.getViewerRunCalendar.mockResolvedValue({ ...savedCalendar([event], 'search run'), viewer_branch_id: 'search run-official' })
    api.getViewerTournamentHistory.mockResolvedValue({ ...savedHistory([historyEvent(event, { result_published: true, champion_player_id: 'P1', finalist_player_id: 'P2' })], 'search run'), viewer_branch_id: 'search run-official' })
    renderAppAt('/viewer/search?q=gold')
    expect(await screen.findByRole('link', { name: 'Planned Event: GOLD-1' })).toHaveAttribute('href', '/viewer/runs/search%20run/calendar/GOLD-1')
    expect(screen.getByRole('link', { name: 'Week Detail: W12' })).toHaveAttribute('href', '/viewer/runs/search%20run/weeks/12')
    expect(screen.getByRole('link', { name: 'Tournament Detail: GOLD-1' })).toHaveAttribute('href', '/viewer/runs/search%20run/tournaments/GOLD-1')
    expect(api.getRun).not.toHaveBeenCalled(); expect(api.listEvents).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows safe active-run Search empty and no-match states without raw payloads', async () => {
    setTestActiveRun('search run'); renderAppAt('/viewer/search')
    expect(await screen.findByRole('heading', { name: 'Search', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('No Product Run search context is available yet.')).toBeInTheDocument()
    expect(api.getViewerPlayers).not.toHaveBeenCalled()
    cleanup()
    api.getViewerPlayers.mockResolvedValue(publicRoster('search run', [publicPlayer()]))
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([], 'search run'))
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([], 'search run'))
    renderAppAt('/viewer/search?q=nomatch')
    expect(await screen.findByText('No matching Viewer results found.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Player One' })).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent(/raw_secret|potential_ovr|planner_generated/)
    expectNoForbiddenViewerActions()
  })

  it('shows active run status, safe links, and small real summaries on the Viewer homepage', async () => {
    setTestActiveRun('run-a')
    api.getViewerOfficialRunContext.mockResolvedValue({
      product_run_id: 'run-a',
      product_run_display_name: 'Run A',
      product_run_status: 'active',
      product_run_storage_kind: 'custom_local',
      product_run_read_only: false,
      official_branch_id: 'run-a-official',
      official_branch_display_name: 'Official',
      official_branch_status: 'active',
      official_branch_read_only: false,
      official_branch_seed: 99,
      legacy_simulation_run_id: 'run-a',
      head_checkpoint_id: 'checkpoint',
      head_checkpoint_kind: 'week',
      current_season: 30,
      current_week: 40,
      current_event_id: 'E2',
      current_event_sequence: 2,
      resolution_version: 'viewer_official_branch_v1'
    })
    api.getViewerTournamentHistory.mockResolvedValue({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      tournament_count: 2,
      published_result_count: 1,
      tournaments: [{
        event_id: 'E2',
        season: '2030/31',
        season_week: 40,
        event_name: 'Canonical Diamond',
        template_id: 'TEMP-B',
        category: 'DIAMOND',
        tour_level: 'WORLD_TOUR',
        host_country: 'CZE',
        host_city: 'Prague',
        region: 'EUROPE',
        main_draw_size: 16,
        qualification_draw_size: 8,
        seeds_count: 4,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: true,
        champion_player_id: 'P1',
        finalist_player_id: 'P2'
      }]
    })
    api.listViewerOfficialRankingHistory.mockResolvedValue({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      public_head_ordinal: 1830,
      publication_count: 1,
      publications: [{ season_index: 30, week: 40, week_ordinal: 1830, snapshot_fingerprint: 'b'.repeat(64), policy_id: 'best-15', best_n: 15, row_count: 48 }]
    })
    api.getViewerFinalsRace.mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      latest_target_season_index: 30,
      publications: [{
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'run-a',
        viewer_branch_id: 'run-a-official',
        target_season_index: 30,
        cutoff_season_index: 30,
        cutoff_week: 40,
        best_n: 9,
        selection_published: true,
        finals_event_id: 'WTF-2030',
        rows: []
      }]
    })

    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: 'Active Viewer run: run-a' })).toBeInTheDocument()
    const statusPanel = screen.getByLabelText('Active Viewer run status')
    await waitFor(() => expect(statusPanel).toHaveTextContent('Run A'))
    expect(statusPanel).toHaveTextContent('run-a-official')
    expect(statusPanel).toHaveTextContent('30')
    expect(statusPanel).toHaveTextContent('40')
    expect(statusPanel).toHaveTextContent('1')
    expect(statusPanel).toHaveTextContent('Selection published')
    expect(screen.getByRole('link', { name: 'Canonical Diamond' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments/E2')
    expect(screen.getByText(/ordinal 1830/i)).toBeInTheDocument()
    expect(screen.getByText(/Target season 30/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open active run history' })).toHaveAttribute('href', '/viewer/runs/run-a/history')
    expectNoForbiddenViewerActions()
  })
  it('shows a sports-facing unavailable state when active-run homepage APIs fail', async () => {
    setTestActiveRun('run-a')
    api.getViewerTournamentHistory.mockRejectedValueOnce(new Error('canonical unavailable'))

    renderAppAt('/viewer')

    expect(await screen.findByText(/Active run summary is temporarily unavailable/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Latest Completed Tournament' })).toBeInTheDocument()
    expect(screen.queryByText(/canonical unavailable/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('shows canonical current Official Ranking metadata for the active Product Run', async () => {
    setTestActiveRun('run-a')
    api.getViewerOfficialRanking.mockResolvedValue({
      schema_version: 'viewer_official_ranking.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      season_index: 29,
      week: 6,
      week_ordinal: 1774,
      snapshot_fingerprint: 'b'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 2,
      rows: [
        { rank: 1, player_id: 'P1', points: 1000 },
        { rank: 2, player_id: 'P2', points: 900 }
      ]
    })

    renderAppAt('/viewer/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    const panel = await screen.findByRole('article', { name: 'Currently published ranking' })
    await waitFor(() => expect(panel).toHaveTextContent('run-a'))
    expect(panel).toHaveTextContent('run-a-official')
    expect(panel).toHaveTextContent('2029')
    expect(panel).toHaveTextContent('6')
    expect(panel).toHaveTextContent('2')
    expect(panel).toHaveTextContent('15')
    expect(api.getViewerOfficialRanking).toHaveBeenCalledWith('run-a')
    const table = screen.getByRole('table', { name: 'Current Official Ranking Top 10' })
    expect(within(table).getByText('P1')).toBeInTheDocument()
    expect(within(table).getByText('1000')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open full publication history' })).toHaveAttribute(
      'href',
      '/viewer/runs/run-a/rankings'
    )
    expect(screen.queryByRole('link', { name: /View latest ranking snapshot/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows canonical Finals Race standings for the active Product Run', async () => {
    setTestActiveRun('run-a')
    api.getViewerFinalsRace.mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      latest_target_season_index: 29,
      publications: [{
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'run-a',
        viewer_branch_id: 'run-a-official',
        target_season_index: 29,
        cutoff_season_index: 29,
        cutoff_week: 55,
        best_n: 8,
        selection_published: true,
        finals_event_id: 'FINALS-2029',
        rows: [{
          rank: 1,
          player_id: 'R1',
          race_points: 1200,
          tournaments_counted: 1,
          finals_selected: true,
          finals_seed: 1,
          qualification_source: 'race',
          counted_results: [
            { event_id: 'E1', completed_season_index: 29, completed_week: 12, race_points: 1200 }
          ]
        }]
      }]
    })

    renderAppAt('/viewer/rankings/race')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Saved Race standings' })
    expect(api.getViewerFinalsRace).toHaveBeenCalledWith('run-a')
    expect(within(table).getByRole('link', { name: 'R1' })).toHaveAttribute(
      'href',
      '/viewer/runs/run-a/players/R1/career'
    )
    expect(within(table).getByText('1200')).toBeInTheDocument()
    expect(within(within(table).getAllByRole('row')[1]).getAllByRole('cell')[3]).toHaveTextContent(/^1$/)
    expect(within(table).getByText('Race qualified · seed 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open run-scoped Race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.queryByText(/snapshot sequence/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows canonical ranking empty-player state and race empty snapshot state for active runs', async () => {
    setTestActiveRun('run-a')
    api.getViewerOfficialRanking.mockResolvedValue({
      schema_version: 'viewer_official_ranking.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      season_index: 29,
      week: 1,
      week_ordinal: 1769,
      snapshot_fingerprint: 'a'.repeat(64),
      policy_id: 'best-15',
      best_n: 15,
      row_count: 0,
      rows: []
    })

    renderAppAt('/viewer/rankings')
    expect(await screen.findByText('The published ranking contains exactly 0 players.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open full publication history' })).toHaveAttribute('href', '/viewer/runs/run-a/rankings')
    expect(screen.queryByRole('link', { name: /View latest ranking snapshot/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/rankings/race')
    expect(await screen.findByText('No Race publication has been saved in this Viewer Branch yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open run-scoped Race' })).toHaveAttribute('href', '/viewer/runs/run-a/race')
    expect(screen.queryByText(/snapshot sequence/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows top-level Season Hub metadata when an active Viewer run exists', async () => {
    setTestActiveRun('run-a'); mockCanonicalMetadata('run-a'); renderAppAt('/viewer/tour')
    expect(await screen.findByRole('heading', { name: 'Season Hub', level: 2 })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Open Product Run tournaments' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments')
    expect(screen.getByRole('link', { name: 'Open Product Run schedule' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    expectNoLegacyMetadataReads(); expectNoForbiddenViewerActions()
  })
  it('shows active-run Current Week events matching the selected Viewer week', async () => {
    setTestActiveRun('week run')
    const events = [calendarEvent({ event_id: 'MATCHING', event_name: 'Exact selected week', season: '2004/05', season_week: 10 }), calendarEvent({ event_id: 'OTHER-WEEK', event_name: 'Wrong week', season: '2004/05', season_week: 11 }), calendarEvent({ event_id: 'OTHER-SEASON', event_name: 'Wrong season', season: '2005/06', season_week: 10 })]
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar(events, 'week run'))
    renderAppAt('/viewer/tour/current-week')
    expect(await screen.findByRole('link', { name: 'Exact selected week' })).toHaveAttribute('href', '/viewer/runs/week%20run/calendar/MATCHING')
    expect(screen.queryByRole('link', { name: 'Wrong week' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Wrong season' })).not.toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled(); expectNoForbiddenViewerActions()
  })

  it.each(['/viewer/tour/tournaments', '/viewer/tournaments'] as const)('shows canonical tournament catalog metadata on %s', async (route) => {
    setTestActiveRun('run-a'); mockCanonicalMetadata('run-a'); renderAppAt(route)
    expect(await screen.findByRole('heading', { name: 'All Tournaments', level: 2 })).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Saved tournaments' })
    expect(within(table).getByRole('link', { name: 'Published Open' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar/EVENT-LATEST')
    expect(within(table).getByRole('link', { name: 'P1' })).toHaveAttribute('href', '/viewer/runs/run-a/players/P1/career')
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run-a')
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run-a')
    expectNoLegacyMetadataReads(); expectNoForbiddenViewerActions()
  })

  it('shows conservative active-run Tour deferred subpages with safe source links only', async () => {
    setTestActiveRun('run-a')
    const routes = [
      ['/viewer/tour/matches', 'Match Center'],
      ['/viewer/tour/categories', 'Tournament Categories'],
      ['/viewer/tour/champions', 'Past Champions']
    ] as const

    for (const [route, title] of routes) {
      cleanup()
      setTestActiveRun('run-a')
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument()
      expectNoForbiddenViewerActions()
    }
  })
  it('shows active-run top-level tournament and current-week empty states without event metadata', async () => {
    setTestActiveRun('run-a')
    api.getViewerRunCalendar.mockResolvedValue({ ...savedCalendar([], 'run-a'), viewer_branch_id: 'run-a-official' })
    api.getViewerTournamentHistory.mockResolvedValue({ ...savedHistory([], 'run-a'), viewer_branch_id: 'run-a-official' })
    renderAppAt('/viewer/tour/tournaments')
    expect(await screen.findByText('The saved calendar has no tournaments.')).toBeInTheDocument()
    cleanup(); renderAppAt('/viewer/tour/current-week')
    expect(await screen.findByText('No canonical events are scheduled for this selected week.')).toBeInTheDocument()
    expectNoLegacyMetadataReads(); expectNoForbiddenViewerActions()
  })

  it('links top-level History activity, week, tournament, and snapshot metadata safely', async () => {
    setTestActiveRun('run-a')
    renderAppAt('/viewer/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('does not invent History links from unverified legacy activity records', async () => {
    setTestActiveRun('run-a')
    api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [{ event_id: 'UNVERIFIED-ACTIVITY', payload: { raw_secret: 'secret' } }] })
    renderAppAt('/viewer/history')
    expect(await screen.findByRole('heading', { name: 'History', level: 2 })).toBeInTheDocument()
    expect(await screen.findByText('Published history')).toBeInTheDocument()
    expect(api.getRunActivity).not.toHaveBeenCalled()
    expect(screen.queryByText('UNVERIFIED-ACTIVITY')).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent(/raw_secret|UNVERIFIED-ACTIVITY/)
    expectNoForbiddenViewerActions()
  })

  it('shows active-run Records and Stats source metadata with deferred groups and safe links', async () => {
    for (const [route, title] of [['/viewer/records', 'Records'], ['/viewer/stats', 'Stats']]) {
      cleanup(); resetApiMocks(); setTestActiveRun('record run'); mockCanonicalMetadata('record run')
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      const metadata = await screen.findByLabelText(title + ' canonical Product Run metadata summary')
      expect(await within(metadata).findByRole('link', { name: 'Published Open' })).toHaveAttribute('href', '/viewer/runs/record%20run/tournaments/EVENT-LATEST')
      expect(metadata).toHaveTextContent('Completed tournaments1')
      expect(metadata).toHaveTextContent('Official Ranking publications1')
      expect(metadata).toHaveTextContent('Finals Race publications1')
      expect(within(metadata).getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/record%20run/race')
      expectNoLegacyMetadataReads(); expectNoForbiddenViewerActions()
    }
  })


  it('renders conservative deferred Stats/Records subpages without active run data', async () => {
    const routes = [
      ['/viewer/stats/title-leaders', 'Title Leaders', 'No title leader table is shown until a real records read model exists.'],
      ['/viewer/stats/no1-weeks', 'Weeks at No.1', 'No weeks-at-No.1 table is shown until a real ranking history read model exists.'],
      ['/viewer/stats/streaks', 'Streaks', 'No streak table is shown until a real streak records read model exists.'],
      ['/viewer/stats/upsets', 'Biggest Upsets', 'No upset table is shown until real match and ranking history read models exist.'],
      ['/viewer/stats/best-seasons', 'Best Seasons', 'No best-season table is shown until a real season statistics read model exists.'],
      ['/viewer/stats/player-stats', 'Player Stats', 'No player statistics table is shown until a real player statistics read model exists.'],
      ['/viewer/stats/tournament-stats', 'Tournament Stats', 'No tournament statistics table is shown until a real tournament statistics read model exists.'],
      ['/viewer/stats/country-stats', 'Country Stats', 'No country statistics table is shown until a real country statistics read model exists.'],
      ['/viewer/stats/awards', 'Awards', 'No awards are shown until a real awards read model exists.'],
      ['/viewer/stats/hall-of-fame', 'Hall of Fame', 'No Hall of Fame entries are shown until a real Hall of Fame read model exists.'],
      ['/viewer/stats/era-rankings', 'Era Rankings', 'No era rankings are shown until a real era comparison read model exists.']
    ] as const

    for (const [route, title] of routes) {
      cleanup()
      resetApiMocks()
      clearTestActiveRun()
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      await expectNoSelectedRunNotice()
      expect(api.getRunStatusSummary).not.toHaveBeenCalled()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run metadata, safe links, and route-specific deferred copy on Stats/Records subpages', async () => {
    const routes = [
      ['/viewer/stats/title-leaders', 'Title Leaders', 'No title leader table is shown until a real records read model exists.'],
      ['/viewer/stats/no1-weeks', 'Weeks at No.1', 'No weeks-at-No.1 table is shown until a real ranking history read model exists.'],
      ['/viewer/stats/streaks', 'Streaks', 'No streak table is shown until a real streak records read model exists.'],
      ['/viewer/stats/upsets', 'Biggest Upsets', 'No upset table is shown until real match and ranking history read models exist.'],
      ['/viewer/stats/best-seasons', 'Best Seasons', 'No best-season table is shown until a real season statistics read model exists.'],
      ['/viewer/stats/player-stats', 'Player Stats', 'No player statistics table is shown until a real player statistics read model exists.'],
      ['/viewer/stats/tournament-stats', 'Tournament Stats', 'No tournament statistics table is shown until a real tournament statistics read model exists.'],
      ['/viewer/stats/country-stats', 'Country Stats', 'No country statistics table is shown until a real country statistics read model exists.'],
      ['/viewer/stats/awards', 'Awards', 'No awards are shown until a real awards read model exists.'],
      ['/viewer/stats/hall-of-fame', 'Hall of Fame', 'No Hall of Fame entries are shown until a real Hall of Fame read model exists.'],
      ['/viewer/stats/era-rankings', 'Era Rankings', 'No era rankings are shown until a real era comparison read model exists.']
    ] as const

    for (const [route, title, deferredCopy] of routes) {
      cleanup(); resetApiMocks(); setTestActiveRun('metadata run'); mockCanonicalMetadata('metadata run')
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(screen.getByText(deferredCopy)).toBeInTheDocument()
      const metadata = await screen.findByLabelText(title + ' source metadata')
      expect(await within(metadata).findByRole('link', { name: 'Published Open' })).toHaveAttribute('href', '/viewer/runs/metadata%20run/tournaments/EVENT-LATEST')
      expect(metadata).toHaveTextContent('Product Runmetadata run')
      expect(metadata).toHaveTextContent('Completed tournaments1')
      expect(metadata).toHaveTextContent('Official Ranking publications1')
      expect(metadata).toHaveTextContent('Finals Race publications1')
      expect(within(metadata).getByRole('link', { name: 'Season 29 W1 · #1769' })).toHaveAttribute('href', '/viewer/runs/metadata%20run/rankings/1769')
      expectNoLegacyMetadataReads()
      expect(document.body).not.toHaveTextContent(/raw_secret|Fake record holder|GOAT ranking payload|invented winner|award payload/)
      expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run History Records and Stats empty metadata states without fake leaders', async () => {
    setTestActiveRun('run-a')
    api.getViewerRunCalendar.mockResolvedValue({ ...savedCalendar([], 'run-a'), viewer_branch_id: 'run-a-official' })
    api.getViewerTournamentHistory.mockResolvedValue({ ...savedHistory([], 'run-a'), viewer_branch_id: 'run-a-official' })
    api.listViewerOfficialRankingHistory.mockResolvedValue({ ...savedRankings(), product_run_id: 'run-a', viewer_branch_id: 'run-a-official', public_head_ordinal: 1768 })
    for (const route of ['/viewer/history', '/viewer/records', '/viewer/stats']) {
      cleanup(); renderAppAt(route)
      expect(await screen.findByRole('heading', { level: 2, name: route === '/viewer/history' ? 'History' : route === '/viewer/records' ? 'Records' : 'Stats' })).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Published Open' })).not.toBeInTheDocument()
      expect(document.body).not.toHaveTextContent(/Fake record holder|invented winner|fake leader|raw_secret/)
      expectNoLegacyMetadataReads(); expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run top-level Players metadata without redirecting to the run-scoped page', async () => {
    setTestActiveRun('people run')
    api.getViewerPlayers.mockResolvedValue(publicRoster('people run', [publicPlayer()]))
    renderAppAt('/viewer/players')
    const table = await screen.findByRole('table', { name: 'Saved player directory' })
    expect(within(table).getByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/people%20run/players/P1/career')
    expect(within(table).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/people%20run/countries/EGY')
    expect(api.getViewerPlayers).toHaveBeenCalledWith('people run')
    expect(api.listRunPlayers).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Open Product Run players' })).toHaveAttribute('href', '/viewer/runs/people%20run/players')
    expectNoForbiddenViewerActions()
  })

  it('shows active-run top-level Countries metadata without redirecting to the run-scoped page', async () => {
    setTestActiveRun('people run'); api.getViewerCountries.mockResolvedValue(publicCountries('people run', [publicCountry()]))
    renderAppAt('/viewer/countries')
    const panel = await screen.findByLabelText('Countries canonical Product Run summary')
    expect(await within(panel).findByRole('link', { name: 'Player One' })).toHaveAttribute('href', '/viewer/runs/people%20run/players/P1/career')
    expect(within(panel).getAllByRole('link', { name: 'EGY' })[0]).toHaveAttribute('href', '/viewer/runs/people%20run/countries/EGY')
    expect(api.getViewerCountries).toHaveBeenCalledWith('people run'); expect(api.listRunNations).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })


  it('rejects malformed public player identities and never links country fields without IDs', async () => {
    setTestActiveRun('people run')
    api.getViewerPlayers.mockResolvedValue(publicRoster('people run', [publicPlayer('', 'Unknown Player')]))
    renderAppAt('/viewer/players')
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid or foreign source data')
    expect(screen.queryByRole('link', { name: 'Unknown Player' })).not.toBeInTheDocument()
    cleanup()
    api.getViewerCountries.mockResolvedValue(publicCountries('people run', [{ ...publicCountry(), country_code: '', top_player_id: null, top_player_name: 'Unknown Top Player' }]))
    renderAppAt('/viewer/countries')
    expect(await screen.findByText('Unknown Top Player')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Unknown Top Player' })).not.toBeInTheDocument()
    expect(document.querySelector('a[href$="/countries/"]')).toBeNull()
    expectNoForbiddenViewerActions()
  })

  it('shows empty states on active-run top-level Players and Countries hubs without metadata', async () => {
    setTestActiveRun('run-a'); renderAppAt('/viewer/players')
    expect(await screen.findByText('No Saved players exist in this Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Product Run players' })).toHaveAttribute('href', '/viewer/runs/run-a/players')
    cleanup(); renderAppAt('/viewer/countries')
    expect(await screen.findByText('No canonical countries are available for this Product Run yet.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Product Run countries' })).toHaveAttribute('href', '/viewer/runs/run-a/countries')
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer ranking and race snapshot pages', async () => {
    setTestActiveRun('run-a')

    renderAppAt('/viewer/runs/run-a/rankings')
    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()

    cleanup()
    renderAppAt('/viewer/runs/run-a/race')
    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('offers the real Saved Calendar link without changing source data when the Viewer week changes', async () => {
    setTestActiveRun('run-a'); const user = userEvent.setup(); renderAppAt('/viewer/tour/calendar')
    expect(await screen.findByRole('link', { name: 'Open active run schedule' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar')
    await chooseViewerWeek(user, 24)
    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
    expect(localStorage.getItem('beta_engine:viewer_context')).toContain('24')
    expectNoLegacyMetadataReads(); expectNoForbiddenViewerActions()
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
      '/viewer/tour/matches',
      '/viewer/tour/categories',
      '/viewer/tour/champions',
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
    expect(await screen.findByRole('heading', { name: 'Season Calendar', level: 2 })).toBeInTheDocument()
    const list = await screen.findByRole('list', { name: 'Viewer season calendar events 2029/30' })
    expect(within(list).getByRole('link', { name: 'Open planned event' })).toHaveAttribute('href', '/viewer/runs/run-a/calendar/E1?season=2029%2F30&week=2')
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run-a'); expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer tournaments/events page', async () => {
    renderAppAt('/viewer/runs/run-a/tournaments')

    expect(await screen.findByText('Tournaments', { selector: 'h2' })).toBeInTheDocument()
    expect(screen.getByText(/Canonical multi-season tournament schedule and saved results for the selected Viewer Branch/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer players page', async () => {
    renderAppAt('/viewer/runs/run-a/players')
    expect(await screen.findByRole('heading', { name: 'Players', level: 2 })).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledWith('run-a')
    expect(screen.getByLabelText('Viewer Product Run context')).toHaveTextContent('run-a')
    expect(api.listRunPlayers).not.toHaveBeenCalled(); expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer countries/nations page', async () => {
    renderAppAt('/viewer/runs/run-a/countries')
    expect(await screen.findByRole('heading', { name: 'Countries', level: 2 })).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledWith('run-a')
    expect(screen.getByLabelText('Viewer Product Run context')).toHaveTextContent('run-a')
    expect(api.listRunNations).not.toHaveBeenCalled(); expectNoForbiddenViewerActions()
  })

  it('preserves the real run-scoped Viewer history/activity page', async () => {
    setTestActiveRun('run-a')
    renderAppAt('/viewer/runs/run-a/history')

    expect(await screen.findByRole('heading', { name: 'History' })).toBeInTheDocument()
    expect(screen.getByText(/Canonical Saved-Revision sporting publication history/i)).toBeInTheDocument()
    expect(screen.queryByText(/Read-only run activity and season timeline/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('renders sports-facing Viewer Finals summary from existing Finals summary data only', async () => {
    setTestActiveRun('run-a')
    renderAppAt('/viewer/runs/run-a/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Finals Summary' })).toBeInTheDocument()
    expect(await screen.findByText('No canonical World Tour Finals Race publication exists yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('renders Viewer Finals qualification subpage metadata, links, and collapsed technical data', async () => {
    api.getViewerFinalsRace.mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      latest_target_season_index: 30,
      publications: [{
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'run-a',
        viewer_branch_id: 'run-a-official',
        target_season_index: 30,
        cutoff_season_index: 30,
        cutoff_week: 40,
        best_n: 9,
        selection_published: true,
        finals_event_id: 'WTF-2030',
        rows: [{ rank: 1, player_id: 'P1', race_points: 1200, tournaments_counted: 8, finals_selected: true, finals_seed: 1, qualification_source: 'race', counted_results: [] }]
      }]
    })

    renderAppAt('/viewer/runs/run-a/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Qualification Summary' }).closest('article')
    await waitFor(() => expect(summary).toHaveTextContent('run-a-official'))
    expect(summary).toHaveTextContent('30')
    expect(summary).toHaveTextContent('W40')
    expect(summary).toHaveTextContent('1')
    expect(screen.getByRole('table', { name: 'Canonical World Tour Finals participants' })).toHaveTextContent('P1')
    expectNoForbiddenViewerActions()
  })
  it('shows deferred state for missing or unrecognized Viewer Finals qualification data', async () => {
    renderAppAt('/viewer/runs/run-a/finals/qualification')

    expect(await screen.findByRole('heading', { name: 'Finals Qualification' })).toBeInTheDocument()
    expect(await screen.findByText('No canonical World Tour Finals Race publication exists yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('renders Viewer Finals result subpage metadata, player/source links, and collapsed technical data', async () => {
    api.getViewerFinalsRace.mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      latest_target_season_index: 30,
      publications: [{
        schema_version: 'viewer_finals_race_publication.v1',
        product_run_id: 'run-a',
        viewer_branch_id: 'run-a-official',
        target_season_index: 30,
        cutoff_season_index: 30,
        cutoff_week: 40,
        best_n: 9,
        selection_published: true,
        finals_event_id: 'WTF-2030',
        rows: []
      }]
    })
    api.getViewerTournamentResult.mockResolvedValue({
      schema_version: 'viewer_tournament_result.v1',
      product_run_id: 'run-a',
      viewer_branch_id: 'run-a-official',
      event_id: 'WTF-2030',
      completed_season_index: 30,
      completed_week: 41,
      champion_player_id: 'P1',
      finalist_player_id: 'P2',
      qualification_winner_ids: [],
      players: [],
      matches: []
    })

    renderAppAt('/viewer/runs/run-a/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals Result' })).toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Canonical Finals Result' }).closest('article')
    await waitFor(() => expect(summary).toHaveTextContent('WTF-2030'))
    expect(summary).toHaveTextContent('P1')
    expect(summary).toHaveTextContent('P2')
    expect(within(summary as HTMLElement).getByRole('link', { name: 'WTF-2030' })).toHaveAttribute('href', '/viewer/runs/run-a/tournaments/WTF-2030')
    expectNoForbiddenViewerActions()
  })
  it('shows deferred state for missing or unrecognized Viewer Finals result data', async () => {
    renderAppAt('/viewer/runs/run-a/finals/result')

    expect(await screen.findByRole('heading', { name: 'Finals Result' })).toBeInTheDocument()
    expect(await screen.findByText('No canonical World Tour Finals Race publication exists yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
  it('shows deferred states when Viewer Finals qualification and result data are missing', async () => {
    renderAppAt('/viewer/runs/run-a/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(await screen.findByText('No canonical World Tour Finals Race publication exists yet.')).toBeInTheDocument()
    expect(screen.getByText('Confirmed World Tour Finals participants are not published yet.')).toBeInTheDocument()
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

  it('keeps context-aware mode switcher mappings identity-safe across Viewer and Admin routes', async () => {
    const context = { activeProductRunId: 'product A', activeLegacySimulationRunId: 'legacy A' }
    expect(getModeSwitcherTarget('/viewer/runs/product%20A/calendar', context).adminTarget).toBe('/admin/runs/product%20A/branches')
    expect(getModeSwitcherTarget('/admin/runs/legacy%20A/calendar', context).viewerTarget).toBe('/viewer/runs/product%20A/rankings')
    expect(getModeSwitcherTarget('/admin/runs/foreign/calendar', context).viewerTarget).toBe('/viewer/runs')
    for (const [route, target] of [['/viewer/players', '/admin/players'], ['/viewer/countries', '/admin/world/countries'], ['/viewer/tour', '/admin/tour-seasons']]) {
      expect(getModeSwitcherTarget(route, context).adminTarget).toBe(target)
    }
    renderAppAt('/viewer')
    expect(await screen.findByTestId('viewer-primary-nav')).toBeInTheDocument()
    expect(within(screen.getByLabelText('Mode switcher')).getByRole('link', { name: 'Admin / Engine' })).toHaveAttribute('href', '/admin')
    expectNoForbiddenViewerActions()
  })


  it('renders conservative deferred Rankings subpages without active run data', async () => {
    const routes = [
      ['/viewer/rankings/next-gen', 'Next Gen Race'],
      ['/viewer/rankings/elo', 'Elo Ranking'],
      ['/viewer/rankings/power', 'Power Rating'],
      ['/viewer/rankings/form', 'Form Ranking'],
      ['/viewer/rankings/no1-history', 'No.1 History']
    ] as const

    for (const [route, title] of routes) {
      cleanup()
      resetApiMocks()
      clearTestActiveRun()
      renderAppAt(route)

      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      await expectNoSelectedRunNotice()
      expect(api.getRunStatusSummary).not.toHaveBeenCalled()
      expect(api.listRankingSnapshots).not.toHaveBeenCalled()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run metadata, safe links, and route-specific deferred copy on Rankings subpages', async () => {
    const routes = [
      ['/viewer/rankings/next-gen', 'Next Gen Race', 'No Next Gen ranking table is shown until a real Next Gen ranking read model exists.'],
      ['/viewer/rankings/elo', 'Elo Ranking', 'No Elo ranking table is shown until a real Elo ranking read model exists.'],
      ['/viewer/rankings/power', 'Power Rating', 'No Power Rating table is shown until a real Power Rating read model exists.'],
      ['/viewer/rankings/form', 'Form Ranking', 'No form ranking table is shown until a real form ranking read model exists.'],
      ['/viewer/rankings/no1-history', 'No.1 History', 'No No.1 history table is shown until a real ranking history read model exists.']
    ] as const

    for (const [route, title, deferredCopy] of routes) {
      cleanup(); resetApiMocks(); setTestActiveRun('metadata run'); mockCanonicalMetadata('metadata run')
      renderAppAt(route)
      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(screen.getByText(deferredCopy)).toBeInTheDocument()
      const metadata = await screen.findByLabelText(title + ' source metadata')
      expect(await within(metadata).findByRole('link', { name: 'Published Open' })).toHaveAttribute('href', '/viewer/runs/metadata%20run/tournaments/EVENT-LATEST')
      expect(metadata).toHaveTextContent('Product Runmetadata run')
      expect(metadata).toHaveTextContent('Completed tournaments1')
      expect(metadata).toHaveTextContent('Official Ranking publications1')
      expect(metadata).toHaveTextContent('Finals Race publications1')
      expect(within(metadata).getByRole('link', { name: 'Season 29 W1 · #1769' })).toHaveAttribute('href', '/viewer/runs/metadata%20run/rankings/1769')
      expectNoLegacyMetadataReads()
      expect(document.body).not.toHaveTextContent(/raw_secret|Fake record holder|GOAT ranking payload|invented winner|award payload/)
      expectNoForbiddenViewerActions()
    }
  })


  it('renders conservative deferred Players subpages without active run data', async () => {
    const routes = [
      ['/viewer/players/all', 'All Players'],
      ['/viewer/players/active', 'Active Players'],
      ['/viewer/players/retired', 'Retired Players']
    ] as const

    for (const [route, title] of routes) {
      cleanup()
      resetApiMocks()
      clearTestActiveRun()
      renderAppAt(route)

      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
      expect(api.listRunPlayers).not.toHaveBeenCalled()
      expect(api.getRunStatusSummary).not.toHaveBeenCalled()
      expect(api.listEvents).not.toHaveBeenCalled()
      expect(api.listRankingSnapshots).not.toHaveBeenCalled()
      expect(api.listRaceSnapshots).not.toHaveBeenCalled()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run metadata, safe links, samples, and route-specific deferred copy on Players subpages', async () => {
    const routes = [
      ['/viewer/players/all', 'All Players', 'No full player directory is shown until a real player directory read model exists.'],
      ['/viewer/players/active', 'Active Players', 'No active-player list is shown until a real player status read model exists.'],
      ['/viewer/players/retired', 'Retired Players', 'No retired-player list is shown until a real player career-status read model exists.']
    ] as const

    for (const [route, title, deferredCopy] of routes) {
      cleanup()
      resetApiMocks()
      setTestActiveRun('phase-3ak-run')
      api.listRunPlayers.mockResolvedValue({
        run_id: 'phase-3ak-run',
        total: 124,
        limit: 50,
        offset: 0,
        players: [
          {
            player_id: 'P-A',
            name: 'Actual Player A',
            country_code: 'EG',
            age: 24,
            source_type: 'planner_generated',
            override_id: 'hidden-override',
            quality_band: 'elite',
            is_top_band: true,
            origin_source_type: 'manual_override',
            origin_quality_band: 'hidden-origin-band',
            origin_override_id: 'hidden-origin-override',
            origin_season: 2030,
            technique: 81,
            movement: 82,
            physical: 83,
            mental: 84,
            overall: 85
          },
          {
            player_id: 'P-B',
            name: 'Actual Player B',
            country_code: 'NZ',
            age: 29,
            source_type: 'manual_override',
            override_id: null,
            quality_band: null,
            is_top_band: false,
            origin_source_type: null,
            origin_quality_band: null,
            origin_override_id: null,
            origin_season: null,
            technique: 71,
            movement: 72,
            physical: 73,
            mental: 74,
            overall: 75
          }
        ]
      })
      api.getRunStatusSummary.mockResolvedValue({
        run_id: 'phase-3ak-run',
        season: 2034,
        seed: 33,
        progress: { next_event_index: 2, total_events: 5, completed_event_count: 2 },
        finals: { qualification_available: false, result_available: false },
        rollover: null,
        source: { source_type: 'fresh_seed', parent_run_id: null },
        lineage: { child_run_count: 0 },
        history_counts: { events: 2, ranking_snapshots: 3, race_snapshots: 4 }
      })
      api.listEvents.mockResolvedValue({
        run_id: 'phase-3ak-run',
        events: [
          { event_sequence: 1, event_id: 'EVENT-A', season: 2034, week: 2, template_id: 'TEMP-A', tournament_result: { raw_secret: 'hidden event payload' } },
          { event_sequence: 2, event_id: 'EVENT-B', season: 2034, week: 4, template_id: 'TEMP-B', tournament_result: { raw_secret: 'hidden event payload' } }
        ]
      })
      api.listRankingSnapshots.mockResolvedValue({ run_id: 'phase-3ak-run', snapshots: [
        { snapshot_sequence: 1, snapshot_kind: 'ranking', source_event_id: 'EVENT-A', payload: { raw_secret: 'hidden ranking payload' } },
        { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden ranking payload' } },
        { snapshot_sequence: 3, snapshot_kind: 'ranking', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden ranking payload' } }
      ] })
      api.listRaceSnapshots.mockResolvedValue({ run_id: 'phase-3ak-run', snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVENT-A', payload: { raw_secret: 'hidden race payload' } },
        { snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } },
        { snapshot_sequence: 6, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } },
        { snapshot_sequence: 7, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } }
      ] })

      renderAppAt(route)

      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(screen.getByText(deferredCopy)).toBeInTheDocument()
      const metadata = await screen.findByLabelText(`${title} source metadata`)
      expect(metadata).toHaveTextContent('Active run IDphase-3ak-run')
      expect(metadata).toHaveTextContent('Total player count124')
      expect(metadata).toHaveTextContent('Returned/sample player count2/2')
      expect(metadata).toHaveTextContent('Completed/persisted event count2')
      expect(metadata).toHaveTextContent('Ranking snapshot count3')
      expect(metadata).toHaveTextContent('Race snapshot count4')

      const samples = screen.getByLabelText(`${title} safe sample players`)
      expect(within(samples).getByRole('link', { name: 'Actual Player A' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/players/P-A/career')
      expect(within(samples).getByRole('link', { name: 'P-A' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/players/P-A/career')
      expect(within(samples).getByRole('link', { name: 'EG' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/countries/EG')
      expect(samples).toHaveTextContent('Age24')
      expect(samples).toHaveTextContent('Power Rating85')
      expect(samples).toHaveTextContent('Quality bandelite')

      expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/players')
      expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/countries')
      expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/rankings')
      expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/phase-3ak-run/tournaments')
      expect(screen.getByRole('link', { name: 'Open Viewer search' })).toHaveAttribute('href', '/viewer/search')
      expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')
      expect(document.body).not.toHaveTextContent(/source_type|origin_source_type|override_id|origin_override_id|raw_secret|hidden event payload|hidden ranking payload|hidden race payload/i)
      expect(document.body).not.toHaveTextContent(/Player Directory Row|Active status value|Retired status value|Prospect score|Form score value|Player bio|Awards list|Storyline card|Fake player list/i)
      expectNoForbiddenViewerActions()
    }
  })


  it('renders conservative Country Ranking without active run data', async () => {
    clearTestActiveRun()
    renderAppAt('/viewer/countries/ranking')

    expect(await screen.findByRole('heading', { name: 'Country Ranking', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(api.listRunNations).not.toHaveBeenCalled()
    expect(api.getRunStatusSummary).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders conservative deferred Countries subpages without active run data', async () => {
    const routes = [
      ['/viewer/countries/all', 'All Countries'],
      ['/viewer/countries/hosting', 'Hosting Nations'],
      ['/viewer/countries/talent-pipeline', 'Talent Pipeline'],
      ['/viewer/countries/records', 'Country Records']
    ] as const

    for (const [route, title] of routes) {
      cleanup()
      resetApiMocks()
      clearTestActiveRun()
      renderAppAt(route)

      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(screen.getByText('No data is available for this run yet.')).toBeInTheDocument()
      expect(api.listRunNations).not.toHaveBeenCalled()
      expect(api.getRunStatusSummary).not.toHaveBeenCalled()
      expect(api.listEvents).not.toHaveBeenCalled()
      expect(api.listRankingSnapshots).not.toHaveBeenCalled()
      expect(api.listRaceSnapshots).not.toHaveBeenCalled()
      expectNoForbiddenViewerActions()
    }
  })

  it('shows active-run metadata, safe links, samples, and deferred copy on Country Ranking', async () => {
    setTestActiveRun('phase-3ap-run')
    api.listRunNations.mockResolvedValue({
      run_id: 'phase-3ap-run',
      total: 64,
      limit: 50,
      offset: 0,
      nations: [
        {
          country_code: 'EG',
          country_name: 'Egypt',
          total_players: 18,
          average_overall: 82.5,
          manual_override_count: 99,
          planner_generated_count: 101,
          rollover_carried_count: 77,
          top_player_id: 'ALI-1',
          top_player_name: 'Ali Farag',
          top_player_overall: 94
        },
        {
          country_code: 'NZ',
          country_name: 'New Zealand',
          total_players: 6,
          average_overall: 76.25,
          manual_override_count: 0,
          planner_generated_count: 6,
          rollover_carried_count: 0,
          top_player_id: null,
          top_player_name: 'Known Top Name',
          top_player_overall: 88
        }
      ]
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'phase-3ap-run',
      season: 2036,
      seed: 45,
      progress: { next_event_index: 2, total_events: 5, completed_event_count: 2 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: { source_type: 'fresh_seed', parent_run_id: null },
      lineage: { child_run_count: 0 },
      history_counts: { events: 2, ranking_snapshots: 3, race_snapshots: 4 }
    })
    api.listEvents.mockResolvedValue({
      run_id: 'phase-3ap-run',
      events: [
        { event_sequence: 1, event_id: 'EVENT-A', season: 2036, week: 2, template_id: 'TEMP-A', tournament_result: { raw_secret: 'hidden event payload' } },
        { event_sequence: 2, event_id: 'EVENT-B', season: 2036, week: 4, template_id: 'TEMP-B', tournament_result: { raw_secret: 'hidden event payload' } }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({ run_id: 'phase-3ap-run', snapshots: [
      { snapshot_sequence: 1, snapshot_kind: 'ranking', source_event_id: 'EVENT-A', payload: { raw_secret: 'hidden ranking payload' } },
      { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden ranking payload' } },
      { snapshot_sequence: 3, snapshot_kind: 'ranking', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden ranking payload' } }
    ] })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'phase-3ap-run', snapshots: [
      { snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVENT-A', payload: { raw_secret: 'hidden race payload' } },
      { snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } },
      { snapshot_sequence: 6, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } },
      { snapshot_sequence: 7, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } }
    ] })

    renderAppAt('/viewer/countries/ranking')

    expect(await screen.findByRole('heading', { name: 'Country Ranking', level: 2 })).toBeInTheDocument()
    expect(screen.getByText('No country ranking table is shown until a real country ranking read model exists.')).toBeInTheDocument()
    const metadata = await screen.findByLabelText('Country Ranking source metadata')
    expect(metadata).toHaveTextContent('Active run IDphase-3ap-run')
    expect(metadata).toHaveTextContent('Total country/nation count64')
    expect(metadata).toHaveTextContent('Returned/sample country count2/2')
    expect(metadata).toHaveTextContent('Completed/persisted event count2')
    expect(metadata).toHaveTextContent('Ranking snapshot count3')
    expect(metadata).toHaveTextContent('Race snapshot count4')

    const samples = screen.getByLabelText('Country Ranking safe sample countries')
    expect(within(samples).getByRole('link', { name: 'EG' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/countries/EG')
    expect(within(samples).getByRole('link', { name: 'Egypt' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/countries/EG')
    expect(within(samples).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/players/ALI-1/career')
    expect(samples).toHaveTextContent('Player count18')
    expect(samples).toHaveTextContent('Average Power Rating82.5')
    expect(samples).toHaveTextContent('Top player Power Rating94')
    expect(within(samples).queryByRole('link', { name: 'Known Top Name' })).not.toBeInTheDocument()

    expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/countries')
    expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/players')
    expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/rankings')
    expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/phase-3ap-run/tournaments')
    expect(screen.getByRole('link', { name: 'Open Viewer search' })).toHaveAttribute('href', '/viewer/search')
    expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.listRunNations).toHaveBeenCalledWith('phase-3ap-run', { limit: 50, offset: 0 })
    expect(document.body).not.toHaveTextContent(/manual_override_count|planner_generated_count|rollover_carried_count|raw_secret|hidden event payload|hidden ranking payload|hidden race payload/i)
    expect(document.body).not.toHaveTextContent(/Fake country ranking row|ranking position|medal table|award winner|Country record value|Talent pipeline rank|Hosting ranking|Storyline card/i)
    expectNoForbiddenViewerActions()
  })

  it('shows active-run metadata, safe links, samples, and route-specific deferred copy on Countries subpages', async () => {
    const routes = [
      ['/viewer/countries/all', 'All Countries', 'No full country directory is shown until a real country directory read model exists.'],
      ['/viewer/countries/hosting', 'Hosting Nations', 'No hosting nation table is shown until a real hosting read model exists.'],
      ['/viewer/countries/talent-pipeline', 'Talent Pipeline', 'No talent pipeline table is shown until a real country talent read model exists.'],
      ['/viewer/countries/records', 'Country Records', 'No country records table is shown until a real country records read model exists.']
    ] as const

    for (const [route, title, deferredCopy] of routes) {
      cleanup()
      resetApiMocks()
      setTestActiveRun('phase-3al-run')
      api.listRunNations.mockResolvedValue({
        run_id: 'phase-3al-run',
        total: 64,
        limit: 50,
        offset: 0,
        nations: [
          {
            country_code: 'EG',
            country_name: 'Egypt',
            total_players: 18,
            average_overall: 82.5,
            average_age: 26.4,
            top_band_count: 5,
            manual_override_count: 99,
            planner_generated_count: 88,
            rollover_carried_count: 77,
            top_player_id: 'ALI-1',
            top_player_name: 'Ali Farag',
            top_player_overall: 94
          },
          {
            country_code: 'NZ',
            country_name: 'New Zealand',
            total_players: 6,
            average_overall: 76.25,
            average_age: 29.1,
            top_band_count: 1,
            manual_override_count: 0,
            planner_generated_count: 6,
            rollover_carried_count: 0,
            top_player_id: null,
            top_player_name: 'Known Top Name',
            top_player_overall: 88
          }
        ]
      })
      api.getRunStatusSummary.mockResolvedValue({
        run_id: 'phase-3al-run',
        season: 2035,
        seed: 44,
        progress: { next_event_index: 2, total_events: 5, completed_event_count: 2 },
        finals: { qualification_available: false, result_available: false },
        rollover: null,
        source: { source_type: 'fresh_seed', parent_run_id: null },
        lineage: { child_run_count: 0 },
        history_counts: { events: 2, ranking_snapshots: 3, race_snapshots: 4 }
      })
      api.listEvents.mockResolvedValue({
        run_id: 'phase-3al-run',
        events: [
          { event_sequence: 1, event_id: 'EVENT-A', season: 2035, week: 2, template_id: 'TEMP-A', tournament_result: { raw_secret: 'hidden event payload' } },
          { event_sequence: 2, event_id: 'EVENT-B', season: 2035, week: 4, template_id: 'TEMP-B', tournament_result: { raw_secret: 'hidden event payload' } }
        ]
      })
      api.listRankingSnapshots.mockResolvedValue({ run_id: 'phase-3al-run', snapshots: [
        { snapshot_sequence: 1, snapshot_kind: 'ranking', source_event_id: 'EVENT-A', payload: { raw_secret: 'hidden ranking payload' } },
        { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden ranking payload' } },
        { snapshot_sequence: 3, snapshot_kind: 'ranking', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden ranking payload' } }
      ] })
      api.listRaceSnapshots.mockResolvedValue({ run_id: 'phase-3al-run', snapshots: [
        { snapshot_sequence: 4, snapshot_kind: 'race', source_event_id: 'EVENT-A', payload: { raw_secret: 'hidden race payload' } },
        { snapshot_sequence: 5, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } },
        { snapshot_sequence: 6, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } },
        { snapshot_sequence: 7, snapshot_kind: 'race', source_event_id: 'EVENT-B', payload: { raw_secret: 'hidden race payload' } }
      ] })

      renderAppAt(route)

      expect(await screen.findByRole('heading', { name: title, level: 2 })).toBeInTheDocument()
      expect(screen.getByText(deferredCopy)).toBeInTheDocument()
      const metadata = await screen.findByLabelText(`${title} source metadata`)
      expect(metadata).toHaveTextContent('Active run IDphase-3al-run')
      expect(metadata).toHaveTextContent('Total country/nation count64')
      expect(metadata).toHaveTextContent('Returned/sample country count2/2')
      expect(metadata).toHaveTextContent('Completed/persisted event count2')
      expect(metadata).toHaveTextContent('Ranking snapshot count3')
      expect(metadata).toHaveTextContent('Race snapshot count4')

      const samples = screen.getByLabelText(`${title} safe sample countries`)
      expect(within(samples).getByRole('link', { name: 'EG' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/countries/EG')
      expect(within(samples).getByRole('link', { name: 'Egypt' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/countries/EG')
      expect(within(samples).getByRole('link', { name: 'Ali Farag' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/players/ALI-1/career')
      expect(samples).toHaveTextContent('Player count18')
      expect(samples).toHaveTextContent('Average Power Rating82.5')
      expect(samples).toHaveTextContent('Top player Power Rating94')
      expect(within(samples).queryByRole('link', { name: 'Known Top Name' })).not.toBeInTheDocument()

      expect(screen.getByRole('link', { name: 'Open active run countries' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/countries')
      expect(screen.getByRole('link', { name: 'Open active run players' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/players')
      expect(screen.getByRole('link', { name: 'Open active run rankings' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/rankings')
      expect(screen.getByRole('link', { name: 'Open active run tournaments' })).toHaveAttribute('href', '/viewer/runs/phase-3al-run/tournaments')
      expect(screen.getByRole('link', { name: 'Open Viewer search' })).toHaveAttribute('href', '/viewer/search')
      expect(screen.getByRole('link', { name: 'Open run browser' })).toHaveAttribute('href', '/viewer/runs')
      expect(api.listRunNations).toHaveBeenCalledWith('phase-3al-run', { limit: 50, offset: 0 })
      expect(document.body).not.toHaveTextContent(/manual_override_count|planner_generated_count|rollover_carried_count|raw_secret|hidden event payload|hidden ranking payload|hidden race payload/i)
      expect(document.body).not.toHaveTextContent(/Fake country ranking|Hosting record row|Talent pipeline rank|Medal table|Award winner|Country record value|Storyline card/i)
      expectNoForbiddenViewerActions()
    }
  })

  it('Admin routes still render', async () => {
    renderAppAt('/admin')
    expect(await screen.findByRole('heading', { name: 'Squash Engine Home' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Global Admin navigation' })).toBeInTheDocument()
    expect(within(screen.getByRole('navigation', { name: 'Global Admin navigation' })).getByRole('link', { name: 'Packages' })).toHaveAttribute('href', '/admin/packages')
    expect(screen.queryByTestId('viewer-primary-nav')).not.toBeInTheDocument()
  })
})
