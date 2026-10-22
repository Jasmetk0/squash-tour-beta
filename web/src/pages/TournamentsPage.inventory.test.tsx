import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsTournamentsPage } from './TournamentsPage'

const api = vi.hoisted(() => ({ getTournaments: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function tournament(id: string, name: string, tours: string[], categories: string[], notes: string[] = []) {
  return {
    tournament_id: id, name, tour_levels: tours, categories, notes,
    default_host_country: null, default_region: null, default_duration_weeks: null,
    has_qualification: null, source_template_ids: ['template-a'], status: 'read_only_foundation',
  }
}

const tournaments = [
  tournament('zulu_id', 'Zulu', ['WORLD_TOUR'], ['DIAMOND'], ['Review Zulu source']),
  tournament('alpha_id', 'Alpha', ['ELITE_TOUR'], ['IRON'], ['Review Alpha source']),
  tournament('bravo_id', 'Bravo', ['WORLD_TOUR', 'ELITE_TOUR'], ['IRON', 'DIAMOND']),
]

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><AdminTourSeasonsTournamentsPage /></MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Read-only tournament master inventory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getTournaments.mockResolvedValue({
      tournaments, source_path: 'tournament-templates.json', status: 'read_only_foundation',
    })
  })

  it('filters by exact tour and category and retains true source order on reset', async () => {
    mount()
    expect(await screen.findByText('Showing 3 of 3 tournament records')).toBeInTheDocument()
    const links = () => within(screen.getByRole('table', { name: 'Tournament master records table' }))
      .getAllByRole('link').map(link => link.getAttribute('href'))
    expect(links()).toEqual([
      '/admin/tour-seasons/tournaments/zulu_id',
      '/admin/tour-seasons/tournaments/alpha_id',
      '/admin/tour-seasons/tournaments/bravo_id',
    ])
    expect(screen.getByRole('table', { name: 'Tournament master records table' }).parentElement)
      .toHaveClass('table-responsive')

    const tour = screen.getByRole('combobox', { name: 'Filter tournament tour level' })
    const category = screen.getByRole('combobox', { name: 'Filter tournament category' })
    fireEvent.change(tour, { target: { value: 'WORLD_TOUR' } })
    expect(screen.getByText('Showing 2 of 3 tournament records')).toBeInTheDocument()
    fireEvent.change(category, { target: { value: 'IRON' } })
    expect(links()).toEqual(['/admin/tour-seasons/tournaments/bravo_id'])
    expect(screen.getByText('Showing 1 of 3 tournament records')).toBeInTheDocument()
    expect(screen.queryByText('Zulu notes: Review Zulu source')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear tournament filters' }))
    expect(tour).toHaveValue('')
    expect(category).toHaveValue('')
    expect(links()[0]).toBe('/admin/tour-seasons/tournaments/zulu_id')
    expect(screen.getByText('Zulu notes: Review Zulu source')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear tournament filters' })).toBeDisabled()
    expect(api.getTournaments).toHaveBeenCalledTimes(1)
  })

  it('trims case-insensitive ID searches and sorts names without modifying source rows', async () => {
    mount()
    expect(await screen.findByText('Showing 3 of 3 tournament records')).toBeInTheDocument()
    const search = screen.getByRole('searchbox', { name: 'Search tournament name or ID' })
    fireEvent.change(search, { target: { value: ' ALPHA_ID ' } })
    const table = () => screen.getByRole('table', { name: 'Tournament master records table' })
    expect(within(table()).getByRole('link', { name: 'Alpha (alpha_id)' }))
      .toHaveAttribute('href', '/admin/tour-seasons/tournaments/alpha_id')
    expect(screen.queryByText('Zulu notes: Review Zulu source')).not.toBeInTheDocument()
    expect(screen.getByText('Alpha notes: Review Alpha source')).toBeInTheDocument()

    fireEvent.change(search, { target: { value: '' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Sort tournament records' }),
      { target: { value: 'name' } })
    const order = within(table()).getAllByRole('link').map(link => link.textContent)
    expect(order).toEqual(['Alpha (alpha_id)', 'Bravo (bravo_id)', 'Zulu (zulu_id)'])
    expect(api.getTournaments).toHaveBeenCalledTimes(1)
  })

  it('distinguishes a truly empty tournament registry from no matches', async () => {
    api.getTournaments.mockResolvedValue({
      tournaments: [], source_path: null, status: 'read_only_foundation'
    })
    mount()
    expect(await screen.findByText('No tournament master records available.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 tournament records')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search tournament name or ID' }),
      { target: { value: 'none' } })
    expect(screen.queryByText('No tournament records match the current filters.')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Tournament master records table' })).not.toBeInTheDocument()
  })
})
