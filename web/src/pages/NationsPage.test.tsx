import { fireEvent, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NationsPage } from './NationsPage'
import { renderWithRoute } from '../test/testUtils'
import * as api from '../api/client'

vi.mock('../api/client', async () => {
  const actual = await vi.importActual<typeof import('../api/client')>('../api/client')
  return {
    ...actual,
    listRunNations: vi.fn(),
    getRunNationDetail: vi.fn()
  }
})

describe('NationsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(api.listRunNations as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      run_id: 'run-a',
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
          top_player_name: 'Ali',
          top_player_overall: 91
        },
        {
          country_code: 'ENG',
          country_name: 'England',
          total_players: 3,
          average_overall: 72.4,
          average_age: 24.2,
          top_band_count: 1,
          manual_override_count: 0,
          planner_generated_count: 2,
          rollover_carried_count: 1,
          top_player_id: 'ENG-0001',
          top_player_name: 'Joel',
          top_player_overall: 87
        }
      ]
    })
    ;(api.getRunNationDetail as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      run_id: 'run-a',
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
          name: 'Ali',
          age: 24,
          overall: 91,
          source_type: 'planner_generated',
          quality_band: 'top',
          is_top_band: true
        }
      ]
    })
  })

  it('renders nations table, applies search/sort, opens detail, and handles loading/error states', async () => {
    renderWithRoute(<NationsPage />, '/runs/run-a/nations')

    expect(await screen.findByRole('heading', { name: 'Run Nations Dashboard' })).toBeInTheDocument()
    expect(await screen.findByText('EGY — Egypt')).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Search country'), { target: { value: 'egy' } })
    await waitFor(() =>
      expect(api.listRunNations).toHaveBeenLastCalledWith(
        'run-a',
        expect.objectContaining({ search: 'egy', sort: 'total_players_desc' })
      )
    )

    fireEvent.change(screen.getByLabelText('Sort'), { target: { value: 'avg_overall_desc' } })
    await waitFor(() =>
      expect(api.listRunNations).toHaveBeenLastCalledWith(
        'run-a',
        expect.objectContaining({ search: 'egy', sort: 'avg_overall_desc' })
      )
    )

    fireEvent.click(screen.getByRole('button', { name: /EGY — Egypt/ }))
    expect(await screen.findByText(/Source mix: carryover 1 \| intake 3 \| manual 1/)).toBeInTheDocument()
    expect(await screen.findByText(/Origin band distribution/)).toBeInTheDocument()
    expect(await screen.findByText('Ali (EGY-0001)')).toBeInTheDocument()

    ;(api.listRunNations as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('boom'))
    renderWithRoute(<NationsPage />, '/runs/run-a/nations')
    expect(await screen.findByText(/Failed to load nations/)).toBeInTheDocument()
  })
})
