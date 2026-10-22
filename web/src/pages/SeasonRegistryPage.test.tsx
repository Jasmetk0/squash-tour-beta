import { fireEvent, screen, waitFor, within } from '@testing-library/react'
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

  it('locally filters by year or label and exact registry status without refetching', async () => {
    api.getSeasonRegistry.mockResolvedValue({
      ...registry,
      seasons: [
        registry.seasons[0],
        { ...registry.seasons[0], label: '2001/02', season_start_year: 2001, season_index: 1, status: 'archived' },
        { ...registry.seasons[0], label: '2002/03', season_start_year: 2002, season_index: 2 },
      ]
    })
    renderWithRoute(<AdminTourSeasonsSeasonRegistryPage />, '/admin/tour-seasons/season-registry')
    expect(await screen.findByRole('link', { name: '2001/02' })).toBeInTheDocument()
    expect(screen.getByText('Showing 3 of 3 registry seasons')).toBeInTheDocument()
    const table = () => screen.getByRole('table', { name: 'Season registry entries' })
    expect(table().parentElement).toHaveClass('table-responsive')
    const rows = () => within(table()).getAllByRole('row')
    expect(rows()).toHaveLength(4)
    const search = screen.getByRole('searchbox', { name: 'Search registry seasons' })
    const status = screen.getByRole('combobox', { name: 'Filter registry status' })
    fireEvent.change(search, { target: { value: ' 2001 ' } })
    expect(screen.getByText('Showing 1 of 3 registry seasons')).toBeInTheDocument()
    expect(within(table()).getByRole('link', { name: '2001/02' })).toBeInTheDocument()
    expect(within(table()).queryByRole('link', { name: '2000/01' })).not.toBeInTheDocument()

    fireEvent.change(status, { target: { value: 'registry_only' } })
    expect(screen.getByText('Showing 0 of 3 registry seasons')).toBeInTheDocument()
    expect(screen.getByText('No registry seasons match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season registry entries' })).not.toBeInTheDocument()
    fireEvent.change(search, { target: { value: ' 2002/03 ' } })
    expect(screen.getByText('Showing 1 of 3 registry seasons')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '2002/03' })).toHaveAttribute('href', '/admin/seasons/detail/2002%2F03')
    fireEvent.click(screen.getByRole('button', { name: 'Clear season filters' }))
    expect(search).toHaveValue('')
    expect(status).toHaveValue('')
    expect(rows()).toHaveLength(4)
    expect(screen.getByRole('button', { name: 'Clear season filters' })).toBeDisabled()
    expect(api.getSeasonRegistry).toHaveBeenCalledTimes(1)
  })

  it('keeps an empty registry distinct from a filtered-empty inventory', async () => {
    api.getSeasonRegistry.mockResolvedValue({ ...registry, seasons: [], season_count: 0 })
    renderWithRoute(<AdminTourSeasonsSeasonRegistryPage />, '/admin/tour-seasons/season-registry')
    expect(await screen.findByText('No season registry entries available.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 registry seasons')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search registry seasons' }),
      { target: { value: 'no-such-season' } })
    expect(screen.queryByText('No registry seasons match the current filters.')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season registry entries' })).not.toBeInTheDocument()
  })

  it('renders registry table week fields from the API fixture', async () => {
    renderWithRoute(<AdminTourSeasonsSeasonRegistryPage />, '/admin/tour-seasons/season-registry')

    expect(await screen.findByRole('link', { name: '2000/01' })).toBeInTheDocument()
    expect(screen.getByText('SW1–SW61')).toBeInTheDocument()
    expect(screen.getAllByText('YW37').length).toBeGreaterThan(0)
    expect(screen.getAllByText('YW36').length).toBeGreaterThan(0)
  })
})
