import { fireEvent, screen, waitFor, within } from '@testing-library/react'
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
// Legacy assertions verify the existing English copy; CS/EN transitions have separate coverage.
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

const finalsQualification = (runId: string, season = 2028) => ({
  run_id: runId, season, source_as_of_season: season, source_as_of_week: 60,
  qualification: { qualified_players: [] }
})
const finalsResult = (runId: string, season = 2028) => ({
  run_id: runId, season, event_id: 'FINALS', source_as_of_season: season,
  source_as_of_week: 60, result: { champion_player_id: 'P1' }
})

describe('RunDiagnosticsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRun.mockImplementation(async (runId: string) => ({
      run: { run_id: runId, season: 2028, seed: 11, next_event_index: 6, total_events: 24, completed_event_ids: ['E1', 'E2'] },
      season_state: {
        season: 2028,
        next_event_index: 6,
        completed_event_ids: ['E1', 'E2'],
        ordered_events: [{ event_id: 'E1', season: 2028, week: 5, tour: 'WORLD', category: 'GOLD', template_id: 'TMP-1' }]
      }
    }))
    api.getRunStatusSummary.mockImplementation(async (runId: string) => ({
      run_id: runId,
      season: 2028,
      seed: 11,
      progress: { next_event_index: 6, total_events: 24, completed_event_count: 5 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    }))
    api.getFinalsSummary.mockImplementation(async (runId: string) => ({ run_id: runId, season: 2028, qualification: null, result: null }))
    api.getLatestRollover.mockImplementation(async (runId: string) => ({
      rollover: { run_id: runId, from_season: 2028, to_season: 2029, transitioned_players: 64, metadata: {} }
    }))
    api.getRunSource.mockResolvedValue({
      source: {
        source_type: 'new_run',
        parent_run_id: null,
        source_rollover_run_id: null,
        source_rollover_from_season: null,
        source_rollover_to_season: null
      }
    })
    api.getRunLineage.mockImplementation(async (runId: string) => ({
      lineage: {
        run_id: runId,
        source: {
          source_type: 'new_run',
          parent_run_id: null,
          source_rollover_run_id: null,
          source_rollover_from_season: null,
          source_rollover_to_season: null
        },
        children: ['run-child-1']
      }
    }))
    api.listEvents.mockImplementation(async (runId: string) => ({ run_id: runId,
      events: [
        { event_sequence: 5, event_id: 'E5', season: 2028, week: 12, template_id: null, tournament_result: { done: true } },
        { event_sequence: 4, event_id: 'E4', season: 2028, week: 11, template_id: null, tournament_result: null }
      ]
    }))
    api.listRankingSnapshots.mockImplementation(async (runId: string) => ({ run_id: runId,
      snapshots: [{ snapshot_sequence: 17, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    }))
    api.listRaceSnapshots.mockImplementation(async (runId: string) => ({ run_id: runId,
      snapshots: [{ snapshot_sequence: 14, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    }))
  })


  it('routes reused persisted event IDs to their sequence-selected timeline instead of ambiguous ID-only detail', async () => {
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: [
      { event_sequence: 8, event_id: 'REUSED', season: 2028, week: 13, template_id: null,
        tournament_result: { winner: 'P8' } },
      { event_sequence: 3, event_id: 'REUSED', season: 2027, week: 35, template_id: null,
        tournament_result: { winner: 'P3' } },
      { event_sequence: 2, event_id: 'UNIQUE', season: 2028, week: 4, template_id: null,
        tournament_result: { winner: 'P2' } }
    ] })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
    expect(await screen.findByText('Some event IDs are reused. Event links open their selected sequence in history.')).toBeInTheDocument()
    const targeted = '/runs/run-a/events?selectedEventId=REUSED&selectedEventSequence=8'
    expect(screen.getByRole('link', { name: 'Inspect latest completed event (REUSED)' }))
      .toHaveAttribute('href', targeted)
    const recent = screen.getByRole('list', { name: 'Diagnostics recent events' })
    expect(within(recent).getByRole('link', { name: /REUSED.*Seq 8/ }))
      .toHaveAttribute('href', targeted)
    expect(within(recent).getByRole('link', { name: /REUSED.*Seq 3/ }))
      .toHaveAttribute('href', '/runs/run-a/events?selectedEventId=REUSED&selectedEventSequence=3')
    expect(within(recent).getByRole('link', { name: /UNIQUE.*Seq 2/ }))
      .toHaveAttribute('href', '/runs/run-a/events/UNIQUE')
    expect(screen.getByRole('link', { name: 'Inspect latest ranking snapshot (Seq 17)' }))
      .toHaveAttribute('href', '/runs/run-a/snapshots/ranking/17')
  })

  it('encodes Run and parent Run IDs in all diagnostics navigation while retaining raw API identity', async () => {
    api.getRunSource.mockResolvedValueOnce({
      source: {
        source_type: 'rollover_bootstrap', parent_run_id: 'parent x/y',
        source_rollover_run_id: 'parent x/y', source_rollover_from_season: 2027, source_rollover_to_season: 2028,
      }
    })
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'run x/y', season: 2028, qualification: finalsQualification('run x/y'), result: null,
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run%20x%2Fy/diagnostics')
    expect(await screen.findByRole('link', { name: 'Run Detail' })).toHaveAttribute(
      'href', '/runs/run%20x%2Fy'
    )
    expect(screen.getByRole('link', { name: 'Open world generation diagnostics' })).toHaveAttribute(
      'href', '/runs/run%20x%2Fy/world-generation'
    )
    expect(await screen.findByRole('link', { name: 'parent x/y' })).toHaveAttribute(
      'href', '/runs/parent%20x%2Fy'
    )
    expect(await screen.findByRole('link', { name: 'Inspect Finals qualification detail (qualification available, result pending)' }))
      .toHaveAttribute('href', '/runs/run%20x%2Fy/finals/qualification')
    expect(api.getRun).toHaveBeenCalledWith('run x/y')
    expect(api.getRunSource).toHaveBeenCalledWith('run x/y')
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

  it('uses verified status-summary metrics when the Run detail endpoint is unavailable', async () => {
    api.getRun.mockRejectedValueOnce(new Error('Run detail offline'))
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByText('Failed to load run details: Run detail offline')).toBeInTheDocument()
    expect(screen.getByText('Run: run-a')).toBeInTheDocument()
    expect(screen.getByText('Run ID')).toBeInTheDocument()
    expect(screen.getByText('Seed')).toBeInTheDocument()
    expect(screen.getByText('11')).toBeInTheDocument()
    expect(screen.getByText('6 / 24')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
    expect(screen.getByText('Week Detail (current week unavailable)')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Inspect current week detail/ })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' }))
      .toHaveAttribute('href', '/runs/run-a/events/E5')
    expect(screen.queryByText(/Run details belong to another Run/)).not.toBeInTheDocument()
  })

  it('renders richer latest-activity summaries with direct detail links', async () => {
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-rich',
      events: [{ event_sequence: 5, event_id: 'E5', season: 2028, week: 12, template_id: null, tournament_result: { done: true } }]
    })
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run-rich',
      snapshots: [{ snapshot_sequence: 17, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'run-rich',
      snapshots: [{ snapshot_sequence: 14, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-rich/diagnostics')

    expect(await screen.findByText('Latest completed event')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: /E5 \(Seq 5\)/ })).toHaveAttribute('href', '/runs/run-rich/events/E5')
    expect(await screen.findByRole('link', { name: 'Seq 17' })).toHaveAttribute('href', '/runs/run-rich/snapshots/ranking/17')
    expect(await screen.findByRole('link', { name: 'Seq 14' })).toHaveAttribute('href', '/runs/run-rich/snapshots/race/14')
  })

  it.each(['ascending', 'unordered'] as const)(
    'uses the greatest persisted sequences for latest diagnostics when API lists are %s',
    async (order) => {
      const events = [
        { event_sequence: 1, event_id: 'E1', season: 2028, week: 1, template_id: null, tournament_result: { done: true } },
        { event_sequence: 2, event_id: 'E2', season: 2028, week: 3, template_id: null, tournament_result: { done: true } },
        { event_sequence: 8, event_id: 'E8', season: 2028, week: 14, template_id: null, tournament_result: { done: true } },
        { event_sequence: 9, event_id: 'E9', season: 2028, week: 15, template_id: null, tournament_result: null },
        { event_sequence: 10, event_id: 'E10', season: 2028, week: 16, template_id: null, tournament_result: null },
      ]
      const rankings = [
        { snapshot_sequence: 1, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'WEEK', source_event_id: 'E8', payload: {} },
        { snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} },
      ]
      const races = [
        { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E2', payload: {} },
        { snapshot_sequence: 16, snapshot_kind: 'WEEK', source_event_id: 'E8', payload: {} },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} },
      ]
      api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: order === 'ascending'
        ? events : [events[3], events[0], events[4], events[1], events[2]] })
      api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: order === 'ascending'
        ? [rankings[0], rankings[2], rankings[1]] : rankings })
      api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: order === 'ascending'
        ? [races[0], races[2], races[1]] : races })
      renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

      expect(await screen.findByRole('link', { name: 'E8 (Seq 8)' }))
        .toHaveAttribute('href', '/runs/run-a/events/E8')
      expect(screen.getByRole('link', { name: 'Seq 12' }))
        .toHaveAttribute('href', '/runs/run-a/snapshots/ranking/12')
      expect(screen.getByRole('link', { name: 'Seq 16' }))
        .toHaveAttribute('href', '/runs/run-a/snapshots/race/16')
      expect(screen.getByRole('link', { name: 'Inspect latest completed event (E8)' }))
        .toHaveAttribute('href', '/runs/run-a/events/E8')
      expect(screen.getByRole('link', { name: 'Inspect latest ranking snapshot (Seq 12)' }))
        .toHaveAttribute('href', '/runs/run-a/snapshots/ranking/12')
      expect(screen.getByRole('link', { name: 'Inspect latest race snapshot (Seq 16)' }))
        .toHaveAttribute('href', '/runs/run-a/snapshots/race/16')
      expect(screen.queryByRole('link', { name: 'Inspect latest completed event (E9)' }))
        .not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Inspect latest completed event (E2)' }))
        .not.toBeInTheDocument()
      const recentEvents = within(screen.getByRole('list', { name: 'Diagnostics recent events' }))
        .getAllByRole('link')
      expect(recentEvents.map(link => link.textContent)).toEqual([
        'E10 • Seq 10',
        'E9 • Seq 9',
        'E8 • Seq 8',
      ])
      expect(recentEvents.map(link => link.getAttribute('href'))).toEqual([
        '/runs/run-a/events/E10',
        '/runs/run-a/events/E9',
        '/runs/run-a/events/E8',
      ])
    },
  )

  it.each(['events', 'ranking', 'race'] as const)(
    'rejects %s history from another Run without exposing its inspection links',
    async (history) => {
      if (history === 'events') {
        api.listEvents.mockResolvedValueOnce({ run_id: 'another-run', events: [
          { event_sequence: 99, event_id: 'FOREIGN', season: 2030, week: 1,
            template_id: null, tournament_result: { done: true } }
        ] })
      }
      if (history === 'ranking') {
        api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'another-run', snapshots: [
          { snapshot_sequence: 99, snapshot_kind: 'WEEK', source_event_id: 'FOREIGN', payload: {} }
        ] })
      }
      if (history === 'race') {
        api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'another-run', snapshots: [
          { snapshot_sequence: 99, snapshot_kind: 'WEEK', source_event_id: 'FOREIGN', payload: {} }
        ] })
      }

      renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
      expect(await screen.findByRole('alert')).toHaveTextContent(
        'History response belongs to another Run. Unrelated artifacts and inspection links are hidden.',
      )
      expect(screen.queryByRole('link', { name: /FOREIGN/ })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /Seq 99/ })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /Inspect latest.*FOREIGN/ })).not.toBeInTheDocument()
      if (history === 'events') {
        expect(screen.getByText('Event history belongs to a different Run.')).toBeInTheDocument()
        expect(screen.queryByRole('list', { name: 'Diagnostics recent events' })).not.toBeInTheDocument()
        expect(screen.getByText('Run mismatch')).toBeInTheDocument()
        expect(screen.getByRole('link', { name: 'Inspect latest ranking snapshot (Seq 17)' }))
          .toHaveAttribute('href', '/runs/run-a/snapshots/ranking/17')
      } else {
        expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' }))
          .toHaveAttribute('href', '/runs/run-a/events/E5')
        expect(screen.getByText('Run mismatch')).toBeInTheDocument()
        const stillValidSnapshot = history === 'ranking' ? 'race' : 'ranking'
        expect(screen.getByRole('link', {
          name: `Inspect latest ${stillValidSnapshot} snapshot (Seq ${stillValidSnapshot === 'race' ? 14 : 17})`,
        })).toBeInTheDocument()
      }
    },
  )

  it.each(['run', 'status', 'both'] as const)(
    'does not mix wrong-Run %s summary into the current diagnostics',
    async (wrong) => {
      if (wrong === 'run' || wrong === 'both') {
        api.getRun.mockResolvedValueOnce({
          run: { run_id: 'FOREIGN_RUN', season: 2039, seed: 999, next_event_index: 0,
            total_events: 1, completed_event_ids: [] },
          season_state: { season: 2039, next_event_index: 0, completed_event_ids: [],
            ordered_events: [{ event_id: 'FOREIGN_WEEK', week: 99, season: 2039,
              tour: 'WORLD', category: 'GOLD', template_id: 'FOREIGN' }] }
        })
      }
      if (wrong === 'status' || wrong === 'both') {
        api.getRunStatusSummary.mockResolvedValueOnce({
          run_id: 'FOREIGN_RUN', season: 2039, seed: 999,
          progress: { next_event_index: 999, total_events: 999, completed_event_count: 999 },
          history_counts: { events: 999, ranking_snapshots: 999, race_snapshots: 999 },
          finals: { qualification_available: false, result_available: false },
          rollover: null, source: null, lineage: { child_run_count: 0 },
        })
      }
      renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
      await waitFor(() => expect(screen.getAllByRole('alert')).toHaveLength(wrong === 'both' ? 2 : 1))
      expect(screen.queryByText('FOREIGN_RUN')).not.toBeInTheDocument()
      expect(screen.queryByText('2039')).not.toBeInTheDocument()
      expect(screen.queryByText('999')).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /W99/ })).not.toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' }))
        .toHaveAttribute('href', '/runs/run-a/events/E5')
      if (wrong === 'run' || wrong === 'both') {
        expect(screen.getByText(/Run details belong to another Run/)).toBeInTheDocument()
        expect(screen.getByText('Week Detail (current week unavailable)')).toBeInTheDocument()
      } else {
        expect(screen.getByText('Run: run-a')).toBeInTheDocument()
      }
      if (wrong === 'status' || wrong === 'both') {
        expect(screen.getByText(/Status summary belongs to another Run/)).toBeInTheDocument()
        if (wrong === 'status') expect(screen.getByText('6/24')).toBeInTheDocument()
      }
    },
  )

  it.each(['finals', 'rollover', 'lineage'] as const)(
    'rejects %s from another Run without misrepresenting available artifacts',
    async (resource) => {
      if (resource === 'finals') {
        api.getFinalsSummary.mockResolvedValueOnce({
          run_id: 'FOREIGN_RUN', season: 2099,
          qualification: finalsQualification('FOREIGN_RUN', 2099), result: {
            ...finalsResult('FOREIGN_RUN', 2099), result: { champion_player_id: 'FOREIGN_CHAMPION' }
          }
        })
      }
      if (resource === 'rollover') {
        api.getLatestRollover.mockResolvedValueOnce({
          rollover: { run_id: 'FOREIGN_RUN', from_season: 2098, to_season: 2099,
            transitioned_players: 999, metadata: {} }
        })
      }
      if (resource === 'lineage') {
        api.getRunLineage.mockResolvedValueOnce({
          lineage: { run_id: 'FOREIGN_RUN',
            source: { source_type: 'new_run', parent_run_id: null,
              source_rollover_run_id: null, source_rollover_from_season: null, source_rollover_to_season: null },
            children: ['FOREIGN_CHILD'] }
        })
      }
      renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
      const warning = {
        finals: 'Finals summary contains mismatched Run or season data. Its status and inspection links are hidden.',
        rollover: 'Rollover summary belongs to another Run. Its result and inspection link are hidden.',
        lineage: 'Lineage belongs to another Run. Child count and season-chain inspection link are hidden.',
      }[resource]
      expect(await screen.findByRole('alert')).toHaveTextContent(warning)
      expect(screen.queryByText('2099')).not.toBeInTheDocument()
      expect(screen.queryByText('999')).not.toBeInTheDocument()
      expect(screen.queryByText('FOREIGN_CHILD')).not.toBeInTheDocument()
      expect(screen.queryByText('FOREIGN_CHAMPION')).not.toBeInTheDocument()

      if (resource === 'finals') {
        expect(screen.queryByRole('link', { name: /Inspect Finals (result|qualification)/ })).not.toBeInTheDocument()
        expect(screen.getByRole('link', { name: 'Inspect latest rollover details' })).toBeInTheDocument()
      }
      if (resource === 'rollover') {
        expect(screen.queryByRole('link', { name: 'Inspect latest rollover details' })).not.toBeInTheDocument()
        expect(screen.queryByText('Transitioned players')).not.toBeInTheDocument()
        expect(screen.getByRole('link', { name: /Inspect season chain/ })).toBeInTheDocument()
      }
      if (resource === 'lineage') {
        expect(screen.queryByRole('link', { name: /Inspect season chain/ })).not.toBeInTheDocument()
        expect(screen.getByText('Child run count')).toBeInTheDocument()
        expect(screen.getByRole('link', { name: 'Inspect latest rollover details' })).toBeInTheDocument()
      }
      expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' }))
        .toHaveAttribute('href', '/runs/run-a/events/E5')
    },
  )

  it.each([
    { issue: 'foreign qualification Run', qualification: finalsQualification('another-run'), result: null },
    { issue: 'wrong qualification season', qualification: finalsQualification('run-a', 2029), result: null },
    { issue: 'foreign result Run', qualification: finalsQualification('run-a'), result: finalsResult('another-run') },
    { issue: 'wrong result season', qualification: finalsQualification('run-a'), result: finalsResult('run-a', 2029) },
  ])('rejects nested Finals identity: $issue', async ({qualification, result}) => {
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'run-a', season: 2028, qualification, result
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Finals summary contains mismatched Run or season data. Its status and inspection links are hidden.'
    )
    expect(screen.queryByRole('link', {name: /Inspect Finals (result|qualification)/}))
      .not.toBeInTheDocument()
    expect(screen.getByRole('link', {name: 'Inspect latest completed event (E5)'}))
      .toHaveAttribute('href', '/runs/run-a/events/E5')
    expect(screen.getByRole('link', {name: 'Inspect latest rollover details'}))
      .toHaveAttribute('href', '/runs/run-a/rollover')
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
    api.getRunStatusSummary.mockResolvedValueOnce({
      run_id: 'run-links', season: 2028, seed: 11,
      progress: { next_event_index: 1, total_events: 24, completed_event_count: 5 },
      finals: { qualification_available: false, result_available: false },
      rollover: null, source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    })

    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'run-links',
      season: 2028,
      qualification: finalsQualification('run-links'),
      result: null
    })
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-links',
      events: [{ event_sequence: 5, event_id: 'E5', season: 2028, week: 12, template_id: null, tournament_result: { done: true } }]
    })
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run-links',
      snapshots: [{ snapshot_sequence: 17, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'run-links',
      snapshots: [{ snapshot_sequence: 14, snapshot_kind: 'WEEK', source_event_id: 'E5', payload: {} }]
    })
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-links', season: 2028, seed: 11, next_event_index: 1, total_events: 24, completed_event_ids: ['E1'] },
      season_state: {
        season: 2028,
        next_event_index: 1,
        completed_event_ids: ['E1'],
        ordered_events: [
          { event_id: 'E1', season: 2028, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'TMP-1' },
          { event_id: 'E2', season: 2028, week: 11, tour: 'WORLD', category: 'GOLD', template_id: 'TMP-2' }
        ]
      }
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
    expect(screen.getByRole('link', { name: 'Inspect current week detail (W11 from E2)' })).toHaveAttribute(
      'href',
      '/runs/run-links/weeks/11'
    )
    expect(
      screen.getByRole('link', { name: 'Inspect Finals qualification detail (qualification available, result pending)' })
    ).toHaveAttribute('href', '/runs/run-links/finals/qualification')
    expect(screen.getByRole('link', { name: 'Inspect latest rollover details' })).toHaveAttribute(
      'href',
      '/runs/run-links/rollover'
    )
    expect(screen.getByRole('link', { name: 'Inspect season chain (1 child run(s))' })).toHaveAttribute(
      'href',
      '/runs/run-links/season-chain'
    )
  })

  it('uses finals result detail in diagnostics when finals result exists', async () => {
    api.getFinalsSummary.mockResolvedValueOnce({
      run_id: 'run-links',
      season: 2028,
      qualification: finalsQualification('run-links'),
      result: finalsResult('run-links')
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-links/diagnostics')

    expect(await screen.findByRole('link', { name: 'Inspect Finals result detail (result available)' })).toHaveAttribute(
      'href',
      '/runs/run-links/finals/result'
    )
  })

  it('shows readable empty/not-found states for optional diagnostics sections', async () => {
    api.getLatestRollover.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunSource.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.getRunLineage.mockRejectedValueOnce({ status: 404, message: 'not found' })
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: [] })
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: [] })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: [] })

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
    api.listEvents.mockResolvedValueOnce({ run_id: 'run-a', events: [] })
    api.listRankingSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: [] })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'run-a', snapshots: [] })

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
    expect(screen.getByRole('link', { name: 'Season Calendar' })).toHaveAttribute('href', '/runs/run-a/calendar')
    expect(screen.getByText('Week Detail (current week unavailable)')).toBeInTheDocument()
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

  it.each([
    { issue: 'season', statusSeason: 2029, statusIndex: 0, statusTotal: 24 },
    { issue: 'next-event cursor', statusSeason: 2028, statusIndex: 1, statusTotal: 24 },
    { issue: 'total-event count', statusSeason: 2028, statusIndex: 0, statusTotal: 25 },
  ])('hides current-week navigation when Run detail and status summary disagree on $issue',
    async ({statusSeason, statusIndex, statusTotal}) => {
      api.getRun.mockResolvedValueOnce({
        run: { run_id: 'run-a', season: 2028, seed: 11, next_event_index: 0,
          total_events: 24, completed_event_ids: [] },
        season_state: { season: 2028, next_event_index: 0, completed_event_ids: [],
          ordered_events: [{ event_id: 'NEXT', season: 2028, week: 8,
            tour: 'WORLD', category: 'GOLD', template_id: 'TMP-1' }] }
      })
      api.getRunStatusSummary.mockResolvedValueOnce({
        run_id: 'run-a', season: statusSeason, seed: 11,
        progress: { next_event_index: statusIndex, total_events: statusTotal, completed_event_count: 5 },
        finals: { qualification_available: false, result_available: false },
        rollover: null, source: { source_type: 'new_run', parent_run_id: null },
        lineage: { child_run_count: 1 },
        history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
      })
      renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'Run detail and status summary disagree on season or progress. Current-week links are hidden.'
      )
      expect(screen.getByText('Conflicting progress values are hidden until the run reads agree.')).toBeInTheDocument()
      // Both summary surfaces must remain explicitly unverified, not a mix of reads.
      const context = screen.getByRole('list', { name: 'Current context' })
      expect(within(context).getAllByText('—')).toHaveLength(3)
      const summary = screen.getByRole('heading', { name: 'Run diagnostics summary' }).closest('article')
      expect(summary).not.toBeNull()
      expect(Array.from(summary!.querySelectorAll('.compact-summary-card__value')).map((node) => node.textContent))
        .toEqual(['run-a', '—', '—', '—', '—'])
      // Neither independently sampled value may masquerade as verified progress.
      expect(screen.queryByText(`${statusIndex}/${statusTotal}`)).not.toBeInTheDocument()
      expect(screen.queryByText(`${statusIndex} / ${statusTotal}`)).not.toBeInTheDocument()
      expect(screen.getByText('Week Detail (current week unavailable)')).toBeInTheDocument()
      expect(screen.queryByRole('link', { name: 'Week Detail (current week)' })).not.toBeInTheDocument()
      expect(screen.queryByRole('link', { name: /Inspect current week detail/ })).not.toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' }))
        .toHaveAttribute('href', '/runs/run-a/events/E5')
    },
  )

  it.each([
    { caseName: 'season state from a different season', runIndex: 0, stateIndex: 0, stateSeason: 2029, eventSeason: 2029 },
    { caseName: 'stale next-event index', runIndex: 1, stateIndex: 0, stateSeason: 2028, eventSeason: 2028 },
    { caseName: 'planned event from another season', runIndex: 0, stateIndex: 0, stateSeason: 2028, eventSeason: 2029 }
  ])('hides current-week links for $caseName', async ({runIndex, stateIndex, stateSeason, eventSeason}) => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2028, seed: 11, next_event_index: runIndex,
        total_events: 24, completed_event_ids: [] },
      season_state: {
        season: stateSeason, next_event_index: stateIndex, completed_event_ids: [],
        ordered_events: [{event_id: 'STALE_EVENT', season: eventSeason, week: 99,
          tour: 'WORLD', category: 'GOLD', template_id: 'STALE'}]
      }
    })
    api.getRunStatusSummary.mockResolvedValueOnce({
      run_id: 'run-a', season: 2028, seed: 11,
      progress: { next_event_index: runIndex, total_events: 24, completed_event_count: 5 },
      finals: { qualification_available: false, result_available: false },
      rollover: null, source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    })

    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Run calendar and progress disagree. Current-week links are hidden.'
    )
    expect(screen.getByText('Week Detail (current week unavailable)')).toBeInTheDocument()
    expect(screen.queryByRole('link', {name: /Inspect current week detail/})).not.toBeInTheDocument()
    expect(screen.queryByRole('link', {name: 'Week Detail (current week)'})).not.toBeInTheDocument()
    expect(screen.queryByText(/STALE_EVENT/)).not.toBeInTheDocument()
    expect(screen.getByText('Conflicting progress values are hidden until the run reads agree.')).toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Run diagnostics summary' }).closest('article')!
    expect(within(summary).getAllByText('—').length).toBeGreaterThan(1)
    expect(screen.getByRole('link', {name: 'Inspect latest completed event (E5)'}))
      .toHaveAttribute('href', '/runs/run-a/events/E5')
  })

  it.each([
    { caseName: 'lost completed event', stateIds: ['E1'] },
    { caseName: 'substituted completed event', stateIds: ['E1', 'OTHER'] },
    { caseName: 'duplicate hiding another completed event', stateIds: ['E1', 'E1'] }
  ])('rejects independently read SeasonState with $caseName without hiding trusted history', async ({ stateIds }) => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2028, seed: 11, next_event_index: 2,
        total_events: 3, completed_event_ids: ['E1', 'E2'] },
      season_state: {
        season: 2028, next_event_index: 2, completed_event_ids: stateIds,
        ordered_events: [
          { event_id: 'E1', season: 2028, week: 3, tour: 'WORLD', category: 'GOLD', template_id: 'T1' },
          { event_id: 'E2', season: 2028, week: 4, tour: 'WORLD', category: 'GOLD', template_id: 'T2' },
          { event_id: 'E3', season: 2028, week: 8, tour: 'WORLD', category: 'GOLD', template_id: 'T3' }
        ]
      }
    })
    api.getRunStatusSummary.mockResolvedValueOnce({
      run_id: 'run-a', season: 2028, seed: 11,
      progress: { next_event_index: 2, total_events: 3, completed_event_count: 2 },
      finals: { qualification_available: false, result_available: false },
      rollover: null, source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
    expect(await screen.findByRole('alert')).toHaveTextContent('Run calendar and progress disagree. Current-week links are hidden.')
    expect(screen.getByText('Conflicting progress values are hidden until the run reads agree.')).toBeInTheDocument()
    expect(within(screen.getByRole('list', { name: 'Current context' })).getAllByText('—')).toHaveLength(3)
    expect(screen.getByText('Week Detail (current week unavailable)')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Inspect current week detail/ })).not.toBeInTheDocument()
    const summary = screen.getByRole('heading', { name: 'Run diagnostics summary' }).closest('article')!
    expect(Array.from(summary.querySelectorAll('.compact-summary-card__value')).map((node) => node.textContent))
      .toEqual(['run-a', '—', '—', '—', '—'])
    expect(screen.getByRole('link', { name: 'Inspect latest completed event (E5)' }))
      .toHaveAttribute('href', '/runs/run-a/events/E5')
  })

  it('accepts equivalent completed-event ID sets in different order', async () => {
    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2028, seed: 11, next_event_index: 2,
        total_events: 3, completed_event_ids: ['E2', 'E1'] },
      season_state: {
        season: 2028, next_event_index: 2, completed_event_ids: ['E1', 'E2'],
        ordered_events: [
          { event_id: 'E1', season: 2028, week: 3, tour: 'WORLD', category: 'GOLD', template_id: 'T1' },
          { event_id: 'E2', season: 2028, week: 4, tour: 'WORLD', category: 'GOLD', template_id: 'T2' },
          { event_id: 'E3', season: 2028, week: 8, tour: 'WORLD', category: 'GOLD', template_id: 'T3' }
        ]
      }
    })
    api.getRunStatusSummary.mockResolvedValueOnce({
      run_id: 'run-a', season: 2028, seed: 11,
      progress: { next_event_index: 2, total_events: 3, completed_event_count: 2 },
      finals: { qualification_available: false, result_available: false },
      rollover: null, source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    })
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
    expect(await screen.findByRole('link', { name: 'Inspect current week detail (W8 from E3)' }))
      .toHaveAttribute('href', '/runs/run-a/weeks/8')
    expect(screen.queryByText('Conflicting progress values are hidden until the run reads agree.')).not.toBeInTheDocument()
    expect(screen.getByText('2/3')).toBeInTheDocument()
  })

  it('includes a targeted week detail quick-navigation link when next planned week is available', async () => {
    api.getRunStatusSummary.mockResolvedValueOnce({
      run_id: 'run-a', season: 2028, seed: 11,
      progress: { next_event_index: 0, total_events: 24, completed_event_count: 5 },
      finals: { qualification_available: false, result_available: false },
      rollover: null, source: { source_type: 'new_run', parent_run_id: null },
      lineage: { child_run_count: 1 },
      history_counts: { events: 5, ranking_snapshots: 7, race_snapshots: 6 }
    })

    api.getRun.mockResolvedValueOnce({
      run: { run_id: 'run-a', season: 2028, seed: 11, next_event_index: 0, total_events: 24, completed_event_ids: [] },
      season_state: {
        season: 2028,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [{ event_id: 'E9', season: 2028, week: 8, tour: 'WORLD', category: 'GOLD', template_id: 'TMP-9' }]
      }
    })

    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')

    expect(await screen.findByRole('link', { name: 'Week Detail (current week)' })).toHaveAttribute(
      'href',
      '/runs/run-a/weeks/8'
    )
  })
  it('drops a cached latest event after its independent refresh fails and restores it on recovery', async () => {
    const history = { run_id: 'run-a', events: [
      { event_sequence: 5, event_id: 'E5', season: 2028, week: 12,
        template_id: null, tournament_result: { done: true } }
    ] }
    api.listEvents.mockResolvedValueOnce(history)
      .mockRejectedValueOnce(new Error('temporary event outage'))
      .mockResolvedValueOnce(history)
    renderWithRoute(<RunDiagnosticsPage />, '/runs/run-a/diagnostics')
    expect(await screen.findByRole('link', { name: 'Inspect latest completed event (E5)' }))
      .toHaveAttribute('href', '/runs/run-a/events/E5')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh read-only data' }))
    expect(await screen.findByText('Failed to load events: temporary event outage')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Inspect latest completed event (E5)' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Inspect latest ranking snapshot (Seq 17)' }))
      .toHaveAttribute('href', '/runs/run-a/snapshots/ranking/17')
    fireEvent.click(screen.getByRole('button', { name: 'Refresh read-only data' }))
    expect(await screen.findByRole('link', { name: 'Inspect latest completed event (E5)' }))
      .toHaveAttribute('href', '/runs/run-a/events/E5')
    expect(api.listEvents).toHaveBeenCalledTimes(3)
  })

})
