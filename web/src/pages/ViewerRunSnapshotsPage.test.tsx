import { cleanup, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunSnapshotDetailPage } from './ViewerRunSnapshotsPage'

const api = vi.hoisted(() => ({
  getRaceSnapshot: vi.fn(),
  listRaceSnapshots: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

afterEach(() => cleanup())

function renderRaceRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/race/:snapshotSequence" element={<ViewerRunSnapshotDetailPage />} />
    </Routes>,
    { route }
  )
}

function mockCanonicalSourceContext(runId = 'viewer-run-1', sourceEventId = 'EVENT-1'): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: runId,
    viewer_branch_id: 'branch-viewer',
    season_count: 1,
    event_count: 2,
    seasons: [{
      season: '2027/28',
      event_count: 2,
      events: [
        {
          event_id: sourceEventId,
          season: '2027/28',
          season_week: 3,
          calendar_year: 2027,
          year_week: 40,
          template_id: 'WT-PLAT',
          event_name: 'Source Open',
          category: 'Platinum',
          tour_level: 'WORLD_TOUR',
          host_country: 'EGY',
          host_city: 'Cairo',
          region: 'Africa',
          duration_in_season_weeks: 1,
          start_season_week: 3,
          end_season_week: 3,
          status: 'completed',
          main_draw_size: 32,
          qualification_draw_size: 16,
          seeds_count: 8,
          qualifier_spots: 4,
          wild_cards: 2,
          byes: 0,
          prestige: 90
        },
        {
          event_id: 'EVENT-2',
          season: '2027/28',
          season_week: 4,
          calendar_year: 2027,
          year_week: 41,
          template_id: 'ET-GOLD',
          event_name: 'Second Open',
          category: 'Gold',
          tour_level: 'ELITE_TOUR',
          host_country: 'ENG',
          host_city: 'London',
          region: 'Europe',
          duration_in_season_weeks: 1,
          start_season_week: 4,
          end_season_week: 4,
          status: 'planned',
          main_draw_size: 32,
          qualification_draw_size: 16,
          seeds_count: 8,
          qualifier_spots: 4,
          wild_cards: 2,
          byes: 0,
          prestige: 80
        }
      ]
    }]
  })
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: runId,
    viewer_branch_id: 'branch-viewer',
    tournament_count: 1,
    published_result_count: 1,
    tournaments: [{
      event_id: sourceEventId,
      season: '2027/28',
      season_week: 3,
      event_name: 'Source Open',
      template_id: 'WT-PLAT',
      category: 'Platinum',
      tour_level: 'WORLD_TOUR',
      host_country: 'EGY',
      host_city: 'Cairo',
      region: 'Africa',
      main_draw_size: 32,
      qualification_draw_size: 16,
      seeds_count: 8,
      qualifier_spots: 4,
      wild_cards: 2,
      byes: 0,
      ranking_status: 'published',
      result_published: true,
      champion_player_id: 'P1',
      finalist_player_id: 'P2'
    }]
  })
}

function raceRows(count: number): Array<Record<string, unknown>> {
  return Array.from({ length: count }, (_, index) => ({
    position: index + 1,
    player_id: `R${index + 1}`,
    player_name: index === 0 ? 'Mostafa Asal' : `Race Player ${index + 1}`,
    country: index === 0 ? 'EGY' : 'NZL',
    race_points: 9000 - index,
    tournaments_counted: index === 0 ? 8 : 6,
    qualification_status: index === 0 ? 'Qualified' : 'Chasing',
    next_max_points_possible: index === 0 ? 1200 : 900
  }))
}

function expectNoForbiddenViewerActions(): void {
  for (const label of [
    'Simulate', 'Generate', 'Persist', 'Apply', 'Execute', 'Delete', 'Edit', 'Import',
    'Rollover', 'Rebuild', 'Override', 'Save changes', 'Commit', 'Regenerate', 'Repair',
    'Merge', 'Overwrite'
  ]) {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  }
}

function expectNoAdminLinks(): void {
  screen.queryAllByRole('link').forEach((link) => {
    expect(link.getAttribute('href') ?? '').not.toMatch(/^\/admin/)
  })
}

describe('ViewerRunSnapshotDetailPage Race compatibility', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCanonicalSourceContext()
  })

  it('keeps invalid detail sequence strings local without API calls', async () => {
    renderRaceRoute('/viewer/runs/viewer-run-1/race/not-a-sequence')

    expect(await screen.findByRole('heading', { name: 'Race to Finals' })).toBeInTheDocument()
    expect(screen.getByText(/Snapshot sequence "not-a-sequence" is invalid/i)).toBeInTheDocument()
    expect(api.getRaceSnapshot).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders missing Race snapshots as a safe no-data state', async () => {
    api.getRaceSnapshot.mockRejectedValue(new api.ApiError('missing publication', 404))
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/404')

    expect(await screen.findByText(/Snapshot sequence 404 was not found for this run/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Read-only data' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders Race detail API errors without inferring sporting rows', async () => {
    api.getRaceSnapshot.mockRejectedValue(new Error('detail outage'))
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-1', snapshots: [] })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByText(/Failed to load publication: detail outage/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Payload summary' })).not.toBeInTheDocument()
    expect(screen.queryByText(/Mostafa Asal/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('normalizes unsafe neighboring snapshots before previous/next links', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { safe: true }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [
        null,
        { snapshot_sequence: 11, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-0', payload: {} },
        { snapshot_sequence: { bad: true }, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', payload: {} },
        { snapshot_sequence: 12, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} },
        { snapshot_sequence: -99, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', payload: {} },
        { snapshot_sequence: 13, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-2', payload: {} }
      ]
    })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/12')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '#11' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race/11'
    )
    expect(screen.getByRole('link', { name: '#13' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race/13'
    )
    expect(screen.queryByRole('link', { name: /#-99/i })).not.toBeInTheDocument()
  })

  it('keeps missing source context fail-soft without inventing links', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 12,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: { context: 'missing' }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 12, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })
    api.getViewerRunCalendar.mockRejectedValue(new Error('calendar outage'))
    api.getViewerTournamentHistory.mockRejectedValue(new Error('history outage'))
    renderRaceRoute('/viewer/runs/viewer-run-1/race/12')

    expect(await screen.findByRole('heading', { name: 'Source links' })).toBeInTheDocument()
    expect(screen.getByText('Source event detail unavailable.')).toBeInTheDocument()
    expect(screen.getByText('No Saved Calendar match for source event.')).toBeInTheDocument()
    expect(screen.getByText('No canonical week context available.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Open source event|Open planned event|Open week/i })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps parseable Race payloads on conservative detail summary and technical disclosure collapsed', async () => {
    api.getRaceSnapshot.mockResolvedValue({
      snapshot_sequence: 5,
      snapshot_kind: 'RACE_WEEKLY_PUBLICATION',
      source_event_id: 'EVENT-1',
      payload: {
        race_to_finals: { rows: raceRows(11) },
        secret_debug_marker: 'race-detail-hidden-payload'
      }
    })
    api.listRaceSnapshots.mockResolvedValue({
      run_id: 'viewer-run-1',
      snapshots: [{ snapshot_sequence: 5, snapshot_kind: 'RACE_WEEKLY_PUBLICATION', source_event_id: 'EVENT-1', payload: {} }]
    })
    renderRaceRoute('/viewer/runs/viewer-run-1/race/5')

    expect(await screen.findByRole('heading', { name: 'Payload summary' })).toBeInTheDocument()
    expect(await screen.findByText(/Snapshot payload table rendering deferred/i)).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: /race preview table/i })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to race publications/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-1/race'
    )

    const technicalSection = screen.getByText('Show technical payload').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    await userEvent.click(screen.getByText('Show technical payload'))
    expect(within(technicalSection as HTMLElement).getByText(/race-detail-hidden-payload/i)).toBeVisible()
    expectNoForbiddenViewerActions()
    expectNoAdminLinks()
  })
})
