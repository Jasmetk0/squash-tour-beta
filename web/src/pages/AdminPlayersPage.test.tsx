import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminPlayersPage } from './AdminPlayersPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getInitialPlayerPool: vi.fn(),
  generateInitialPlayerPool: vi.fn(),
  regenerateInitialPlayerPool: vi.fn(),
  lockInitialPoolPlayer: vi.fn(),
  unlockInitialPoolPlayer: vi.fn()
}))

vi.mock('../api/client', () => api)

const player = {
  player_id: 'P-2000-AAA-0001',
  name: 'Adam Ahmed AA01',
  country_code: 'AAA',
  nationality: 'AAA',
  birth_year: 1976,
  birth_year_week: 12,
  age_at_generation: 24,
  current_age_years: 24,
  current_ability: 78,
  potential_ability: 88,
  potential_tier: 'A',
  career_stage: 'prime',
  play_style: 'balanced',
  archetype: 'all_court',
  attributes: { technique: 78, movement: 77, physical: 76, mental: 79, consistency: 78, clutch: 75, recovery: 77 },
  hidden_career_traits: { potential_ceiling: 88, growth_curve: 'steady', professionalism: 0.8, ambition: 0.7, travel_tolerance: 0.6, schedule_aggression: 0.5, injury_proneness: 0.2, resilience: 0.7 },
  locked: false,
  generation_source: 'initial_pool',
  manual_override: false,
  generation_seed: 101,
  generation_fingerprint: 'fp1',
  created_for_season: '2000/2001'
}

const response = {
  players: [player],
  summary: {
    total_players: 1,
    locked_players: 0,
    unlocked_players: 1,
    countries_represented: 1,
    average_current_ability: 78,
    average_potential_ability: 88,
    by_country: { AAA: 1 },
    by_career_stage: { prime: 1 },
    by_potential_tier: { A: 1 }
  },
  metadata: { season: '2000/2001', seed: 12345, target_pool_size: 1, country_code: null, region: null, dry_run: true, generated_count: 1, preserved_locked_count: 0, changed_count: 1, generation_fingerprint: 'pool-fp' }
}

describe('AdminPlayersPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getInitialPlayerPool.mockResolvedValue(response)
    api.generateInitialPlayerPool.mockResolvedValue(response)
    api.regenerateInitialPlayerPool.mockResolvedValue(response)
    api.lockInitialPoolPlayer.mockResolvedValue({ ...player, locked: true })
  })

  it('renders initial pool controls, summary, table, detail, and wires API actions', async () => {
    renderWithRoute(<AdminPlayersPage />, '/admin/players')

    expect(await screen.findByRole('heading', { name: 'Players / Initial Pool' })).toBeInTheDocument()
    expect(screen.getByText(/Locked players are preserved by regeneration/)).toBeInTheDocument()
    expect(screen.getByLabelText('Season')).toHaveValue('2000/2001')
    expect(screen.getByLabelText('Seed')).toHaveValue(12345)

    const table = await screen.findByRole('table', { name: 'Initial player pool table' })
    expect(within(table).getByText('Adam Ahmed AA01')).toBeInTheDocument()
    expect(screen.getByText(/potential_ceiling: 88/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Generate preview' }))
    expect(api.generateInitialPlayerPool).toHaveBeenCalledWith(expect.objectContaining({ dry_run: true, season: '2000/2001' }))

    await userEvent.click(screen.getByRole('button', { name: 'Regenerate unlocked' }))
    expect(api.regenerateInitialPlayerPool).toHaveBeenCalledWith(expect.objectContaining({ dry_run: false, seed: 12345 }))

    await userEvent.click(screen.getByRole('button', { name: 'Lock' }))
    expect(api.lockInitialPoolPlayer).toHaveBeenCalledWith('P-2000-AAA-0001')
  })
})
