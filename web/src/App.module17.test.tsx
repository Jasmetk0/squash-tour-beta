import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

const api = vi.hoisted(() => ({
  getHealth: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listRuns: vi.fn(),
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listEvents: vi.fn(),
  getRunActivity: vi.fn(),
  getEvent: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  getLatestRollover: vi.fn(),
  getRolloverBySeason: vi.fn(),
  getPlayerTransitions: vi.fn(),
  getNextSeasonPlayers: vi.fn(),
  rolloverNextSeason: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  getRunTalentPlan: vi.fn(),
  listGeneratedPlayersProvenance: vi.fn(),
  bootstrapNextSeason: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getAdminRankingTable: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('./api/client', () => api)

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

describe('Module 17 pages through routes', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    api.listRuns.mockResolvedValue({ runs: [] })
    api.getCountriesMetadata.mockResolvedValue({ dataset_status: 'temporary_seed_demo', country_count: 0, source_path: 'config/world/countries.json' })
    api.getTournamentTemplatesMetadata.mockResolvedValue({ template_count: 0, source_path: 'config/tournament_templates/mvp_templates.json', referenced_by_calendar: false, referenced_template_ids: [] })
    api.getViewerRankingTable.mockResolvedValue({ rows: [], summary: { season: '2000/2001', table_type: 'ranking', player_count: 0, total_source_players: 0, ranked_player_count: 0, zero_point_players: 0, countries_represented: 0, leader_player_id: null, leader_points: null, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false }, metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'generated-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 100, warnings: [] }, validation_warnings: ['Rolling 61-week ranking not implemented.'], validation_errors: [] })
  })

  it('renders the Phase 1 landing page at root', async () => {
    renderAppAt('/')
    expect(await screen.findByText('Choose how you want to use the deterministic FAX squash world.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Browse the generated squash world/i })).toHaveAttribute('href', '/viewer')
    expect(screen.getByRole('link', { name: /Build, validate, and simulate the world/i })).toHaveAttribute('href', '/admin')
  })

  it('renders the Admin Engine dashboard route', async () => {
    renderAppAt('/admin')
    expect(await screen.findByRole('heading', { name: 'Admin Engine Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Tour & Seasons' })).toHaveAttribute('href', '/admin/tour-seasons')
  })

  it('renders the Viewer MSA home route with no active run empty state', async () => {
    localStorage.removeItem('beta_engine:viewer_active_run_id')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: 'MSA Website Home' })).toBeInTheDocument()
    expect(screen.getByText('Select a Viewer run first to enable run-scoped MSA website links.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Rankings' })).toHaveAttribute('href', '/viewer/rankings')
    expect(screen.queryByRole('link', { name: 'Players' })).toHaveAttribute('href', '/viewer/players')
    expect(screen.queryByRole('link', { name: 'Countries' })).toHaveAttribute('href', '/viewer/countries')
    expect(screen.queryByRole('link', { name: 'History' })).toHaveAttribute('href', '/viewer/history')
    expect(screen.queryByRole('link', { name: 'Finals' })).not.toBeInTheDocument()
  })

  it('renders the Viewer MSA home route with active run links', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-1')
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/viewer')
    expect(await screen.findByRole('heading', { name: 'MSA Website Home' })).toBeInTheDocument()
    expect(screen.getAllByText(/viewer-run-1/)[0]).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/rankings')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Tournaments' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/tournaments')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Players' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/players')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'Countries' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/countries')).toBe(true)
    expect(screen.getAllByRole('link', { name: 'History' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-1/history')).toBe(true)
  })

  it('renders top-level Viewer rankings with active run link', async () => {
    localStorage.setItem('beta_engine:viewer_active_run_id', 'viewer-run-2')
    renderAppAt('/viewer/rankings')
    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Rankings' }).some((link) => link.getAttribute('href') === '/viewer/runs/viewer-run-2/rankings')).toBe(true)
  })

  beforeEach(() => {
    api.getEvent.mockResolvedValue({ event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: null, tournament_result: {} })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 1, total_events: 10, completed_event_ids: [] },
      season_state: { season: 2027, next_event_index: 1, completed_event_ids: [], ordered_events: [] }
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 5,
      progress: { next_event_index: 1, total_events: 10, completed_event_count: 0 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
      history_counts: { events: 0, ranking_snapshots: 1, race_snapshots: 1 }
    })
    api.listEvents.mockResolvedValue({ events: [] })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2027, qualification: {}, result: null })
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      source_as_of_season: 2027,
      source_as_of_week: 42,
      qualification: { qualified_player_ids: ['P1'] }
    })
    api.getFinalsResult.mockRejectedValue(new Error('no result yet'))
    api.getLatestRollover.mockRejectedValue(new Error('no rollover'))
    api.getRolloverBySeason.mockResolvedValue({
      rollover: { run_id: 'run-a', from_season: 2027, to_season: 2028, transitioned_players: 64, metadata: {} }
    })
    api.getPlayerTransitions.mockResolvedValue({ run_id: 'run-a', to_season: 2028, transitions: [] })
    api.getNextSeasonPlayers.mockResolvedValue({ run_id: 'run-a', to_season: 2028, players: [] })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: []
      }
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'ranking-4' } }]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: { name: 'race-7' } }]
    })
    api.getRunTalentPlan.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      seed: 5,
      total_talents: 1,
      dataset_status: 'active',
      config_version: 'cfg',
      config_fingerprint: 'fp',
      countries: [
        {
          country_code: 'EGY',
          planned_count: 1,
          quality_weights: { solid_prospect: 1 },
          actual_band_counts: { solid_prospect: 1 },
          bias_profile: {}
        }
      ]
    })
    api.listGeneratedPlayersProvenance.mockResolvedValue({
      run_id: 'run-a',
      players: [
        {
          run_id: 'run-a',
          season: 2027,
          player_id: 'EGY-00001',
          country_code: 'EGY',
          talent_sequence: 1,
          talent_seed_value: 1,
          quality_band: 'solid_prospect',
          is_top_band: false
        }
      ]
    })
  })

  it('renders Finals route', async () => {
    renderAppAt('/runs/run-a/finals')
    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
  })

  it('renders Finals qualification detail route', async () => {
    renderAppAt('/runs/run-a/finals/qualification')
    expect(await screen.findByRole('heading', { name: 'Finals qualification detail' })).toBeInTheDocument()
  })

  it('renders Finals result detail route', async () => {
    api.getFinalsResult.mockResolvedValueOnce({
      run_id: 'run-a',
      season: 2027,
      event_id: 'WORLD_TOUR_FINALS',
      source_as_of_season: 2027,
      source_as_of_week: 42,
      result: { champion_player_id: 'P1' }
    })
    renderAppAt('/runs/run-a/finals/result')
    expect(await screen.findByRole('heading', { name: 'Finals result detail' })).toBeInTheDocument()
  })

  it('renders Rollover route', async () => {
    renderAppAt('/runs/run-a/rollover')
    expect(await screen.findByRole('heading', { name: 'Season Rollover' })).toBeInTheDocument()
  })


  it('renders rollover season detail route', async () => {
    renderAppAt('/runs/run-a/rollover/2028')
    expect(await screen.findByRole('heading', { name: 'Rollover season detail' })).toBeInTheDocument()
  })

  it('renders diagnostics route', async () => {
    renderAppAt('/runs/run-a/diagnostics')
    expect(await screen.findByRole('heading', { name: 'Run diagnostics' })).toBeInTheDocument()
  })

  it('renders world generation route', async () => {
    renderAppAt('/runs/run-a/world-generation')
    expect(await screen.findByRole('heading', { name: 'World generation diagnostics' })).toBeInTheDocument()
  })

  it('renders runs browser route', async () => {
    api.listRuns.mockResolvedValueOnce({ runs: [] })
    renderAppAt('/runs')
    expect(await screen.findByRole('heading', { name: 'Runs browser' })).toBeInTheDocument()
  })

  it('renders activity route', async () => {
    api.getRunActivity.mockResolvedValue({ run_id: 'run-a', items: [] })
    renderAppAt('/runs/run-a/activity')
    expect(await screen.findByRole('heading', { name: 'Run activity' })).toBeInTheDocument()
  })

  it('renders season calendar route', async () => {
    renderAppAt('/runs/run-a/calendar')
    expect(await screen.findByRole('heading', { name: 'Season calendar' })).toBeInTheDocument()
  })

  it('renders week detail route', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 0, total_events: 2, completed_event_ids: [] },
      season_state: {
        season: 2027,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [
          { event_id: 'E2', season: 2027, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP' },
          { event_id: 'E3', season: 2027, week: 10, tour: 'WORLD', category: 'SILVER', template_id: 'TEMP2' }
        ]
      }
    })
    renderAppAt('/runs/run-a/weeks/9')
    expect(await screen.findByRole('heading', { name: 'Week detail' })).toBeInTheDocument()
  })

  it('renders Bootstrap/Lineage route', async () => {
    renderAppAt('/runs/run-a/bootstrap-lineage')
    expect(await screen.findByRole('heading', { name: 'Bootstrap / Lineage' })).toBeInTheDocument()
  })


  it('renders Season Chain route', async () => {
    renderAppAt('/runs/run-a/season-chain')
    expect(await screen.findByRole('heading', { name: 'Season Chain' })).toBeInTheDocument()
  })



  it('renders planned event detail route', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2027, seed: 5, next_event_index: 0, total_events: 1, completed_event_ids: [] },
      season_state: {
        season: 2027,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [{ event_id: 'E2', season: 2027, week: 9, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP' }]
      }
    })
    renderAppAt('/runs/run-a/calendar/E2')
    expect(await screen.findByRole('heading', { name: 'Planned event detail' })).toBeInTheDocument()
  })

  it('renders Event detail route', async () => {
    renderAppAt('/runs/run-a/events/E2')
    expect(await screen.findByRole('heading', { name: 'Event detail' })).toBeInTheDocument()
  })

  it('renders ranking snapshot detail route', async () => {
    renderAppAt('/runs/run-a/snapshots/ranking/4')
    expect(await screen.findByRole('heading', { name: 'Ranking snapshot detail' })).toBeInTheDocument()
  })

  it('renders race snapshot detail route', async () => {
    renderAppAt('/runs/run-a/snapshots/race/7')
    expect(await screen.findByRole('heading', { name: 'Race snapshot detail' })).toBeInTheDocument()
  })
})
