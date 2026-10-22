import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsValidationPage } from './CalendarValidationPage'

const api = vi.hoisted(() => ({
  getSeasonRegistry: vi.fn(), getCategories: vi.fn(), getTournaments: vi.fn(),
  getSeasonTemplates: vi.fn(), getTourSeasonsValidation: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><AdminTourSeasonsValidationPage /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Calendar Validation issue search', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonRegistry.mockResolvedValue({
      season_count: 50, week_count: 61, season_week_1_year_week: 37,
    })
    api.getCategories.mockResolvedValue({ categories: [{
      category_id: 'category-1', name: 'Diamond', notes: ['Needs manual review'],
      main_draw_size: null, qualification_draw_size: 16, schedule_footprint_weeks: 2,
      source_template_ids: ['t-1'],
    }] })
    api.getTournaments.mockResolvedValue({ tournaments: [{
      tournament_id: 'event-1', name: 'Alpha Open', notes: [],
      default_category: 'DIAMOND', default_host_country: 'ENG', default_region: 'EU',
      source_template_ids: ['t-1'],
    }] })
    api.getSeasonTemplates.mockResolvedValue({ templates: [] })
    api.getTourSeasonsValidation.mockResolvedValue({
      status: 'ok', summary: { total_checks: 0, warning_count: 0, info_count: 0, ok_count: 0 },
      sections: [],
    })
  })

  it('searches issue messages, IDs and labels without changing authoritative totals', async () => {
    mount()
    expect(await screen.findByText(/Notes present: Needs manual review/)).toBeInTheDocument()
    expect(screen.getByText('Total checks: 5')).toBeInTheDocument()
    const search = screen.getByRole('searchbox', { name: 'Search validation issues' })
    fireEvent.change(search, { target: { value: '  NEEDS MANUAL REVIEW  ' } })
    expect(screen.getByText(/Notes present: Needs manual review/)).toBeInTheDocument()
    expect(screen.queryByText(/Main draw mixed or unavailable/)).not.toBeInTheDocument()
    expect(screen.getByText('Total checks: 5')).toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'category-1-main-draw-size' } })
    expect(screen.getByText(/Main draw mixed or unavailable/)).toBeInTheDocument()
    expect(screen.queryByText(/Notes present: Needs manual review/)).not.toBeInTheDocument()
    expect(api.getCategories).toHaveBeenCalledTimes(1)
    expect(api.getSeasonRegistry).toHaveBeenCalledTimes(1)
  })

  it('combines severity with text search and resets both controls', async () => {
    mount()
    expect(await screen.findByText(/Notes present: Needs manual review/)).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search validation issues' }),
      { target: { value: 'Diamond' } })
    expect(screen.getByText(/Main draw mixed or unavailable/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Warnings' }))
    expect(screen.getByText(/Notes present: Needs manual review/)).toBeInTheDocument()
    expect(screen.queryByText(/Main draw mixed or unavailable/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear validation issue filters' }))
    expect(screen.getByRole('searchbox', { name: 'Search validation issues' })).toHaveValue('')
    expect(screen.getByRole('button', { name: 'All' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText(/Main draw mixed or unavailable/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear validation issue filters' })).toBeDisabled()
    expect(api.getTourSeasonsValidation).toHaveBeenCalledTimes(1)
  })
})
