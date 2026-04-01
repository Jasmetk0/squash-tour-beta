import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunDiagnosticsPage } from './RunDiagnosticsPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  getRunStatusSummary: vi.fn(),
  getFinalsSummary: vi.fn(),
  getLatestRollover: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

describe('RunDiagnosticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2028, seed: 11, next_event_index: 6, total_events: 24, completed_event_ids: ['E1', 'E2'] },
      season_state: { season: 2028, next_event_index: 6, completed_event_ids: ['E1', 'E2'], ordered_events: [] }
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: 'run-a',
      season: 2028,
      seed: 11,
      progress: { next_event_index: 6, total_events: 24, completed_event_count: 5 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    })
    api.getFinalsSummary.mockResolvedValue({ run_id: 'run-a', season: 2028, qualification: null, result: null })
    api.getLatestRollover.mockResolvedValue({
      rollover: { run_id: 'run-a', from_season: 2028, to_season: 2029, transitioned_players: 64, metadata: {} }
    })
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockResolvedValue({
      lineage: {
        run_id: 'run-a',
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: ['run-child-1']
      }
    })
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 5, event_id: 'E5', season: 2028, week: 12, template_id: null, tournament_result: { done: true } },
        { event_sequence: 4, event_id: 'E4', season: 2028, week: 11, template_id: null, tournament_result: null }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 17, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [{ snapshot_sequence: 14, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
  })

  it('renders diagnostics route content with compact summary', async () => {
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByRole('heading', { name: 'Run diagnostics' })).toBeInTheDocument()
    expect(screen.getByText('Run diagnostics summary')).toBeInTheDocument()
    expect(await screen.findByText('Run ID')).toBeInTheDocument()
    expect(screen.getByText('Run: run-a')).toBeInTheDocument()
    expect(screen.getAllByText('2028').length).toBeGreaterThan(0)
    expect(screen.getByText('6 / 24')).toBeInTheDocument()
    expect(screen.getAllByText('Ranking snapshots').length).toBeGreaterThan(0)
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('renders richer latest-activity summaries with direct detail links', async () => {
    api.listEvents.mockResolvedValueOnce({
      events: [{ event_sequence: 5, event_id: 'E5', season: 2028, week: 12, template_id: null, tournament_result: { done: true } }]
    })
    api.listRankingSnapshots.mockResolvedValueOnce({
      snapshots: [{ snapshot_sequence: 17, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({
      snapshots: [{ snapshot_sequence: 14, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-rich/diagnostics')

    expect(await screen.findByText('Latest completed event')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /E5 \(Seq 5\)/ })).toHaveAttribute('href', '/runs/run-rich/events/E5')
    expect(await screen.findByRole('link', { name: 'Seq 17' })).toHaveAttribute('href', '/runs/run-rich/snapshots/ranking/17')
    expect(await screen.findByRole('link', { name: 'Seq 14' })).toHaveAttribute('href', '/runs/run-rich/snapshots/race/14')
  })

  it('renders availability and artifact-state statuses', async () => {
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-availability/diagnostics')

    expect(await screen.findByText('Availability / artifact state')).toBeInTheDocument()
    expect(await screen.findByText('new_run')).toBeInTheDocument()
    expect(screen.getAllByText('Finals qualification').length).toBeGreaterThan(0)
    expect(screen.getAllByText('None yet').length).toBeGreaterThan(0)
    expect(screen.getByText('Latest rollover')).toBeInTheDocument()
    expect(screen.getAllByText('Available').length).toBeGreaterThan(0)
    expect(screen.getByText('Source metadata')).toBeInTheDocument()
    expect(screen.getByText('Lineage metadata')).toBeInTheDocument()
  })

  it('renders most relevant next inspection links from loaded data', async () => {
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'run-a',
      season: 2028,
      qualification: { qualified_players: [] },
      result: null
    })
    api.listEvents.mockResolvedValueOnce({
      events: [{ event_sequence: 5, event_id: 'E5', season: 2028, week: 12, template_id: null, tournament_result: { done: true } }]
    })
    api.listRankingSnapshots.mockResolvedValueOnce({
      snapshots: [{ snapshot_sequence: 17, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({
      snapshots: [{ snapshot_sequence: 14, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-links/diagnostics')

    expect(await screen.findByText('Most relevant next inspection links')).toBeInTheDocument()
    expect(await screen.findByText('new_run')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' })).toHaveAttribute(
      'href',
      '/runs/run-links/events/E5'
    )
    expect(screen.getByRole('link', { name: 'Inspect latest ranking snapshot (Seq 17)' })).toHaveAttribute(
      'href',
      '/runs/run-links/snapshots/ranking/17'
    )
    expect(screen.getByRole('link', { name: 'Inspect latest race snapshot (Seq 14)' })).toHaveAttribute(
      'href',
      '/runs/run-links/snapshots/race/14'
    )
    expect(
      screen.getByRole('link', { name: 'Inspect Finals status (qualification available, result pending)' })
    ).toHaveAttribute('href', '/runs/run-links/finals')
    expect(screen.getByRole('link', { name: 'Inspect latest rollover details' })).toHaveAttribute(
      'href',
      '/runs/run-links/rollover'
    )
    expect(screen.getByRole('link', { name: 'Inspect season chain (1 child run(s))' })).toHaveAttribute(
      'href',
      '/runs/run-links/season-chain'
    )
  })

  it('shows readable empty/not-found states for optional diagnostics sections', async () => {
    api.getLatestRollover.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunSource.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunLineage.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.listEvents.mockResolvedValueOnce({ events: [] })
    api.listRankingSnapshots.mockResolvedValueOnce({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValueOnce({ snapshots: [] })

    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByText('No rollover has been executed for this run yet.')).toBeInTheDocument()
    expect(await screen.findByText('No source metadata available.')).toBeInTheDocument()
    expect(await screen.findByText('No lineage metadata available.')).toBeInTheDocument()
    expect(await screen.findByText('No events are available yet.')).toBeInTheDocument()
    expect(await screen.findByText('No targeted inspection links yet. Use quick navigation below.')).toBeInTheDocument()
    expect(screen.getAllByText('Missing').length).toBeGreaterThan(1)
  })


  it('shows readable error state for ranking snapshots in latest snapshots summary', async () => {
    api.listRankingSnapshots.mockRejectedValueOnce(new Error('ranking unavailable'))

    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByText('Error: ranking unavailable')).toBeInTheDocument()
    expect(screen.getAllByText('Error').length).toBeGreaterThan(0)
  })

  it('shows readable error state for race snapshots in latest snapshots summary', async () => {
    api.listRaceSnapshots.mockRejectedValueOnce(new Error('race unavailable'))

    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByText('Error: race unavailable')).toBeInTheDocument()
  })

  it('keeps true empty states for latest snapshots when snapshot queries succeed with no data', async () => {
    api.listEvents.mockResolvedValueOnce({ events: [] })
    api.listRankingSnapshots.mockResolvedValueOnce({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValueOnce({ snapshots: [] })

    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByText('Latest ranking snapshot')).toBeInTheDocument()
    await screen.findByText('No events are available yet.')
    expect(screen.getAllByText('None yet').length).toBeGreaterThan(1)
    expect(screen.queryByText(/Error:/i)).not.toBeInTheDocument()
  })

  it('includes quick navigation links to run subpages', async () => {
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByRole('link', { name: 'Run Detail' })).toHaveAttribute('href', '/runs/run-a')
    expect(screen.getByRole('link', { name: 'Events' })).toHaveAttribute('href', '/runs/run-a/events')
    expect(screen.getByRole('link', { name: 'Activity' })).toHaveAttribute('href', '/runs/run-a/activity')
    expect(screen.getByRole('link', { name: 'World Tour Finals' })).toHaveAttribute('href', '/runs/run-a/finals')
    expect(screen.getByRole('link', { name: 'Season Rollover' })).toHaveAttribute('href', '/runs/run-a/rollover')
    expect(screen.getByRole('link', { name: 'Bootstrap / Lineage' })).toHaveAttribute(
      'href',
      '/runs/run-a/bootstrap-lineage'
    )
    expect(screen.getByRole('link', { name: 'Season Chain' })).toHaveAttribute('href', '/runs/run-a/season-chain')
    expect(screen.getByRole('link', { name: 'Ranking snapshots' })).toHaveAttribute('href', '/runs/run-a/snapshots/ranking')
    expect(screen.getByRole('link', { name: 'Race snapshots' })).toHaveAttribute('href', '/runs/run-a/snapshots/race')
  })
})
