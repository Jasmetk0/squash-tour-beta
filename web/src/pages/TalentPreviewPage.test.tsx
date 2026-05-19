import { screen, waitFor } from '@testing-library/react'
import { within } from '@testing-library/react'
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
          elite_talents: 2,
          tour_talents: 10,
          pro_depth: 30,
          bias_profile: {
            professionalism_tendency: 0.1,
            technical_vs_physical_lean: 0.05,
            mental_sharpness_tendency: 0.02
          },
          dampener: {
            active: false,
            recent_greatness_score: 0,
            multipliers: { generational_talent: 1, special_prospect: 1 }
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
          total_elite_talents: 30,
          total_tour_talents: 90,
          total_pro_depth: 300,
          average_elite_talents_per_year: 3,
          average_tour_talents_per_year: 9,
          average_pro_depth_per_year: 30,
          average_top_band_rate: 0.071428
        }
      ],
      global_elite_talents: 30,
      global_tour_talents: 90,
      global_pro_depth: 300
    })
  })

  it('renders and loads single-year + multi-year data', async () => {
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')

    expect(await screen.findByRole('heading', { name: 'Talent Preview' })).toBeInTheDocument()
    expect((await screen.findAllByRole('cell', { name: 'AAA' })).length).toBeGreaterThan(0)
    const forecastTable = await screen.findByRole('table', { name: 'Country forecast table' })
    expect(forecastTable).toBeInTheDocument()
    expect(within(forecastTable).getByRole('cell', { name: '90' })).toBeInTheDocument()
    expect(within(forecastTable).getByRole('cell', { name: '300' })).toBeInTheDocument()
  })

  it('shows loading and error states', async () => {
    api.getTalentClassPreview.mockRejectedValueOnce(new api.ApiError('preview failed', 500))
    api.getTalentClassSummary.mockRejectedValueOnce(new api.ApiError('summary failed', 500))
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')

    expect(await screen.findByText(/Technical preview unavailable:/i)).toBeInTheDocument()
    expect(await screen.findByText(/Forecast unavailable:/i)).toBeInTheDocument()
  })


  it('shows expected mode definitions and country detail link', async () => {
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')
    expect(await screen.findByText(/Talent Preview does not create players./i)).toBeInTheDocument()
    expect(await screen.findByText(/Elite Talents:/i)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Open Country' })).toHaveAttribute('href', '/admin/world/countries/AAA')
  })

  it('reacts to changed inputs', async () => {
    renderWithRoute(<TalentPreviewPage />, '/world/talent-preview')
    await screen.findByRole('heading', { name: 'Talent Preview' })

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
