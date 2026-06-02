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

function renderViewerRoute(route: string, element: JSX.Element, path = '/viewer/runs/:runId/*'): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
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
    expect(within(aliRow).getByText('EGY')).toBeInTheDocument()
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
    expect(screen.getAllByText('EGY').length).toBeGreaterThan(0)
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
    expect(screen.getByText('Cairo Open')).toBeInTheDocument()
    ;['12', '8', '14', '1', '28', '11', '7', '4', '700'].forEach((value) =>
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

  it('renders sports-facing country metadata without fake achievements or forbidden actions', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries', <ViewerRunCountriesPage />, '/viewer/runs/:runId/countries')

    expect(await screen.findByRole('heading', { name: 'Countries' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2c').length).toBeGreaterThan(0)
    expect(await screen.findByText('Egypt')).toBeInTheDocument()
    expect(screen.getByText('EGY')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('78.40')).toBeInTheDocument()
    expect(screen.getByText(/carryover 1 · intake 3 · manual 1/i)).toBeInTheDocument()
    expect(screen.getByText(/Ali A \(EGY-0001\)/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open country profile/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2c/countries/EGY'
    )
    expect(screen.queryByText(/country-list-payload-should-not-render/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Team Championship/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Title/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/Top 100/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })
})

describe('ViewerRunCountryDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCountryDetail()
  })

  it('renders sports-facing country profile and keeps technical data collapsed', async () => {
    renderViewerRoute('/viewer/runs/viewer-run-2c/countries/EGY', <ViewerRunCountryDetailPage />, '/viewer/runs/:runId/countries/:countryCode')

    expect(await screen.findByRole('heading', { name: 'Country Profile' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2c').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EGY').length).toBeGreaterThan(0)
    expect(await screen.findByText('Egypt')).toBeInTheDocument()
    expect(screen.getByText('Ali A (EGY-0001)')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to countries/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/countries')
    expect(screen.getByRole('link', { name: /Player list/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2c/players?country=EGY')
    const technicalSection = screen.getByText('Show technical country data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/country-detail-hidden-payload/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical country data'))
    expect(within(technicalSection as HTMLElement).getByText(/country-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
  })
})
