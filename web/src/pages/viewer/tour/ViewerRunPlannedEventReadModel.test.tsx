import { Route, Routes } from 'react-router-dom'
import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { calendarEvent, historyEvent, savedCalendar, savedHistory } from '../../../test/viewerCalendarFixtures'
import { ViewerRunPlannedEventPage } from '../../ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status: number) { super(message) } },
  getViewerRunCalendar: vi.fn(), getViewerTournamentHistory: vi.fn(),
  getRun: vi.fn(), listEvents: vi.fn(),
}))
vi.mock('../../../api/client', () => api)

function renderPlanned(route = '/viewer/runs/run%20alpha/calendar/EVENT%2F1'): void {
  renderWithViewerProviders(<Routes>
    <Route path="/viewer/runs/:runId/calendar/:eventId" element={<ViewerRunPlannedEventPage />} />
    <Route path="/viewer/runs/:runId/planned-missing" element={<ViewerRunPlannedEventPage />} />
  </Routes>, { route })
}

describe('ViewerRunPlannedEventPage canonical source contract', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar())
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory())
  })

  it('renders exact Saved metadata and encoded source links without inferring results', async () => {
    renderPlanned()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
    const links = within(screen.getByRole('list', { name: 'Planned event source links' }))
    expect(links.getByRole('link', { name: 'Season calendar' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expect(links.getByRole('link', { name: 'Week W5' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/weeks/5?season=2028%2F2029')
    expect(links.getByRole('link', { name: 'Tournament detail' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/EVENT%2F1')
    expect(screen.queryByText('Completed · result published')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('allows opening a planned canonical detail before any published result exists', async () => {
    renderPlanned()
    expect(await screen.findByRole('link', { name: 'Tournament detail' })).toBeInTheDocument()
    expect(screen.getByText('planned')).toBeInTheDocument()
    expect(screen.queryByText('CHAMPION')).not.toBeInTheDocument()
  })

  it('reports an absent exact event instead of partially matching its ID', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([calendarEvent({ event_id: 'EVENT/10' })]))
    renderPlanned()
    expect(await screen.findByText('This event is not present in the Saved Calendar Package.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tournament detail' })).not.toBeInTheDocument()
  })

  it('keeps planned metadata usable when Tournament History fails', async () => {
    api.getViewerTournamentHistory.mockRejectedValue(new Error('history outage'))
    renderPlanned()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(screen.queryByText('Completed · result published')).not.toBeInTheDocument()
  })

  it.each([
    { season_week: 6 }, { template_id: 'FOREIGN' }, { event_id: 'EVENT/10' },
    { season: '2029/2030' }, { host_country: 'CZE' },
  ])('rejects published results with inconsistent occurrence or metadata: %j', async (change) => {
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(undefined, {
      result_published: true, champion_player_id: 'FOREIGN-CHAMPION', finalist_player_id: 'FOREIGN-FINALIST', ...change,
    })]))
    renderPlanned()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(screen.queryByText('FOREIGN-CHAMPION')).not.toBeInTheDocument()
    expect(screen.queryByText('Completed · result published')).not.toBeInTheDocument()
  })

  it('shows completed status only for the exact canonical published result', async () => {
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(undefined, {
      result_published: true, champion_player_id: 'CHAMPION', finalist_player_id: 'FINALIST',
    })]))
    renderPlanned()
    expect(await screen.findByText('CHAMPION')).toBeInTheDocument()
    expect(screen.getByText('Completed · result published')).toBeInTheDocument()
  })

  it('retains explicit future scheduled status without manufacturing a result', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([calendarEvent({ status: 'scheduled', season_week: 30 })]))
    renderPlanned()
    expect(await screen.findByText('scheduled')).toBeInTheDocument()
    expect(screen.queryByText('Completed · result published')).not.toBeInTheDocument()
  })

  it('does not infer completion for a prior planned event', async () => {
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([calendarEvent({ season_week: 1 })]))
    renderPlanned()
    expect(await screen.findByText('planned')).toBeInTheDocument()
    expect(screen.queryByText('Completed · result published')).not.toBeInTheDocument()
  })

  it('reports Calendar read errors without falling back to legacy data', async () => {
    api.getViewerRunCalendar.mockRejectedValue(new Error('calendar outage'))
    renderPlanned()
    expect(await screen.findByText('Failed to load canonical Saved Calendar: calendar outage')).toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled()
    expect(api.listEvents).not.toHaveBeenCalled()
  })

  it('does not call APIs for a missing event parameter', () => {
    renderPlanned('/viewer/runs/run%20alpha/planned-missing')
    expect(screen.getByText('No planned event ID was provided in the URL.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
  })
})
