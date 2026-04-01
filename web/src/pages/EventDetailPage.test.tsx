import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventDetailPage } from './EventDetailPage'

const api = vi.hoisted(() => ({
  getEvent: vi.fn(),
  getRun: vi.fn(),
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

function renderEventDetailRoute(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/events/:eventId" element={<EventDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('EventDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2028, seed: 7, next_event_index: 2, total_events: 4, completed_event_ids: ['E10'] },
      season_state: {
        season: 2028,
        next_event_index: 1,
        completed_event_ids: ['E10'],
        ordered_events: [
          { event_id: 'E10', season: 2028, week: 3, tour: 'WORLD', category: 'SILVER', template_id: 'psa-silver' },
          { event_id: 'E11', season: 2028, week: 4, tour: 'WORLD', category: 'GOLD', template_id: 'psa-gold' },
          { event_id: 'E12', season: 2028, week: 5, tour: 'WORLD', category: 'PLATINUM', template_id: 'psa-platinum' }
        ]
      }
    })
    api.listRankingSnapshots.mockResolvedValue({ snapshots: [] })
    api.listRaceSnapshots.mockResolvedValue({ snapshots: [] })
  })

  it('renders event detail from direct URL with metadata and payload', async () => {
    api.getEvent.mockResolvedValue({
      event_sequence: 11,
      event_id: 'E11',
      season: 2028,
      week: 4,
      template_id: 'psa-gold',
      tournament_result: { champion_id: 'P-1' }
    })
    api.listEvents.mockResolvedValue({
      events: [
        { event_sequence: 10, event_id: 'E10', season: 2028, week: 3, template_id: 'psa-silver', tournament_result: {} },
        { event_sequence: 11, event_id: 'E11', season: 2028, week: 4, template_id: 'psa-gold', tournament_result: {} },
        { event_sequence: 12, event_id: 'E12', season: 2028, week: 5, template_id: 'psa-platinum', tournament_result: {} }
      ]
    })
    api.listRankingSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 3, snapshot_kind: 'WEEK', source_event_id: 'E10', payload: {} },
        { snapshot_sequence: 4, snapshot_kind: 'WEEK', source_event_id: 'E11', payload: {} }
      ]
    })
    api.listRaceSnapshots.mockResolvedValue({
      snapshots: [
        { snapshot_sequence: 8, snapshot_kind: 'WEEK', source_event_id: 'E11', payload: {} },
        { snapshot_sequence: 9, snapshot_kind: 'WEEK', source_event_id: 'E12', payload: {} }
      ]
    })

    renderEventDetailRoute('/runs/run-a/events/E11')

    expect(await screen.findByRole('heading', { name: 'Event detail' })).toBeInTheDocument()
    expect(await screen.findByText(/champion_id/)).toBeInTheDocument()
    expect(screen.getAllByText('E11').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Raw event payload' })).toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledWith('run-a', 'E11')
    expect(api.listEvents).toHaveBeenCalledWith('run-a')
    expect(api.getRun).toHaveBeenCalledWith('run-a')
    expect(api.listRankingSnapshots).toHaveBeenCalledWith('run-a')
    expect(api.listRaceSnapshots).toHaveBeenCalledWith('run-a')
    expect(screen.getByRole('link', { name: 'Back to events history' })).toHaveAttribute('href', '/runs/run-a/events')
    expect(screen.getByRole('link', { name: 'Back to events history at this event' })).toHaveAttribute(
      'href',
      '/runs/run-a/events#event-E11'
    )
    expect(screen.getByRole('link', { name: 'Open activity' })).toHaveAttribute('href', '/runs/run-a/activity')
    expect(screen.getByRole('link', { name: 'Back to Season Calendar' })).toHaveAttribute('href', '/runs/run-a/calendar')
    expect(screen.getByRole('link', { name: 'Open planned-event detail' })).toHaveAttribute('href', '/runs/run-a/calendar/E11')
    expect(screen.getByRole('link', { name: 'Open planned-event detail page' })).toHaveAttribute('href', '/runs/run-a/calendar/E11')
    expect(screen.getByRole('link', { name: 'Ranking snapshot #4' })).toHaveAttribute('href', '/runs/run-a/snapshots/ranking/4')
    expect(screen.getByRole('link', { name: 'Race snapshot #8' })).toHaveAttribute('href', '/runs/run-a/snapshots/race/8')

    const e10Links = screen.getAllByRole('link', { name: 'E10' })
    expect(e10Links.some((link) => link.getAttribute('href') === '/runs/run-a/events/E10')).toBe(true)
    expect(e10Links.some((link) => link.getAttribute('href') === '/runs/run-a/calendar/E10')).toBe(true)
    const e12Links = screen.getAllByRole('link', { name: 'E12' })
    expect(e12Links.some((link) => link.getAttribute('href') === '/runs/run-a/events/E12')).toBe(true)
    expect(e12Links.some((link) => link.getAttribute('href') === '/runs/run-a/calendar/E12')).toBe(true)
    expect(screen.getByText('Plan position')).toBeInTheDocument()
    expect(screen.getByText('2 of 3')).toBeInTheDocument()
    expect(screen.getByText(/Previous planned:/)).toBeInTheDocument()
  })

  it('shows readable missing-event behavior for invalid event IDs', async () => {
    api.getEvent.mockRejectedValue(new api.ApiError('event not found', 404))
    api.listEvents.mockResolvedValue({ events: [] })

    renderEventDetailRoute('/runs/run-a/events/UNKNOWN')

    expect(await screen.findByText('Event UNKNOWN was not found for this run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to events history' })).toHaveAttribute('href', '/runs/run-a/events')
    expect(screen.getAllByText('None').length).toBeGreaterThan(0)
  })

  it('shows planned neighbor boundary behavior at the start of the season plan', async () => {
    api.getEvent.mockResolvedValue({
      event_sequence: 10,
      event_id: 'E10',
      season: 2028,
      week: 3,
      template_id: 'psa-silver',
      tournament_result: {}
    })
    api.listEvents.mockResolvedValue({
      events: [{ event_sequence: 10, event_id: 'E10', season: 2028, week: 3, template_id: 'psa-silver', tournament_result: {} }]
    })

    renderEventDetailRoute('/runs/run-a/events/E10')

    expect(await screen.findByText(/Previous planned:/)).toBeInTheDocument()
    expect(screen.getAllByText('None').length).toBeGreaterThan(0)
    expect(screen.getByRole('link', { name: 'E11' })).toHaveAttribute('href', '/runs/run-a/calendar/E11')
  })

  it('shows readable context when persisted event has no matching planned-season entry', async () => {
    api.getEvent.mockResolvedValue({
      event_sequence: 99,
      event_id: 'ARCHIVE_ONLY',
      season: 2028,
      week: 50,
      template_id: 'legacy',
      tournament_result: {}
    })
    api.listEvents.mockResolvedValue({
      events: [{ event_sequence: 99, event_id: 'ARCHIVE_ONLY', season: 2028, week: 50, template_id: 'legacy', tournament_result: {} }]
    })

    renderEventDetailRoute('/runs/run-a/events/ARCHIVE_ONLY')

    expect(await screen.findByText("Event ARCHIVE_ONLY is not present in this run's ordered season plan.")).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open planned-event detail' })).toHaveAttribute(
      'href',
      '/runs/run-a/calendar/ARCHIVE_ONLY'
    )
  })
})
