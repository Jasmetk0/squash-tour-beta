import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SeasonRankingPointsPreview } from './SeasonRankingPointsPreview'

const api = vi.hoisted(() => ({
  getAdminPointBreakdown: vi.fn(), getAdminRankingSnapshot: vi.fn(), getAdminRankingTable: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function mount(label: string | null = '2000/01') {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><SeasonRankingPointsPreview seasonLabelRaw={label} /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Season ranking preview table accessibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getAdminRankingTable.mockResolvedValue({
      summary: {
        player_count: 1, ranked_player_count: 1, zero_point_players: 0,
        countries_represented: 1, leader_player_id: 'p1', leader_points: 12,
      },
      rows: [{
        player_id: 'p1', player_name: 'Player One', country_code: 'CZE',
        table_points: 12, rank: 1, movement: null, source_generation: 'sample',
      }],
    })
    api.getAdminRankingSnapshot.mockRejectedValue(new Error('not found'))
    api.getAdminPointBreakdown.mockResolvedValue({
      metadata: {
        applied_only: true, filters: { include_zero_point_awards: false },
        table_type: 'ranking', source: 'sample',
      },
      validation_warnings: [], validation_errors: [],
      summary_rows: [{
        player_id: 'p1', player_name: 'Player One', top_result_event_id: 'open',
        top_result_stage: 'winner', ranking_points: 12,
      }],
    })
  })

  it('keeps ranking and point tables readable with proper accessible labels and scroll wrappers', async () => {
    mount()
    const ranking = await screen.findByRole('table', { name: 'Season ranking top ten' })
    expect(ranking.parentElement).toHaveClass('table-responsive')
    expect(within(ranking).getByRole('cell', { name: 'Player One (p1)' })).toBeInTheDocument()
    expect(within(ranking).getByRole('cell', { name: 'CZE' })).toBeInTheDocument()
    const points = await screen.findByRole('table', { name: 'Season point breakdown top ten' })
    expect(points.parentElement).toHaveClass('table-responsive')
    expect(within(points).getByRole('cell', { name: 'open / sample' })).toBeInTheDocument()
    expect(within(points).getByRole('cell', { name: 'winner' })).toBeInTheDocument()
    expect(api.getAdminRankingTable).toHaveBeenCalledWith('2000/01', { limit: 10 })
    expect(api.getAdminPointBreakdown).toHaveBeenCalledWith(
      '2000/01', { limit: 10, applied_only: true, include_zero_point_awards: false }
    )
  })

  it('keeps empty result messages and does not render empty tables', async () => {
    api.getAdminRankingTable.mockResolvedValue({
      summary: { player_count: 0, ranked_player_count: 0, zero_point_players: 0,
        countries_represented: 0, leader_player_id: null, leader_points: null },
      rows: [],
    })
    api.getAdminPointBreakdown.mockResolvedValue({
      metadata: { applied_only: true, filters: { include_zero_point_awards: false },
        table_type: 'ranking', source: 'sample' },
      validation_warnings: [], validation_errors: [], summary_rows: [],
    })
    mount()
    expect(await screen.findByText('No ranking rows available.')).toBeInTheDocument()
    expect(await screen.findByText('No point breakdown rows available.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season ranking top ten' })).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season point breakdown top ten' })).not.toBeInTheDocument()
  })

  it('does not fetch preview endpoints for an invalid season label', () => {
    mount('invalid')
    expect(screen.getByText('Ranking & points preview unavailable for invalid season label.')).toBeInTheDocument()
    expect(api.getAdminRankingTable).not.toHaveBeenCalled()
    expect(api.getAdminRankingSnapshot).not.toHaveBeenCalled()
    expect(api.getAdminPointBreakdown).not.toHaveBeenCalled()
  })
})
