import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LegacyRunPlayersExplorerPage } from './LegacyRunPlayersExplorerPage'

const api = vi.hoisted(() => ({ listRunPlayers: vi.fn(), getRunPlayerDetail: vi.fn() }))
vi.mock('../api/client', () => api)

const player = {
  player_id: 'player/one', name: 'Player One', country_code: 'CZE',
  age: 22, source_type: 'planner_generated', quality_band: 'elite',
  technique: 72, movement: 76, physical: 79, mental: 68,
}

function mount(initial = '/runs/run-a/players/legacy') {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[initial]}>
        <Link to="/runs/run-b/players/legacy">Switch Run</Link>
        <Routes>
          <Route path="/runs/:runId/players/legacy" element={<LegacyRunPlayersExplorerPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Legacy Run player selection scope', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listRunPlayers.mockImplementation(async () => ({ total: 1, players: [player] }))
    api.getRunPlayerDetail.mockImplementation(async (_runId: string, id: string) => ({
      ...player, player_id: id, is_top_band: true, override_id: null,
      origin_source_type: 'planner_generated', origin_quality_band: 'elite',
      origin_season: 2028, origin_override_id: null,
      play_style: 'balanced', archetype: 'all-rounder',
    }))
  })

  it('does not fetch the old selected player from a newly selected Run', async () => {
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'player/one' }))
    await waitFor(() => expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run-a', 'player/one'))
    expect(await screen.findByRole('link', { name: 'View career history' })).toHaveAttribute(
      'href', '/runs/run-a/players/player%2Fone/career'
    )
    fireEvent.click(screen.getByRole('link', { name: 'Switch Run' }))
    expect(await screen.findByText('Select a player from the table to inspect detail.')).toBeInTheDocument()
    await waitFor(() => expect(api.listRunPlayers.mock.calls.some(([runId]) => runId === 'run-b')).toBe(true))
    expect(api.getRunPlayerDetail.mock.calls.filter(([runId]) => runId === 'run-b')).toHaveLength(0)
    expect(screen.queryByRole('link', { name: 'View career history' })).not.toBeInTheDocument()
  })

  it('safely encodes both Run and player IDs in the career link', async () => {
    mount('/runs/run%20x%2Fy/players/legacy')
    fireEvent.click(await screen.findByRole('button', { name: 'player/one' }))
    expect(await screen.findByRole('link', { name: 'View career history' })).toHaveAttribute(
      'href', '/runs/run%20x%2Fy/players/player%2Fone/career'
    )
    expect(api.getRunPlayerDetail).toHaveBeenCalledWith('run x/y', 'player/one')
  })
})
