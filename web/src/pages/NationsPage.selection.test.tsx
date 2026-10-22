import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { NationsPage } from './NationsPage'

const api = vi.hoisted(() => ({ listRunNations: vi.fn(), getRunNationDetail: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/runs/run-a/nations']}>
        <Link to="/runs/run-b/nations">Switch Run</Link>
        <Routes><Route path="/runs/:runId/nations" element={<NationsPage />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const nation = {
  country_code: 'EGY', country_name: 'Egypt', total_players: 5, average_overall: 78.4,
  average_age: 25.2, top_band_count: 2, rollover_carried_count: 1,
  planner_generated_count: 3, manual_override_count: 1,
  top_player_id: 'p1', top_player_name: 'Ali', top_player_overall: 92,
}

describe('Nations Dashboard source-scoped selection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.listRunNations.mockImplementation(async (runId: string) => ({
      run_id: runId, total: 1, limit: 300, offset: 0, nations: [nation],
    }))
    api.getRunNationDetail.mockImplementation(async (runId: string, code: string) => ({
      ...nation, run_id: runId, country_code: code, source_mix: {},
      average_visible_stats: { technique: 80, movement: 80, physical: 80, mental: 80 },
      band_distribution: [], origin_band_distribution: [], top_players: [],
    }))
  })

  it('does not request an old selected country for a different Run after navigation', async () => {
    mount()
    fireEvent.click(await screen.findByRole('button', { name: 'EGY — Egypt' }))
    await waitFor(() => expect(api.getRunNationDetail).toHaveBeenCalledWith('run-a', 'EGY'))
    expect(await screen.findByText(/Source mix: carryover/)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'Switch Run' }))
    expect(await screen.findByText('Select a country from the table to inspect detail.')).toBeInTheDocument()
    await waitFor(() => expect(api.listRunNations).toHaveBeenCalledWith(
      'run-b', expect.objectContaining({ sort: 'total_players_desc' })
    ))
    expect(api.getRunNationDetail.mock.calls.filter(([id]) => id === 'run-b')).toHaveLength(0)
    expect(screen.getByRole('table', { name: 'Run nations table' })).toBeInTheDocument()
  })

  it('does not show an empty grid when a Run has no matching nations', async () => {
    api.listRunNations.mockResolvedValue({
      run_id: 'run-a', total: 0, limit: 300, offset: 0, nations: [],
    })
    mount()
    expect(await screen.findByText('No nations match the current search or Run.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Run nations table' })).not.toBeInTheDocument()
    expect(screen.getByText('Select a country from the table to inspect detail.')).toBeInTheDocument()
    expect(api.getRunNationDetail).not.toHaveBeenCalled()
  })
})
