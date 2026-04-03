import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TalentPreviewPage } from './TalentPreviewPage'
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
    getTalentClassPreview: vi.fn(),
    getTalentClassSummary: vi.fn()
  }
})

vi.mock('../api/client', () => api)

describe('TalentPreviewPage', () => {
  beforeEach(() => {
    api.getTalentClassPreview.mockReset()
    api.getTalentClassSummary.mockReset()
    api.getTalentClassPreview.mockResolvedValue({
      year: 2030,
      seed: 123,
      dataset_status: 'temporary_seed_demo',
      country_count: 1,
      source_path: 'config/world/countries.json',
      total_talents: 42,
      countries: [
        {
          country_code: 'AAA',
          country_name: 'Alpha',
          planned_count: 42,
          quality_weights: {
            solid_prospect: 0.6,
            strong_prospect: 0.3,
            elite_prospect: 0.08,
            special_prospect: 0.019,
            generational_talent: 0.001
          },
          actual_band_counts: {
            solid_prospect: 30,
            strong_prospect: 10,
            elite_prospect: 2,
            special_prospect: 0,
            generational_talent: 0
          },
          bias_profile: {
            professionalism_tendency: 0.1,
            technical_vs_physical_lean: 0.05,
            mental_sharpness_tendency: 0.02
          }
        }
      ]
    })
    api.getTalentClassSummary.mockResolvedValue({
      year_start: 2030,
      years: 10,
      seed: 123,
      dataset_status: 'temporary_seed_demo',
      country_count: 1,
      source_path: 'config/world/countries.json',
      total_talents_across_span: 420,
      average_total_talents_per_year: 42,
      global_band_totals: {
        solid_prospect: 300,
        strong_prospect: 90,
        elite_prospect: 25,
        special_prospect: 4,
        generational_talent: 1
      },
      countries: [
        {
          country_code: 'AAA',
          country_name: 'Alpha',
          total_planned_talents: 420,
          average_talents_per_year: 42,
          total_elite_count: 25,
          total_special_count: 4,
          total_generational_count: 1,
          average_top_band_rate: 0.071428
        }
      ]
    })
  })

  it('renders and loads single-year + multi-year data', async () => {
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')

    expect(await screen.findByRole('heading', { name: 'Talent Class Preview' })).toBeInTheDocument()
    expect((await screen.findAllByRole('cell', { name: 'AAA' })).length).toBeGreaterThan(0)
    expect(await screen.findByRole('table', { name: 'Talent preview multi-year summary table' })).toBeInTheDocument()
  })

  it('shows loading and error states', async () => {
    api.getTalentClassPreview.mockRejectedValueOnce(new api.ApiError('preview failed', 500))
    api.getTalentClassSummary.mockRejectedValueOnce(new api.ApiError('summary failed', 500))
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')

    expect(await screen.findByText(/Preview unavailable:/i)).toBeInTheDocument()
    expect(await screen.findByText(/Summary unavailable:/i)).toBeInTheDocument()
  })

  it('reacts to changed inputs', async () => {
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')
    await screen.findByRole('heading', { name: 'Talent Class Preview' })

    await userEvent.clear(screen.getByLabelText('Preview year'))
    await userEvent.type(screen.getByLabelText('Preview year'), '2040')
    await userEvent.clear(screen.getByLabelText('Seed'))
    await userEvent.type(screen.getByLabelText('Seed'), '777')
    await userEvent.clear(screen.getByLabelText('Multi-year span'))
    await userEvent.type(screen.getByLabelText('Multi-year span'), '5')

    await waitFor(() => {
      expect(api.getTalentClassPreview).toHaveBeenLastCalledWith({ year: 2040, seed: 777 })
      expect(api.getTalentClassSummary).toHaveBeenLastCalledWith({ year_start: 2040, years: 5, seed: 777 })
    })
  })
})
