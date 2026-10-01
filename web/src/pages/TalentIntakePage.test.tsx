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
    getRunWeeklyIntakeCohortSeasonPreview: vi.fn(),
    materializeRunProspects: vi.fn()
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
    api.materializeRunProspects.mockReset()
    api.materializeRunProspects.mockResolvedValue({
      run_id: 'run-1',
      world_id: 'official_fax_world',
      season: '2000/2001',
      season_start_year: 2000,
      annual_target: 204,
      requested_prospect_count: 204,
      created_count: 204,
      existing_count: 0,
      skipped_count: 0,
      conflict_count: 0,
      total_persisted_for_scope: 204,
      weeks_materialized: [],
      country_totals: [],
      already_materialized: false,
      message: 'Prospect cohort materialized.'
    })
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
    expect(screen.getByText(/materialized only after confirmation/i)).toBeInTheDocument()
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

  it('requires review confirmation and materializes without overwrite', async () => {
    renderWithRoute(<TalentIntakePage />, '/admin/runs/run-1/players/intake')
    await screen.findByText('FAX World')

    const confirmButton = screen.getByRole('button', { name: 'Confirm materialization' })
    expect(confirmButton).toBeDisabled()
    expect(api.materializeRunProspects).not.toHaveBeenCalled()

    await userEvent.click(
      screen.getByLabelText(/I reviewed this cohort preview and want to materialize these 15-year-old prospects/i)
    )
    expect(confirmButton).toBeEnabled()
    await userEvent.click(confirmButton)

    await waitFor(() => {
      expect(api.materializeRunProspects).toHaveBeenCalledWith('run-1', {
        base_annual_intake_target: 200,
        season_growth_rate: 0.015,
        overwrite: false
      })
    })
    expect(await screen.findByText('Prospect cohort materialized.')).toBeInTheDocument()
    expect(screen.getByText(/Created 204; existing 0; persisted in scope 204/i)).toBeInTheDocument()
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
