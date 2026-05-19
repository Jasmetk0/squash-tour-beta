import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CountryDetailPage } from './CountryDetailPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listCountries: vi.fn(),
  getTalentClassSummary: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('CountryDetailPage', () => {
  beforeEach(() => {
    api.listCountries.mockReset()
    api.getTalentClassSummary.mockReset()

    api.listCountries.mockResolvedValue({
      countries: [
        {
          code: 'EGY',
          name: 'Egypt',
          region: 'MENA',
          population: 100000000,
          wealth_support: 5,
          squash_popularity: 5,
          squash_tradition: 5,
          system_quality: 5,
          competition_density: 4,
          federation_quality: 5,
          court_count: 5000,
          travel_region: 'MENA',
          notes: 'Strong domestic ladder.',
          style_dna: { attacking: 0.8 },
          flag_asset: 'flags/egy.svg'
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
      global_band_totals: {},
      global_elite_talents: 30,
      global_tour_talents: 90,
      global_pro_depth: 300,
      countries: [
        {
          country_code: 'EGY',
          country_name: 'Egypt',
          total_planned_talents: 420,
          average_talents_per_year: 42,
          total_elite_count: 20,
          total_special_count: 4,
          total_generational_count: 1,
          total_elite_talents: 25,
          total_tour_talents: 110,
          total_pro_depth: 285,
          average_elite_talents_per_year: 2.5,
          average_tour_talents_per_year: 11,
          average_pro_depth_per_year: 28.5,
          average_top_band_rate: 0.06
        }
      ]
    })
  })

  it('renders grouped country sections and talent preview summary', async () => {
    renderWithRoute(<CountryDetailPage />, '/admin/world/countries/EGY')

    expect(await screen.findByRole('heading', { name: 'Egypt (EGY)' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Identity' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Scale / Resources' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Squash Model Inputs' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Style DNA' })).toBeInTheDocument()
    expect(screen.getByText('attacking')).toBeInTheDocument()
    expect(await screen.findByText('Elite Talents')).toBeInTheDocument()
    expect(await screen.findByText('25')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Edit in Countries list/editor' })).toHaveAttribute(
      'href',
      '/admin/world/countries?edit=EGY'
    )
    expect(screen.queryByRole('heading', { name: 'Inputs' })).not.toBeInTheDocument()
  })

  it('shows not-found state when country code does not exist', async () => {
    renderWithRoute(<CountryDetailPage />, '/admin/world/countries/ZZZ')

    expect(await screen.findByRole('heading', { name: 'Country not found' })).toBeInTheDocument()
    expect(screen.getByText(/No country exists for code ZZZ/)).toBeInTheDocument()
  })
})
