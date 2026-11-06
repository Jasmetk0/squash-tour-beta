import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { clearViewerStorage, expectNoForbiddenViewerActions, renderWithViewerProviders, setViewerActiveRunId } from '../../../test/viewerTestUtils'
import { calendarEvent, historyEvent, savedCalendar, savedHistory, savedRankings, savedRace } from '../../../test/viewerCalendarFixtures'
import { ViewerStatsPage } from './ViewerStatsPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  listViewerOfficialRankingHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
  getFinalsSummary: vi.fn(),
  getRunStatusSummary: vi.fn(),
  listEvents: vi.fn(),
  listRaceSnapshots: vi.fn(),
  listRankingSnapshots: vi.fn()
}))

vi.mock('../../../api/client', () => api)


function renderStats(): void {
  renderWithViewerProviders(<ViewerStatsPage />)
}

function resetApiMocks(): void {
  const event = calendarEvent({ event_id: 'EVT-3', event_name: 'Stats Open' })
  api.getViewerRunCalendar.mockResolvedValue(savedCalendar([event], 'stats run'))
  api.getViewerTournamentHistory.mockResolvedValue(savedHistory([historyEvent(event, { result_published: true, champion_player_id: 'CHAMPION', finalist_player_id: 'FINALIST' })], 'stats run'))
  api.listViewerOfficialRankingHistory.mockResolvedValue({ ...savedRankings(), product_run_id: 'stats run' })
  api.getViewerFinalsRace.mockResolvedValue({ ...savedRace(), product_run_id: 'stats run' })
}

describe('ViewerStatsPage', () => {
  beforeEach(() => {
    clearViewerStorage()
    vi.clearAllMocks()
    resetApiMocks()
  })

  it('renders the no-active-run landing without forbidden Viewer action labels', () => {
    renderStats()

    expect(screen.getByRole('heading', { level: 2, name: 'Stats' })).toBeInTheDocument()
    expect(screen.getByText('Stats library destination prepared for connected run-scoped statistical read models.')).toBeInTheDocument()
    expect(screen.getByText('No Product Run is selected yet.')).toBeInTheDocument()

    expectNoForbiddenViewerActions()
  })

  it('renders active-run source metadata, deferred groups, and encoded links', async () => {
    setViewerActiveRunId('stats run')

    renderStats()

    expect(await screen.findByText('Stats Overview')).toBeInTheDocument()
    expect(screen.getByText('stats run')).toBeInTheDocument()
    expect(screen.getByText('Completed tournaments')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Stats Open' })).toHaveAttribute('href', '/viewer/runs/stats%20run/tournaments/EVT-3')
    for (const legacy of [api.getFinalsSummary, api.getRunStatusSummary, api.listEvents, api.listRankingSnapshots, api.listRaceSnapshots]) expect(legacy).not.toHaveBeenCalled()

    const deferredText = screen.getByRole('list', { name: 'Deferred stat groups' }).textContent ?? ''
    expect(deferredText.indexOf('Player Stats')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Tournament Stats')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Country Stats')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Awards')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Hall of Fame')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Era Rankings')).toBeGreaterThanOrEqual(0)
    expect(deferredText.indexOf('Player Stats')).toBeLessThan(deferredText.indexOf('Tournament Stats'))
    expect(deferredText.indexOf('Tournament Stats')).toBeLessThan(deferredText.indexOf('Country Stats'))
    expect(deferredText.indexOf('Country Stats')).toBeLessThan(deferredText.indexOf('Awards'))
    expect(deferredText.indexOf('Awards')).toBeLessThan(deferredText.indexOf('Hall of Fame'))
    expect(deferredText.indexOf('Hall of Fame')).toBeLessThan(deferredText.indexOf('Era Rankings'))
    expect(screen.getByRole('link', { name: 'Open active run race' })).toHaveAttribute('href', '/viewer/runs/stats%20run/race')
  })
})
