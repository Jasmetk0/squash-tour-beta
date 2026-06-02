import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, beforeEach, vi } from 'vitest'

import { ViewerRunCalendarPage, ViewerRunPlannedEventPage, ViewerRunWeekPage } from './ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn(),
  listRankingSnapshots: vi.fn(),
  listRaceSnapshots: vi.fn()
}))

vi.mock('../api/client', () => api)

function renderViewerCalendarRoute(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/viewer/runs/:runId/calendar" element={<ViewerRunCalendarPage />} />
          <Route path="/viewer/runs/:runId/calendar/:eventId" element={<ViewerRunPlannedEventPage />} />
          <Route path="/viewer/runs/:runId/weeks/:week" element={<ViewerRunWeekPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
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
    mockRunMetadata()
    mockEvents()
    mockSnapshots()
  })

  it('renders sports-facing run calendar metadata and Viewer route links without primary raw JSON', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2d').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('2028')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-COMPLETE').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-NEXT').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-FUTURE').length).toBeGreaterThan(0)
    expect(screen.getAllByText('WT-PLAT').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('WT-BRONZE').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Platinum').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Bronze').length).toBeGreaterThan(0)
    expect(screen.getAllByText('World Tour').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elite Tour').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Completed').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Current/next').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Upcoming').length).toBeGreaterThan(0)
    expect(screen.getAllByRole('link', { name: /Open planned event/i })[1]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT'
    )
    expect(screen.getAllByRole('link', { name: /Open week detail/i })[1]).toHaveAttribute('href', '/viewer/runs/viewer-run-2d/weeks/2')
    expect(screen.getAllByRole('link', { name: /Open tournament detail/i })[0]).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-COMPLETE'
    )
    const nextRow = seasonCalendarEventRow('EVENT-NEXT')
    expect(within(nextRow).getByText('Champion')).toBeInTheDocument()
    expect(within(nextRow).getByRole('link', { name: 'Linked Champion' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/players/PLAYER-42/career'
    )
    expect(within(nextRow).getByText('Result status')).toBeInTheDocument()
    expect(within(nextRow).getByText('completed')).toBeInTheDocument()
    expect(within(nextRow).getByText('Matches')).toBeInTheDocument()
    expect(within(nextRow).getByText('31 of 31')).toBeInTheDocument()
    expect(screen.getByText('Show technical calendar data')).toBeInTheDocument()
    expect(screen.queryByText(/raw_calendar_marker_should_be_hidden/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/raw_week_result_marker_should_be_hidden/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
  })


  it('keeps season calendar champion plain text when parsed tournament_result has no player id', async () => {
    api.listEvents.mockResolvedValue({
      run_id: 'viewer-run-2d',
      events: [
        {
          event_sequence: 2,
          event_id: 'EVENT-NEXT',
          season: 2028,
          week: 2,
          template_id: 'ET-GOLD',
          tournament_result: { champion: { player_name: 'Plain Calendar Champion' }, result_status: 'completed', match_count: 15 }
        }
      ]
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    const nextRow = seasonCalendarEventRow('EVENT-NEXT')
    expect(within(nextRow).getByText('Champion')).toBeInTheDocument()
    expect(within(nextRow).getByText('Plain Calendar Champion')).toBeInTheDocument()
    expect(within(nextRow).queryByRole('link', { name: 'Plain Calendar Champion' })).not.toBeInTheDocument()
    expect(within(nextRow).getByText('Result status')).toBeInTheDocument()
    expect(within(nextRow).getByText('Matches')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('does not show fake season calendar metadata for unknown persisted tournament_result payloads', async () => {
    api.listEvents.mockResolvedValue({
      run_id: 'viewer-run-2d',
      events: [
        {
          event_sequence: 2,
          event_id: 'EVENT-NEXT',
          season: 2028,
          week: 2,
          template_id: 'ET-GOLD',
          tournament_result: { unknown_calendar_payload_marker_should_be_hidden: true }
        }
      ]
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar')

    expect(await screen.findByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    const nextRow = seasonCalendarEventRow('EVENT-NEXT')
    expect(within(nextRow).queryByText('Champion')).not.toBeInTheDocument()
    expect(within(nextRow).queryByText('Result status')).not.toBeInTheDocument()
    expect(within(nextRow).queryByText('Matches')).not.toBeInTheDocument()
    expect(screen.queryByText(/unknown_calendar_payload_marker_should_be_hidden/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

})

describe('ViewerRunPlannedEventPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mockRunMetadata()
    mockEvents()
    mockSnapshots()
  })

  it('renders sports-facing planned event detail with collapsed technical data and no commissioner controls', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    expect(screen.getAllByText('viewer-run-2d').length).toBeGreaterThan(0)
    expect(screen.getAllByText('EVENT-NEXT').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('2028')).length).toBeGreaterThan(0)
    expect(screen.getAllByText('W2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elite Tour').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Current/next').length).toBeGreaterThan(0)
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to season calendar/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar'
    )
    expect(screen.getByRole('link', { name: /Open week detail/i })).toHaveAttribute('href', '/viewer/runs/viewer-run-2d/weeks/2')
    const technicalSection = screen.getByText('Show technical planned event data').closest('details')
    expect(technicalSection).not.toHaveAttribute('open')
    expect(screen.getByText(/event_id/i)).not.toBeVisible()
    await userEvent.click(screen.getByText('Show technical planned event data'))
    expect(within(technicalSection as HTMLElement).getByText(/EVENT-NEXT/i)).toBeVisible()
    expect(screen.queryByText(/wildcard/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/withdrawal/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/late replacement/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/commissioner/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
    expect(screen.queryByRole('navigation', { name: /run navigation/i })).not.toBeInTheDocument()
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
    expect(screen.getByText('Week context')).toBeInTheDocument()
    expect(screen.getByText('Tournaments this week')).toBeInTheDocument()
    expect(screen.getByText('Publications this week')).toBeInTheDocument()
    expect(screen.getByText('Links')).toBeInTheDocument()
    expect(screen.getAllByText('2').length).toBeGreaterThan(0)
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    expect(screen.queryByText('EVENT-COMPLETE')).not.toBeInTheDocument()
    expect(screen.queryByText('EVENT-FUTURE')).not.toBeInTheDocument()
    expect(screen.getAllByText('W2').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Gold').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Elite Tour').length).toBeGreaterThan(0)
    expect(screen.getAllByText('ET-GOLD').length).toBeGreaterThan(0)
    expect(screen.getByText('Available')).toBeInTheDocument()
    expect(screen.getByText('Champion')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Linked Champion' })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/players/PLAYER-42/career'
    )
    expect(screen.getByText('Result status')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.getByText('Matches')).toBeInTheDocument()
    expect(screen.getByText('31 of 31')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open planned event/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/calendar/EVENT-NEXT'
    )
    expect(screen.getByRole('link', { name: /Open tournament detail/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/tournaments/EVENT-NEXT'
    )
    expect(screen.getByText('Ranking publications count')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Ranking publication #4/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/rankings/4'
    )
    expect(screen.getByText('Race publications count')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Race publication #7/i })).toHaveAttribute(
      'href',
      '/viewer/runs/viewer-run-2d/race/7'
    )
    expect(screen.queryByText(/raw_week_result_marker_should_be_hidden/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/storyline/i)).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })


  it('keeps champion plain text when parsed tournament_result has no player id', async () => {
    api.listEvents.mockResolvedValue({
      run_id: 'viewer-run-2d',
      events: [
        {
          event_sequence: 2,
          event_id: 'EVENT-NEXT',
          season: 2028,
          week: 2,
          template_id: 'ET-GOLD',
          tournament_result: { champion: { player_name: 'Plain Champion' }, result_status: 'completed', match_count: 15 }
        }
      ]
    })

    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/2')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect((await screen.findAllByText('EVENT-NEXT')).length).toBeGreaterThan(0)
    expect(screen.getByText('Champion')).toBeInTheDocument()
    expect(screen.getByText('Plain Champion')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Plain Champion' })).not.toBeInTheDocument()
    expect(screen.getByText('Result status')).toBeInTheDocument()
    expect(screen.getByText('Matches')).toBeInTheDocument()
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
    expect(screen.getByText('Available')).toBeInTheDocument()
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
    expect(await screen.findByText('This preview is not connected for this data shape yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows no-data state for a missing empty week', async () => {
    renderViewerCalendarRoute('/viewer/runs/viewer-run-2d/weeks/12')

    expect(await screen.findByRole('heading', { name: 'Week Detail' })).toBeInTheDocument()
    expect(await screen.findByText('No data is available for this run yet.')).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
