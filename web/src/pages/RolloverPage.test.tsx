import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RolloverPage } from './RolloverPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getLatestRollover: vi.fn(),
  getRunStatusSummary: vi.fn(),
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
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2028,
      seed: 42,
      progress: {
        next_event_index: 3,
        total_events: 24,
        completed_event_count: 3
      },
      finals: {
        qualification_available: false,
        result_available: false
      },
      rollover: {
        latest_to_season: 2028,
        transitioned_players: 3
      },
      source: {
        source_type: 'new_run',
        parent_run_id: null
      },
      lineage: {
        child_run_count: 0
      },
      history_counts: {
        events: 3,
        ranking_snapshots: 3,
        race_snapshots: 3
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
        to_season: 2029,
        already_persisted: false
      }
    })
  })

  it('renders stronger latest rollover summary and bridge navigation', async () => {
    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    expect(await screen.findByText('Season Rollover')).toBeInTheDocument()
    expect(await screen.findByText(/Current run bridge navigation/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/runs/run-a')
    expect(screen.getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', '/runs/run-a/diagnostics')
    expect(screen.getByRole('link', { name: 'Season Chain' })).toHaveAttribute('href', '/runs/run-a/season-chain')

    expect(await screen.findByText(/Latest rollover summary/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/From season/i)).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/To season/i)).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/Transitioned players/i)).length).toBeGreaterThan(0)
  })

  it('restores rollover action button and success refresh flow', async () => {
    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    const rolloverButton = await screen.findByRole('button', { name: /Roll over to next season/i })
    expect(rolloverButton).toBeInTheDocument()

    await userEvent.click(rolloverButton)

    await waitFor(() => expect(api.rolloverNextSeason).toHaveBeenCalledWith('run-a'))
    await screen.findByText(/Rollover complete for season 2029/i)
    await waitFor(() => expect(api.getLatestRollover.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getRolloverBySeason.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getPlayerTransitions.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getNextSeasonPlayers.mock.calls.length).toBeGreaterThanOrEqual(2))
  })

  it('shows readable rollover action error state', async () => {
    api.rolloverNextSeason.mockRejectedValueOnce(new api.ApiError('{"detail":"Season must be complete"}', 400))

    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    await userEvent.click(await screen.findByRole('button', { name: /Roll over to next season/i }))
    expect(await screen.findByText(/Could not execute rollover: Season must be complete/i)).toBeInTheDocument()
  })

  it('shows open rollover season detail link when latest rollover exists', async () => {
    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    expect(await screen.findByRole('link', { name: 'Open rollover season detail' })).toHaveAttribute('href', '/runs/run-a/rollover/2028')
    expect(await screen.findByRole('link', { name: 'Inspect latest rollover season detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/rollover/2028'
    )
  })

  it.each(['2e3', '0x7ec', '2028.0', '-2028', '999999999999999999999999'])(
    'rejects noncanonical rollover season input %s without fetching the wrong year',
    async (raw) => {
      renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')
      expect(await screen.findByRole('link', { name: 'Open rollover season detail' }))
        .toHaveAttribute('href', '/runs/run-a/rollover/2028')
      await waitFor(() => expect(api.getRolloverBySeason).toHaveBeenCalledWith('run-a', 2028))
      api.getRolloverBySeason.mockClear()
      fireEvent.change(screen.getByRole('textbox', { name: 'To season' }), { target: { value: raw } })
      fireEvent.click(screen.getByRole('button', { name: 'Load season data' }))
      expect(screen.getByRole('alert')).toHaveTextContent(
        'Enter a positive whole-number season using decimal digits only.'
      )
      expect(screen.getByRole('link', { name: 'Open selected rollover season detail' }))
        .toHaveAttribute('href', '/runs/run-a/rollover/2028')
      expect(api.getRolloverBySeason).not.toHaveBeenCalled()
    }
  )

  it('accepts a correct year and preserves reserved Run ID characters in links', async () => {
    renderWithRoute(<RolloverPage />, '/runs/run%20x%2Fy/rollover')
    const input = screen.getByRole('textbox', { name: 'To season' })
    await waitFor(() => expect(input).toHaveValue('2028'))
    fireEvent.change(input, { target: { value: '2030' } })
    fireEvent.click(screen.getByRole('button', { name: 'Load season data' }))
    await waitFor(() => expect(api.getRolloverBySeason).toHaveBeenCalledWith('run x/y', 2030))
    expect(screen.getByRole('link', { name: 'Run Detail' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy')
    expect(screen.getByRole('link', { name: 'Diagnostics' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy/diagnostics')
    expect(screen.getByRole('link', { name: 'Open selected rollover season detail' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy/rollover/2030')
    expect(screen.getByRole('link', { name: 'Open rollover season detail' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy/rollover/2028')
    expect(screen.getByRole('link', { name: 'Inspect latest rollover season detail' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy/rollover/2028')
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows explicit readable no-rollover state', async () => {
    api.getLatestRollover.mockRejectedValueOnce(new api.ApiError('{"detail":"No rollover found for run"}', 404))

    renderWithRoute(<RolloverPage />, '/runs/run-a/rollover')

    expect(await screen.findByText(/No rollover has been executed for this run yet/i)).toBeInTheDocument()
    expect(await screen.findByText(/No rollover yet. Enter a target season to inspect if persisted/i)).toBeInTheDocument()
  })
})
