import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ViewerRankingsReadOnlyPage } from './RankingTables'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getAdminRankingTable: vi.fn(),
  getViewerRankingTable: vi.fn(),
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

describe('Viewer rankings read model page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getViewerRankingTable.mockResolvedValue(rankingResponse)
  })

  it('renders read-only MSA rankings table and filters', async () => {
    renderWithRoute(<ViewerRankingsReadOnlyPage />, '/viewer/rankings')

    expect(await screen.findByRole('heading', { name: 'MSA Rankings' })).toBeInTheDocument()
    expect(screen.getByText('Current ranking table from active season points. Historical weekly ranking snapshots are not available yet.')).toBeInTheDocument()
    expect(screen.getByLabelText('Season')).toHaveValue('2000/2001')
    expect(screen.getByLabelText('Table type')).toBeInTheDocument()
    expect(screen.getByLabelText('Country filter')).toBeInTheDocument()
    expect(screen.getByLabelText('Search')).toBeInTheDocument()

    const table = await screen.findByRole('table', { name: 'Ranking race table' })
    expect(within(table).getByText('Adam Ahmed')).toBeInTheDocument()
    expect(within(table).getByText('EGY')).toBeInTheDocument()
    expect(screen.getByText('Rolling 61-week ranking not implemented.')).toBeInTheDocument()
  })

  it('loads viewer API with selected params', async () => {
    renderWithRoute(<ViewerRankingsReadOnlyPage />, '/viewer/rankings')

    await userEvent.selectOptions(await screen.findByLabelText('Table type'), 'race')
    await userEvent.clear(screen.getByLabelText('Top N'))
    await userEvent.type(screen.getByLabelText('Top N'), '25')
    await userEvent.type(screen.getByLabelText('Country filter'), 'egy')
    await userEvent.type(screen.getByLabelText('Search'), 'Adam')
    await userEvent.click(screen.getByRole('button', { name: 'Load table' }))

    expect(api.getViewerRankingTable).toHaveBeenLastCalledWith('2000/2001', expect.objectContaining({ table_type: 'race', limit: 25, country_code: 'EGY', search: 'Adam' }))
  })
})
