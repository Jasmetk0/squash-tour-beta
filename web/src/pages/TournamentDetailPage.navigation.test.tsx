import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsTournamentDetailPage } from './TournamentDetailPage'

const api = vi.hoisted(() => ({ getTournaments: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function master(tournament_id: string, name: string) {
  return {
    tournament_id, name, status: 'read_only_foundation', source: 'tournament-templates',
    template_count: 1, source_template_ids: ['source-template'],
    categories: ['DIAMOND'], tour_levels: ['WORLD_TOUR'],
    default_category: null, default_duration_weeks: null,
    host_countries: [], regions: [], default_host_country: null, default_region: null,
    has_qualification: null, notes: [],
  }
}

function mount(id: string) {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[`/admin/tour-seasons/tournaments/${encodeURIComponent(id)}`]}>
        <Routes>
          <Route path="/admin/tour-seasons/tournaments/:tournamentId" element={<AdminTourSeasonsTournamentDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Read-only tournament master detail navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getTournaments.mockResolvedValue({
      tournaments: [
        master('z_first', 'Zulu'),
        master('a_middle', 'Alpha'),
        master('c_last', 'Charlie'),
      ],
      source_path: 'tournaments.json', status: 'read_only_foundation',
    })
  })

  it('follows the actual backend source order without guessing tour rankings', async () => {
    mount('a_middle')
    expect(await screen.findByText('Tournament 2 of 3 in backend source order.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Previous tournament: Zulu' }))
      .toHaveAttribute('href', '/admin/tour-seasons/tournaments/z_first')
    expect(screen.getByRole('link', { name: 'Next tournament: Charlie →' }))
      .toHaveAttribute('href', '/admin/tour-seasons/tournaments/c_last')

    fireEvent.click(screen.getByRole('link', { name: 'Next tournament: Charlie →' }))
    expect(await screen.findByText('Tournament 3 of 3 in backend source order.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Next tournament:/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← Previous tournament: Alpha' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('link', { name: '← Previous tournament: Alpha' }))
    expect(await screen.findByText('Tournament 2 of 3 in backend source order.')).toBeInTheDocument()
    expect(api.getTournaments).toHaveBeenCalledTimes(1)
  })

  it('offers no invented neighbors for missing tournament masters', async () => {
    mount('missing')
    expect(await screen.findByText('Tournament master not found.')).toBeInTheDocument()
    expect(screen.queryByText(/in backend source order/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Previous tournament:/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Next tournament:/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to Tournaments' }))
      .toHaveAttribute('href', '/admin/tour-seasons/tournaments')
  })

  it('keeps single-record backend catalogs without artificial navigation', async () => {
    api.getTournaments.mockResolvedValue({
      tournaments: [master('alone', 'Only Tournament')], source_path: null,
      status: 'read_only_foundation',
    })
    mount('alone')
    expect(await screen.findByText('Tournament 1 of 1 in backend source order.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Previous tournament:/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Next tournament:/ })).not.toBeInTheDocument()
  })
})
