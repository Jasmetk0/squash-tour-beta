import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PlayersPage } from './PlayersPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listRunPlayers: vi.fn(),
  getRunPlayerDetail: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('PlayersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listRunPlayers.mockResolvedValue({
      run_id: 'run-a',
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
          overall: 67
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
      hidden_traits: { potential_ceiling: 90, growth_curve: 'late', professionalism: 0.8, ambition: 0.7, travel_tolerance: 0.6, schedule_aggression: 0.7, injury_proneness: 0.2, resilience: 0.8 },
      source_type: 'planner_generated',
      quality_band: 'elite_talent',
      is_top_band: true,
      override_id: null,
      origin_source_type: 'planner_generated',
      origin_quality_band: 'elite_talent',
      origin_override_id: null,
      origin_season: 2027,
      talent_seed_value: 101,
      talent_sequence: 1
    })
  })

  it('renders players table, applies filters, opens detail, and handles loading/error states', async () => {
    renderWithRoute(<PlayersPage />, '/runs/run-a/players')

    expect(await screen.findByRole('heading', { name: 'Run Players Explorer' })).toBeInTheDocument()
    const table = await screen.findByRole('table')
    expect(within(table).getByText('Ali A')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Search (name / ID)'), 'EGY-0001')
    await waitFor(() => {
      expect(api.listRunPlayers).toHaveBeenLastCalledWith(
        'run-a',
        expect.objectContaining({ search: 'EGY-0001' })
      )
    })

    await userEvent.type(screen.getByLabelText('Country code'), 'egy')
    await waitFor(() => {
      expect(api.listRunPlayers).toHaveBeenLastCalledWith(
        'run-a',
        expect.objectContaining({ country_code: 'EGY' })
      )
    })

    await userEvent.selectOptions(screen.getByLabelText('Source type'), 'planner_generated')
    await waitFor(() => {
      expect(api.listRunPlayers).toHaveBeenLastCalledWith(
        'run-a',
        expect.objectContaining({ source_type: 'planner_generated' })
      )
    })

    await userEvent.click(screen.getByRole('button', { name: 'EGY-0001' }))
    await waitFor(() => expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run-a', 'EGY-0001'))
    expect(await screen.findByText(/Source: planner_generated/)).toBeInTheDocument()
    expect(await screen.findByText(/Origin source: planner_generated/)).toBeInTheDocument()
  })

  it('shows list error state', async () => {
    api.listRunPlayers.mockRejectedValueOnce(new Error('boom'))
    renderWithRoute(<PlayersPage />, '/runs/run-a/players')
    expect(await screen.findByText(/Failed to load players/)).toBeInTheDocument()
  })
})
