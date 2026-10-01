import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TalentIntakePage } from './TalentIntakePage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }

  return {
    ApiError,
    getRunWeeklyIntakeCohortSeasonPreview: vi.fn()
  }
})

vi.mock('../api/client', () => api)

const preview = {
  run_id: 'run-1',
  world_id: 'official_fax_world',
  world_name: 'FAX World',
  season: '2000/2001',
  season_start_year: 2000,
  season_index: 0,
  base_annual_intake_target: 200,
  season_growth_rate: 0.015,
  season_variation_multiplier: 1.02,
  annual_target: 204,
  total_weekly_target: 204,
  weeks: [
    {
      season_week: 1,
      target_intake_count: 4,
      total_allocated: 4,
      week_weight: 1,
      calendar_year: 2000,
      year_week: 1,
      birth_year: 1985,
      birth_year_week: 1,
      allocations: []
    },
    {
      season_week: 2,
      target_intake_count: 3,
      total_allocated: 3,
      week_weight: 1,
      calendar_year: 2000,
      year_week: 2,
      birth_year: 1985,
      birth_year_week: 2,
      allocations: []
    }
  ],
  country_totals: [
    { country_code: 'CZE', country_name: 'Czechia', allocated_count: 40 },
    { country_code: 'ENG', country_name: 'England', allocated_count: 32 }
  ]
}

describe('TalentIntakePage', () => {
  beforeEach(() => {
    api.getRunWeeklyIntakeCohortSeasonPreview.mockReset()
    api.getRunWeeklyIntakeCohortSeasonPreview.mockResolvedValue(preview)
  })

  it('loads the run-scoped season cohort preview without materializing players', async () => {
    renderWithRoute(<TalentIntakePage />, '/admin/runs/run-1/players/intake')

    expect(await screen.findByRole('heading', { name: 'Talent Intake' })).toBeInTheDocument()
    await waitFor(() => {
      expect(api.getRunWeeklyIntakeCohortSeasonPreview).toHaveBeenCalledWith('run-1', {
        base_annual_intake_target: 200,
        season_growth_rate: 0.015
      })
    })
    expect(await screen.findByText('FAX World')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Talent intake country totals' })).toBeInTheDocument()
    expect(screen.getByText('Czechia (CZE)')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Talent intake weekly schedule' })).toBeInTheDocument()
    expect(screen.getByText(/does not create or persist players/i)).toBeInTheDocument()
  })

  it('supports entering a Run ID from the global Talent Intake route', async () => {
    renderWithRoute(<TalentIntakePage />, '/admin/players/intake')

    expect(api.getRunWeeklyIntakeCohortSeasonPreview).not.toHaveBeenCalled()
    await userEvent.type(screen.getByLabelText('Run ID'), 'run-1')

    await waitFor(() => {
      expect(api.getRunWeeklyIntakeCohortSeasonPreview).toHaveBeenCalledWith('run-1', {
        base_annual_intake_target: 200,
        season_growth_rate: 0.015
      })
    })
  })

  it('updates the preview when annual volume controls change', async () => {
    renderWithRoute(<TalentIntakePage />, '/admin/runs/run-1/players/intake')
    await screen.findByText('FAX World')

    const annual = screen.getByLabelText('Base annual intake')
    await userEvent.clear(annual)
    await userEvent.type(annual, '250')

    await waitFor(() => {
      expect(api.getRunWeeklyIntakeCohortSeasonPreview).toHaveBeenLastCalledWith('run-1', {
        base_annual_intake_target: 250,
        season_growth_rate: 0.015
      })
    })
  })
})
