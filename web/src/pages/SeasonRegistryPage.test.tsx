import { screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsSeasonRegistryPage } from './SeasonRegistryPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getSeasonRegistry: vi.fn(),
  ApiError: class ApiError extends Error { status = 400 }
}))

vi.mock('../api/client', () => api)

const registry = {
  start_season: '2000/01',
  end_season: '2049/50',
  season_count: 50,
  week_count: 61,
  season_week_1_year_week: 37,
  seasons: [
    {
      season_start_year: 2000,
      label: '2000/01',
      season_index: 0,
      week_count: 61,
      season_week_start: 1,
      season_week_end: 61,
      year_week_start: 37,
      year_week_end: 36,
      status: 'registry_only'
    }
  ]
}

describe('AdminTourSeasonsSeasonRegistryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonRegistry.mockResolvedValue(registry)
  })

  it('renders the canonical season-week to year-week boundary examples', async () => {
    renderWithRoute(<AdminTourSeasonsSeasonRegistryPage />, '/admin/tour-seasons/season-registry')

    await waitFor(() => expect(api.getSeasonRegistry).toHaveBeenCalled())
    expect(await screen.findByText('SW1 → YW37')).toBeInTheDocument()
    expect(screen.getByText('SW25 → YW61')).toBeInTheDocument()
    expect(screen.getByText('SW26 → YW1')).toBeInTheDocument()
    expect(screen.getByText('SW61 → YW36')).toBeInTheDocument()
  })

  it('renders registry table week fields from the API fixture', async () => {
    renderWithRoute(<AdminTourSeasonsSeasonRegistryPage />, '/admin/tour-seasons/season-registry')

    expect(await screen.findByRole('link', { name: '2000/01' })).toBeInTheDocument()
    expect(screen.getByText('SW1–SW61')).toBeInTheDocument()
    expect(screen.getAllByText('YW37').length).toBeGreaterThan(0)
    expect(screen.getAllByText('YW36').length).toBeGreaterThan(0)
  })
})
