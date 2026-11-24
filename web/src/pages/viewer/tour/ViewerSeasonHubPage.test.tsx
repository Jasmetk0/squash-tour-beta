import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import {
  calendarEvent, historyEvent, racePublication, savedCalendar, savedHistory, savedRace,
} from '../../../test/viewerCalendarFixtures'
import { clearViewerStorage, expectNoForbiddenViewerActions, setViewerActiveProductRunId } from '../../../test/viewerTestUtils'
import { ViewerSeasonHubPage } from './ViewerSeasonHubPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  getViewerFinalsRace: vi.fn(),
}))
const active = vi.hoisted(() => ({
  run: 'run alpha', branch: 'viewer-branch',
  pending: false, fetching: false, error: false, refetch: vi.fn(),
}))
vi.mock('../../../api/client', () => api)
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: () => ({
    data: { product_run_id: active.run, official_branch_id: active.branch },
    isPending: active.pending, isFetching: active.fetching,
    isError: active.error, refetch: active.refetch,
  }),
}))
// Signed native season comparison is separately owned/tested; this PR changes
// only the verified legacy Saved Tour summary and its source gating.
vi.mock('./ViewerSignedSeasonComparison', () => ({
  ViewerSignedSeasonComparison: () => null,
}))

const eventA = calendarEvent()
const eventB = calendarEvent({
  event_id: 'EVENT/2', event_name: 'Future Open', season_week: 8,
  start_season_week: 8, end_season_week: 8,
})
const published = historyEvent(eventA, {
  result_published: true, champion_player_id: 'champion', finalist_player_id: 'finalist',
})
function sources(branch = active.branch) {
  return {
    calendar: { ...savedCalendar([eventA, eventB]), viewer_branch_id: branch },
    history: { ...savedHistory([published, historyEvent(eventB)]), viewer_branch_id: branch },
    finals: { ...savedRace([racePublication()]), viewer_branch_id: branch,
      publications: [{ ...racePublication(), viewer_branch_id: branch }] },
  }
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter><ViewerContextProvider>
        <LanguageProvider><ViewerSeasonHubPage /></LanguageProvider>
      </ViewerContextProvider></MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Season Hub joins exact public Saved sources (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    clearViewerStorage()
    vi.clearAllMocks()
    active.run = 'run alpha'
    active.branch = 'viewer-branch'
    active.pending = false
    active.fetching = false
    active.error = false
    const source = sources()
    api.getViewerRunCalendar.mockResolvedValue(source.calendar)
    api.getViewerTournamentHistory.mockResolvedValue(source.history)
    api.getViewerFinalsRace.mockResolvedValue(source.finals)
  })

  it('does not read or render Saved Tour without a Product Run', () => {
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    for (const fn of Object.values(api)) expect(fn).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('requires verified current Run/Branch context before any source GET', async () => {
    setViewerActiveProductRunId('run alpha')
    active.run = 'foreign-run'
    const user = userEvent.setup()
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('nemá ověřenou Viewer Branch')
    for (const fn of Object.values(api)) expect(fn).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(active.refetch).toHaveBeenCalledTimes(1)
  })

  it('shows only matched Saved sources, published event status and verified Finals Race', async () => {
    setViewerActiveProductRunId('run alpha')
    mount()
    expect(await screen.findByText('Future Open')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Přehled uložené Tour' })).toBeInTheDocument()
    expect(screen.getByText('Source Open')).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVENT%2F1')
    expect(screen.getByText('S28 · cutoff S28 W5')).toBeInTheDocument()
    expect(screen.getByText('viewer-branch')).toBeInTheDocument()
    expect(screen.getByText(/2028\/2029 · W8/)).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'W8' })).not.toBeInTheDocument()
    expect(screen.getByText(/nemusí být příští skutečně hraný turnaj/)).toBeInTheDocument()
    for (const fn of Object.values(api)) expect(fn).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('fails closed on a foreign Finals Race or inconsistent Tournament History', async () => {
    setViewerActiveProductRunId('run alpha')
    const good = sources()
    api.getViewerFinalsRace.mockResolvedValueOnce(sources('foreign').finals)
      .mockResolvedValueOnce(good.finals)
    api.getViewerTournamentHistory.mockResolvedValueOnce(good.history)
      .mockResolvedValueOnce({ ...good.history, published_result_count: 99 })
      .mockResolvedValueOnce(good.history)
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná data')
    expect(screen.queryByText('Source Open')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná data')
    expect(screen.queryByText('Future Open')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByText('Future Open')).toBeInTheDocument()
  })

  it('distinguishes genuine empty source from a source read failure', async () => {
    setViewerActiveProductRunId('run alpha')
    api.getViewerRunCalendar.mockResolvedValueOnce(savedCalendar([]))
    api.getViewerTournamentHistory.mockResolvedValueOnce(savedHistory([]))
    api.getViewerFinalsRace.mockResolvedValueOnce(savedRace([]))
    const view = mount()
    expect(await screen.findByText('V uložené Tour nejsou žádné turnaje.')).toBeInTheDocument()
    view.unmount()
    api.getViewerTournamentHistory.mockReset().mockRejectedValue(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('veřejný zdroj není dostupný')
    expect(screen.queryByText('Future Open')).not.toBeInTheDocument()
  })

  it('never displays a late prior-Branch response as the new Branch', async () => {
    setViewerActiveProductRunId('run alpha')
    let resolveOld!: (value: ReturnType<typeof sources>['history']) => void
    api.getViewerTournamentHistory.mockImplementationOnce(() =>
      new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(sources('branch-b').history)
    api.getViewerRunCalendar.mockImplementation(() => Promise.resolve(sources(active.branch).calendar))
    api.getViewerFinalsRace.mockImplementation(() => Promise.resolve(sources(active.branch).finals))
    const view = mount()
    await waitFor(() => expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    view.refresh()
    expect(await screen.findByText('Future Open')).toBeInTheDocument()
    await act(async () => { resolveOld(sources('viewer-branch').history) })
    expect(screen.getByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText('viewer-branch')).not.toBeInTheDocument()
  })

  it('provides English copy without altering source identities or GET volume', async () => {
    setViewerActiveProductRunId('run alpha')
    localStorage.setItem('squash-engine-language-v1', 'en')
    mount()
    expect(await screen.findByText('Future Open')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Season Hub' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Product Run tournaments' })).toBeInTheDocument()
    for (const fn of Object.values(api)) expect(fn).toHaveBeenCalledTimes(1)
  })
})
