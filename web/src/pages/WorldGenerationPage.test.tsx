import { fireEvent, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { WorldGenerationPage } from './WorldGenerationPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunTalentPlan: vi.fn(),
  listGeneratedPlayersProvenance: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('WorldGenerationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRunTalentPlan.mockResolvedValue({
      run_id: 'run-a',
      season: 2028,
      seed: 444,
      total_talents: 2,
      dataset_status: 'active',
      config_version: 'v1',
      config_fingerprint: 'fp',
      countries: [
        {
          country_code: 'EGY',
          planned_count: 2,
          quality_weights: { elite_prospect: 0.1, solid_prospect: 0.9 },
          actual_band_counts: { elite_prospect: 1, solid_prospect: 1 },
          bias_profile: { professionalism_tendency: 0.1 }
        }
      ]
    })
    api.listGeneratedPlayersProvenance.mockResolvedValue({
      run_id: 'run-a',
      players: [
        {
          run_id: 'run-a',
          season: 2028,
          player_id: 'EGY-00001',
          country_code: 'EGY',
          talent_sequence: 1,
          talent_seed_value: 123,
          quality_band: 'elite_prospect',
          is_top_band: true,
          source_type: 'planner_generated',
          override_id: null
        }
      ]
    })
  })

  it('renders persisted plan and generated players provenance tables', async () => {
    renderWithRoute(<WorldGenerationPage />, '/runs/run-a/world-generation')

    expect(await screen.findByRole('heading', { name: 'World generation diagnostics' })).toBeInTheDocument()
    expect(await screen.findByLabelText('Run talent country allocations table')).toBeInTheDocument()
    expect(await screen.findByLabelText('Generated players provenance table')).toBeInTheDocument()
    expect(screen.getByText('EGY-00001')).toBeInTheDocument()
  })

  it('makes filtered-empty provenance recoverable and clearly distinguishes the 300-row limit', async () => {
    api.listGeneratedPlayersProvenance.mockResolvedValue({ run_id: 'run-a', players: [] })
    renderWithRoute(<WorldGenerationPage />, '/runs/run-a/world-generation')
    expect(await screen.findByText('No persisted generated-player provenance found.')).toBeInTheDocument()
    expect(screen.getByText(/limited to the first 300 matching players/)).toBeInTheDocument()
    const clear = screen.getByRole('button', { name: 'Clear provenance filters' })
    expect(clear).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Filter by country'), { target: { value: 'egy' } })
    expect(await screen.findByText('No generated-player provenance matches the current filters.')).toBeInTheDocument()
    expect(clear).toBeEnabled()
    fireEvent.click(clear)
    expect(screen.getByLabelText('Filter by country')).toHaveValue('')
    expect(screen.getByLabelText('Filter by quality band')).toHaveValue('')
    expect(await screen.findByText('No persisted generated-player provenance found.')).toBeInTheDocument()
  })

  it('distinguishes a saved talent plan with zero countries from a request failure', async () => {
    api.getRunTalentPlan.mockResolvedValue({
      run_id: 'run-a', season: 2028, seed: 444, total_talents: 0,
      dataset_status: 'active', config_version: 'v1', countries: [],
    })
    renderWithRoute(<WorldGenerationPage />, '/runs/run-a/world-generation')
    expect(await screen.findByText('No country allocations were returned in the saved talent plan.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Run talent country allocations table' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Failed to load run talent plan/)).not.toBeInTheDocument()
  })

  it('passes filters to provenance API call and handles errors', async () => {
    api.listGeneratedPlayersProvenance.mockRejectedValueOnce(new Error('boom'))
    renderWithRoute(<WorldGenerationPage />, '/runs/run-a/world-generation')
    expect(await screen.findByText(/Failed to load generated players provenance/)).toBeInTheDocument()

    api.listGeneratedPlayersProvenance.mockResolvedValue({ run_id: 'run-a', players: [] })
    fireEvent.change(screen.getByLabelText('Filter by country'), { target: { value: 'egy' } })
    fireEvent.change(screen.getByLabelText('Filter by quality band'), { target: { value: 'elite_prospect' } })

    expect(await screen.findByText('No generated-player provenance matches the current filters.')).toBeInTheDocument()
    expect(api.listGeneratedPlayersProvenance).toHaveBeenLastCalledWith('run-a', {
      country_code: 'EGY',
      quality_band: 'elite_prospect',
      limit: 300
    })
  })
})
