import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RolloverPage } from './RolloverPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getLatestRollover: vi.fn(),
  getRolloverBySeason: vi.fn(),
  getPlayerTransitions: vi.fn(),
  getNextSeasonPlayers: vi.fn(),
  rolloverNextSeason: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('RolloverPage', () => {
  beforeEach(() => {
    api.getLatestRollover.mockResolvedValue({
      rollover: {
        run_id: 'run-a',
        from_season: 2027,
        to_season: 2028,
        transitioned_players: 3,
        metadata: { status: 'mvp_rollover' }
      }
    })
    api.getRolloverBySeason.mockResolvedValue({
      rollover: {
        run_id: 'run-a',
        from_season: 2027,
        to_season: 2028,
        transitioned_players: 3,
        metadata: { status: 'mvp_rollover' }
      }
    })
    api.getPlayerTransitions.mockResolvedValue({
      run_id: 'run-a',
      to_season: 2028,
      transitions: [{ player_id: 'P1', transition: { notes: ['steady'] } }]
    })
    api.getNextSeasonPlayers.mockResolvedValue({
      run_id: 'run-a',
      to_season: 2028,
      players: [{ player_id: 'P1', state: { readiness: 0.8 } }]
    })
    api.rolloverNextSeason.mockResolvedValue({
      rollover: {
        to_season: 2028,
        already_persisted: false
      }
    })
  })

  it('renders latest rollover data and target season summary counts', async () => {
    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    expect(await screen.findByText('Season Rollover')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Current context' })).toBeInTheDocument()
    expect(await screen.findByText(/Latest rollover summary/i)).toBeInTheDocument()
    expect(await screen.findByText(/Target season inspection summary/i)).toBeInTheDocument()
    expect(await screen.findByText(/Transition records/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/Next-season players/i)).length).toBeGreaterThan(0)

    expect(screen.getAllByRole('link', { name: 'Open rollover season detail' })[0]).toHaveAttribute('href', '/runs/run-a/rollover/2028')
  })

  it('calls rollover endpoint and refreshes rollover queries', async () => {
    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    await userEvent.click(await screen.findByRole('button', { name: /Roll over to next season/i }))

    await waitFor(() => expect(api.rolloverNextSeason).toHaveBeenCalledWith('run-a'))
    await waitFor(() => expect(api.getLatestRollover.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getRolloverBySeason.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getPlayerTransitions.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getNextSeasonPlayers.mock.calls.length).toBeGreaterThanOrEqual(2))
  })

  it('loads a user-selected target season', async () => {
    api.getLatestRollover.mockRejectedValueOnce(new api.ApiError('{"detail":"No rollover found for run"}', 404))
    api.getRolloverBySeason.mockResolvedValueOnce({
      rollover: {
        run_id: 'run-a',
        from_season: 2028,
        to_season: 2029,
        transitioned_players: 5,
        metadata: {}
      }
    })

    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    const input = await screen.findByLabelText(/To season/i)
    fireEvent.change(input, { target: { value: '2029' } })
    await userEvent.click(screen.getByRole('button', { name: /Load season data/i }))

    await waitFor(() => expect(api.getRolloverBySeason).toHaveBeenCalledWith('run-a', 2029))
  })

  it('shows readable empty states for no transitions and no players payloads', async () => {
    api.getPlayerTransitions.mockResolvedValueOnce({ run_id: 'run-a', to_season: 2028, transitions: [] })
    api.getNextSeasonPlayers.mockResolvedValueOnce({ run_id: 'run-a', to_season: 2028, players: [] })

    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    expect(await screen.findByText(/No transition records are available/i)).toBeInTheDocument()
    expect(await screen.findByText(/No next-season players are available/i)).toBeInTheDocument()
  })

  it('shows readable error when rollover action fails', async () => {
    api.rolloverNextSeason.mockRejectedValueOnce(new api.ApiError('{"detail":"Season must be complete"}', 400))

    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    await userEvent.click(await screen.findByRole('button', { name: /Roll over to next season/i }))

    expect(await screen.findByText(/Season must be complete/i)).toBeInTheDocument()
  })
})
