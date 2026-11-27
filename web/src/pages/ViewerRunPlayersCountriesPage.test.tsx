import { screen, within, act, waitFor } from '@testing-library/react'
import { Route, Routes, useLocation } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createTestQueryClient, makeViewerProductRunRouteTestValue, renderWithViewerProviders } from '../test/viewerTestUtils'
import { LanguageProvider } from '../i18n/LanguageContext'
import { ViewerProductRunRouteContextProvider } from '../viewer/ViewerProductRunRouteContext'
import {
  ViewerRunCountriesPage,
  ViewerRunCountryDetailPage,
  ViewerRunPlayerCareerPage,
  ViewerRunPlayersPage
} from './ViewerRunPlayersCountriesPage'

const api = vi.hoisted(() => ({
  getViewerPlayers: vi.fn(),
  getViewerCountries: vi.fn(),
  listRunPlayers: vi.fn(),
  getRunPlayerDetail: vi.fn(),
  getRunPlayerCareerHistory: vi.fn(),
  getRunPlayerCareerPerformance: vi.fn(),
  getRunPlayerTournamentResults: vi.fn(),
  listRunNations: vi.fn(),
  getRunNationDetail: vi.fn()
}))

vi.mock('../api/client', () => api)

function TestLocation(): JSX.Element {
  const location = useLocation()
  return <output aria-label="Current URL">{location.pathname}{location.search}</output>
}
function renderViewerRoute(route: string, element: JSX.Element, path = '/viewer/runs/:runId/*', branch = 'branch-viewer') {
  const runId = decodeURIComponent(route.split('/')[3])
  const context = makeViewerProductRunRouteTestValue(runId)
  const value = { ...context, officialBranchId: branch,
    officialContext: { ...context.officialContext, product_run_id: runId, official_branch_id: branch } }
  const client = createTestQueryClient()
  const view = renderWithViewerProviders(
    <LanguageProvider><ViewerProductRunRouteContextProvider value={value}>
      <TestLocation /><Routes><Route path={path} element={element} /></Routes>
    </ViewerProductRunRouteContextProvider></LanguageProvider>,
    { route, queryClient: client, includeProductRunRouteContext: false }
  )
  return { ...view, client }
}

const forbiddenLabels = [
  'Simulate',
  'Generate',
  'Persist',
  'Apply',
  'Execute',
  'Delete',
  'Edit',
  'Import',
  'Rollover',
  'Rebuild',
  'Override',
  'Save changes',
  'Commit',
  'Regenerate',
  'Repair',
  'Merge',
  'Overwrite'
]

function expectNoForbiddenViewerActions(): void {
  forbiddenLabels.forEach((label) => {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  })
}

function mockPlayerList(): void {
  api.listRunPlayers.mockResolvedValue({
    run_id: 'viewer-run-2c',
    total: 2,
    limit: 200,
    offset: 0,
    players: [
      {
        player_id: 'EGY-0001',
        name: 'Ali A',
        country_code: 'EGY',
        age: 20,
        source_type: 'planner_generated',
        override_id: null,
        quality_band: 'elite_talent',
        is_top_band: true,
        origin_source_type: 'planner_generated',
        origin_quality_band: 'elite_talent',
        origin_override_id: null,
        origin_season: 2027,
        technique: 70,
        movement: 68,
        physical: 66,
        mental: 65,
        overall: 67,
        secret_debug_marker: 'player-list-payload-should-not-render'
      },
      {
        player_id: 'ENG-0001',
        name: 'Bob B',
        country_code: 'ENG',
        age: 22,
        source_type: 'rollover_carried',
        override_id: null,
        quality_band: null,
        is_top_band: false,
        origin_source_type: null,
        origin_quality_band: null,
        origin_override_id: null,
        origin_season: null,
        technique: 72,
        movement: 71,
        physical: 70,
        mental: 73,
        overall: 72
      }
    ]
  })
}

function mockPlayerDetail(): void {
  api.getRunPlayerDetail.mockResolvedValue({
    player_id: 'EGY-0001',
    name: 'Ali A',
    country_code: 'EGY',
    age: 20,
    play_style: 'attacking',
    archetype: 'shotmaker',
    technique: 70,
    movement: 68,
    physical: 66,
    mental: 65,
    consistency: 64,
    clutch: 63,
    recovery: 62,
    overall: 67,
    hidden_traits: {
      potential_ceiling: 90,
      growth_curve: 'late',
      professionalism: 0.8,
      ambition: 0.7,
      travel_tolerance: 0.6,
      schedule_aggression: 0.7,
      injury_proneness: 0.2,
      resilience: 0.8
    },
    source_type: 'planner_generated',
    quality_band: 'elite_talent',
    is_top_band: true,
    override_id: null,
    origin_source_type: 'planner_generated',
    origin_quality_band: 'elite_talent',
    origin_override_id: null,
    origin_season: 2027,
    talent_seed_value: 101,
    talent_sequence: 1,
    secret_debug_marker: 'player-detail-hidden-payload'
  })
  api.getRunPlayerCareerHistory.mockResolvedValue({
    requested_run_id: 'viewer-run-2c',
    player_id: 'EGY-0001',
    player_name: 'Ali A',
    country_code: 'EGY',
    entries: [
      {
        run_id: 'viewer-run-2c',
        season: 2027,
        age: 20,
        overall: 67,
        technique: 70,
        movement: 68,
        physical: 66,
        mental: 65,
        source_type: 'planner_generated',
        quality_band: 'elite_talent',
        is_top_band: true,
        origin_source_type: 'planner_generated',
        origin_quality_band: 'elite_talent',
        origin_override_id: null,
        origin_season: 2027
      }
    ]
  })
  api.getRunPlayerCareerPerformance.mockResolvedValue({
    requested_run_id: 'viewer-run-2c',
    player_id: 'EGY-0001',
    player_name: 'Ali A',
    country_code: 'EGY',
    entries: [
      {
        run_id: 'viewer-run-2c',
        season: 2027,
        ranking_position: 12,
        race_position: 8,
        tournaments_played: 14,
        titles: 1,
        finals: 2,
        semifinals: 3,
        quarterfinals: 5,
        wins: 28,
        losses: 11
      }
    ]
  })
  api.getRunPlayerTournamentResults.mockResolvedValue({
    requested_run_id: 'viewer-run-2c',
    player_id: 'EGY-0001',
    player_name: 'Ali A',
    country_code: 'EGY',
    entries: [
      {
        run_id: 'viewer-run-2c',
        season: 2027,
        week: 7,
        event_sequence: 1,
        event_id: 'event-cairo-2027',
        event_name: 'Cairo Open',
        event_category: 'gold',
        template_id: 'gold_template',
        finish: 'Final',
        is_title: false,
        wins: 4,
        losses: 1,
        ranking_points_awarded: 700
      },
      {
        run_id: 'viewer-run-2c',
        season: 2027,
        week: 8,
        event_sequence: 2,
        event_id: null,
        event_name: 'Local Showcase',
        event_category: 'silver',
        template_id: 'silver_template',
        finish: 'Quarterfinal',
        is_title: false,
        wins: 2,
        losses: 1,
        ranking_points_awarded: 175
      },
      {
        run_id: 'viewer-run-2c',
        season: 2027,
        week: null,
        event_sequence: 3,
        event_id: null,
        event_name: 'No Week Invitational',
        event_category: 'bronze',
        template_id: null,
        finish: 'R16',
        is_title: false,
        wins: 0,
        losses: 1,
        ranking_points_awarded: null
      }
    ]
  })
}

function mockEmptyPlayerCareerData(): void {
  api.getRunPlayerCareerHistory.mockResolvedValue({
    requested_run_id: 'viewer-run-2c',
    player_id: 'EGY-0001',
    player_name: 'Ali A',
    country_code: 'EGY',
    entries: []
  })
  api.getRunPlayerCareerPerformance.mockResolvedValue({
    requested_run_id: 'viewer-run-2c',
    player_id: 'EGY-0001',
    player_name: 'Ali A',
    country_code: 'EGY',
    entries: []
  })
  api.getRunPlayerTournamentResults.mockResolvedValue({
    requested_run_id: 'viewer-run-2c',
    player_id: 'EGY-0001',
    player_name: 'Ali A',
    country_code: 'EGY',
    entries: []
  })
}

function mockCountries(): void {
  api.listRunNations.mockResolvedValue({
    run_id: 'viewer-run-2c',
    total: 2,
    limit: 300,
    offset: 0,
    nations: [
      {
        country_code: 'EGY',
        country_name: 'Egypt',
        total_players: 5,
        average_overall: 78.4,
        average_age: 25.2,
        top_band_count: 2,
        manual_override_count: 1,
        planner_generated_count: 3,
        rollover_carried_count: 1,
        top_player_id: 'EGY-0001',
        top_player_name: 'Ali A',
        top_player_overall: 91,
        secret_debug_marker: 'country-list-payload-should-not-render'
      },
      {
        country_code: 'USA',
        country_name: 'United States',
        total_players: 0,
        average_overall: null,
        average_age: null,
        top_band_count: 0,
        manual_override_count: 0,
        planner_generated_count: 0,
        rollover_carried_count: 0,
        top_player_id: null,
        top_player_name: null,
        top_player_overall: null
      }
    ]
  })
}

function mockCountryDetail(): void {
  api.getRunNationDetail.mockResolvedValue({
    run_id: 'viewer-run-2c',
    country_code: 'EGY',
    country_name: 'Egypt',
    total_players: 5,
    average_overall: 78.4,
    average_age: 25.2,
    top_band_count: 2,
    manual_override_count: 1,
    planner_generated_count: 3,
    rollover_carried_count: 1,
    average_visible_stats: { technique: 80.1, movement: 79.1, physical: 76.1, mental: 78.1 },
    source_mix: { rollover_carried: 1, planner_generated: 3, manual_override: 1 },
    band_distribution: [{ band: 'top', count: 2 }],
    origin_band_distribution: [{ band: 'elite_talent', count: 2 }],
    top_players: [
      {
        player_id: 'EGY-0001',
        name: 'Ali A',
        age: 24,
        overall: 91,
        source_type: 'planner_generated',
        quality_band: 'top',
        is_top_band: true
      },
      {
        player_id: null,
        name: 'Unlinked Player',
        age: 28,
        overall: 80,
        source_type: 'rollover_carried',
        quality_band: 'contender',
        is_top_band: false
      }
    ],
    secret_debug_marker: 'country-detail-hidden-payload'
  })
}

describe('ViewerRunPlayersPage', () => {
  beforeEach(() => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.resetAllMocks()
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      player_count: 2,
      active_player_count: 2,
      retired_player_count: 0,
      players: [
        { player_id: 'EGY-0001', name: 'Ali A', country_code: 'EGY', age: 20, status: 'active', tour_entry_season_index: 0, tour_entry_week: 1, current_ovr: 167, potential_ovr: null, current_form: null, match_sharpness: null, long_term_fatigue: null, identity_source: 'run_prospect' },
        { player_id: 'ENG-0001', name: 'Bob B', country_code: 'ENG', age: 22, status: 'active', tour_entry_season_index: 0, tour_entry_week: 1, current_ovr: 172, potential_ovr: null, current_form: null, match_sharpness: null, long_term_fatigue: null, identity_source: 'initial_world' }
      ]
    })
  })

  it('renders canonical player metadata and profile links', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledWith('viewer-run-2c')
    const aliRow = (await screen.findByText('Ali A')).closest('tr') as HTMLElement
    expect(within(aliRow).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries/EGY')
    expect(within(aliRow).getByText('20')).toBeInTheDocument()
    expect(within(aliRow).getByText('active')).toBeInTheDocument()
    expect(within(aliRow).getByText('167')).toBeInTheDocument()
    expect(within(aliRow).getByText('run prospect')).toBeInTheDocument()
    expect(within(aliRow).getByRole('link', { name: /Open Player Profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career'
    )
    expectNoForbiddenViewerActions()
  })

  it('bounds a 101-player roster to 50 rows and preserves exact profile links', async () => {
    const original = await api.getViewerPlayers()
    const players = Array.from({ length: 101 }, (_, i) => ({ ...original.players[0],
      player_id: 'P-' + (i + 1), name: 'Player ' + String(i + 1).padStart(3, '0'), current_ovr: 100 }))
    api.getViewerPlayers.mockClear()
    api.getViewerPlayers.mockResolvedValue({ ...original, players, player_count: 101, active_player_count: 101, retired_player_count: 0 })
    const user = userEvent.setup()
    renderViewerRoute('/viewer/runs/viewer-run-2c/players?vpSort=name&vpPage=2&keep=yes', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')
    const table = await screen.findByRole('table', { name: 'Saved Run player directory' })
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    const row = within(table).getByText('Player 051').closest('tr') as HTMLElement
    expect(within(row).getByRole('link', { name: 'Open Player Profile' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players/P-51/career?vpSort=name&vpPage=2&keep=yes')
    await user.click(screen.getByRole('button', { name: 'Next' }))
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('vpPage=3')
    await user.selectOptions(screen.getByLabelText('Identity source'), 'run_prospect')
    expect(screen.getByLabelText('Current URL')).not.toHaveTextContent('vpPage=')
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('keep=yes')
    expect(within(table).getByText('Player 001')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledTimes(1)
  })

  it.each(['vpPage=2', 'vpPage=01', 'vpMinAge=35&vpMaxAge=18', 'vpMinAge=-1', 'vpCountry=EGY&country=ENG'])(
    'rejects invalid or ambiguous directory links: %s', async query => {
      renderViewerRoute('/viewer/runs/viewer-run-2c/players?' + query + '&keep=yes', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')
      expect(await screen.findByRole('alert')).toHaveTextContent('invalid filters or page')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await userEvent.setup().click(screen.getByRole('button', { name: 'Clear filters' }))
      expect(await screen.findByRole('table')).toBeInTheDocument()
      expect(screen.getByLabelText('Current URL')).toHaveTextContent('/players?keep=yes')
    }
  )

  it('retains existing country links and localized controls', async () => {
    localStorage.setItem('squash-engine-language-v1', 'cs')
    renderViewerRoute('/viewer/runs/viewer-run-2c/players?country=EGY', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')
    expect(await screen.findByText('Ali A')).toBeInTheDocument()
    expect(screen.queryByText('Bob B')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Hráči' })).toBeInTheDocument()
    expect(screen.getByLabelText('Země')).toHaveValue('EGY')
  })

  it('keeps the player list page read-only on canonical API error', async () => {
    api.getViewerPlayers.mockRejectedValue(new Error('player list outage'))

    renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByText(/Failed to load canonical players/i)).toBeInTheDocument()
    expect(screen.queryByText(/player list outage/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open Player Profile/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows canonical no-match copy for an empty player list', async () => {
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      player_count: 0,
      active_player_count: 0,
      retired_player_count: 0,
      players: []
    })

    renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByText('No canonical players match these filters.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open Player Profile/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('builds encoded Viewer-only player links from canonical identities', async () => {
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      player_count: 1,
      active_player_count: 1,
      retired_player_count: 0,
      players: [{ player_id: 'P/1 #A', name: 'Encoded Player', country_code: 'CDE', age: 24, status: 'active', tour_entry_season_index: 0, tour_entry_week: 1, current_ovr: 188, potential_ovr: null, current_form: null, match_sharpness: null, long_term_fatigue: null, identity_source: 'initial_world' }]
    })

    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByRole('link', { name: /Open Player Profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career'
    )
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunPlayerCareerPage canonical current profile', () => {
  beforeEach(() => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.resetAllMocks()
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      player_count: 2,
      active_player_count: 1,
      retired_player_count: 1,
      players: [
        {
          player_id: 'EGY-0001',
          name: 'Ali A',
          country_code: 'EGY',
          age: 20,
          status: 'active',
          tour_entry_season_index: 1,
          tour_entry_week: 3,
          current_ovr: 167,
          potential_ovr: null,
          current_form: null,
          match_sharpness: null,
          long_term_fatigue: null,
          identity_source: 'run_prospect'
        },
        {
          player_id: 'ENG-0001',
          name: 'Retired B',
          country_code: 'ENG',
          age: 35,
          status: 'retired',
          tour_entry_season_index: 0,
          tour_entry_week: 1,
          current_ovr: null,
          potential_ovr: null,
          current_form: null,
          match_sharpness: null,
          long_term_fatigue: null,
          identity_source: 'initial_world'
        }
      ]
    })
  })

  it('renders canonical current player profile and defers historical sections', async () => {
    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career',
      <ViewerRunPlayerCareerPage />,
      '/viewer/runs/:runId/players/:playerId/career'
    )

    expect(await screen.findByText('Ali A')).toBeInTheDocument()
    expect(api.getViewerPlayers).toHaveBeenCalledWith('viewer-run-2c')
    expect(await screen.findByText('branch-viewer')).toBeInTheDocument()
    expect(screen.getByText('S2 W7')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Current sporting state' })).toBeInTheDocument()
    expect(screen.getByText('167')).toBeInTheDocument()
    expect(screen.queryByText('185')).not.toBeInTheDocument()
    expect(screen.queryByText('Potential Power Rating')).not.toBeInTheDocument()
    expect(screen.queryByText('Current form')).not.toBeInTheDocument()
    expect(screen.queryByText('Match sharpness')).not.toBeInTheDocument()
    expect(screen.queryByText('Long-term fatigue')).not.toBeInTheDocument()
    expect(screen.getByText('run prospect')).toBeInTheDocument()
    expect(screen.getByText('S1 W3')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'EGY' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/countries/EGY'
    )
    expect(screen.getByRole('link', { name: 'Back to players' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players'
    )
    expect(screen.getByText(/canonical per-player season history is not published yet/i)).toBeInTheDocument()
    expect(screen.getByText(/canonical per-player tournament\/performance history is not published yet/i)).toBeInTheDocument()

    expect(api.getRunPlayerDetail).not.toHaveBeenCalled()
    expect(api.getRunPlayerCareerHistory).not.toHaveBeenCalled()
    expect(api.getRunPlayerCareerPerformance).not.toHaveBeenCalled()
    expect(api.getRunPlayerTournamentResults).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('withholds foreign branch and private fields in public profile data', async () => {
    const roster = await api.getViewerPlayers()
    api.getViewerPlayers.mockResolvedValue({ ...roster, viewer_branch_id: 'other-branch' })
    renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid or belongs to another source')
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
    api.getViewerPlayers.mockResolvedValue({ ...roster, players: roster.players.map((p: object) => ({ ...p, potential_ovr: 199 })) })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry read (GET)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid or belongs to another source')
    expect(screen.queryByText('199')).not.toBeInTheDocument()
    api.getViewerPlayers.mockResolvedValue(roster)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry read (GET)' }))
    expect(await screen.findByText('Ali A')).toBeInTheDocument()
  })

  it('withholds stale profile during refresh and rejects duplicate player identity', async () => {
    const roster = await api.getViewerPlayers()
    const { client } = renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')
    expect(await screen.findByText('Ali A')).toBeInTheDocument()
    let release!: (value: unknown) => void
    api.getViewerPlayers.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
    const refresh = client.invalidateQueries({ queryKey: ['viewer-run-players-canonical', 'viewer-run-2c', 'branch-viewer'] })
    await waitFor(() => expect(screen.queryByText('Ali A')).not.toBeInTheDocument())
    await act(async () => { release({ ...roster, players: [roster.players[0], roster.players[0]], active_player_count: 2, retired_player_count: 0 }); await refresh })
    expect(await screen.findByRole('alert')).toHaveTextContent('invalid or belongs to another source')
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
  })

  it('localizes a retired profile and preserves the directory selection', async () => {
    localStorage.setItem('squash-engine-language-v1', 'cs')
    renderViewerRoute('/viewer/runs/viewer-run-2c/players/ENG-0001/career?vpPage=2&vpSort=age&keep=yes', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')
    expect(await screen.findByText('Retired B')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Profil hráče' })).toBeInTheDocument()
    expect(screen.getByText('po kariéře')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Zpět na hráče' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players?vpPage=2&vpSort=age&keep=yes')
    expect(screen.getByRole('heading', { name: 'Aktuální sportovní stav' }).closest('article')).toHaveTextContent('—')
  })

  it('fails closed when the canonical player id is absent', async () => {
    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/players/UNKNOWN/career',
      <ViewerRunPlayerCareerPage />,
      '/viewer/runs/:runId/players/:playerId/career'
    )

    expect(await screen.findByText(/No canonical player with this ID exists/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Current sporting state' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps current profile unavailable on canonical API failure', async () => {
    api.getViewerPlayers.mockRejectedValue(new Error('canonical player outage'))

    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career',
      <ViewerRunPlayerCareerPage />,
      '/viewer/runs/:runId/players/:playerId/career'
    )

    expect(await screen.findByText(/Failed to load canonical player profile/i)).toBeInTheDocument()
    expect(screen.queryByText(/canonical player outage/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('builds encoded canonical links from route identities', async () => {
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      player_count: 1,
      active_player_count: 1,
      retired_player_count: 0,
      players: [{
        player_id: 'P/1 #A',
        name: 'Encoded Player',
        country_code: 'CDE',
        age: 24,
        status: 'active',
        tour_entry_season_index: null,
        tour_entry_week: null,
        current_ovr: 188,
        potential_ovr: null,
        current_form: null,
        match_sharpness: null,
        long_term_fatigue: null,
        identity_source: 'initial_world'
      }]
    })

    renderViewerRoute(
      '/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career',
      <ViewerRunPlayerCareerPage />,
      '/viewer/runs/:runId/players/:playerId/career'
    )

    expect(await screen.findByText('Encoded Player')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'CDE' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/countries/CDE'
    )
    expectNoForbiddenViewerActions()
  })
})

function countryListRoster(run = 'viewer-run-2c', rows: Array<{
  id: string; name: string; code: string; rating: number; status: 'active' | 'retired'
}> = [
  { id: 'EGY-0001', name: 'Ali A', code: 'EGY', rating: 191, status: 'active' },
  { id: 'EGY-0002', name: 'Egypt Two', code: 'EGY', rating: 180, status: 'active' },
  { id: 'EGY-0003', name: 'Egypt Three', code: 'EGY', rating: 175, status: 'active' },
  { id: 'EGY-0004', name: 'Egypt Four', code: 'EGY', rating: 174, status: 'active' },
  { id: 'EGY-0005', name: 'Egypt Five', code: 'EGY', rating: 172, status: 'retired' },
  { id: 'USA-0001', name: 'US Player', code: 'USA', rating: 150, status: 'active' },
]) {
  const active = rows.filter(row => row.status === 'active').length
  return {
    schema_version: 'viewer_players.v1', product_run_id: run, viewer_branch_id: 'branch-viewer',
    season_index: 2, week: 7, player_count: rows.length, active_player_count: active,
    retired_player_count: rows.length - active,
    players: rows.map(row => ({
      player_id: row.id, name: row.name, country_code: row.code, age: 24, status: row.status,
      tour_entry_season_index: 0, tour_entry_week: 1, current_ovr: row.rating,
      potential_ovr: null, current_form: null, match_sharpness: null,
      long_term_fatigue: null, identity_source: 'initial_world',
    })),
  }
}

describe('ViewerRunCountriesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getViewerPlayers.mockResolvedValue(countryListRoster())
    api.getViewerCountries.mockResolvedValue({
      schema_version: 'viewer_countries.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      country_count: 2,
      countries: [
        { country_code: 'EGY', player_count: 5, active_player_count: 4, retired_player_count: 1, average_current_ovr: 178.4, top_player_id: 'EGY-0001', top_player_name: 'Ali A', top_player_current_ovr: 191 },
        { country_code: 'USA', player_count: 1, active_player_count: 1, retired_player_count: 0, average_current_ovr: 150, top_player_id: 'USA-0001', top_player_name: 'US Player', top_player_current_ovr: 150 }
      ]
    })
  })

  it('renders canonical country metadata with profile links', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('columnheader', { name: 'Country' })).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledWith('viewer-run-2c')
    const egyptRow = screen.getByText('EGY').closest('tr') as HTMLElement
    expect(within(egyptRow).getByText('5')).toBeInTheDocument()
    expect(within(egyptRow).getByText('4')).toBeInTheDocument()
    expect(within(egyptRow).getByText('1')).toBeInTheDocument()
    expect(within(egyptRow).getByText('178.40')).toBeInTheDocument()
    expect(within(egyptRow).getByRole('link', { name: /Ali A/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players/EGY-0001/career')
    expect(within(egyptRow).getByRole('link', { name: /Open country profile/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries/EGY')
    expectNoForbiddenViewerActions()
  })

  it('keeps the country list page read-only on canonical API error', async () => {
    api.getViewerCountries.mockRejectedValue(new Error('country list outage'))

    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByText(/Failed to load canonical countries/i)).toBeInTheDocument()
    expect(screen.queryByText(/country list outage/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows canonical no-match copy for an empty country list', async () => {
    api.getViewerPlayers.mockResolvedValue(countryListRoster('viewer-run-2c', []))
    api.getViewerCountries.mockResolvedValue({
      schema_version: 'viewer_countries.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      country_count: 0,
      countries: []
    })

    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByText('No canonical countries match these filters.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('rejects a country projection from a different branch or clock instead of displaying its rows', async () => {
    api.getViewerCountries.mockResolvedValueOnce({
      schema_version: 'viewer_countries.v1', product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'foreign-branch', season_index: 2, week: 7,
      country_count: 0, countries: [],
    })
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')
    expect(await screen.findByRole('alert')).toHaveTextContent('Saved country and player sources do not match')
    expect(screen.queryByText('foreign-branch')).not.toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('builds encoded Viewer-only country links from canonical identities', async () => {
    api.getViewerPlayers.mockResolvedValue(countryListRoster('run/alpha #1', [
      { id: 'P/1 #A', name: 'Encoded Player', code: 'CDE', rating: 188, status: 'active' },
    ]))
    api.getViewerCountries.mockResolvedValue({
      schema_version: 'viewer_countries.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      country_count: 1,
      countries: [{ country_code: 'CDE', player_count: 1, active_player_count: 1, retired_player_count: 0, average_current_ovr: 188, top_player_id: 'P/1 #A', top_player_name: 'Encoded Player', top_player_current_ovr: 188 }]
    })

    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('link', { name: /Open country profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/countries/CDE'
    )
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunCountryDetailPage canonical current profile', () => {
  beforeEach(() => {
    localStorage.setItem('squash-engine-language-v1', 'en')
    vi.resetAllMocks()
    api.getViewerCountries.mockResolvedValue({
      schema_version: 'viewer_countries.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      country_count: 1,
      countries: [{
        country_code: 'EGY',
        player_count: 2,
        active_player_count: 1,
        retired_player_count: 1,
        average_current_ovr: 191,
        top_player_id: 'EGY-0001',
        top_player_name: 'Ali A',
        top_player_current_ovr: 191
      }]
    })
    api.getViewerPlayers.mockResolvedValue({
      schema_version: 'viewer_players.v1',
      product_run_id: 'viewer-run-2c',
      viewer_branch_id: 'branch-viewer',
      season_index: 2,
      week: 7,
      player_count: 2,
      active_player_count: 1,
      retired_player_count: 1,
      players: [
        {
          player_id: 'EGY-0001',
          name: 'Ali A',
          country_code: 'EGY',
          age: 24,
          status: 'active',
          tour_entry_season_index: 0,
          tour_entry_week: 1,
          current_ovr: 191,
          potential_ovr: null,
          current_form: null,
          match_sharpness: null,
          long_term_fatigue: null,
          identity_source: 'initial_world'
        },
        {
          player_id: 'EGY-0002',
          name: 'Retired E',
          country_code: 'EGY',
          age: 37,
          status: 'retired',
          tour_entry_season_index: 0,
          tour_entry_week: 1,
          current_ovr: null,
          potential_ovr: null,
          current_form: null,
          match_sharpness: null,
          long_term_fatigue: null,
          identity_source: 'initial_world'
        }
      ]
    })
  })

  it('renders canonical current country profile and player roster', async () => {
    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/countries/EGY',
      <ViewerRunCountryDetailPage />,
      '/viewer/runs/:runId/countries/:countryCode'
    )

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(api.getViewerCountries).toHaveBeenCalledWith('viewer-run-2c')
    expect(api.getViewerPlayers).toHaveBeenCalledWith('viewer-run-2c')
    expect(await screen.findByText('branch-viewer')).toBeInTheDocument()
    expect(screen.getByText('S2 W7')).toBeInTheDocument()
    expect(screen.getAllByText('EGY').length).toBeGreaterThan(0)
    expect(screen.getByText('191.00')).toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Potential' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Ali A/ })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career'
    )
    expect(screen.getByRole('link', { name: /Retired E/ })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/EGY-0002/career'
    )
    expect(screen.getByText(/canonical historical source mix/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to countries' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/countries'
    )

    expect(api.getRunNationDetail).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it.each([
    { viewer_branch_id: 'foreign' }, { season_index: 3 }, { week: 8 }
  ])('rejects mismatched public source clocks: %j', async patch => {
    const countries = await api.getViewerCountries()
    api.getViewerCountries.mockResolvedValue({ ...countries, ...patch })
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')
    expect(await screen.findByRole('alert')).toHaveTextContent('sources do not match')
    expect(screen.queryByRole('heading', { name: 'Overview' })).not.toBeInTheDocument()
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
  })

  it.each([
    { player_count: 3, active_player_count: 2 }, { average_current_ovr: 190 },
    { top_player_id: 'FOREIGN' }, { top_player_name: 'Wrong name' }, { top_player_current_ovr: 190 }
  ])('rejects inconsistent country aggregates: %j', async patch => {
    const countries = await api.getViewerCountries()
    api.getViewerCountries.mockResolvedValue({ ...countries, countries: [{ ...countries.countries[0], ...patch }] })
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')
    expect(await screen.findByRole('alert')).toHaveTextContent('sources do not match')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('retries both sources and restores the profile after a consistent response', async () => {
    const countries = await api.getViewerCountries()
    api.getViewerCountries.mockResolvedValue({ ...countries, week: 8 })
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')
    expect(await screen.findByRole('alert')).toHaveTextContent('sources do not match')
    api.getViewerCountries.mockResolvedValue(countries)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Retry read (GET)' }))
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
  })

  it('bounds the country roster to 50 rows and preserves unrelated parameters', async () => {
    const roster = await api.getViewerPlayers()
    const countries = await api.getViewerCountries()
    const players = Array.from({ length: 101 }, (_, i) => ({ ...roster.players[0], player_id: 'P-' + String(i).padStart(3, '0'), name: 'Player ' + i }))
    api.getViewerPlayers.mockResolvedValue({ ...roster, players, player_count: 101, active_player_count: 101, retired_player_count: 0 })
    api.getViewerCountries.mockResolvedValue({ ...countries, countries: [{ ...countries.countries[0], player_count: 101, active_player_count: 101, retired_player_count: 0, top_player_id: 'P-000', top_player_name: 'Player 0' }] })
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY?vcPlayerPage=2&keep=yes', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(51)
    expect(within(table).getByRole('link', { name: 'Player 50 (P-050)' }))
      .toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players/P-050/career')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Last' }))
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('link', { name: 'Player 100 (P-100)' }))
      .toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players/P-100/career')
    expect(screen.getByLabelText('Current URL')).toHaveTextContent('vcPlayerPage=3&keep=yes')
  })

  it('fails closed when the canonical country code is absent', async () => {
    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/countries/XXX',
      <ViewerRunCountryDetailPage />,
      '/viewer/runs/:runId/countries/:countryCode'
    )

    expect(await screen.findByText(/No canonical country with this code exists/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Overview' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps the country profile unavailable on canonical API failure', async () => {
    api.getViewerCountries.mockRejectedValue(new Error('canonical country outage'))

    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/countries/EGY',
      <ViewerRunCountryDetailPage />,
      '/viewer/runs/:runId/countries/:countryCode'
    )

    expect(await screen.findByText(/Failed to load canonical country profile/i)).toBeInTheDocument()
    expect(screen.queryByText(/canonical country outage/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('normalizes country route code case against canonical data', async () => {
    renderViewerRoute(
      '/viewer/runs/viewer-run-2c/countries/egy',
      <ViewerRunCountryDetailPage />,
      '/viewer/runs/:runId/countries/:countryCode'
    )

    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getAllByText('EGY').length).toBeGreaterThan(0)
    expectNoForbiddenViewerActions()
  })
})

