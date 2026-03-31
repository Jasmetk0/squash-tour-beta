import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPage } from './RunPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  simulateNextTournament: vi.fn(),
  simulateNextWeek: vi.fn(),
  simulateFullSeason: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('RunPage', () => {
  beforeEach(() => {
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2025, seed: 3, next_event_index: 1, total_events: 4, completed_event_ids: ['E1'] },
      season_state: { season: 2025, next_event_index: 1, completed_event_ids: ['E1'], ordered_events: [] }
    })
    api.simulateNextTournament.mockResolvedValue({ step: { mode: 'simulate_next_tournament' } })
    api.simulateNextWeek.mockResolvedValue({ step: { mode: 'simulate_next_week' } })
    api.simulateFullSeason.mockResolvedValue({ step: { mode: 'simulate_full_season' } })
  })

  it('calls each simulation endpoint', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await userEvent.click(await screen.findByRole('button', { name: 'Simulate next tournament' }))
    await waitFor(() => expect(api.simulateNextTournament).toHaveBeenCalledWith('run-a'))

    await userEvent.click(screen.getByRole('button', { name: 'Simulate next week' }))
    await waitFor(() => expect(api.simulateNextWeek).toHaveBeenCalledWith('run-a'))

    await userEvent.click(screen.getByRole('button', { name: 'Simulate full season' }))
    await waitFor(() => expect(api.simulateFullSeason).toHaveBeenCalledWith('run-a'))
  })

  it('renders navigation links for finals, rollover, and bootstrap lineage', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByRole('link', { name: /View World Tour Finals/i })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(await screen.findByRole('link', { name: /View season rollover/i })).toHaveAttribute('href', '/runs/run-a/rollover')
    expect(await screen.findByRole('link', { name: /View bootstrap and lineage/i })).toHaveAttribute(
      'href',
      '/runs/run-a/bootstrap-lineage'
    )
  })
})
