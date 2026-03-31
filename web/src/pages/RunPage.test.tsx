import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPage } from './RunPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  getRun: vi.fn(),
  getFinalsSummary: vi.fn(),
  getLatestRollover: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  simulateNextTournament: vi.fn(),
  simulateNextWeek: vi.fn(),
  simulateFullSeason: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('RunPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2025, seed: 3, next_event_index: 1, total_events: 4, completed_event_ids: ['E1'] },
      season_state: { season: 2025, next_event_index: 1, completed_event_ids: ['E1'], ordered_events: [] }
    })
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2025,
      qualification: { run_id: 'run-a', season: 2025, source_as_of_season: 2025, source_as_of_week: 40, qualification: {} },
      result: null
    })
    api.getLatestRollover.mockResolvedValue({
      rollover: { run_id: 'run-a', from_season: 2025, to_season: 2026, transitioned_players: 128, metadata: {} }
    })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'bootstrap',
        parent_run_id: 'run-parent',
        source_rollover_run_id: 'run-parent',
        source_rollover_from_season: 2025,
        source_rollover_to_season: 2026
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'bootstrap',
          parent_run_id: 'run-parent',
          source_rollover_run_id: 'run-parent',
          source_rollover_from_season: 2025,
          source_rollover_to_season: 2026
        },
        children: ['run-child-1', 'run-child-2']
      }
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

  it('renders finals overview from finals summary data', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('World Tour Finals overview')).toBeInTheDocument()
    expect(screen.getByText('Available')).toBeInTheDocument()
    expect(screen.getByText('Not simulated yet')).toBeInTheDocument()
  })

  it('renders latest rollover overview from rollover api data', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('Latest rollover overview')).toBeInTheDocument()
    expect(screen.getByText('From season')).toBeInTheDocument()
    expect(screen.getByText('To season')).toBeInTheDocument()
    expect(screen.getByText('2026')).toBeInTheDocument()
    expect(screen.getByText('128')).toBeInTheDocument()
  })

  it('renders source and lineage overview from source + lineage data', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('Run source and lineage overview')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'run-parent' })).toHaveAttribute('href', '/runs/run-parent')
    expect(screen.getByText('Child runs: 2')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'run-child-1' })).toHaveAttribute('href', '/runs/run-child-1')
    expect(screen.getByRole('link', { name: 'run-child-2' })).toHaveAttribute('href', '/runs/run-child-2')
  })

  it('renders readable not-found empty states for rollover and lineage metadata', async () => {
    api.getLatestRollover.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunSource.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunLineage.mockRejectedValueOnce({ status: 404, message: 'not found' })

    renderWithRoute(<RunPage />, '/runs/run-a')

    expect(await screen.findByText('No rollover yet for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No source metadata available for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No lineage metadata available for this run.')).toBeInTheDocument()
  })

  it('refreshes overview queries after simulation succeeds', async () => {
    renderWithRoute(<RunPage />, '/runs/run-a')

    await screen.findByText('World Tour Finals overview')
    expect(api.getFinalsSummary).toHaveBeenCalledTimes(1)
    expect(api.getLatestRollover).toHaveBeenCalledTimes(1)
    expect(api.getRunSource).toHaveBeenCalledTimes(1)
    expect(api.getRunLineage).toHaveBeenCalledTimes(1)

    await userEvent.click(screen.getByRole('button', { name: 'Simulate next tournament' }))

    await waitFor(() => expect(api.getFinalsSummary).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getLatestRollover).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getRunSource).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(api.getRunLineage).toHaveBeenCalledTimes(2))
  })
})
