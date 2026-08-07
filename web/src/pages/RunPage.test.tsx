import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPage } from './RunPage'
import { renderWithRoute } from '../test/testUtils'
import { faxReferenceRunContainer, FAX_REFERENCE_BRANCH_ID, FAX_REFERENCE_LEGACY_RUN_ID } from '../test/faxReferenceFixture'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  getRun: vi.fn(),
  getRunContainer: vi.fn(),
  getRunStatusSummary: vi.fn(),
  getFinalsSummary: vi.fn(),
  getLatestRollover: vi.fn(),
  getRunSource: vi.fn(),
  getRunLineage: vi.fn(),
  getRunWorldStatus: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn(),
  simulateWorldTourFinals: vi.fn(),
  rolloverNextSeason: vi.fn(),
  rebuildRunWorld: vi.fn(),
  simulateNextMatch: vi.fn(),
  simulateNextRound: vi.fn(),
  simulateNextTournament: vi.fn(),
  simulateNextWeek: vi.fn(),
  simulateFullSeason: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('RunPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: FAX_REFERENCE_LEGACY_RUN_ID, season: 2025, seed: 3, next_event_index: 1, total_events: 4, completed_event_ids: ['E1'] },
      season_state: {
        season: 2025,
        next_event_index: 1,
        completed_event_ids: ['E1'],
        ordered_events: [
          { event_id: 'E1', season: 2025, week: 9, tour: 'WORLD', category: 'PLATINUM', template_id: 'TEMP-1' },
          { event_id: 'E2', season: 2025, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-2' },
          { event_id: 'E3', season: 2025, week: 11, tour: 'WORLD', category: 'SILVER', template_id: 'TEMP-3' }
        ]
      }
    })
    api.getRunContainer.mockResolvedValue({
      ...faxReferenceRunContainer,
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      official_branch_id: FAX_REFERENCE_BRANCH_ID,
    })
    api.getRunStatusSummary.mockResolvedValue({
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      season: 2025,
      seed: 3,
      progress: { next_event_index: 1, total_events: 4, completed_event_count: 1 },
      finals: { qualification_available: true, result_available: false },
      rollover: { latest_to_season: 2026, transitioned_players: 128 },
      source: { source_type: 'bootstrap', parent_run_id: 'run-parent' },
      lineage: { child_run_count: 2 },
      history_counts: { events: 3, ranking_snapshots: 3, race_snapshots: 3 }
    })
    api.getFinalsSummary.mockResolvedValue({
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      season: 2025,
      qualification: { run_id: FAX_REFERENCE_LEGACY_RUN_ID, season: 2025, source_as_of_season: 2025, source_as_of_week: 40, qualification: {} },
      result: null
    })
    api.getLatestRollover.mockResolvedValue({
      rollover: { run_id: FAX_REFERENCE_LEGACY_RUN_ID, from_season: 2025, to_season: 2026, transitioned_players: 128, metadata: {} }
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
        run_id: FAX_REFERENCE_LEGACY_RUN_ID,
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
    api.getRunWorldStatus.mockResolvedValue({
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      world_id: 'official_fax_world',
      source_type: 'fresh_seed',
      stored_world_generation_fingerprint: 'fp-a',
      current_world_generation_fingerprint: 'fp-a',
      is_stale: false,
      rebuild_supported: true,
      message: 'Run world inputs are fresh; rebuild is available for this pristine fresh-seed run.'
    })
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 3, event_id: 'E3', season: 2025, week: 11, template_id: null, tournament_result: null },
        { event_sequence: 1, event_id: 'E1', season: 2025, week: 9, template_id: null, tournament_result: null },
        { event_sequence: 2, event_id: 'E2', season: 2025, week: 10, template_id: null, tournament_result: null },
        { event_sequence: 4, event_id: 'E4', season: 2025, week: 12, template_id: null, tournament_result: null }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 10, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'TOURNAMENT', source_event_id: null, payload: {} },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 11, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E3', payload: {} },
        { snapshot_sequence: 5, snapshot_kind: 'TOURNAMENT', source_event_id: null, payload: {} },
        { snapshot_sequence: 6, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: 'E4', payload: {} }
      ]
    })
    api.simulateWorldTourFinals.mockResolvedValue({
      finals: {
        run_id: FAX_REFERENCE_LEGACY_RUN_ID,
        season: 2025,
        event_id: 'WTF-2025',
        already_simulated: false,
        result: { champion_id: 'p-1' }
      }
    })
    api.rolloverNextSeason.mockResolvedValue({
      rollover: {
        run_id: FAX_REFERENCE_LEGACY_RUN_ID,
        from_season: 2025,
        to_season: 2026,
        transitioned_players: 128,
        metadata: {},
        already_persisted: false
      }
    })
    api.rebuildRunWorld.mockResolvedValue({
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      world_id: 'official_fax_world',
      source_type: 'fresh_seed',
      stored_world_generation_fingerprint: 'fp-a',
      current_world_generation_fingerprint: 'fp-a',
      is_stale: false,
      rebuild_supported: true,
      message: 'Run rebuilt.'
    })
    api.simulateNextMatch.mockResolvedValue({ step: { mode: 'simulate_next_match' } })
    api.simulateNextRound.mockResolvedValue({ step: { mode: 'simulate_next_round' } })
    api.simulateNextTournament.mockResolvedValue({ step: { mode: 'simulate_next_tournament' } })
    api.simulateNextWeek.mockResolvedValue({ step: { mode: 'simulate_next_week' } })
    api.simulateFullSeason.mockResolvedValue({ step: { mode: 'simulate_full_season' } })
  })

  it('renders the run-scoped Admin Home identity and live progress', async () => {
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByRole('heading', { name: 'Home' })).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'E2 · W10' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_LEGACY_RUN_ID}/calendar/E2`)
    expect(screen.getByText(`Run: ${FAX_REFERENCE_LEGACY_RUN_ID}`)).toBeInTheDocument()
    const context = screen.getByRole('list', { name: 'Current context' })
    expect(within(context).getByText('W10')).toBeInTheDocument()
    expect(within(context).getByText('1/4')).toBeInTheDocument()
  })

  it('renders real branch, world, activity, and admin navigation context', async () => {
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByText('official_fax_world')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'run-parent' })).toHaveAttribute('href', '/admin/runs/run-parent')
    expect(screen.getByText('Viewer Branch')).toBeInTheDocument()
    expect(screen.queryByText('Official branch')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Manage branches and Viewer Branch' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_LEGACY_RUN_ID}/branches`)
    expect(screen.getByText(FAX_REFERENCE_BRANCH_ID)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'E3' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_LEGACY_RUN_ID}/events/E3`)
    expect(screen.getByRole('link', { name: 'Open Simulate' })).toHaveAttribute('href', '/admin/simulate')
    expect(screen.getByRole('link', { name: 'Diagnostics' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_LEGACY_RUN_ID}/diagnostics`)
  })

  it('shows no attention warning when loaded run signals are healthy', async () => {
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByText('No warnings require attention.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Simulate next tournament' })).not.toBeInTheDocument()
  })

  it('surfaces a stale-world warning and preserves the rebuild command', async () => {
    api.getRunWorldStatus.mockResolvedValueOnce({ run_id: FAX_REFERENCE_LEGACY_RUN_ID, world_id: 'official_fax_world', source_type: 'fresh_seed', stored_world_generation_fingerprint: 'old', current_world_generation_fingerprint: 'new', is_stale: true, rebuild_supported: true, message: 'World inputs changed.' })
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByText(/World inputs are stale/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Rebuild Run from Current World Data' }))
    await waitFor(() => expect(api.rebuildRunWorld).toHaveBeenCalledWith(FAX_REFERENCE_LEGACY_RUN_ID))
    expect(await screen.findByText('Run world rebuilt.')).toBeInTheDocument()
  })

  it('routes pending Finals to their dedicated workflow without executing them from Home', async () => {
    const runResponse = await api.getRun()
    const statusResponse = await api.getRunStatusSummary()
    api.getRunStatusSummary.mockResolvedValueOnce({ ...statusResponse, progress: { next_event_index: 4, total_events: 4, completed_event_count: 4 } })
    api.getRun.mockResolvedValueOnce({ ...runResponse, run: { ...runResponse.run, next_event_index: 4, completed_event_ids: ['E1', 'E2', 'E3', 'E4'] }, season_state: { ...runResponse.season_state, next_event_index: 4 } })
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByText(/World Tour Finals result is pending/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Review World Tour Finals' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_LEGACY_RUN_ID}/finals`)
    expect(screen.queryByRole('button', { name: 'Simulate World Tour Finals' })).not.toBeInTheDocument()
    expect(api.simulateWorldTourFinals).not.toHaveBeenCalled()
  })

  it('routes an available rollover to its dedicated workflow without executing it from Home', async () => {
    const runResponse = await api.getRun()
    const statusResponse = await api.getRunStatusSummary()
    api.getRunStatusSummary.mockResolvedValueOnce({ ...statusResponse, progress: { next_event_index: 4, total_events: 4, completed_event_count: 4 } })
    api.getRun.mockResolvedValueOnce({ ...runResponse, run: { ...runResponse.run, next_event_index: 4, completed_event_ids: ['E1', 'E2', 'E3', 'E4'] }, season_state: { ...runResponse.season_state, next_event_index: 4 } })
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: FAX_REFERENCE_LEGACY_RUN_ID,
      season: 2025,
      qualification: { run_id: FAX_REFERENCE_LEGACY_RUN_ID, season: 2025, source_as_of_season: 2025, source_as_of_week: 40, qualification: {} },
      result: { champion_id: 'p-1' }
    })
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByRole('link', { name: 'Continue to season rollover' })).toHaveAttribute('href', `/admin/runs/${FAX_REFERENCE_LEGACY_RUN_ID}/rollover`)
    expect(screen.queryByRole('button', { name: 'Roll over to next season' })).not.toBeInTheDocument()
    expect(api.rolloverNextSeason).not.toHaveBeenCalled()
  })

  it('summarizes overview request failures as admin attention', async () => {
    api.getRunWorldStatus.mockRejectedValueOnce(new Error('world unavailable'))
    renderWithRoute(<RunPage />, `/runs/${FAX_REFERENCE_LEGACY_RUN_ID}`)
    expect(await screen.findByText('1 run overview request(s) failed. Refresh or inspect diagnostics.')).toBeInTheDocument()
  })
})
