import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { renderWithViewerProviders } from '../test/viewerTestUtils'
import { ViewerRunCalendarPage, ViewerRunPlannedEventPage, ViewerRunWeekPage } from './ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerCompletedTournaments: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  listRaceSnapshots: vi.fn()
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

function event(
  eventId: string,
  week: number,
  {
    category,
    tourLevel,
    templateId,
    name,
    status = 'planned'
  }: {
    category: string
    tourLevel: 'WORLD_TOUR' | 'ELITE_TOUR'
    templateId: string
    name: string
    status?: 'planned' | 'active' | 'completed' | 'cancelled' | 'scheduled'
  }
) {
  return {
    event_id: eventId,
    season: 2028,
    season_week: week,
    calendar_year: 2028,
    year_week: 36 + week,
    template_id: templateId,
    event_name: name,
    category,
    tour_level: tourLevel,
    host_country: 'CZE',
    host_city: 'Brno',
    region: 'Europe',
    duration_in_season_weeks: 1,
    start_season_week: week,
    end_season_week: week,
    status,
    main_draw_size: 32,
    qualification_draw_size: 16,
    seeds_count: 8,
    qualifier_spots: 4,
    wild_cards: 2,
    byes: 0,
    prestige: 8.5
  }
}

function mockCanonicalCalendar(): void {
  api.getViewerRunCalendar.mockResolvedValue({
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    season_count: 1,
    event_count: 3,
    seasons: [
      {
        season: 2028,
        event_count: 3,
        events: [
          event('EVENT-COMPLETE', 1, {
            category: 'Platinum',
            tourLevel: 'WORLD_TOUR',
            templateId: 'WT-PLAT',
            name: 'World Platinum',
            status: 'completed'
          }),
          event('EVENT-NEXT', 2, {
            category: 'Gold',
            tourLevel: 'ELITE_TOUR',
            templateId: 'ET-GOLD',
            name: 'Elite Gold'
          }),
          event('EVENT-FUTURE', 3, {
            category: 'Bronze',
            tourLevel: 'WORLD_TOUR',
            templateId: 'WT-BRONZE',
            name: 'World Bronze'
          })
        ]
      }
    ]
  })
}

function mockCompleted(): void {
  api.getViewerCompletedTournaments.mockResolvedValue({
    schema_version: 'viewer_completed_tournaments.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    tournament_count: 1,
    tournaments: [
      {
        event_id: 'EVENT-COMPLETE',
        completed_season_index: 28,
        completed_week: 1,
        champion_player_id: 'PLAYER-CHAMP',
        finalist_player_id: 'PLAYER-FINAL',
        qualification_winner_ids: ['PLAYER-Q'],
        player_count: 32,
        match_count: 31
      }
    ]
  })
}

function mockSnapshots(): void {
  api.listViewerOfficialRankingHistory.mockResolvedValue({
    schema_version: 'viewer_official_ranking_history.v1',
    product_run_id: 'viewer-run-2d',
    viewer_branch_id: 'branch-viewer',
    public_head_ordinal: 1709,
    publication_count: 2,
    publications: [
      {
        season_index: 28,
        week: 2,
        week_ordinal: 1709,
        snapshot_fingerprint: 'a'.repeat(64),
        policy_id: 'official-weekly',
        best_n: 12,
        row_count: 64
      },
      {
        season_index: 28,
        week: 1,
        week_ordinal: 1708,
        snapshot_fingerprint: 'b'.repeat(64),
        policy_id: 'official-weekly',
        best_n: 12,
        row_count: 64
      }
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
  for (const label of [
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
  ]) {
    expect(screen.queryByRole('button', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: new RegExp(label, 'i') })).not.toBeInTheDocument()
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  mockCanonicalCalendar()
  mockCompleted()
  mockSnapshots()
})

describe('ViewerRunCalendarPage canonical Saved Calendar', () => {
  it('renders Saved Calendar schedule and canonical completed result metadata', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-2d')
    expect(api.getViewerCompletedTournaments).toHaveBeenCalledWith('viewer-run-2d')
    expect((await screen.findAllByText('EVENT-COMPLETE')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-NEXT').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-FUTURE').length).toBeGreaterThan(0)
    expect(screen.getAllByText('WT-PLAT').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('WORLD TOUR').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ELITE TOUR').length).toBeGreaterThan(0)

    const completed = seasonCalendarEventRow('EVENT-COMPLETE')
    expect(within(completed).getByText('Completed · canonical result published')).toBeInTheDocument()
    expect(within(completed).getByText('PLAYER-CHAMP')).toBeInTheDocument()
    expect(within(completed).getByText('PLAYER-FINAL')).toBeInTheDocument()
    expect(within(completed).getByText('31')).toBeInTheDocument()

    expect(screen.getAllByRole('link', { name: /Open planned event/i })[1]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT'
    )
    expect(screen.getAllByRole('link', { name: /Open week detail/i })[1]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/weeks/2'
    )
    expect(screen.getAllByRole('link', { name: /Open tournament detail/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-COMPLETE'
    )
    expect(screen.getByText('Calendar authority')).toBeInTheDocument()
    expect(screen.getByText('Saved Run Package state')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('renders a safe empty Saved Calendar without invented schedule data', async () => {
    api.getViewerRunCalendar.mockResolvedValueOnce({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'viewer-run-2d',
      viewer_branch_id: 'branch-viewer',
      season_count: 1,
      event_count: 0,
      seasons: [{ season: 2028, event_count: 0, events: [] }]
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByText('The Saved Calendar Package contains no events.')).toBeInTheDocument()
    expect(screen.queryByText(/winner|final score|standings/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})

describe('ViewerRunPlannedEventPage canonical Saved Calendar', () => {
  it('renders a Saved Calendar event without legacy persisted-event dependencies', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('viewer-run-2d')
    expect(screen.getAllByText('EVENT-NEXT').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('Elite Gold')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('W2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ELITE TOUR').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
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
    expect(screen.getByText('Not published')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows canonical completion facts for a completed Saved Calendar event', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/EVENT-COMPLETE')

    expect(await screen.findByText('Completed · canonical result published')).toBeInTheDocument()
    expect(screen.getByText('PLAYER-CHAMP')).toBeInTheDocument()
    expect(screen.getByText('PLAYER-FINAL')).toBeInTheDocument()
    expect(screen.getByText('31')).toBeInTheDocument()
  })

  it('fails safely when the requested event is absent from the Saved Calendar', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/MISSING')

    expect(await screen.findByText('Event MISSING is not present in the Saved Calendar Package.')).toBeInTheDocument()
    expect(screen.queryByText(/champion|winner|final score/i)).not.toBeInTheDocument()
  })

  it('handles encoded Saved Calendar event identities without unsafe output', async () => {
    const encoded = event('EVT/1 #A', 7, {
      category: 'Gold',
      tourLevel: 'WORLD_TOUR',
      templateId: 'WT-GOLD',
      name: 'Encoded Open'
    })
    api.getViewerRunCalendar.mockResolvedValueOnce({
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      season_count: 1,
      event_count: 1,
      seasons: [{ season: 2030, event_count: 1, events: [encoded] }]
    })
    api.getViewerCompletedTournaments.mockResolvedValueOnce({
      schema_version: 'viewer_completed_tournaments.v1',
      product_run_id: 'run/alpha #1',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 0,
      tournaments: []
    })

    renderViewerCalendarRoute('/viewer/runs/run%2Falpha%20%231/calendar/EVT%2F1%20%23A')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run/alpha #1')
    expect(screen.getAllByText('EVT/1 #A').length).toBeGreaterThan(0)
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

describe('ViewerRunWeekPage canonical Saved Calendar schedule', () => {
  it('renders Saved Calendar events and source-matched public ranking/race publications', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    expect(screen.queryByText('EVENT-COMPLETE')).not.toBeInTheDocument()
    expect(screen.queryByText('EVENT-FUTURE')).not.toBeInTheDocument()
    expect(screen.getAllByText('W2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ELITE TOUR').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT'
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-NEXT'
    )
    expect(screen.getByText('Ranking publications count')).toBeInTheDocument()
    expect(screen.getByText('Race publications count')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Ranking publication #1709/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/rankings/1709'
    )
    expect(screen.getByText('Official · 64 ranked players · official-weekly')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Race publication #7/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/race/7'
    )
    expectNoForbiddenViewerActions()
  })

  it('shows canonical completed Tournament Result summaries for the selected week', async () => {
    api.getViewerCompletedTournaments.mockResolvedValueOnce({
      schema_version: 'viewer_completed_tournaments.v1',
      product_run_id: 'viewer-run-2d',
      viewer_branch_id: 'branch-viewer',
      tournament_count: 1,
      tournaments: [
        {
          event_id: 'EVENT-NEXT',
          completed_season_index: 28,
          completed_week: 2,
          champion_player_id: 'WEEK-CHAMP',
          finalist_player_id: 'WEEK-FINAL',
          qualification_winner_ids: [],
          player_count: 16,
          match_count: 15
        }
      ]
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    const completed = await screen.findByRole('list', { name: 'Viewer week canonical completed tournaments' })
    expect(within(completed).getByText('WEEK-CHAMP')).toBeInTheDocument()
    expect(within(completed).getByText('WEEK-FINAL')).toBeInTheDocument()
    expect(within(completed).getByText('15')).toBeInTheDocument()
  })

  it('shows deferred publication metadata when neither canonical ranking nor Race matches the week', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValueOnce({
      schema_version: 'viewer_official_ranking_history.v1',
      product_run_id: 'viewer-run-2d',
      viewer_branch_id: 'branch-viewer',
      public_head_ordinal: 1715,
      publication_count: 1,
      publications: [{
        season_index: 28,
        week: 8,
        week_ordinal: 1715,
        snapshot_fingerprint: 'c'.repeat(64),
        policy_id: 'official-weekly',
        best_n: 12,
        row_count: 64
      }]
    })
    api.listRaceSnapshots.mockResolvedValueOnce({ run_id: 'viewer-run-2d', snapshots: [] })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByText('No canonical ranking or source-matched Race publication is available for this week.')).toBeInTheDocument()
  })

  it('shows no-data state for a missing empty week', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/12')

    expect(await screen.findByText('No Saved Calendar event or canonical publication is available for this week.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps invalid week params local without calling Calendar or publication APIs', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/not-a-week')

    expect(await screen.findByText('Week must be a positive whole number in the URL (for example /weeks/12).')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerCompletedTournaments).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.listRaceSnapshots).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
