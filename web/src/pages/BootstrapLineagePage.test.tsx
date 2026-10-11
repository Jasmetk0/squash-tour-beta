import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BootstrapLineagePage } from './BootstrapLineagePage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  getRunStatusSummary: vi.fn(),
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
    vi.resetAllMocks()

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
        children: ['run-child-a', 'run-child-b']
      }
    })

    api.getRunStatusSummary.mockImplementation(async (runId: string) => {
      if (runId === 'run-a') {
        return {
          run_id: 'run-a',
          season: 2028,
          seed: 7,
          progress: { next_event_index: 3, total_events: 22, completed_event_count: 3 },
          finals: { qualification_available: false, result_available: false },
          rollover: null,
          source: { source_type: 'bootstrapped_rollover', parent_run_id: 'run-parent' },
          lineage: { child_run_count: 2 },
          history_counts: { events: 3, ranking_snapshots: 3, race_snapshots: 3 }
        }
      }

      if (runId === 'run-parent') {
        return {
          run_id: 'run-parent',
          season: 2027,
          seed: 9,
          progress: { next_event_index: 22, total_events: 22, completed_event_count: 22 },
          finals: { qualification_available: true, result_available: true },
          rollover: { latest_to_season: 2028, transitioned_players: 64 },
          source: { source_type: 'new_run', parent_run_id: null },
          lineage: { child_run_count: 1 },
          history_counts: { events: 22, ranking_snapshots: 22, race_snapshots: 22 }
        }
      }

      return {
        run_id: runId,
        season: runId === 'run-child-a' ? 2029 : 2030,
        seed: 11,
        progress: { next_event_index: 1, total_events: 22, completed_event_count: 1 },
        finals: { qualification_available: false, result_available: false },
        rollover: null,
        source: { source_type: 'bootstrapped_rollover', parent_run_id: 'run-a' },
        lineage: { child_run_count: 0 },
        history_counts: { events: 1, ranking_snapshots: 1, race_snapshots: 1 }
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

  it('renders stronger provenance and lineage summary sections', async () => {
    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    expect(await screen.findByText('Current run provenance summary')).toBeInTheDocument()
    expect(await screen.findByText('Classification')).toBeInTheDocument()
    expect(await screen.findByText('rollover-derived')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Rollover provenance' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Open source rollover detail' })).toHaveAttribute(
      'href',
      '/runs/run-parent/rollover/2028'
    )
  })

  it('restores bootstrap action form and success flow with refresh', async () => {
    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    expect(await screen.findByRole('heading', { name: 'Bootstrap next season child run' })).toBeInTheDocument()
    await userEvent.type(await screen.findByLabelText(/Child run ID/i), 'run-child-2029')
    await userEvent.type(screen.getByLabelText(/Child seed/i), '91')
    await userEvent.click(screen.getByRole('button', { name: /Bootstrap next season/i }))

    await waitFor(() =>
      expect(api.bootstrapNextSeason).toHaveBeenCalledWith('run-a', { child_run_id: 'run-child-2029', child_seed: 91 })
    )
    await waitFor(() => expect(api.getRunSource.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getRunLineage.mock.calls.length).toBeGreaterThanOrEqual(2))
    await waitFor(() => expect(api.getRunStatusSummary.mock.calls.length).toBeGreaterThanOrEqual(4))

    expect(await screen.findByText(/Transitioned players/i)).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /Open child run/i })).toHaveAttribute('href', '/runs/run-child-2029')
  })

  it('shows readable bootstrap error state', async () => {
    api.bootstrapNextSeason.mockRejectedValueOnce(new api.ApiError('{"detail":"Persist rollover before bootstrapping"}', 400))

    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    await userEvent.type(await screen.findByLabelText(/Child run ID/i), 'run-child-fail')
    await userEvent.click(screen.getByRole('button', { name: /Bootstrap next season/i }))

    expect(await screen.findByText(/Persist rollover before bootstrapping/i)).toBeInTheDocument()
  })

  it('keeps child run links in lineage API order', async () => {
    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    const childAHeading = await screen.findByRole('heading', { name: 'run-child-a' })
    const childBHeading = await screen.findByRole('heading', { name: 'run-child-b' })
    expect(childAHeading.compareDocumentPosition(childBHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()

    const diagnosticsLinks = await screen.findAllByRole('link', { name: 'Diagnostics' })
    expect(diagnosticsLinks.some((link) => link.getAttribute('href') === '/runs/run-child-a/diagnostics')).toBe(true)
    expect(diagnosticsLinks.some((link) => link.getAttribute('href') === '/runs/run-child-b/diagnostics')).toBe(true)
  })

  it('shows explicit no-parent, no-children, and no-rollover states', async () => {
    api.getRunSource.mockResolvedValueOnce({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockResolvedValueOnce({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: []
      }
    })

    renderWithRoute(<BootstrapLineagePage />, '/runs/run-a/bootstrap-lineage')

    expect(await screen.findByText('No parent run linked for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No child runs linked for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No rollover provenance is linked for this run.')).toBeInTheDocument()
  })
})
