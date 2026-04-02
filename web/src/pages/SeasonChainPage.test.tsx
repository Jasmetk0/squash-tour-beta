import { screen, within } from '@testing-library/react'
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
          source_type: 'rollover_bootstrap',
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
      season: runId === 'run-parent' ? 2027 : runId === 'run-a' ? 2028 : runId === 'run-child-1' ? 2029 : 2030,
      seed: 1,
      progress: { next_event_index: 3, total_events: 20, completed_event_count: 2 },
      finals: { qualification_available: true, result_available: runId === 'run-child-2' },
      rollover: runId === 'run-a' ? { latest_to_season: 2029, transitioned_players: 64 } : null,
      source: { source_type: runId === 'run-parent' ? 'fresh_seed' : 'rollover_bootstrap', parent_run_id: runId === 'run-parent' ? null : 'run-parent' },
      lineage: { child_run_count: runId === 'run-parent' ? 1 : 0 },
      history_counts: { events: 2, ranking_snapshots: 2, race_snapshots: 2 }
    }))
  })

  it('renders richer chain summary signals', async () => {
    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    expect(await screen.findByRole('heading', { name: 'Season Chain' })).toBeInTheDocument()
    expect(await screen.findByText('Parent status')).toBeInTheDocument()
    expect(screen.getByText('Children status')).toBeInTheDocument()
    expect(screen.getByText('Rollover exists')).toBeInTheDocument()
    expect(screen.getByText('Finals signal')).toBeInTheDocument()
    expect(screen.getByText('Source metadata')).toBeInTheDocument()
    expect(screen.getByText('Lineage metadata')).toBeInTheDocument()
  })

  it('renders season-to-season signals for parent/current/children relationships', async () => {
    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    expect(await screen.findByRole('heading', { name: 'Season-to-season signals' })).toBeInTheDocument()
    expect(await screen.findByText('Parent season 2027 → current season 2028')).toBeInTheDocument()
    expect(await screen.findByText('2028 → 2029 (run-child-1); 2028 → 2030 (run-child-2)')).toBeInTheDocument()
    expect(await screen.findByText('Latest rollover to season 2029')).toBeInTheDocument()
    expect(await screen.findByText('Rollover-derived (rollover_bootstrap)')).toBeInTheDocument()
  })

  it('renders relevant next inspection links from loaded chain data', async () => {
    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    const linksSection = await screen.findByRole('heading', { name: 'Most relevant next inspection links' })
    const list = linksSection.parentElement as HTMLElement

    expect(await within(list).findByRole('link', { name: 'Parent diagnostics' })).toHaveAttribute('href', '/runs/run-parent/diagnostics')
    expect(await within(list).findByRole('link', { name: 'Current rollover' })).toHaveAttribute('href', '/runs/run-a/rollover')
    expect(await within(list).findByRole('link', { name: 'Current finals' })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(await within(list).findByRole('link', { name: 'Child diagnostics: run-child-1' })).toHaveAttribute('href', '/runs/run-child-1/diagnostics')
    expect(await within(list).findByRole('link', { name: 'Current bootstrap / lineage' })).toHaveAttribute('href', '/runs/run-a/bootstrap-lineage')
  })

  it('renders readable empty states when parent and children are absent', async () => {
    api.getRunSource.mockResolvedValueOnce({
      source: {
        source_type: 'fresh_seed',
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
          source_type: 'fresh_seed',
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
    expect(screen.getByText('No parent run linked')).toBeInTheDocument()
    expect(screen.getByText('No child runs to compare')).toBeInTheDocument()
  })

  it('renders child run cards in lineage API order', async () => {
    renderWithRoute(<SeasonChainPage />, '/runs/run-a/season-chain')

    const childSectionHeading = await screen.findByRole('heading', { name: 'Child runs' })
    await screen.findByRole('heading', { name: 'run-child-2' })
    const childSection = childSectionHeading.parentElement as HTMLElement
    const childHeadings = within(childSection).getAllByRole('heading', { level: 4 })
      .map((item) => item.textContent)
      .filter((text): text is string => Boolean(text))

    expect(childHeadings).toEqual(['run-child-1', 'run-child-2'])
    expect(screen.getByText('Season progression: 2028 → 2029')).toBeInTheDocument()
    expect(screen.getByText('Season progression: 2028 → 2030')).toBeInTheDocument()
  })
})
