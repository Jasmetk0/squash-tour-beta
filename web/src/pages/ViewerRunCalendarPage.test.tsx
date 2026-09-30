import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Route, Routes } from 'react-router-dom'
import { describe, expect, it, beforeEach, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunCalendarPage, ViewerRunPlannedEventPage, ViewerRunWeekPage } from './ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
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

function renderViewerCalendarRoute(route: string): void {
  renderWithViewerProviders(
    <Routes>
      <Route path="/viewer/runs/:runId/calendar" element={<ViewerRunCalendarPage />} />
      <Route path="/viewer/runs/:runId/calendar/:eventId" element={<ViewerRunPlannedEventPage />} />
      <Route path="/viewer/runs/:runId/weeks/:week" element={<ViewerRunWeekPage />} />
    </Routes>,
    { route }
  )
}

function mockRunMetadata(): void {
  api.getRun.mockResolvedValue({
    run: {
      run_id: 'viewer-run-2d',
      season: 2028,
      seed: 52,
      config_version: 'v2d',
      config_fingerprint: 'fp-2d',
      next_event_index: 1,
      total_events: 3,
      completed_event_ids: ['EVENT-COMPLETE']
    },
    season_state: {
      season: 2028,
      next_event_index: 1,
      completed_event_ids: ['EVENT-COMPLETE'],
      ordered_events: [
        { event_id: 'EVENT-COMPLETE', season: 2028, week: 1, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
        { event_id: 'EVENT-NEXT', season: 2028, week: 2, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' },
        { event_id: 'EVENT-FUTURE', season: 2028, week: 3, tour: 'World Tour', category: 'Bronze', template_id: 'WT-BRONZE' }
      ]
    }
  })
}

function mockEvents(): void {
  api.listEvents.mockResolvedValue({
    run_id: 'viewer-run-2d',
    events: [
      {
        event_sequence: 1,
        event_id: 'EVENT-COMPLETE',
        season: 2028,
        week: 1,
        template_id: 'WT-PLAT',
        tournament_result: { raw_calendar_marker_should_be_hidden: true }
      },
      {
        event_sequence: 2,
        event_id: 'EVENT-NEXT',
        season: 2028,
        week: 2,
        template_id: 'ET-GOLD',
        tournament_result: {
          champion: { player_id: 'PLAYER-42', player_name: 'Linked Champion' },
          result_status: 'completed',
          match_count: 31,
          completed_match_count: 31,
          raw_week_result_marker_should_be_hidden: true
        }
      }
    ]
  })
}


function mockCanonicalCalendarHistory(): void {
  api.getViewerTournamentHistory.mockResolvedValue({
    schema_version: 'viewer_tournament_history.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    tournament_count: 3,
    published_result_count: 1,
    tournaments: [
      {
        event_id: 'EVENT-COMPLETE',
        season: '2000/2001',
        season_week: 1,
        event_name: 'Season Opener',
        template_id: 'WT-PLAT',
        category: 'PLATINUM',
        tour_level: 'WORLD_TOUR',
        host_country: 'EGY',
        host_city: 'Cairo',
        region: 'AFRICA',
        main_draw_size: 32,
        qualification_draw_size: 16,
        seeds_count: 8,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: true,
        champion_player_id: 'PLAYER-42',
        finalist_player_id: 'PLAYER-99'
      },
      {
        event_id: 'EVENT-NEXT',
        season: '2000/2001',
        season_week: 2,
        event_name: 'Gold Open',
        template_id: 'ET-GOLD',
        category: 'GOLD',
        tour_level: 'ELITE_TOUR',
        host_country: 'CZE',
        host_city: 'Prague',
        region: 'EUROPE',
        main_draw_size: 16,
        qualification_draw_size: 8,
        seeds_count: 4,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: false,
        champion_player_id: null,
        finalist_player_id: null
      },
      {
        event_id: 'EVENT-FUTURE',
        season: '2001/2002',
        season_week: 3,
        event_name: 'Future Bronze',
        template_id: 'WT-BRONZE',
        category: 'BRONZE',
        tour_level: 'WORLD_TOUR',
        host_country: 'USA',
        host_city: null,
        region: 'AMERICAS',
        main_draw_size: 8,
        qualification_draw_size: 0,
        seeds_count: 2,
        qualifier_spots: 0,
        wild_cards: 1,
        byes: 0,
        ranking_status: 'ranked',
        result_published: false,
        champion_player_id: null,
        finalist_player_id: null
      }
    ]
  })
}

function mockSnapshots(): void {
  api.listRankingSnapshots.mockResolvedValue({
    run_id: 'viewer-run-2d',
    snapshots: [
      { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'EVENT-NEXT', payload: { table: 'metadata-only' } },
      { snapshot_sequence: 5, snapshot_kind: 'WEEK', source_event_id: 'EVENT-COMPLETE', payload: {} }
    ]
  })
  api.listRaceSnapshots.mockResolvedValue({
    run_id: 'viewer-run-2d',
    snapshots: [{ snapshot_sequence: 7, snapshot_kind: 'WEEK', source_event_id: 'EVENT-NEXT', payload: {} }]
  })
}


function seasonCalendarEventRow(eventId: string): HTMLElement {
  for (const eventLabel of screen.getAllByText(eventId)) {
    const row = eventLabel.closest('li')
    if (row) return row
  }
  throw new Error(`Missing season calendar row for ${eventId}`)
}

function expectNoForbiddenViewerActions(): void {
  const forbiddenLabels = [
    'Simulate',
    'Generate',
    'Persist',
    'Apply',
    'Execute',
    'Delete',
    'Edit',
    'Import',
    'Rollover',
    'Rebuild',
    'Override',
    'Save changes',
    'Commit',
    'Regenerate',
    'Repair',
    'Merge',
    'Overwrite'
  ]

  forbiddenLabels.forEach((label) => {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  })
}

describe('ViewerRunCalendarPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCanonicalCalendarHistory()
  })

  it('renders canonical saved Calendar Packages without legacy run/event reads', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Canonical season timeline' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('viewer-run-2d')
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()

    const list = screen.getByRole('list', { name: 'Viewer canonical season calendar events' })
    expect(within(list).getByText('Season Opener')).toBeInTheDocument()
    expect(within(list).getByText('Gold Open')).toBeInTheDocument()
    expect(within(list).getByText('Future Bronze')).toBeInTheDocument()
    expect(screen.getAllByText('2000/2001').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2001/2002').length).toBeGreaterThan(0)

    const completed = within(list).getByText('Season Opener').closest('li') as HTMLElement
    expect(within(completed).getByText('PLATINUM')).toBeInTheDocument()
    expect(within(completed).getByText('WORLD TOUR')).toBeInTheDocument()
    expect(within(completed).getByText('Cairo, EGY')).toBeInTheDocument()
    expect(within(completed).getByText('Published')).toBeInTheDocument()
    expect(within(completed).getByText('PLAYER-42')).toBeInTheDocument()
    expect(within(completed).getByRole('link', { name: 'Open planned event' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-COMPLETE'
    )
    expect(within(completed).getByRole('link', { name: 'Open week detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/weeks/1'
    )
    expect(within(completed).getByRole('link', { name: 'Open tournament detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-COMPLETE'
    )

    expect(screen.queryByText('Show technical calendar data')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows a canonical empty state when no saved Calendar Package exists', async () => {
    api.getViewerTournamentHistory.mockRejectedValueOnce(
      new api.ApiError('missing calendar', 404)
    )

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(
      await screen.findByText('No saved Calendar Package is available for this Viewer Branch yet.')
    ).toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('renders an empty saved Calendar without inventing tournament data', async () => {
    api.getViewerTournamentHistory.mockResolvedValueOnce({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'viewer-run-2d',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 0,
      published_result_count: 0,
      tournaments: []
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(
      await screen.findByText('No tournaments are present in the saved Calendar Packages.')
    ).toBeInTheDocument()
    expect(screen.queryByRole('list', { name: 'Viewer canonical season calendar events' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunPlannedEventPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockCanonicalCalendarHistory()
  })

  it('renders canonical saved Calendar event detail without legacy run/event reads', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('viewer-run-2d')
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()

    expect(screen.getAllByText('EVENT-NEXT').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold Open').length).toBeGreaterThan(0)
    expect(screen.getAllByText('2000/2001').length).toBeGreaterThan(0)
    expect(screen.getAllByText('W2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ELITE TOUR').length).toBeGreaterThan(0)
    expect(screen.getAllByText('GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Prague, CZE').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Not published').length).toBeGreaterThan(0)

    expect(screen.getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar'
    )
    expect(screen.getByRole('link', { name: 'Week W2' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/weeks/2'
    )
    expect(screen.getByRole('link', { name: 'Tournament detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-NEXT'
    )
    expect(screen.queryByText(/Persisted event record/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/next event index/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('fails safely when the event is not present in saved Calendar Packages', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/UNKNOWN-EVENT')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(
      await screen.findByText('This event is not present in the saved Calendar Packages.')
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tournament detail' })).not.toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('handles encoded canonical event IDs without unsafe legacy fallback', async () => {
    api.getViewerTournamentHistory.mockResolvedValueOnce({
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 1,
      published_result_count: 0,
      tournaments: [{
        event_id: 'EVT/1 #A',
        season: '2030/2031',
        season_week: 7,
        event_name: 'Encoded Open',
        template_id: 'WT-GOLD',
        category: 'GOLD',
        tour_level: 'WORLD_TOUR',
        host_country: 'CZE',
        host_city: null,
        region: 'EUROPE',
        main_draw_size: 16,
        qualification_draw_size: 8,
        seeds_count: 4,
        qualifier_spots: 4,
        wild_cards: 2,
        byes: 0,
        ranking_status: 'ranked',
        result_published: false,
        champion_player_id: null,
        finalist_player_id: null
      }]
    })

    renderViewerCalendarRoute('/viewer/runs/run%2Falpha%20%231/calendar/EVT%2F1%20%23A')

    expect(await screen.findByText('Encoded Open')).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith('run/alpha #1')
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(screen.getByRole('link', { name: 'Season calendar' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/calendar'
    )
    expect(screen.getByRole('link', { name: 'Tournament detail' })).toHaveAttribute(
      'href',
      '/viewer/runs/run%2Falpha%20%231/tournaments/EVT%2F1%20%23A'
    )
    expect(document.body).not.toHaveTextContent('[object Object]')
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunWeekPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
    mockEvents()
    mockSnapshots()
  })

  it('renders sports-facing week detail with events from the selected week only', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2d').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    expect(screen.getByText('Week context')).toBeInTheDocument()
    expect(screen.getAllByText('Planned events this week').length).toBeGreaterThan(0)
    expect(screen.getByText('Persisted tournament records this week')).toBeInTheDocument()
    expect(screen.getByText('Publications this week')).toBeInTheDocument()
    expect(screen.getByText('Source context links')).toBeInTheDocument()
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    expect(screen.queryByText('EVENT-COMPLETE')).not.toBeInTheDocument()
    expect(screen.queryByText('EVENT-FUTURE')).not.toBeInTheDocument()
    expect(screen.getAllByText('W2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elite Tour').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Persisted event record').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Available').length).toBeGreaterThan(0)
    expect(screen.getByText('Event sequence')).toBeInTheDocument()
    expect(screen.queryByText('Champion')).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Linked Champion' })).not.toBeInTheDocument()
    expect(screen.queryByText('Result status')).not.toBeInTheDocument()
    expect(screen.queryByText('Matches')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT'
    )
    expect(screen.getAllByRole('link', { name: /Open tournament detail/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-NEXT'
    )
    expect(screen.getByText('Ranking publications count')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Ranking publication #4/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/rankings/4'
    )
    expect(screen.getByText('Race publications count')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Race publication #7/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/race/7'
    )
    expect(screen.queryByText(/raw_week_result_marker_should_be_hidden/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/storyline/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })


  it('does not show fake result metadata for unknown persisted tournament_result payloads', async () => {
    api.listEvents.mockResolvedValue({
      run_id: 'viewer-run-2d',
      events: [
        {
          event_sequence: 2,
          event_id: 'EVENT-NEXT',
          season: 2028,
          week: 2,
          template_id: 'ET-GOLD',
          tournament_result: { unknown_payload_marker_should_be_hidden: true }
        }
      ]
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Available').length).toBeGreaterThan(0)
    expect(screen.queryByText('Champion')).not.toBeInTheDocument()
    expect(screen.queryByText('Result status')).not.toBeInTheDocument()
    expect(screen.queryByText('Matches')).not.toBeInTheDocument()
    expect(screen.queryByText(/unknown_payload_marker_should_be_hidden/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows deferred publication metadata message when snapshots cannot be safely matched', async () => {
    api.listRankingSnapshots.mockResolvedValue({
      run_id: 'viewer-run-2d',
      snapshots: [{ snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: null, payload: {} }]
    })
    api.listRaceSnapshots.mockResolvedValue({ run_id: 'viewer-run-2d', snapshots: [] })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect(await screen.findByText('No ranking or race publications are source-matched to this week.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows no-data state for a missing empty week', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/12')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect(await screen.findByText('No planned or persisted tournament records are available for this week.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps invalid week route params local, safe, and free of invented match data', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-1/weeks/not-a-week')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect(screen.getByText('Week must be a positive whole number in the URL (for example /weeks/12).')).toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    expect(api.listRankingSnapshots).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expect(screen.queryByText(/match result|final score|standings|winner/i)).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('[object Object]')
    expectNoForbiddenViewerActions()
  })

})
