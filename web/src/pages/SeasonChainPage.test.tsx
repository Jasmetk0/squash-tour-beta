import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SeasonChainPage } from './SeasonChainPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRunStatusSummary: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('SeasonChainPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'bootstrap',
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
          source_type: 'bootstrap',
          parent_run_id: 'run-parent',
          source_rollover_run_id: 'run-parent',
          source_rollover_from_season: 2027,
          source_rollover_to_season: 2028
        },
        children: ['run-child-1', 'run-child-2']
      }
    })
    api.getRunStatusSummary.mockImplementation(async (runId: string) => ({
      run_id: runId,
      season: runId === 'run-parent' ? 2027 : runId === 'run-a' ? 2028 : 2029,
      seed: 1,
      progress: { next_event_index: 3, total_events: 20, completed_event_count: 2 },
      finals: { qualification_available: true, result_available: false },
      rollover: runId === 'run-a' ? { latest_to_season: 2029, transitioned_players: 64 } : null,
      source: { source_type: runId === 'run-parent' ? 'new_run' : 'bootstrap', parent_run_id: runId === 'run-parent' ? null : 'run-parent' },
      lineage: { child_run_count: runId === 'run-parent' ? 1 : 0 },
      history_counts: { events: 2, ranking_snapshots: 2, race_snapshots: 2 }
    }))
  })

  it('renders season-chain route and current run card from status summary', async () => {
    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    expect(await screen.findByRole('heading', { name: 'Season Chain' })).toBeInTheDocument()
    expect(await screen.findByText('Current run')).toBeInTheDocument()
    expect(screen.getAllByText('run-a').length).toBeGreaterThan(0)
    expect(screen.getByText('3 / 20')).toBeInTheDocument()
  })

  it('renders parent and child run cards when chain data exists', async () => {
    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    expect(await screen.findByText('Parent run')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'run-parent' })).toHaveAttribute('href', '/runs/run-parent')
    expect(await screen.findByRole('heading', { name: 'run-child-1' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'run-child-2' })).toBeInTheDocument()
  })

  it('renders readable empty states when parent and children are absent', async () => {
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

    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    expect(await screen.findByText('No parent run is linked for this run.')).toBeInTheDocument()
    expect(await screen.findByText('No child runs exist for this run yet.')).toBeInTheDocument()
  })
})
