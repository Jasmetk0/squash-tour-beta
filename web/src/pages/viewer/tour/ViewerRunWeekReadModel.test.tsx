import { screen, within } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { calendarEvent, historyEvent, savedCalendar, savedHistory, savedRankings, savedRace, rankingPublication, racePublication } from '../../../test/viewerCalendarFixtures'
import { ViewerRunWeekPage } from '../../ViewerRunCalendarPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error { constructor(message: string, public status: number) { super(message) } },
  getViewerRunCalendar: vi.fn(), getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(), getViewerFinalsRace: vi.fn(),
  getRun: vi.fn(), listEvents: vi.fn(), listRankingSnapshots: vi.fn(), listRaceSnapshots: vi.fn(),
}))
vi.mock('../../../api/client', () => api)
function renderWeek(route = '/viewer/runs/run%20alpha/weeks/5'): void {
  renderWithViewerProviders(<Routes>
    <Route path="/viewer/runs/:runId/weeks/:week" element={<ViewerRunWeekPage />} />
    <Route path="/viewer/runs/:runId/week-missing" element={<ViewerRunWeekPage />} />
  </Routes>, { route })
}
function eventList() { return within(screen.getByRole('list', { name: 'Viewer week Saved Calendar events' })) }

describe('ViewerRunWeekPage canonical Saved sources', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar())
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory())
    api.listViewerOfficialRankingHistory.mockResolvedValue(savedRankings())
    api.getViewerFinalsRace.mockResolvedValue(savedRace())
  })
  it('renders exact Saved week metadata and encoded occurrence links without fake results', async () => {
    renderWeek()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(eventList().getByRole('link', { name: 'Open planned event' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVENT%2F1?season=2028%2F2029&week=5')
    expect(eventList().getByRole('link', { name: 'Open tournament detail' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments/EVENT%2F1')
    for (const legacy of [api.getRun, api.listEvents, api.listRankingSnapshots, api.listRaceSnapshots]) expect(legacy).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
  it('reports Calendar errors without showing an unrelated Tournament History result', async () => {
    api.getViewerRunCalendar.mockRejectedValue(new Error('calendar outage'))
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(undefined, { result_published: true, champion_player_id: 'UNRELATED' })]))
    renderWeek()
    expect(await screen.findByText('Failed to load canonical Saved Calendar: calendar outage')).toBeInTheDocument()
    expect(screen.queryByText('UNRELATED')).not.toBeInTheDocument()
  })
  it('shows the champion only for an exact published occurrence', async () => {
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(undefined, { result_published: true, champion_player_id: 'REAL-CHAMPION', finalist_player_id: 'REAL-FINALIST' })]))
    renderWeek()
    expect(await screen.findByText('REAL-CHAMPION')).toBeInTheDocument()
    expect(eventList().getByText('Completed · result published')).toBeInTheDocument()
  })
  it('keeps planned events usable when Tournament History fails', async () => {
    api.getViewerTournamentHistory.mockRejectedValue(new Error('history outage'))
    renderWeek()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Tournament History: history outage')).toBeInTheDocument()
  })
  it('never manufactures a Calendar event from history-only metadata', async () => {
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(calendarEvent({ event_id: 'HISTORY-ONLY' }), { result_published: true, champion_player_id: 'UNRELATED' })]))
    renderWeek()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(eventList().queryByText('HISTORY-ONLY')).not.toBeInTheDocument()
    expect(screen.queryByText('UNRELATED')).not.toBeInTheDocument()
  })
  it('does not attach a same-ID result from a different week', async () => {
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(calendarEvent({ season_week: 6 }), { result_published: true, champion_player_id: 'WRONG-WEEK' })]))
    renderWeek()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(screen.queryByText('WRONG-WEEK')).not.toBeInTheDocument()
  })
  it('links only the exact ranking and Race publication week', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValue(savedRankings([rankingPublication(), rankingPublication(6)]))
    api.getViewerFinalsRace.mockResolvedValue(savedRace([racePublication()]))
    renderWeek()
    expect(await screen.findByRole('link', { name: 'Ranking publication #1712' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/rankings/1712')
    expect(screen.queryByRole('link', { name: 'Ranking publication #1713' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open canonical Finals Race publication for this cutoff week' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/race')
  })
  it('keeps the valid Race link when Ranking history fails', async () => {
    api.listViewerOfficialRankingHistory.mockRejectedValue(new Error('ranking outage'))
    api.getViewerFinalsRace.mockResolvedValue(savedRace([racePublication()]))
    renderWeek()
    expect(await screen.findByRole('link', { name: 'Open canonical Finals Race publication for this cutoff week' })).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Official Ranking history: ranking outage')).toBeInTheDocument()
  })
  it('keeps valid Ranking links when Race history fails', async () => {
    api.getViewerFinalsRace.mockRejectedValue(new Error('race outage'))
    api.listViewerOfficialRankingHistory.mockResolvedValue(savedRankings([rankingPublication()]))
    renderWeek()
    expect(await screen.findByRole('link', { name: 'Ranking publication #1712' })).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Finals Race publications: race outage')).toBeInTheDocument()
  })
  it('does not expose a publication from another Viewer Branch', async () => {
    api.getViewerFinalsRace.mockResolvedValue({ ...savedRace([racePublication()]), viewer_branch_id: 'foreign' })
    renderWeek()
    expect(await screen.findByText('Finals Race source does not match the Saved Calendar Viewer Branch.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open canonical Finals Race publication for this cutoff week' })).not.toBeInTheDocument()
  })
  it('does not accept a publication beyond its public head even when weeks match', async () => {
    api.listViewerOfficialRankingHistory.mockResolvedValue({ ...savedRankings([rankingPublication()]), public_head_ordinal: 1711 })
    renderWeek()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Ranking publication #1712' })).not.toBeInTheDocument()
  })
  it('keeps the Saved week available when both publication readers fail', async () => {
    api.listViewerOfficialRankingHistory.mockRejectedValue(new Error('ranking outage'))
    api.getViewerFinalsRace.mockRejectedValue(new Error('race outage'))
    renderWeek()
    expect(await screen.findByText('Source Open')).toBeInTheDocument()
    expect(eventList().getByRole('link', { name: 'Open planned event' })).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Official Ranking history: ranking outage')).toBeInTheDocument()
    expect(await screen.findByText('Failed to load Finals Race publications: race outage')).toBeInTheDocument()
  })
  it.each(['0', '-1', '1.5', '5abc', '9007199254740992'])('does not call any reader for invalid week %s', week => {
    renderWeek('/viewer/runs/run%20alpha/weeks/' + week)
    for (const reader of [api.getViewerRunCalendar, api.getViewerTournamentHistory, api.listViewerOfficialRankingHistory, api.getViewerFinalsRace]) expect(reader).not.toHaveBeenCalled()
    expect(screen.queryByRole('list', { name: 'Viewer week Saved Calendar events' })).not.toBeInTheDocument()
  })
  it('does not call readers for a missing week', () => {
    renderWeek('/viewer/runs/run%20alpha/week-missing')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.listViewerOfficialRankingHistory).not.toHaveBeenCalled()
    expect(api.getViewerFinalsRace).not.toHaveBeenCalled()
  })
})
