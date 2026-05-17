import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminRankingTablesSection, ViewerRankingsReadOnlyPage } from './RankingTables'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getAdminRankingTable: vi.fn(),
  getViewerRankingTable: vi.fn(),
  getAdminPointBreakdown: vi.fn(),
  getViewerPointBreakdown: vi.fn(),
  getAdminRankingSnapshot: vi.fn(),
  generateAdminRankingSnapshot: vi.fn(),
  getViewerRankingSnapshot: vi.fn(),
  ApiError: class ApiError extends Error { status = 400 }
}))

vi.mock('../api/client', () => api)

const rankingResponse = {
  rows: [{ rank: 1, dense_rank: 1, ordinal_position: 1, player_id: 'P-1', player_name: 'Adam Ahmed', country_code: 'EGY', nationality: 'EGY', age_years_at_season_start: 25, career_stage: 'prime', current_ability: 88, potential_ability: 91, potential_tier: 'S', archetype: 'attacker', play_style: 'attacking', ranking_points: 1400, race_points: 1200, table_points: 1400, manual_override: false, source_generation: 'initial_pool', locked_from_initial_pool: true, movement: null, previous_rank: null, events_counted: null, player_fingerprint: 'fp-1' }],
  summary: { season: '2000/2001', table_type: 'ranking', player_count: 1, total_source_players: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-1', leader_points: 1400, generated_from_active_players_fingerprint: 'active-fp', rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false },
  metadata: { season: '2000/2001', table_type: 'ranking', source: 'season_active_players', active_players_fingerprint: 'active-fp', generated_fingerprint: 'generated-fp', ranking_basis: 'current active season player ranking_points', filters: { country_code: null, search: null, include_zero_points: true, min_points: null }, limit: 100, warnings: [] },
  validation_warnings: ['Rolling 61-week ranking not implemented.', 'Best-N ranking selection not implemented.'],
  validation_errors: []
}


const snapshotResult = {
  snapshot_exists: true,
  snapshot: {
    season: '2000/2001', season_week: 2, calendar_year: 2000, year_week: 36, seed: 12345, dry_run: false, persisted: true,
    ranking_table: { table_type: 'ranking', rows: [{ ...rankingResponse.rows[0], previous_rank: 2, movement: 1, movement_label: 'up' }], summary: { season: '2000/2001', season_week: 2, table_type: 'ranking', player_count: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-1', leader_points: 1400, previous_snapshot_key: '2000/2001:1', new_entries_count: 0, moved_up_count: 1, moved_down_count: 0, unchanged_count: 0, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: true }, metadata: {} },
    race_table: { table_type: 'race', rows: [{ ...rankingResponse.rows[0], previous_rank: 1, movement: 0, movement_label: 'same' }], summary: { season: '2000/2001', season_week: 2, table_type: 'race', player_count: 1, ranked_player_count: 1, zero_point_players: 0, countries_represented: 1, leader_player_id: 'P-1', leader_points: 1200, previous_snapshot_key: '2000/2001:1', new_entries_count: 0, moved_up_count: 0, moved_down_count: 0, unchanged_count: 1, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: true }, metadata: {} },
    summary: {},
    metadata: { season: '2000/2001', season_week: 2, calendar_year: 2000, year_week: 36, source: 'active_season_players', active_players_fingerprint: 'active-fp', point_awards_fingerprint: 'awards-fp', ranking_table_fingerprint: 'rank-fp', race_table_fingerprint: 'race-fp', snapshot_fingerprint: 'snapshot-fingerprint-abcdef', previous_snapshot_fingerprint: 'previous-fingerprint', dry_run: false, persisted: true, generated_seed: 12345, persistence_path: 'config/world/season_ranking_snapshots.json', publication_basis: 'current active season player ranking_points/race_points', rolling_ranking_implemented: false, best_n_implemented: false },
    validation_warnings: ['Snapshot is based on current active season player totals, not rolling expiry.'], validation_errors: []
  },
  summary: null, metadata: null, validation_warnings: [], validation_errors: []
}

const emptySnapshotResult = { snapshot: null, snapshot_exists: false, summary: null, metadata: null, validation_warnings: ['No published snapshot for this week.'], validation_errors: [] }

const summaryBreakdownResponse = {
  breakdown: null,
  summary_rows: [{ player_id: 'P-1', player_name: 'Adam Ahmed', country_code: 'EGY', ranking_points: 1400, race_points: 1200, breakdown_ranking_points_total: 1400, breakdown_race_points_total: 1200, applied_event_count: 2, total_event_count: 2, consistency_ok: true, top_result_stage: 'champion', top_result_event_id: 'EVT-1' }],
  metadata: { season: '2000/2001', source: 'season_point_awards', active_players_fingerprint: 'active-fp', point_awards_fingerprint: 'awards-fp', generated_fingerprint: 'breakdown-fp', applied_only: true, table_type: 'both', filters: { player_id: null, search: null, country_code: null, include_zero_point_awards: false }, limit: 100, rolling_ranking_implemented: false, best_n_implemented: false, movement_implemented: false },
  validation_warnings: ['Rolling 61-week ranking not implemented.', 'Best-N ranking selection not implemented.'],
  validation_errors: []
}

const playerBreakdownResponse = {
  ...summaryBreakdownResponse,
  breakdown: {
    player_id: 'P-1', player_name: 'Adam Ahmed', country_code: 'EGY', nationality: 'EGY', season: '2000/2001', current_ranking_points: 1400, current_race_points: 1200, breakdown_ranking_points_total: 1400, breakdown_race_points_total: 1200, applied_ranking_points_total: 1400, applied_race_points_total: 1200, unapplied_ranking_points_total: 0, unapplied_race_points_total: 0, applied_event_count: 1, total_event_count: 1, consistency: { ranking_points_match_active_player: true, race_points_match_active_player: true, ranking_points_delta: 0, race_points_delta: 0 },
    entries: [{ event_id: 'EVT-1', season: '2000/2001', season_week: 4, calendar_year: 2000, year_week: 38, event_name: 'Cairo Open', category: 'Gold', tour_level: 'WORLD_TOUR', template_id: 'gold-1', host_country: 'EGY', reached_stage: 'champion', qualifier: false, seed_number: 1, ranking_points_awarded: 1000, race_points_awarded: 1000, applied: true, point_distribution_source: 'fallback.default_stage_points', source_result_fingerprint: 'result-fp', source_player_result_fingerprint: 'player-result-fp', award_fingerprint: 'abcdef1234567890', award_package_fingerprint: 'package-fp', result_package_fingerprint: 'result-package-fp' }]
  }
}

describe('Viewer rankings read model page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getViewerRankingTable.mockResolvedValue(rankingResponse)
    api.getAdminRankingTable.mockResolvedValue(rankingResponse)
    api.getViewerPointBreakdown.mockResolvedValue(summaryBreakdownResponse)
    api.getAdminPointBreakdown.mockResolvedValue(playerBreakdownResponse)
    api.getAdminRankingSnapshot.mockResolvedValue(snapshotResult)
    api.generateAdminRankingSnapshot.mockResolvedValue(snapshotResult)
    api.getViewerRankingSnapshot.mockResolvedValue(snapshotResult)
  })

  it('renders read-only MSA rankings table and filters', async () => {
    renderWithRoute(<ViewerRankingsReadOnlyPage />, '/viewer/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText('Current ranking table from active season points. Historical weekly ranking snapshots are read-only publications below.')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Season')[0]).toHaveValue('2000/2001')
    expect(screen.getByLabelText('Table type')).toBeInTheDocument()
    expect(screen.getByLabelText('Country filter')).toBeInTheDocument()
    expect(screen.getAllByLabelText('Search')[0]).toBeInTheDocument()

    const table = await screen.findByRole('table', { name: 'Ranking race table' })
    expect(within(table).getByText('Adam Ahmed')).toBeInTheDocument()
    expect(within(table).getByText('EGY')).toBeInTheDocument()
    expect(screen.getByText('Rolling 61-week ranking not implemented.')).toBeInTheDocument()
  })

  it('loads viewer API with selected ranking params', async () => {
    renderWithRoute(<ViewerRankingsReadOnlyPage />, '/viewer/rankings')

    await userEvent.selectOptions(await screen.findByLabelText('Table type'), 'race')
    await userEvent.clear(screen.getByLabelText('Top N'))
    await userEvent.type(screen.getByLabelText('Top N'), '25')
    await userEvent.type(screen.getByLabelText('Country filter'), 'egy')
    await userEvent.type(screen.getAllByLabelText('Search')[0], 'Adam')
    await userEvent.click(screen.getByRole('button', { name: 'Load table' }))

    expect(api.getViewerRankingTable).toHaveBeenLastCalledWith('2000/2001', expect.objectContaining({ table_type: 'race', limit: 25, country_code: 'EGY', search: 'Adam' }))
  })

  it('viewer point breakdown panel calls viewer API and renders summary rows and warnings', async () => {
    renderWithRoute(<ViewerRankingsReadOnlyPage />, '/viewer/rankings')

    await userEvent.type(screen.getAllByLabelText('Search')[1], 'Adam')
    await userEvent.click(screen.getByRole('button', { name: 'Load point breakdown' }))

    expect(api.getViewerPointBreakdown).toHaveBeenCalledWith('2000/2001', expect.objectContaining({ search: 'Adam', applied_only: true }))
    const table = await screen.findByRole('table', { name: 'Point breakdown summary rows table' })
    expect(within(table).getByText('Adam Ahmed')).toBeInTheDocument()
    expect(screen.getAllByText('Best-N ranking selection not implemented.').length).toBeGreaterThan(0)
  })

  it('admin point breakdown section renders controls and player breakdown entries', async () => {
    renderWithRoute(<AdminRankingTablesSection />, '/admin/seasons')

    expect(screen.getByText('Player Point Breakdown')).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Player ID'), 'P-1')
    await userEvent.click(screen.getByLabelText('Include zero-point awards'))
    await userEvent.click(screen.getByRole('button', { name: 'Load point breakdown' }))

    expect(api.getAdminPointBreakdown).toHaveBeenCalledWith('2000/2001', expect.objectContaining({ player_id: 'P-1', include_zero_point_awards: true }))
    const table = await screen.findByRole('table', { name: 'Player point breakdown table' })
    expect(within(table).getByText('Cairo Open')).toBeInTheDocument()
    expect(within(table).getByText('champion')).toBeInTheDocument()
    expect(within(table).getByText('abcdef123456')).toBeInTheDocument()
  })

  it('admin weekly ranking snapshots preview persist and load through API', async () => {
    renderWithRoute(<AdminRankingTablesSection />, '/admin/seasons')

    expect(screen.getByText('Weekly Ranking Snapshots')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Preview snapshot' }))
    expect(api.generateAdminRankingSnapshot).toHaveBeenLastCalledWith('2000/2001', 1, expect.objectContaining({ dry_run: true, seed: 12345 }))

    await userEvent.click(screen.getByRole('button', { name: 'Persist snapshot' }))
    expect(api.generateAdminRankingSnapshot).toHaveBeenLastCalledWith('2000/2001', 1, expect.objectContaining({ dry_run: false }))

    await userEvent.click(screen.getByRole('button', { name: 'Load persisted snapshot' }))
    expect(api.getAdminRankingSnapshot).toHaveBeenCalledWith('2000/2001', 1)
    const table = await screen.findByRole('table', { name: 'Ranking snapshot table' })
    expect(within(table).getByText('Adam Ahmed')).toBeInTheDocument()
    expect(within(table).getByText('+1')).toBeInTheDocument()
    expect(screen.getByText('Snapshot is based on current active season player totals, not rolling expiry.')).toBeInTheDocument()
  })

  it('viewer weekly snapshot panel loads read-only persisted snapshot or empty state', async () => {
    api.getViewerRankingSnapshot.mockResolvedValueOnce(emptySnapshotResult).mockResolvedValueOnce(snapshotResult)
    renderWithRoute(<ViewerRankingsReadOnlyPage />, '/viewer/rankings')

    await userEvent.click(screen.getByRole('button', { name: 'Load weekly snapshot' }))
    expect(api.getViewerRankingSnapshot).toHaveBeenCalledWith('2000/2001', 1)
    expect(await screen.findByText('No published snapshot for this week.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Load weekly snapshot' }))
    const table = await screen.findByRole('table', { name: 'Race snapshot table' })
    expect(within(table).getByText('0')).toBeInTheDocument()
  })

})
