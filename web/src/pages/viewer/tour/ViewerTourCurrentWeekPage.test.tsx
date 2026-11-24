import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { ViewerContextProvider, VIEWER_CONTEXT_STORAGE_KEY } from '../../../viewer/ViewerContext'
import {
  clearViewerStorage, expectNoForbiddenViewerActions, setViewerActiveProductRunId,
} from '../../../test/viewerTestUtils'
import { ViewerCurrentWeekPage } from './ViewerTourCurrentWeekPage'

const api = vi.hoisted(() => ({ getViewerRunCalendar: vi.fn() }))
const active = vi.hoisted(() => ({
  run: 'run alpha',
  branch: 'branch-tour',
  pending: false,
  fetching: false,
  error: false,
  refetch: vi.fn(),
}))

vi.mock('../../../api/client', () => api)
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: () => ({
    data: { product_run_id: active.run, official_branch_id: active.branch },
    isPending: active.pending,
    isFetching: active.fetching,
    isError: active.error,
    refetch: active.refetch,
  }),
}))

function savedCalendar(branch = active.branch) {
  return {
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: 'run alpha',
    viewer_branch_id: branch,
    season_count: 1,
    event_count: 1,
    seasons: [{
      season: '2004/05',
      event_count: 1,
      events: [{
        event_id: 'EVT-5', season: '2004/05', season_week: 10,
        calendar_year: 2000, year_week: 1, template_id: 'tmpl',
        event_name: 'Week Ten Open', category: 'Gold',
        tour_level: 'WORLD_TOUR', host_country: 'CZE', host_city: 'Prague',
        region: 'Europe', duration_in_season_weeks: 1,
        start_season_week: 10, end_season_week: 10, status: 'planned',
        main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8,
        qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80,
      }],
    }],
  }
}

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter>
        <ViewerContextProvider>
          <LanguageProvider><ViewerCurrentWeekPage /></LanguageProvider>
        </ViewerContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Viewer Current Week requires exact Saved Run/Branch evidence (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    clearViewerStorage()
    localStorage.removeItem(VIEWER_CONTEXT_STORAGE_KEY)
    vi.clearAllMocks()
    active.run = 'run alpha'
    active.branch = 'branch-tour'
    active.pending = false
    active.fetching = false
    active.error = false
    api.getViewerRunCalendar.mockResolvedValue(savedCalendar())
  })

  it('does not request calendar without an active Product Run', () => {
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows only verified Saved events for the selected week with canonical links', async () => {
    setViewerActiveProductRunId('run alpha')
    mount()
    expect(await screen.findByText('Week Ten Open')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('run alpha')
    expect(screen.getByRole('link', { name: 'Week Ten Open' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT-5')
    expect(screen.getByText('branch-tour')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Vybraný týden' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows ongoing multi-week calendar events without including past or future events', async () => {
    setViewerActiveProductRunId('run alpha')
    const source = savedCalendar()
    const event = source.seasons[0].events[0]
    const events = [
      { ...event, event_id: 'ongoing', event_name: 'Ongoing Open', season_week: 9,
        start_season_week: 9, end_season_week: 11, duration_in_season_weeks: 3 },
      { ...event, event_id: 'last-day', event_name: 'Final Week Open', season_week: 9,
        start_season_week: 9, end_season_week: 10, duration_in_season_weeks: 2 },
      { ...event, event_id: 'past', event_name: 'Past Open', season_week: 8,
        start_season_week: 8, end_season_week: 9, duration_in_season_weeks: 2 },
      { ...event, event_id: 'future', event_name: 'Future Open', season_week: 11,
        start_season_week: 11, end_season_week: 11 },
      event,
    ]
    api.getViewerRunCalendar.mockResolvedValueOnce({
      ...source, event_count: events.length,
      seasons: [{ ...source.seasons[0], events, event_count: events.length }],
    })
    mount()
    expect(await screen.findByRole('link', { name: 'Ongoing Open' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/ongoing')
    expect(screen.getByRole('link', { name: 'Final Week Open' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Week Ten Open' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Past Open' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Future Open' })).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('does not query an unverified or foreign saved Viewer Branch', async () => {
    setViewerActiveProductRunId('run alpha')
    active.run = 'foreign-run'
    const user = userEvent.setup()
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('neodpovídá')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(active.refetch).toHaveBeenCalledTimes(1)
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
  })

  it('rejects a foreign Branch or corrupt event count instead of rendering its rows', async () => {
    setViewerActiveProductRunId('run alpha')
    api.getViewerRunCalendar.mockResolvedValueOnce(savedCalendar('foreign-branch'))
      .mockResolvedValueOnce({ ...savedCalendar(), event_count: 7 })
      .mockResolvedValueOnce(savedCalendar())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná veřejná data')
    expect(screen.queryByText('Week Ten Open')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatná veřejná data')
    expect(screen.queryByText('Week Ten Open')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByText('Week Ten Open')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(3)
  })

  it('distinguishes a real empty selected week from GET failure', async () => {
    setViewerActiveProductRunId('run alpha')
    api.getViewerRunCalendar.mockResolvedValueOnce({
      ...savedCalendar(), season_count: 0, event_count: 0, seasons: [],
    })
    const view = mount()
    expect(await screen.findByText('Pro tento vybraný týden nejsou v uloženém kalendáři žádné události.')).toBeInTheDocument()
    view.unmount()

    api.getViewerRunCalendar.mockReset().mockRejectedValue(new Error('offline'))
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Uložený kalendář není dostupný')
    expect(screen.queryByText('Week Ten Open')).not.toBeInTheDocument()
  })

  it('does not display delayed data from a previous Viewer Branch after a source switch', async () => {
    setViewerActiveProductRunId('run alpha')
    let resolveOld!: (value: ReturnType<typeof savedCalendar>) => void
    api.getViewerRunCalendar.mockImplementationOnce(() =>
      new Promise(resolve => { resolveOld = resolve }))
      .mockResolvedValueOnce(savedCalendar('branch-b'))
    const view = mount()
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    view.refresh()
    expect(await screen.findByText('Week Ten Open')).toBeInTheDocument()
    await act(async () => { resolveOld(savedCalendar('branch-tour')) })
    expect(screen.getByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText('branch-tour')).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('localizes its own labels in English without changing public event identity', async () => {
    setViewerActiveProductRunId('run alpha')
    localStorage.setItem('squash-engine-language-v1', 'en')
    mount()
    expect(await screen.findByText('Week Ten Open')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Current Week' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Product Run schedule' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })
})
