import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsCategoryDetailPage } from './CategoryDetailPage'

const api = vi.hoisted(() => ({ getCategories: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function category(category_id: string, name: string) {
  return {
    category_id, name, status: 'read_only_foundation', source: 'tournament-templates',
    template_count: 0, source_template_ids: [], notes: [],
    valid_from_season: null, valid_to_season: null,
    main_draw_size: null, qualification_draw_size: null, direct_entries: null,
    qualifiers: null, wildcards: null, lucky_losers: null, seeds_count: null,
    tour_level: null, prestige_rank: null, mandatory: null, match_format: null,
    prize_money_total: null, points_by_round: null, qualifying_weeks_count: null,
    main_draw_weeks_count: null, schedule_footprint_weeks: null,
  }
}

function mount(id: string) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[`/admin/tour-seasons/categories/${encodeURIComponent(id)}`]}>
        <Routes>
          <Route path="/admin/tour-seasons/categories/:categoryId" element={<AdminTourSeasonsCategoryDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Derived category detail navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getCategories.mockResolvedValue({
      categories: [
        category('z_first', 'Zulu'),
        category('a_middle', 'Alpha'),
        category('c_last', 'Charlie'),
      ],
      source_path: 'categories.json', status: 'read_only_foundation'
    })
  })

  it('navigates the backend-provided order rather than reordering alphabetically', async () => {
    mount('a_middle')
    expect(await screen.findByText('Category 2 of 3 in the backend source order.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Previous category: Zulu' }))
      .toHaveAttribute('href', '/admin/tour-seasons/categories/z_first')
    expect(screen.getByRole('link', { name: 'Next category: Charlie →' }))
      .toHaveAttribute('href', '/admin/tour-seasons/categories/c_last')

    fireEvent.click(screen.getByRole('link', { name: 'Next category: Charlie →' }))
    expect(await screen.findByText('Category 3 of 3 in the backend source order.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Next category:/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Previous category: Alpha' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: '← Previous category: Alpha' }))
    expect(await screen.findByText('Category 2 of 3 in the backend source order.')).toBeInTheDocument()
    expect(api.getCategories).toHaveBeenCalledTimes(1)
  })

  it('does not invent previous, next or position for a nonexistent category', async () => {
    mount('unknown')
    expect(await screen.findByText('Category not found.')).toBeInTheDocument()
    expect(screen.queryByText(/in the backend source order/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Previous category:/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Next category:/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Categories' }))
      .toHaveAttribute('href', '/admin/tour-seasons/categories')
  })

  it('shows no adjacent navigation for a single-record backend catalog', async () => {
    api.getCategories.mockResolvedValue({
      categories: [category('alone', 'Only category')], source_path: null,
      status: 'read_only_foundation'
    })
    mount('alone')
    expect(await screen.findByText('Category 1 of 1 in the backend source order.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Previous category:/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Next category:/ })).not.toBeInTheDocument()
  })
})
