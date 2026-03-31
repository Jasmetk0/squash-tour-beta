import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BootstrapLineagePage } from './BootstrapLineagePage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  bootstrapNextSeason: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('BootstrapLineagePage', () => {
  beforeEach(() => {
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'bootstrapped_rollover',
        parent_run_id: 'run-parent',
        source_rollover_run_id: 'run-parent',
        source_rollover_from_season: 2027,
        source_rollover_to_season: 2028
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'bootstrapped_rollover',
          parent_run_id: 'run-parent',
          source_rollover_run_id: 'run-parent',
          source_rollover_from_season: 2027,
          source_rollover_to_season: 2028
        },
        children: ['run-child-existing']
      }
    })
    api.bootstrapNextSeason.mockResolvedValue({
      run: { run_id: 'run-child-2029', season: 2029, seed: 91 },
      bootstrap: {
        parent_run_id: 'run-a',
        child_run_id: 'run-child-2029',
        from_season: 2028,
        to_season: 2029,
        child_seed: 91,
        transitioned_players: 64,
        source_rollover_run_id: 'run-a',
        source_rollover_to_season: 2029,
        already_bootstrapped: false
      }
    })
  })

  it('renders source and lineage data from API', async () => {
    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    expect(await screen.findByText('Bootstrap / Lineage')).toBeInTheDocument()
    expect(await screen.findByText(/bootstrapped_rollover/i)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'run-parent' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'run-child-existing' })).toBeInTheDocument()
  })

  it('calls bootstrap endpoint and refreshes source/lineage after success', async () => {
    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    await userEvent.type(await screen.findByLabelText(/Child run ID/i), 'run-child-2029')
    await userEvent.type(screen.getByLabelText(/Child seed/i), '91')
    await userEvent.click(screen.getByRole('button', { name: /Bootstrap next season/i }))

    await waitFor(() =>
      expect(api.bootstrapNextSeason).toHaveBeenCalledWith('run-a', { child_run_id: 'run-child-2029', child_seed: 91 })
    )
    await waitFor(() => expect(api.getRunSource.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getRunLineage.mock.calls.length).toBeGreaterThanOrEqual(2))
    expect(await screen.findByRole('link', { name: /Open child run/i })).toHaveAttribute('href', '/runs/run-child-2029')
  })

  it('omits child_seed when optional input is empty', async () => {
    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    await userEvent.type(await screen.findByLabelText(/Child run ID/i), 'run-child-no-seed')
    await userEvent.click(screen.getByRole('button', { name: /Bootstrap next season/i }))

    await waitFor(() =>
      expect(api.bootstrapNextSeason).toHaveBeenCalledWith('run-a', { child_run_id: 'run-child-no-seed' })
    )
  })

  it('shows readable error when bootstrap action fails', async () => {
    api.bootstrapNextSeason.mockRejectedValueOnce(new api.ApiError('{"detail":"Persist rollover before bootstrapping"}', 400))

    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    await userEvent.type(await screen.findByLabelText(/Child run ID/i), 'run-child-fail')
    await userEvent.click(screen.getByRole('button', { name: /Bootstrap next season/i }))

    expect(await screen.findByText(/Persist rollover before bootstrapping/i)).toBeInTheDocument()
  })

  it('shows readable not-found messages for missing source and lineage metadata', async () => {
    api.getRunSource.mockRejectedValueOnce(new api.ApiError('{"detail":"Run source not found"}', 404))
    api.getRunLineage.mockRejectedValueOnce(new api.ApiError('{"detail":"Run lineage not found"}', 404))

    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    expect(await screen.findByText(/No source metadata is available/i)).toBeInTheDocument()
    expect(await screen.findByText(/No lineage record is available/i)).toBeInTheDocument()
  })
})
