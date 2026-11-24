import { screen, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { calendarEvent, historyEvent, savedCalendar, savedHistory } from '../../../test/viewerCalendarFixtures'
import { expectNoForbiddenViewerActions, renderWithViewerProviders } from '../../../test/viewerTestUtils'
import { ViewerTourDeferredPage } from './ViewerTourDeferredPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  getViewerTournamentResult: vi.fn(),
}))
const selected = vi.hoisted(() => ({ run: 'run alpha' as string | null }))
vi.mock('../../../api/client', () => api)
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => selected.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: run, official_branch_id: 'viewer-branch' },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

describe('ViewerTourDeferredPage public Match Center dispatch', () => {
  beforeEach(() => {
    localStorage.clear()
    selected.run = 'run alpha'
    vi.clearAllMocks()
    const event = calendarEvent()
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar([event]))
    api.getViewerTournamentHistory.mockResolvedValue(savedHistory([
      historyEvent(event, {
        result_published: true, champion_player_id: 'A', finalist_player_id: 'B',
      }),
    ]))
  })

  it('replaces the legacy source-metadata-only Match Center with real published event navigation', async () => {
    renderWithViewerProviders(
      <LanguageProvider><ViewerTourDeferredPage kind="matches" /></LanguageProvider>,
      { includeViewerContext: false },
    )
    const table = await screen.findByRole('table', { name: 'Turnaje s publikovanými výsledky' })
    expect(within(table).getByRole('link', { name: 'Source Open' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVENT%2F1')
    expect(screen.getByText('viewer-branch')).toBeInTheDocument()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('remains read-only and does not query any tournament data without a Product Run', () => {
    selected.run = null
    renderWithViewerProviders(
      <LanguageProvider><ViewerTourDeferredPage kind="matches" /></LanguageProvider>,
      { includeViewerContext: false },
    )
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expect(api.getViewerTournamentResult).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })
})
