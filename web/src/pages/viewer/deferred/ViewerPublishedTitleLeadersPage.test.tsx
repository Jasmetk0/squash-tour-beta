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
  run: 'run alpha' as string | null, branch: 'branch-a', foreignContext: false,
}))
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => active.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: {
      product_run_id: active.foreignContext ? 'foreign' : run,
      official_branch_id: active.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

type Event = ReturnType<typeof event>
function event(index: number, season = '2031/32', category = 'GOLD', winner: string | null = 'player-a') {
  return {
    event_id: 'event ' + index, season, season_week: index,
    calendar_year: 2031, year_week: 30, template_id: 'template-' + index,
    event_name: 'Open ' + index, category, tour_level: 'WORLD_TOUR',
    host_country: 'CZE', host_city: 'Brno', region: 'Europe',
    duration_in_season_weeks: 1, start_season_week: index, end_season_week: index,
    status: winner === null ? 'planned' : 'completed',
    main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8,
    qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80,
    winner,
  }
}
const examples = [
  event(1, '2030/31', 'GOLD', 'player-a'),
  event(2, '2031/32', 'PLATINUM', 'player-b'),
  event(3, '2031/32', 'GOLD', null),
  event(4, '2031/32', 'GOLD', 'player-a'),
  event(5, '2031/32', 'GOLD', 'player-b'),
]
function sources(events: Event[] = examples, run = active.run ?? '', branch = active.branch) {
  const bySeason = new Map<string, Event[]>()
  for (const e of events) bySeason.set(e.season, [...(bySeason.get(e.season) ?? []), e])
  const published = events.filter(e => e.winner !== null)
  return {
    calendar: {
      schema_version: 'viewer_run_calendar.v1', product_run_id: run,
      viewer_branch_id: branch, season_count: bySeason.size,
      event_count: events.length,
      seasons: [...bySeason].map(([season, es]) => ({
        season, event_count: es.length, events: es,
      })),
    },
    history: {
      schema_version: 'viewer_tournament_history.v1', product_run_id: run,
      viewer_branch_id: branch, tournament_count: events.length,
      published_result_count: published.length,
      tournaments: events.map(e => ({
        event_id: e.event_id, season: e.season, season_week: e.season_week,
        event_name: e.event_name, template_id: e.template_id,
        category: e.category, tour_level: e.tour_level,
        host_country: e.host_country, host_city: e.host_city, region: e.region,
        main_draw_size: e.main_draw_size,
        qualification_draw_size: e.qualification_draw_size, seeds_count: e.seeds_count,
        qualifier_spots: e.qualifier_spots, wild_cards: e.wild_cards, byes: e.byes,
        ranking_status: e.winner ? 'ranked' : 'planned',
        result_published: e.winner !== null,
        champion_player_id: e.winner, finalist_player_id: e.winner ? 'finalist-' + e.event_id : null,
      })),
    },
  }
}
function LanguageToggle(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount() {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LanguageProvider>
            <LanguageToggle />
            <ViewerStatsDeferredPage kind="title-leaders" />
          </LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function leaderboard() {
  return screen.getByRole('table', { name: 'Pořadí publikovaných vítězů' })
}

describe('Title leaders derived from the verified Saved public tournament history (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'
    active.branch = 'branch-a'
    active.foreignContext = false
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      Promise.resolve(sources(examples, run, active.branch).calendar))
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(sources(examples, run, active.branch).history))
  })

  it('does not request public data until a Product Run is selected', () => {
    active.run = null
    mount()
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' }))
      .toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('does not fetch under a foreign context Run', () => {
    active.foreignContext = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('není pro vybraný Run ověřená')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
  })

  it('ranks actual published wins, excludes unpublished, and links exact player and latest event IDs', async () => {
    mount()
    const table = await screen.findByRole('table', { name: 'Pořadí publikovaných vítězů' })
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    const a = within(table).getByRole('row', { name: /player-a/ })
    const b = within(table).getByRole('row', { name: /player-b/ })
    expect(a).toHaveTextContent('2')
    expect(b).toHaveTextContent('2')
    expect(within(a).getByRole('link', { name: 'player-a' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/player-a/career')
    expect(within(a).getByRole('link', { name: 'Open 4' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/event%204')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText(/ne o úplný kariérní rekord/)).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('filters by stored season, category and champion ID with no additional GETs', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table', { name: 'Pořadí publikovaných vítězů' })
    await user.selectOptions(screen.getByLabelText('Sezona'), '2030/31')
    expect(within(leaderboard()).getAllByRole('row')).toHaveLength(2)
    expect(within(leaderboard()).getByRole('link', { name: 'player-a' })).toBeInTheDocument()
    expect(within(leaderboard()).queryByRole('link', { name: 'player-b' })).not.toBeInTheDocument()
    await user.selectOptions(screen.getByLabelText('Sezona'), '2031/32')
    await user.selectOptions(screen.getByLabelText('Kategorie'), 'PLATINUM')
    expect(within(leaderboard()).getByRole('link', { name: 'player-b' })).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat ID vítěze'), 'player-a')
    expect(screen.getByText('Filtrům neodpovídá žádný publikovaný vítěz.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–2 z 2')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('reports genuinely unpublished history separately from an empty calendar', async () => {
    const unpublished = [event(1, '2030/31', 'GOLD', null)]
    api.getViewerRunCalendar.mockReset().mockResolvedValue(sources(unpublished).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(sources(unpublished).history)
    const first = mount()
    expect(await screen.findByText('Zatím není publikován žádný vítěz.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    first.unmount()
    api.getViewerRunCalendar.mockReset().mockResolvedValue(sources([]).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(sources([]).history)
    mount()
    expect(await screen.findByText('Zatím není publikován žádný vítěz.')).toBeInTheDocument()
  })

  it('rejects wrong Viewer Branch, inconsistent counts and self-referential finals instead of fabricating leaders', async () => {
    const user = userEvent.setup()
    const valid = sources()
    api.getViewerRunCalendar.mockReset().mockResolvedValue(valid.calendar)
    api.getViewerTournamentHistory.mockReset()
      .mockResolvedValueOnce({ ...valid.history, viewer_branch_id: 'wrong' })
      .mockResolvedValueOnce({ ...valid.history, published_result_count: 999 })
      .mockResolvedValueOnce({
        ...valid.history,
        tournaments: valid.history.tournaments.map((p, i) =>
          i === 0 ? { ...p, finalist_player_id: p.champion_player_id } : p),
      })
      .mockResolvedValueOnce(valid.history)
    mount()
    for (let index = 0; index < 3; index++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('se neshodují')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    }
    expect(await screen.findByRole('table', { name: 'Pořadí publikovaných vítězů' })).toBeInTheDocument()
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('never shows an old Branch response after a Viewer Branch switch', async () => {
    let resolveOld: ((value: ReturnType<typeof sources>['calendar']) => void) | undefined
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      active.branch === 'branch-a' ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(sources(examples, run, 'branch-b').calendar))
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(sources(examples, run, active.branch).history))
    const view = mount()
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    await act(async () => { view.refresh() })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(sources(examples, 'run alpha', 'branch-a').calendar) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('switches CS/EN without translating immutable ID or refetching from the public API', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table', { name: 'Pořadí publikovaných vítězů' })
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Leaders by published titles' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Published title leaderboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'player-a' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('paginates a long list deterministically and resets page on filter change', async () => {
    const many = Array.from({ length: 32 }, (_, i) => event(i + 1, '2031/32', 'GOLD', 'player-' + i))
    api.getViewerRunCalendar.mockReset().mockResolvedValue(sources(many).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(sources(many).history)
    const user = userEvent.setup()
    mount()
    expect(await screen.findByText('Zobrazeno 1–25 z 32')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 26–32 z 32')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat ID vítěze'), 'player-31')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'player-31' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('keeps the original title-leader position after search while season/category changes the ranking scope', async () => {
    const events = [
      event(1, '2030/31', 'GOLD', 'player-a'),
      event(2, '2030/31', 'GOLD', 'player-a'),
      event(3, '2031/32', 'GOLD', 'player-a'),
      event(4, '2031/32', 'GOLD', 'player-b'),
      event(5, '2031/32', 'GOLD', 'player-b'),
      event(6, '2031/32', 'PLATINUM', 'player-c'),
    ]
    api.getViewerRunCalendar.mockResolvedValue(sources(events).calendar)
    api.getViewerTournamentHistory.mockResolvedValue(sources(events).history)
    const user = userEvent.setup()
    mount()
    const table = await screen.findByRole('table', { name: 'Pořadí publikovaných vítězů' })
    const position = (name: string) => within(within(table).getByRole('row', { name: new RegExp(name) })).getAllByRole('cell')[0]
    expect(position('player-b')).toHaveTextContent(/^2$/)
    await user.type(screen.getByLabelText('Hledat ID vítěze'), 'player-b')
    expect(position('player-b')).toHaveTextContent(/^2$/)
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    await user.selectOptions(screen.getByLabelText('Sezona'), '2031/32')
    expect(position('player-b')).toHaveTextContent(/^1$/)
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

})
