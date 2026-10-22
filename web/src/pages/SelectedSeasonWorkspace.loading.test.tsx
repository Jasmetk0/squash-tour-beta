import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SelectedSeasonWorkspace } from './SelectedSeasonWorkspace'

const api = vi.hoisted(() => ({
  getAdminPointBreakdown: vi.fn(), getAdminRankingSnapshot: vi.fn(), getAdminRankingTable: vi.fn(),
  getSeasonActivePlayers: vi.fn(), getSeasonCalendar: vi.fn(), getSeasonRegistry: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function foreverPending() { return new Promise<never>(() => {}) }

function mount(label: string | null = '2000/01') {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><SelectedSeasonWorkspace selectedSeasonRaw={label} /></MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Selected Season Workspace truthful loading states', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonRegistry.mockResolvedValue({ seasons: [{ label: '2000/01', status: 'registry_only' }] })
    api.getSeasonActivePlayers.mockImplementation(foreverPending)
    api.getSeasonCalendar.mockImplementation(foreverPending)
    api.getAdminRankingTable.mockImplementation(foreverPending)
    api.getAdminRankingSnapshot.mockImplementation(foreverPending)
    api.getAdminPointBreakdown.mockImplementation(foreverPending)
  })

  it('shows Loading rather than Unavailable while five supported inspections have not returned', async () => {
    mount()
    const list = await screen.findByRole('heading', { name: 'Selected Season Workspace' })
    expect(list).toBeInTheDocument()
    await waitFor(() => expect(api.getSeasonActivePlayers).toHaveBeenCalledTimes(1))
    const pills = screen.getAllByRole('list', { name: 'Summary highlights' })
    const statuses = pills.flatMap(item => within(item).getAllByText('Loading…'))
    expect(statuses).toHaveLength(5)
    expect(screen.queryByText(/Unavailable \(/)).not.toBeInTheDocument()
  })

  it('transitions each independently settled check to its real loaded or failed state', async () => {
    api.getSeasonActivePlayers.mockResolvedValue({ summary: { total_active_players: 42 } })
    api.getSeasonCalendar.mockRejectedValue(new Error('calendar service unavailable'))
    mount()
    expect(await screen.findByText('Loaded (42)')).toBeInTheDocument()
    expect(await screen.findByText(/Unavailable \(calendar service unavailable\)/)).toBeInTheDocument()
    expect(screen.getAllByText('Loading…')).toHaveLength(3)
  })

  it('does not start queries for malformed season labels', () => {
    mount('not-a-season')
    expect(screen.getByText('Selected season label is invalid.')).toBeInTheDocument()
    expect(api.getSeasonActivePlayers).not.toHaveBeenCalled()
    expect(api.getAdminRankingTable).not.toHaveBeenCalled()
  })
})
