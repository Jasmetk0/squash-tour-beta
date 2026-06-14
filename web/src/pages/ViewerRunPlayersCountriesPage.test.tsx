import { render, screen, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import {
  ViewerRunCountriesPage,
  ViewerRunCountryDetailPage,
  ViewerRunPlayerCareerPage,
  ViewerRunPlayersPage
} from './ViewerRunPlayersCountriesPage'

const api = vi.hoisted(() => ({
  listRunPlayers: vi.fn(),
  getRunPlayerDetail: vi.fn(),
  getRunPlayerCareerHistory: vi.fn(),
  getRunPlayerCareerPerformance: vi.fn(),
  getRunPlayerTournamentResults: vi.fn(),
  listRunNations: vi.fn(),
  getRunNationDetail: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderViewerRoute(route: string, element: JSX.Element, path = '/viewer/runs/:runId/*'): ReturnType<typeof render> {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path={path} element={element} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
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
    vi.resetAllMocks()
    mockPlayerList()
  })

  it('renders real player metadata and profile links without primary raw JSON', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2c').length).toBeGreaterThan(0)
    const aliRow = (await screen.findByText('Ali A')).closest('tr') as HTMLElement
    expect(within(aliRow).getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries/EGY')
    expect(within(aliRow).getByText('20')).toBeInTheDocument()
    expect(within(aliRow).getByText('elite_talent')).toBeInTheDocument()
    expect(within(aliRow).getByText('67')).toBeInTheDocument()
    expect(within(aliRow).getByRole('link', { name: /Open Player Profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career'
    )
    expect(screen.queryByText(/player-list-payload-should-not-render/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/secret_debug_marker/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('keeps the player list page read-only and empty on API error', async () => {
    api.listRunPlayers.mockRejectedValue(new Error('player list outage'))

    renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load players/i)).toBeInTheDocument()
    expect(screen.getByText(/player list outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
    expect(screen.queryByText('Bob B')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open Player Profile/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows no-data copy for an empty player list without inventing players or links', async () => {
    api.listRunPlayers.mockResolvedValue({ run_id: 'viewer-run-2c', total: 0, limit: 200, offset: 0, players: [] })

    renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByText(/Ali A|Bob B|elite_talent|67|72/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open Player Profile/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('drops malformed player list entries without crashing or rendering object text', async () => {
    api.listRunPlayers.mockResolvedValue({
      run_id: 'viewer-run-2c',
      total: 7,
      limit: 200,
      offset: 0,
      players: [
        null,
        12,
        'bad-player',
        {},
        { player_id: { raw: 'OBJ-ID' }, name: 'Object ID', country_code: 'EGY', age: 21 },
        { player_id: 'OBJ-NAME', name: { raw: 'Object Name' }, country_code: 'EGY', age: 21 },
        { player_id: 'SAFE-1', name: 'Safe Player', country_code: { raw: 'OBJ-COUNTRY' }, age: 'old', quality_band: { raw: 'OBJ-BAND' }, overall: { raw: 99 } }
      ]
    })

    const { container } = renderViewerRoute('/viewer/runs/viewer-run-2c/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    expect(await screen.findByRole('heading', { name: 'Players' })).toBeInTheDocument()
    expect(await screen.findByText('Safe Player')).toBeInTheDocument()
    expect(container).not.toHaveTextContent('[object Object]')
    expect(screen.queryByText(/Object ID|Object Name|OBJ-COUNTRY|OBJ-BAND|99/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Object ID|Object Name|OBJ-ID|OBJ-NAME/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open Player Profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/SAFE-1/career'
    )
    expectNoForbiddenViewerActions()
  })

  it('builds encoded Viewer-only player profile links from the list page', async () => {
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run/alpha #1',
      total: 1,
      limit: 200,
      offset: 0,
      players: [{ player_id: 'P/1 #A', name: 'Encoded Player', country_code: 'CO/DE #1', age: 24, overall: 88 }]
    })

    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/players', <ViewerRunPlayersPage />, '/viewer/runs/:runId/players')

    const profileLink = await screen.findByRole('link', { name: /Open Player Profile/i })
    expect(profileLink).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career')
    expect(profileLink.getAttribute('href')).not.toContain('/admin')
    expect(profileLink.getAttribute('href')).not.toContain('run/alpha #1')
    expect(profileLink.getAttribute('href')).not.toContain('P/1 #A')
    expect(await screen.findByRole('link', { name: 'CO/DE #1' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/countries/CO%2FDE%20%231'
    )
    expectNoForbiddenViewerActions()
  })

})

describe('ViewerRunPlayerCareerPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockPlayerDetail()
  })

  it('renders real player profile summary and keeps technical data collapsed', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Identity' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Attributes / Power Rating' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Origin / source' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Links' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2c').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EGY-0001').length).toBeGreaterThan(0)
    expect(await screen.findByText('Ali A')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'EGY' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries/EGY')
    ;['20', '70', '68', '66', '65', '67', '2027'].forEach((value) =>
      expect(screen.getAllByText(value).length).toBeGreaterThan(0)
    )
    expect(screen.getAllByText('planner_generated').length).toBeGreaterThan(0)
    expect(screen.getAllByText('elite_talent').length).toBeGreaterThan(0)
    expect(screen.getByText('yes')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to players/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players')
    expect(screen.getByRole('link', { name: /Country page/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries/EGY')
    expect(screen.getByRole('heading', { name: 'Season Timeline' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tournament History' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'W7' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/weeks/7')
    expect(screen.getByRole('link', { name: 'W8' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/weeks/8')
    expect(screen.getByRole('link', { name: 'Cairo Open' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/tournaments/event-cairo-2027'
    )
    expect(screen.getByText('Local Showcase')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Local Showcase' })).not.toBeInTheDocument()
    const noWeekRow = screen.getByText('No Week Invitational').closest('tr')
    expect(noWeekRow).not.toBeNull()
    expect(within(noWeekRow as HTMLElement).getAllByText('—').length).toBeGreaterThan(0)
    expect(within(noWeekRow as HTMLElement).queryByRole('link', { name: /^W/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /undefined|null/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'W9' })).not.toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Finish' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Points' })).toBeInTheDocument()
    expect(screen.getByText('Final')).toBeInTheDocument()
    expect(screen.getByText('Quarterfinal')).toBeInTheDocument()
    ;['12', '14', '1', '28', '11', '4', '700', '175', 'bronze', 'R16'].forEach((value) =>
      expect(screen.getAllByText(value).length).toBeGreaterThan(0)
    )
    expect(screen.queryByText(/world champion|grand slam|career high no\. 1|h2h|elo/i)).not.toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical player data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/player-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical player data'))
    expect(within(technicalSection as HTMLElement).getByText(/player-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
  })

  it('shows deferred previews when career, performance, and result entries are empty', async () => {
    mockEmptyPlayerCareerData()

    renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Season Timeline' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Tournament History' })).toBeInTheDocument()
    expect(screen.getAllByText('This preview is not connected for this data shape yet.').length).toBeGreaterThanOrEqual(2)
    expectNoForbiddenViewerActions()
  })


  it('renders safely for encoded slash/hash/space route params without fake data', async () => {
    api.getRunPlayerDetail.mockResolvedValue(null)
    mockEmptyPlayerCareerData()

    const { container } = renderViewerRoute(
      '/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career',
      <ViewerRunPlayerCareerPage />,
      '/viewer/runs/:runId/players/:playerId/career'
    )

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect(screen.getByText('run/alpha #1')).toBeInTheDocument()
    expect(screen.getByText('P/1 #A')).toBeInTheDocument()
    expect(await screen.findAllByText('This preview is not connected for this data shape yet.')).toHaveLength(3)
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run/alpha #1', 'P/1 #A')
    expect(screen.queryByText(/world champion|grand slam|career high no\. 1|h2h|elo|ranking|rank #|wins|losses|titles/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical player data')).not.toBeInTheDocument()
    expect(container).not.toHaveTextContent('[object Object]')
    expectNoForbiddenViewerActions()
  })



  it('keeps Player Profile safe on player detail API error', async () => {
    api.getRunPlayerDetail.mockRejectedValue(new Error('player detail outage'))
    mockEmptyPlayerCareerData()

    renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load player profile/i)).toBeInTheDocument()
    expect(screen.getByText(/player detail outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical player data')).not.toBeInTheDocument()
    expect(screen.queryByText(/world champion|grand slam|career high no\. 1|h2h|elo/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('rejects malformed player detail objects without object text, unsafe country links, or fake stats', async () => {
    api.getRunPlayerDetail.mockResolvedValue({
      player_id: { raw: 'OBJ-P' },
      name: { raw: 'Object Name' },
      country_code: { raw: 'OBJ-COUNTRY' },
      age: { raw: 20 },
      source: { raw: 'source' },
      quality_band: { raw: 'band' },
      ratings: { overall: 99 }
    })
    mockEmptyPlayerCareerData()

    const { container } = renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect(await screen.findAllByText('This preview is not connected for this data shape yet.')).not.toHaveLength(0)
    expect(container).not.toHaveTextContent('[object Object]')
    expect(screen.queryByText(/OBJ-P|Object Name|OBJ-COUNTRY|band|99/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /OBJ-COUNTRY|Country page/i })).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical player data')).not.toBeInTheDocument()
    expect(screen.queryByText(/ranking|rank #|wins|losses|titles/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('normalizes malformed player career, performance, and tournament result entries safely', async () => {
    api.getRunPlayerDetail.mockResolvedValue(null)
    api.getRunPlayerCareerHistory.mockResolvedValue({ entries: [null, 7, 'bad', {}, { run_id: { raw: 'OBJ-RUN' }, season: { raw: 2027 }, age: { raw: 20 }, source_type: { raw: 'OBJ-SOURCE' }, quality_band: { raw: 'OBJ-BAND' } }] })
    api.getRunPlayerCareerPerformance.mockResolvedValue({ entries: [null, 'bad', {}, { season: { raw: 2027 }, wins: { raw: 10 }, losses: { raw: 2 } }] })
    api.getRunPlayerTournamentResults.mockResolvedValue({ entries: [null, 12, 'bad', {}, { week: { raw: 7 }, event_id: { raw: 'OBJ-EVENT' }, event_name: { raw: 'OBJ-NAME' }, event_category: { raw: 'OBJ-CAT' }, ranking_points_awarded: { raw: 500 } }] })

    const { container } = renderViewerRoute('/viewer/runs/viewer-run-2c/players/EGY-0001/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Season Timeline' })).toBeInTheDocument()
    expect(container).not.toHaveTextContent('[object Object]')
    expect(screen.queryByText(/OBJ-RUN|OBJ-SOURCE|OBJ-BAND|OBJ-EVENT|OBJ-NAME|OBJ-CAT|500/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /^W/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /OBJ-EVENT|OBJ-NAME/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('builds encoded Viewer-only detail links from safe player payload values', async () => {
    api.getRunPlayerDetail.mockResolvedValue({ player_id: 'P/1 #A', name: 'Encoded Player', country_code: 'CO/DE #1', age: 22 })
    api.getRunPlayerCareerHistory.mockResolvedValue({ entries: [] })
    api.getRunPlayerCareerPerformance.mockResolvedValue({ entries: [] })
    api.getRunPlayerTournamentResults.mockResolvedValue({ entries: [{ run_id: 'run/alpha #1', season: 2027, week: 9, event_sequence: 1, event_id: 'EVT/1 #A', event_name: 'Encoded Event', wins: 1, losses: 0 }] })

    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByText('Encoded Player')).toBeInTheDocument()
    const countryLinks = screen.getAllByRole('link', { name: /CO\/DE #1|Country page/i })
    countryLinks.forEach((link) => {
      expect(link).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/countries/CO%2FDE%20%231')
      expect(link.getAttribute('href')).not.toContain('run/alpha #1')
      expect(link.getAttribute('href')).not.toContain('CO/DE #1')
      expect(link.getAttribute('href')).not.toContain('/admin')
    })
    expect(screen.getByRole('link', { name: 'Encoded Event' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/tournaments/EVT%2F1%20%23A')
    expect(screen.getByRole('link', { name: 'W9' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/weeks/9')
    expectNoForbiddenViewerActions()
  })

  it('shows deferred preview when player detail data is missing', async () => {
    api.getRunPlayerDetail.mockResolvedValue(null)
    mockEmptyPlayerCareerData()

    renderViewerRoute('/viewer/runs/viewer-run-2c/players/MISSING/career', <ViewerRunPlayerCareerPage />, '/viewer/runs/:runId/players/:playerId/career')

    expect(await screen.findByRole('heading', { name: 'Player Profile' })).toBeInTheDocument()
    expect((await screen.findAllByText('This preview is not connected for this data shape yet.')).length).toBeGreaterThan(0)
    expect(screen.queryByText('Ali A')).not.toBeInTheDocument()
    expect(screen.queryByText(/world champion|grand slam|career high no\. 1|elo|h2h/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical player data')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunCountriesPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCountries()
  })

  it('renders real country metadata with profile links and no primary raw JSON', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('heading', { name: 'Countries' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2c').length).toBeGreaterThan(0)
    expect(await screen.findByRole('columnheader', { name: 'Country' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Players' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Average Power Rating' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Average age' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Top player' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Source mix' })).toBeInTheDocument()
    expect(await screen.findByText(/Egypt/)).toBeInTheDocument()
    expect(screen.getAllByText(/EGY/).length).toBeGreaterThan(0)
    const egyptRow = screen.getByText(/Egypt/).closest('tr') as HTMLElement
    const usaRow = screen.getByText(/United States/).closest('tr') as HTMLElement
    expect(within(egyptRow).getByText('5')).toBeInTheDocument()
    expect(within(egyptRow).getByText('78.40')).toBeInTheDocument()
    expect(within(egyptRow).getByText('25.20')).toBeInTheDocument()
    expect(within(egyptRow).getByText(/carryover 1 · intake 3 · manual 1/i)).toBeInTheDocument()
    expect(within(egyptRow).getByRole('link', { name: 'Ali A (EGY-0001)' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career'
    )
    expect(within(usaRow).getAllByText('—').length).toBeGreaterThan(0)
    expect(within(usaRow).getAllByRole('link')).toHaveLength(1)
    expect(within(egyptRow).getByRole('link', { name: /Open country profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/countries/EGY'
    )
    expect(screen.queryByText(/country-list-payload-should-not-render/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Team Championship|titles?|records?|medals?|hosting|Top 100/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })

  it('keeps the country list page read-only and empty on API error', async () => {
    api.listRunNations.mockRejectedValue(new Error('country list outage'))

    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('heading', { name: 'Countries' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load countries/i)).toBeInTheDocument()
    expect(screen.getByText(/country list outage/i)).toBeInTheDocument()
    expect(screen.queryByText(/Egypt|United States/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open country profile/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows no-data copy for an empty country list without inventing countries or links', async () => {
    api.listRunNations.mockResolvedValue({ run_id: 'viewer-run-2c', total: 0, limit: 300, offset: 0, nations: [] })

    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('heading', { name: 'Countries' })).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expect(screen.queryByText(/Egypt|United States|78\.40|25\.20|Team Championship|records?|Top 100/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open country profile/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('drops malformed country list entries without crashing or rendering object text', async () => {
    api.listRunNations.mockResolvedValue({
      run_id: 'viewer-run-2c',
      total: 7,
      limit: 300,
      offset: 0,
      nations: [
        null,
        12,
        'bad-country',
        {},
        { country_code: { raw: 'OBJ-COUNTRY' }, country_name: 'Object Country', total_players: 1 },
        { country_code: 'SAFE', country_name: { raw: 'Object Name' }, total_players: 'many', average_overall: { raw: 99 }, top_player_id: { raw: 'OBJ-P' }, top_player_name: { raw: 'Obj Player' } }
      ]
    })

    const { container } = renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('heading', { name: 'Countries' })).toBeInTheDocument()
    expect(await screen.findByText('SAFE (SAFE)')).toBeInTheDocument()
    expect(container).not.toHaveTextContent('[object Object]')
    expect(screen.queryByText(/Object Country|Object Name|OBJ-COUNTRY|Obj Player|99/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Object Country|Obj Player|OBJ-P/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open country profile/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries/SAFE')
    expectNoForbiddenViewerActions()
  })

  it('builds encoded Viewer-only country detail links from the list page', async () => {
    api.listRunNations.mockResolvedValue({
      run_id: 'run/alpha #1',
      total: 1,
      limit: 300,
      offset: 0,
      nations: [{ country_code: 'CO/DE #1', country_name: 'Encoded Country', total_players: 4, top_player_id: 'P/1 #A', top_player_name: 'Encoded Player' }]
    })

    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    const countryLink = await screen.findByRole('link', { name: /Open country profile/i })
    expect(countryLink).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/countries/CO%2FDE%20%231')
    expect(countryLink.getAttribute('href')).not.toContain('/admin')
    expect(countryLink.getAttribute('href')).not.toContain('run/alpha #1')
    expect(countryLink.getAttribute('href')).not.toContain('CO/DE #1')
    expect(await screen.findByRole('link', { name: 'Encoded Player (P/1 #A)' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career'
    )
    expectNoForbiddenViewerActions()
  })

})

describe('ViewerRunCountryDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCountryDetail()
  })

  it('renders real country profile summary and keeps technical data collapsed', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Overview' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Player base' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Source mix' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Talent bands' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Top players' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Links' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2c').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EGY').length).toBeGreaterThan(0)
    expect(await screen.findByText('Egypt')).toBeInTheDocument()
    ;['5', '78.40', '25.20', '2', '1', '3', '80.10', '79.10', '76.10', '78.10'].forEach((value) =>
      expect(screen.getAllByText(value).length).toBeGreaterThan(0)
    )
    expect(screen.getByText(/rollover_carried 1 · planner_generated 3 · manual_override 1/i)).toBeInTheDocument()
    expect(screen.getByText(/top 2/i)).toBeInTheDocument()
    expect(screen.getByText(/elite_talent 2/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ali A (EGY-0001)' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/players/EGY-0001/career'
    )
    expect(screen.getByText('Unlinked Player')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Unlinked Player' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open player profile/i })).not.toBeInTheDocument()
    expect(screen.getByText('91')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to countries/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries')
    expect(screen.getByRole('link', { name: /Player list/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players?country=EGY')
    expect(screen.queryByText(/Team Championship|titles?|records?|medals?|hosting|Top 100/i)).not.toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical country data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/country-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical country data'))
    expect(within(technicalSection as HTMLElement).getByText(/country-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
  })


  it('renders safely for encoded slash/hash/space route params without fake data', async () => {
    api.getRunNationDetail.mockResolvedValue(null)

    const { container } = renderViewerRoute(
      '/viewer/runs/run%2Falpha%20%231/countries/CO%2FDE%20%231',
      <ViewerRunCountryDetailPage />,
      '/viewer/runs/:runId/countries/:countryCode'
    )

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(screen.getByText('run/alpha #1')).toBeInTheDocument()
    expect(screen.getByText('CO/DE #1')).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(api.getRunNationDetail).toHaveBeenCalledWith('run/alpha #1', 'CO/DE #1')
    expect(screen.queryByText(/Team Championship|titles?|records?|medals?|hosting|Top 100|ranking|rank #|wins|losses/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical country data')).not.toBeInTheDocument()
    expect(container).not.toHaveTextContent('[object Object]')
    expectNoForbiddenViewerActions()
  })



  it('keeps Country Profile safe on country detail API error', async () => {
    api.getRunNationDetail.mockRejectedValue(new Error('country detail outage'))

    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(await screen.findByText(/Failed to load country profile/i)).toBeInTheDocument()
    expect(screen.getByText(/country detail outage/i)).toBeInTheDocument()
    expect(screen.queryByText('Egypt')).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical country data')).not.toBeInTheDocument()
    expect(screen.queryByText(/Team Championship|titles?|records?|medals?|hosting|Top 100/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('rejects malformed country detail objects without object text, unsafe links, or fake records', async () => {
    api.getRunNationDetail.mockResolvedValue({ country_code: { raw: 'OBJ-COUNTRY' }, country_name: { raw: 'Object Country' }, total_players: { raw: 5 }, average_overall: { raw: 90 }, average_age: { raw: 25 }, source_mix: { manual_override: { raw: 1 } } })

    const { container } = renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(container).not.toHaveTextContent('[object Object]')
    expect(screen.queryByText(/OBJ-COUNTRY|Object Country|90/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /OBJ-COUNTRY|Object Country/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/Team Championship|titles?|records?|medals?|hosting|Top 100/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('normalizes malformed country top players, source mix, and band arrays safely', async () => {
    api.getRunNationDetail.mockResolvedValue({
      country_code: 'EGY',
      country_name: 'Egypt',
      total_players: 5,
      source_mix: { safe_source: 2, object_source: { raw: 1 }, string_source: '3' },
      band_distribution: [null, 'bad', {}, { band: { raw: 'OBJ-BAND' }, count: { raw: 2 } }, { band: 'safe_band', count: 1 }],
      origin_band_distribution: [null, { band: 'origin_safe', count: 3 }, { band: 'origin_object', count: { raw: 4 } }],
      top_players: [null, 'bad', {}, { player_id: { raw: 'OBJ-P' }, name: { raw: 'Object Player' }, overall: { raw: 99 } }, { player_id: 'SAFE-P', name: 'Safe Player', overall: 88, source_type: { raw: 'OBJ-SOURCE' }, quality_band: { raw: 'OBJ-QUALITY' } }]
    })

    const { container } = renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByText('Egypt')).toBeInTheDocument()
    expect(screen.getByText('safe_source 2')).toBeInTheDocument()
    expect(screen.getByText(/safe_band 1/)).toBeInTheDocument()
    expect(screen.getByText(/origin_safe 3/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Safe Player (SAFE-P)' })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players/SAFE-P/career')
    expect(container).not.toHaveTextContent('[object Object]')
    expect(screen.queryByRole('link', { name: /OBJ-P|Object Player/i })).not.toBeInTheDocument()
    const technicalSection = screen.getByText('Show technical country data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/OBJ-P|Object Player|OBJ-BAND|object_source|string_source|OBJ-SOURCE|OBJ-QUALITY|99/)).not.toBeVisible()
    expectNoForbiddenViewerActions()
  })

  it('builds encoded Viewer-only detail links from safe country payload values', async () => {
    api.getRunNationDetail.mockResolvedValue({ country_code: 'CO/DE #1', country_name: 'Encoded Country', total_players: 1, top_players: [{ player_id: 'P/1 #A', name: 'Encoded Player', overall: 91 }] })

    renderViewerRoute('/viewer/runs/run%2Falpha%20%231/countries/CO%2FDE%20%231', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByText('Encoded Country')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Encoded Player (P/1 #A)' })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/players/P%2F1%20%23A/career')
    expect(screen.getByRole('link', { name: /Back to countries/i })).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/countries')
    const playerList = screen.getByRole('link', { name: /Player list/i })
    expect(playerList).toHaveAttribute('href', '/viewer/runs/run%2Falpha%20%231/players?country=CO%2FDE%20%231')
    ;[screen.getByRole('link', { name: 'Encoded Player (P/1 #A)' }), playerList].forEach((link) => {
      expect(link.getAttribute('href')).not.toContain('/admin')
      expect(link.getAttribute('href')).not.toContain('run/alpha #1')
    })
    expect(screen.getByRole('link', { name: 'Encoded Player (P/1 #A)' }).getAttribute('href')).not.toContain('P/1 #A')
    expect(playerList.getAttribute('href')).not.toContain('CO/DE #1')
    expectNoForbiddenViewerActions()
  })

  it('shows deferred preview when country detail data is missing', async () => {
    api.getRunNationDetail.mockResolvedValue(null)

    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/MISSING', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expect(screen.queryByText('Egypt')).not.toBeInTheDocument()
    expect(screen.queryByText(/78\.40|25\.20|country-detail-hidden-payload/i)).not.toBeInTheDocument()
    expect(screen.queryByText('Show technical country data')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
