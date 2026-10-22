import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SeasonHealthPreview } from './SeasonHealthPreview'

const api = vi.hoisted(() => ({
  getAdminPointBreakdown: vi.fn(), getAdminRankingSnapshot: vi.fn(),
  getAdminRankingTable: vi.fn(), getSeasonActivePlayers: vi.fn(),
  getSeasonCalendar: vi.fn(), getSeasonRegistry: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function mount(label = '2000/01') {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><SeasonHealthPreview seasonLabelRaw={label} /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Season Health read-only filter', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonRegistry.mockResolvedValue({ seasons: [{ label: '2000/01' }] })
    api.getSeasonCalendar.mockResolvedValue({ calendar: null, validation_warnings: [], validation_errors: [] })
    api.getSeasonActivePlayers.mockResolvedValue({ summary: { total_active_players: 2 } })
    api.getAdminRankingTable.mockResolvedValue({ summary: { player_count: 0 }, rows: [] })
    api.getAdminRankingSnapshot.mockResolvedValue({ snapshot_exists: false })
    api.getAdminPointBreakdown.mockResolvedValue({ summary_rows: [] })
  })

  it('filters the six existing checks without changing their severity rules or source data', async () => {
    mount()
    expect(await screen.findByText('Season 2000/01 exists in fixed registry.')).toBeInTheDocument()
    expect(await screen.findByText('Active players loaded: 2.')).toBeInTheDocument()
    expect(screen.getByText('Showing 6 of 6 season health checks')).toBeInTheDocument()
    const filter = screen.getByRole('combobox', { name: 'Filter season health checks' })
    const table = () => screen.getByRole('table', { name: 'Season health checks' })
    expect(table().parentElement).toHaveClass('table-responsive')
    expect(within(table()).getAllByRole('row')).toHaveLength(7)

    fireEvent.change(filter, { target: { value: 'OK' } })
    expect(screen.getByText('Showing 3 of 6 season health checks')).toBeInTheDocument()
    expect(within(table()).getByText('Registry check')).toBeInTheDocument()
    expect(within(table()).queryByText('Calendar check')).not.toBeInTheDocument()
    fireEvent.change(filter, { target: { value: 'Info' } })
    expect(screen.getByText('Showing 3 of 6 season health checks')).toBeInTheDocument()
    expect(within(table()).getByText('Calendar check')).toBeInTheDocument()
    expect(within(table()).queryByText('Registry check')).not.toBeInTheDocument()

    fireEvent.change(filter, { target: { value: 'Warning' } })
    expect(screen.getByText('Showing 0 of 6 season health checks')).toBeInTheDocument()
    expect(screen.getByText('No season health checks match the current filter.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season health checks' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear health check filter' }))
    expect(filter).toHaveValue('All')
    expect(table()).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear health check filter' })).toBeDisabled()
    expect(api.getSeasonRegistry).toHaveBeenCalledTimes(1)
    expect(api.getAdminRankingTable).toHaveBeenCalledTimes(1)
  })

  it('preserves the existing fail-safe message for invalid season labels', () => {
    mount('not-a-season')
    expect(screen.getByText('Season health preview unavailable for invalid season label.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season health checks' })).not.toBeInTheDocument()
  })
})
