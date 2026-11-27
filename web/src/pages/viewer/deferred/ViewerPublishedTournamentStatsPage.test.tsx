import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerStatsDeferredPage } from './ViewerStatsDeferredPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(), getViewerTournamentHistory: vi.fn(),
}))
const active = vi.hoisted(() => ({
  run: 'run alpha' as string | null, branch: 'branch-a', foreign: false,
}))
vi.mock('../../../api/client', () => ({
  ...api, ApiError: class ApiError extends Error {},
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => active.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: active.foreign ? 'other' : run, official_branch_id: active.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

type Event = ReturnType<typeof event>
function event(n: number, season: string, category: string, host: string, winner: string | null) {
  return {
    event_id: 'event ' + n, season, season_week: n,
    calendar_year: 2031, year_week: 35, template_id: 'template-' + n,
    event_name: 'Open ' + n, category, tour_level: 'WORLD_TOUR',
    host_country: host, host_city: 'Brno', region: 'Europe',
    duration_in_season_weeks: 1, start_season_week: n, end_season_week: n,
    status: winner === null ? 'planned' : 'completed',
    main_draw_size: 32, qualification_draw_size: 16,
    seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80,
    winner,
  }
}
const examples = [
  event(1, '2030/31', 'GOLD', 'CZE', 'player-a'),
  event(2, '2031/32', 'GOLD', 'CZE', null),
  event(3, '2031/32', 'GOLD', 'EGY', 'player-a'),
  event(4, '2031/32', 'GOLD', 'EGY', 'player-b'),
  event(5, '2031/32', 'PLATINUM', 'CZE', 'player-c'),
]
function saved(events: Event[] = examples, run = active.run ?? '', branch = active.branch) {
  const groups = new Map<string, Event[]>()
  for (const e of events) groups.set(e.season, [...(groups.get(e.season) ?? []), e])
  return {
    calendar: {
      schema_version: 'viewer_run_calendar.v1',
      product_run_id: run, viewer_branch_id: branch,
      season_count: groups.size, event_count: events.length,
      seasons: [...groups].map(([season, es]) => ({ season, event_count: es.length, events: es })),
    },
    history: {
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: run, viewer_branch_id: branch,
      tournament_count: events.length,
      published_result_count: events.filter(e => e.winner !== null).length,
      tournaments: events.map(e => ({
        event_id: e.event_id, season: e.season, season_week: e.season_week,
        event_name: e.event_name, template_id: e.template_id,
        category: e.category, tour_level: e.tour_level, host_country: e.host_country,
        host_city: e.host_city, region: e.region,
        main_draw_size: e.main_draw_size, qualification_draw_size: e.qualification_draw_size,
        seeds_count: e.seeds_count, qualifier_spots: e.qualifier_spots,
        wild_cards: e.wild_cards, byes: e.byes,
        ranking_status: e.winner ? 'ranked' : 'planned',
        result_published: e.winner !== null,
        champion_player_id: e.winner,
        finalist_player_id: e.winner ? 'finalist ' + e.event_id : null,
      })),
    },
  }
}
function ToggleLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount() {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return <QueryClientProvider client={client}>
      <MemoryRouter><LanguageProvider>
        <ToggleLanguage /><ViewerStatsDeferredPage kind="tournament-stats" />
      </LanguageProvider></MemoryRouter>
    </QueryClientProvider>
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Tournament Stats from verified Saved public tournament calendar and results (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'branch-a'; active.foreign = false
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      Promise.resolve(saved(examples, run, active.branch).calendar))
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(saved(examples, run, active.branch).history))
  })

  it('does not fetch or invent a saved source without a Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('does not request calendar or results under a foreign Viewer context', () => {
    active.foreign = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('Nelze ověřit Viewer Branch')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
  })

  it('separates scheduled, completed, published, unique winners and hosting countries using exact saved facts', async () => {
    mount()
    const table = await screen.findByRole('table', { name: 'Statistiky turnajů podle sezony a kategorie' })
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    const gold = within(table).getByRole('row', { name: /2031\/32 GOLD/ })
    const cells = within(gold).getAllByRole('cell')
    expect(cells[2]).toHaveTextContent('3')
    expect(cells[3]).toHaveTextContent('2')
    expect(cells[4]).toHaveTextContent('2')
    expect(cells[5]).toHaveTextContent('2')
    expect(cells[6]).toHaveTextContent('2')
    expect(within(gold).getByRole('link', { name: 'Open 4' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/event%204')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText(/Dokončený kalendářní turnaj a publikovaný výsledek/)).toBeInTheDocument()
    expect(screen.getByText(/včetně zrušených turnajů/)).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'Nejpozdější turnaj podle rozpisu' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('filters by actual saved season, category and host with deterministic reset and no extra GET', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Sezona'), '2031/32')
    await user.selectOptions(screen.getByLabelText('Kategorie'), 'GOLD')
    await user.selectOptions(screen.getByLabelText('Pořadatelská země'), 'EGY')
    const table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    const gold = within(table).getByRole('row', { name: /2031\/32 GOLD/ })
    const cells = within(gold).getAllByRole('cell')
    expect(cells[2]).toHaveTextContent('2')
    expect(cells[3]).toHaveTextContent('2')
    expect(cells[4]).toHaveTextContent('2')
    expect(cells[5]).toHaveTextContent('2')
    expect(cells[6]).toHaveTextContent('1')
    await user.selectOptions(screen.getByLabelText('Sezona'), '2030/31')
    expect(screen.getByText('Filtrům neodpovídají žádné turnaje.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(4)
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('shows a valid empty calendar separately from unpublished tournaments', async () => {
    const noResults = [event(2, '2031/32', 'GOLD', 'CZE', null)]
    api.getViewerRunCalendar.mockReset().mockResolvedValue(saved(noResults).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(saved(noResults).history)
    const first = mount()
    const table = await screen.findByRole('table', { name: 'Statistiky turnajů podle sezony a kategorie' })
    const row = within(table).getByRole('row', { name: /2031\/32 GOLD/ })
    expect(within(row).getAllByRole('cell')[4]).toHaveTextContent('0')
    first.unmount()

    api.getViewerRunCalendar.mockReset().mockResolvedValue(saved([]).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(saved([]).history)
    mount()
    expect(await screen.findByText('Kalendář této Viewer Branch neobsahuje turnaje.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('fails closed for cross-branch, mismatched publication counts and invalid winners; GET retry recovers', async () => {
    const user = userEvent.setup()
    const valid = saved()
    api.getViewerRunCalendar.mockReset().mockResolvedValue(valid.calendar)
    api.getViewerTournamentHistory.mockReset()
      .mockResolvedValueOnce({ ...valid.history, viewer_branch_id: 'foreign-branch' })
      .mockResolvedValueOnce({ ...valid.history, published_result_count: 999 })
      .mockResolvedValueOnce({
        ...valid.history, tournaments: valid.history.tournaments.map((item, i) =>
          i === 0 ? { ...item, finalist_player_id: item.champion_player_id } : item),
      })
      .mockResolvedValueOnce(valid.history)
    mount()
    for (let i = 0; i < 3; i++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídají')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('never renders a delayed response from an older Viewer Branch', async () => {
    let resolveOld: ((value: ReturnType<typeof saved>['calendar']) => void) | undefined
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      active.branch === 'branch-a'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(saved(examples, run, 'branch-b').calendar))
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(saved(examples, run, active.branch).history))
    const view = mount()
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    await act(async () => view.refresh())
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(saved(examples, 'run alpha', 'branch-a').calendar) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('localizes static text without rewriting IDs or refetching public history', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Saved Tournament Stats' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Tournament statistics by season and category' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open 4' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('paginates more than 25 season/category rows and resets page when filters change', async () => {
    const many = Array.from({ length: 32 }, (_, i) =>
      event(i + 1, '2031/32', 'CAT' + String(i).padStart(2, '0'), 'CZE', 'player-' + i))
    api.getViewerRunCalendar.mockReset().mockResolvedValue(saved(many).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(saved(many).history)
    const user = userEvent.setup()
    mount()
    expect(await screen.findByText('Zobrazeno 1–25 z 32')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 26–32 z 32')).toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Kategorie'), 'CAT31')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open 32' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
