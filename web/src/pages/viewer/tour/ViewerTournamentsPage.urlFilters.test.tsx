import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions, makeViewerProductRunRouteTestValue } from '../../../test/viewerTestUtils'
import { ViewerProductRunRouteContextProvider } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerTournamentDetailPath } from '../../../viewer/viewerRoutes'
import { ViewerRunTournamentArchive } from './ViewerRunTournamentArchive'
import { ViewerTournamentsPage } from './ViewerTournamentsPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn()
}))
const source = vi.hoisted(() => ({ run: 'run alpha', branch: 'branch-tour' }))
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => source.run
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: run, official_branch_id: source.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn()
  })
}))

function event(n: number, season: string) {
  return {
    event_id: 'EVT ' + String(n).padStart(3, '0'),
    season, season_week: n, calendar_year: 2031, year_week: 40,
    template_id: 'template-' + n, event_name: 'Open ' + String(n).padStart(3, '0'),
    category: 'GOLD', tour_level: 'WORLD_TOUR', host_country: 'CZE',
    host_city: n === 2 ? 'Brno' : 'Praha', region: 'Europe',
    duration_in_season_weeks: 1, start_season_week: n, end_season_week: n,
    status: 'planned', main_draw_size: 32, qualification_draw_size: 16,
    seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80
  }
}
const events = [event(1, '2030/31'), event(2, '2031/32'), event(3, '2031/32')]
function fixtures(run = source.run, branch = source.branch) {
  return {
    calendar: {
      schema_version: 'viewer_run_calendar.v1', product_run_id: run,
      viewer_branch_id: branch, season_count: 2, event_count: 3,
      seasons: [
        { season: '2030/31', event_count: 1, events: [events[0]] },
        { season: '2031/32', event_count: 2, events: events.slice(1) }
      ]
    },
    history: {
      schema_version: 'viewer_tournament_history.v1', product_run_id: run,
      viewer_branch_id: branch, tournament_count: 3, published_result_count: 1,
      tournaments: events.map(e => ({
        event_id: e.event_id, season: e.season, season_week: e.season_week,
        event_name: e.event_name, template_id: e.template_id,
        category: e.category, tour_level: e.tour_level, host_country: e.host_country,
        host_city: e.host_city, region: e.region, main_draw_size: e.main_draw_size,
        qualification_draw_size: e.qualification_draw_size, seeds_count: e.seeds_count,
        qualifier_spots: e.qualifier_spots, wild_cards: e.wild_cards, byes: e.byes,
        ranking_status: e.season_week === 2 ? 'ranked' : 'planned',
        result_published: e.season_week === 2,
        champion_player_id: e.season_week === 2 ? 'winner EVT 002' : null,
        finalist_player_id: e.season_week === 2 ? 'finalist EVT 002' : null
      }))
    }
  }
}
function Navigation(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  return <>
    <output aria-label="Current URL">{location.pathname}{location.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <button type="button" onClick={() => navigate(1)}>Forward</button>
  </>
}
function mount(url = '/viewer/tour/tournaments?keep=one&keep=two') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[url]}>
          <LanguageProvider><Navigation /><ViewerTournamentsPage /></LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, client, refresh: () => view.rerender(<App />) }
}
function params(): URLSearchParams {
  const text = screen.getByLabelText('Current URL').textContent ?? ''
  return new URLSearchParams(text.split('?')[1] ?? '')
}

describe('Viewer saved tournament URL filters (mocked GET, not HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    source.run = 'run alpha'
    source.branch = 'branch-tour'
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      Promise.resolve(fixtures(run).calendar))
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(fixtures(run).history))
  })

  it('opens an exact published tournament from a multi-filter direct link', async () => {
    mount('/viewer/tour/tournaments?keep=one&keep=two&vtSeason=2031%2F32&vtQ=Brno&vtResult=published')
    const table = await screen.findByRole('table', { name: 'Uložené turnaje' })
    expect(screen.getByLabelText('Filtrovat sezonu')).toHaveValue('2031/32')
    expect(screen.getByLabelText('Hledat turnaj, ID nebo místo')).toHaveValue('Brno')
    expect(screen.getByLabelText('Stav zveřejnění výsledku')).toHaveValue('published')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('link', { name: 'Open 002' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT%20002')
    expect(within(table).getByRole('link', { name: 'winner EVT 002' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/winner%20EVT%20002/career')
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expectNoForbiddenViewerActions()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('carries the exact public archive filters into the actual Run archive route', async () => {
    const user = userEvent.setup()
    const context = makeViewerProductRunRouteTestValue(source.run)
    const value = { ...context, officialBranchId: source.branch,
      officialContext: { ...context.officialContext, product_run_id: source.run, official_branch_id: source.branch } }
    render(<QueryClientProvider client={createTestQueryClient()}>
      <MemoryRouter initialEntries={['/viewer/tour/tournaments?vtSeason=2031%2F32&vtQ=template-2&vtResult=published&keep=yes']}>
        <LanguageProvider><Navigation /><Routes>
          <Route path="/viewer/tour/tournaments" element={<ViewerTournamentsPage />} />
          <Route path="/viewer/runs/:runId/tournaments" element={<ViewerProductRunRouteContextProvider value={value}>
            <ViewerRunTournamentArchive detailPath={viewerTournamentDetailPath} />
          </ViewerProductRunRouteContextProvider>} />
        </Routes></LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>)
    expect(await screen.findByRole('link', { name: 'Open 002' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open 003' })).not.toBeInTheDocument()
    const link = screen.getByRole('link', { name: 'Otevřít turnaje Runu' })
    expect(link).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments?vtSeason=2031%2F32&vtQ=template-2&vtResult=published&keep=yes')
    await user.click(link)
    expect(await screen.findByRole('heading', { name: 'Kanonická historie turnajů' })).toBeInTheDocument()
    expect(await screen.findByText('Open 002')).toBeInTheDocument()
    expect(screen.queryByText('Open 003')).not.toBeInTheDocument()
    expect(params().get('vtQ')).toBe('template-2')
    expect(params().get('keep')).toBe('yes')
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('restores a deep-linked page of a 60-event catalog without repeat GETs', async () => {
    const raw = fixtures()
    const rows = Array.from({ length: 60 }, (_, i) => event(i + 1, '2031/32'))
    api.getViewerRunCalendar.mockResolvedValue({ ...raw.calendar, season_count: 1, event_count: rows.length,
      seasons: [{ season: '2031/32', event_count: rows.length, events: rows }] })
    api.getViewerTournamentHistory.mockResolvedValue({ ...raw.history, tournament_count: rows.length, published_result_count: 0,
      tournaments: rows.map(e => ({ ...raw.history.tournaments[0], event_id: e.event_id, season: e.season,
        season_week: e.season_week, template_id: e.template_id, event_name: e.event_name, host_city: e.host_city })) })
    const user = userEvent.setup()
    mount('/viewer/tour/tournaments?vtPage=2&keep=yes')
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    expect(within(table).getByRole('link', { name: 'Open 026' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(params().get('vtPage')).toBe('3')
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(params().get('vtPage')).toBe('2')
    expect(within(table).getByRole('link', { name: 'Open 026' })).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Filtrovat sezonu'), '2031/32')
    expect(params().get('vtPage')).toBeNull()
    expect(params().get('keep')).toBe('yes')
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it.each(['vtPage=2', 'vtPage=01', 'vtPage=1&vtPage=1'])(
    'withholds the catalog for invalid or ambiguous page links: %s', async page => {
      mount('/viewer/tour/tournaments?' + page + '&keep=yes')
      expect(await screen.findByRole('alert')).toHaveTextContent('neplatnou nebo nedostupnou hodnotu')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await userEvent.setup().click(screen.getByRole('button', { name: 'Vymazat filtry' }))
      expect(await screen.findByRole('table')).toBeInTheDocument()
      expect(params().toString()).toBe('keep=yes')
    }
  )

  it('restores Back/Forward and removes only owned parameters on reset', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Filtrovat sezonu'), '2031/32')
    await user.type(screen.getByLabelText('Hledat turnaj, ID nebo místo'), 'Brno')
    expect(params().get('vtQ')).toBe('Brno')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(params().get('vtSeason')).toBe(null)
    expect(params().get('vtQ')).toBe(null)
    expect(screen.getByLabelText('Filtrovat sezonu')).toHaveValue('all')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByLabelText('Hledat turnaj, ID nebo místo')).toHaveValue('Brno')
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect([...params().keys()]).toEqual(['keep', 'keep'])
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('rejects unknown publication/season filters instead of silently showing all', async () => {
    const user = userEvent.setup()
    mount('/viewer/tour/tournaments?tracking=alpha&vtSeason=undefined&vtResult=maybe')
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatnou nebo nedostupnou hodnotu')
    expect(screen.getByLabelText('Filtrovat sezonu')).toHaveValue('undefined')
    expect(screen.getByLabelText('Stav zveřejnění výsledku')).toHaveValue('maybe')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(params().toString()).toBe('tracking=alpha')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('drops only old filters when Run or Viewer Branch changes', async () => {
    const view = mount('/viewer/tour/tournaments?keep=yes&vtResult=published&vtSeason=2031%2F32')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    source.branch = 'branch-b'
    await act(async () => view.refresh())
    await waitFor(() => expect(screen.getByText('branch-b')).toBeInTheDocument())
    await waitFor(() => expect(params().get('vtSeason')).toBe(null))
    expect(params().get('vtResult')).toBe(null)
    expect(params().get('keep')).toBe('yes')
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()

    source.run = 'run beta'
    await act(async () => view.refresh())
    expect(await screen.findByText('run beta')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(3)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(3)
    expectNoForbiddenViewerActions()
  })

  it('recreates filtered views from a fresh mount with the existing saved source only', async () => {
    const url = '/viewer/tour/tournaments?vtResult=unpublished&vtSeason=2031%2F32'
    const first = mount(url)
    expect(await screen.findByRole('table')).toHaveTextContent('Open 003')
    expect(screen.queryByRole('link', { name: 'Open 002' })).not.toBeInTheDocument()
    first.unmount()
    mount(url)
    expect(await screen.findByRole('table')).toHaveTextContent('Open 003')
    expect(screen.getByLabelText('Stav zveřejnění výsledku')).toHaveValue('unpublished')
  })

  it('rejects duplicate owned filters without discarding unrelated URL parameters', async () => {
    mount('/viewer/tour/tournaments?vtResult=published&vtResult=unpublished&keep=one&keep=two')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expect([...params().keys()]).toEqual(['keep', 'keep'])
  })

  it('withholds the entire catalog while either saved source is refetching', async () => {
    const view = mount()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    let release!: (value: ReturnType<typeof fixtures>['history']) => void
    api.getViewerTournamentHistory.mockImplementationOnce(() => new Promise(resolve => { release = resolve }))
    const refresh = view.client.invalidateQueries({ queryKey: ['viewer-tournaments-history', source.run, source.branch] })
    await waitFor(() => expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByRole('table')).not.toBeInTheDocument())
    await act(async () => { release(fixtures().history); await refresh })
    expect(await screen.findByRole('table')).toBeInTheDocument()
  })

})
