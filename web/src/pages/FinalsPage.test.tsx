import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { FinalsPage } from './FinalsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getFinalsSummary: vi.fn(),
  getFinalsQualification: vi.fn(),
  getFinalsResult: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('FinalsPage', () => {
  beforeEach(() => {
    api.getFinalsSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      qualification: { run_id: 'run-a' },
      result: null
    })
    api.getFinalsQualification.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      source_as_of_season: 2027,
      source_as_of_week: 42,
      qualification: { qualified_player_ids: ['P1', 'P2'], groups: [{ id: 'A' }, { id: 'B' }] }
    })
    api.getFinalsResult.mockResolvedValue({
      run_id: 'run-a',
      season: 2027,
      event_id: 'WORLD_TOUR_FINALS',
      source_as_of_season: 2027,
      source_as_of_week: 42,
      result: { champion_player_id: 'P1', runner_up_player_id: 'P2' }
    })
    api.simulateWorldTourFinals.mockResolvedValue({
      finals: { already_simulated: false }
    })
  })

  it('renders finals summary highlights and payloads', async () => {
    renderWithRoute(<FinalsPage />, '/runs/run-a/finals')

    expect(await screen.findByText('World Tour Finals')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Current context' })).toBeInTheDocument()
    expect(await screen.findByText(/Qualification status/i)).toBeInTheDocument()
    expect(await screen.findByText(/Qualified players/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/Groups/i)).length).toBeGreaterThan(0)
    expect((await screen.findAllByText(/Champion/i)).length).toBeGreaterThan(0)
    expect(await screen.findByText(/WORLD_TOUR_FINALS/i)).toBeInTheDocument()
    expect(await screen.findByText(/runner_up_player_id/i)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open qualification detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/finals/qualification'
    )
    expect(screen.getByRole('link', { name: 'Open result detail' })).toHaveAttribute('href', '/runs/run-a/finals/result')
  })

  it('calls finals simulation endpoint and refetches finals data', async () => {
    renderWithRoute(<FinalsPage />, '/runs/run-a/finals')

    await userEvent.click(await screen.findByRole('button', { name: /Simulate World Tour Finals/i }))

    await waitFor(() => expect(api.simulateWorldTourFinals).toHaveBeenCalledWith('run-a'))
    await waitFor(() => expect(api.getFinalsSummary.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getFinalsQualification.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getFinalsResult.mock.calls.length).toBeGreaterThanOrEqual(2))
  })

  it('shows readable error when finals simulation fails', async () => {
    api.simulateWorldTourFinals.mockRejectedValueOnce(
      new api.ApiError('{"detail":"Cannot simulate finals before completed regular season"}', 400)
    )

    renderWithRoute(<FinalsPage />, '/runs/run-a/finals')

    await userEvent.click(await screen.findByRole('button', { name: /Simulate World Tour Finals/i }))

    expect(await screen.findByText(/Cannot simulate finals before completed regular season/i)).toBeInTheDocument()
  })

  it('shows a readable not-found message for missing finals result', async () => {
    api.getFinalsResult.mockRejectedValueOnce(new api.ApiError('{"detail":"No finals result for run"}', 404))
    renderWithRoute(<FinalsPage />, '/runs/run-a/finals')

    expect(await screen.findByText(/Finals result has not been recorded/i)).toBeInTheDocument()
  })

  it('shows true errors as errors when finals result request fails', async () => {
    api.getFinalsResult.mockRejectedValueOnce(new api.ApiError('{"detail":"Finals result service unavailable"}', 500))
    renderWithRoute(<FinalsPage />, '/runs/run-a/finals')

    expect(await screen.findByText(/Failed to load Finals result/i)).toBeInTheDocument()
    expect(await screen.findByText(/Finals result service unavailable/i)).toBeInTheDocument()
  })
})
