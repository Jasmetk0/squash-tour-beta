import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsCategoriesPage } from './CategoriesPage'

const api = vi.hoisted(() => ({ getCategories: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api,
}))

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><AdminTourSeasonsCategoriesPage /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Canonical tournament category discovery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getCategories.mockResolvedValue({
      categories: [{
        category_id: 'derived-a', name: 'Backend-derived category', template_count: 1,
        main_draw_size: null, qualification_draw_size: null,
        schedule_footprint_weeks: null, mandatory: null,
        source_template_ids: ['template-a'], status: 'read_only_foundation', notes: [],
      }],
      source_path: 'config/tournament_templates', status: 'read_only_foundation',
    })
  })

  it('searches by case-insensitive category code, trims whitespace, and clears the result', async () => {
    mount()
    expect(screen.getByText('Showing 22 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'World Championship' })).toBeInTheDocument()
    const search = screen.getByRole('searchbox', { name: 'Search category name or code' })
    fireEvent.change(search, { target: { value: '  challenger_80  ' } })
    expect(screen.getByText('Showing 1 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Challenger 80' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'World Championship' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Challenger Tour' })).toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'missing-category' } })
    expect(screen.getByText('No canonical categories match your search or tour filter.')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Challenger Tour' })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear category filters' }))
    expect(search).toHaveValue('')
    expect(screen.getByText('Showing 22 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'World Championship' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear category filters' })).toBeDisabled()
    expect(api.getCategories).toHaveBeenCalledTimes(1)
  })

  it('intersects tour-level selection with category search and restores original grouping', () => {
    mount()
    const tour = screen.getByRole('combobox', { name: 'Filter by tour level' })
    fireEvent.change(tour, { target: { value: 'DEVELOPMENT_TOUR' } })
    expect(screen.getByText('Showing 4 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Development Tour' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'World Tour' })).not.toBeInTheDocument()

    const search = screen.getByRole('searchbox', { name: 'Search category name or code' })
    fireEvent.change(search, { target: { value: 'Future 5' } })
    expect(screen.getByText('Showing 1 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Future 5' })).toBeInTheDocument()
    fireEvent.change(tour, { target: { value: 'ELITE_TOUR' } })
    expect(screen.getByText('Showing 0 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByText('No canonical categories match your search or tour filter.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear category filters' }))
    expect(tour).toHaveValue('all')
    expect(search).toHaveValue('')
    expect(screen.getByRole('heading', { name: 'World Tour' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Development Tour' })).toBeInTheDocument()
  })

  it('never hides or changes read-only backend-derived rules when identity filters change', async () => {
    mount()
    expect(await screen.findByRole('link', { name: 'Backend-derived category (derived-a)' }))
      .toHaveAttribute('href', '/admin/tour-seasons/categories/derived-a')
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search category name or code' }),
      { target: { value: 'nonexistent' } })
    expect(screen.getByText('Showing 0 of 22 canonical categories')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Backend-derived category (derived-a)' })).toBeInTheDocument()
    expect(screen.getByText('Derived backend categories: 1')).toBeInTheDocument()
    expect(api.getCategories).toHaveBeenCalledTimes(1)
  })
})
