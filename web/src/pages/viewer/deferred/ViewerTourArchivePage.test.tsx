import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerTourDeferredPage } from './ViewerTourDeferredPage'

const api = vi.hoisted(() => ({
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
}))
const current = vi.hoisted(() => ({
  run: 'run alpha' as string | null, branch: 'branch-a', foreign: false,
}))
vi.mock('../../../api/client', () => ({
  ...api, ApiError: class ApiError extends Error {},
}))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => current.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: {
      product_run_id: current.foreign ? 'foreign-run' : run,
      official_branch_id: current.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))

type Event = ReturnType<typeof event>
function event(n: number, season: string, category: string, published: boolean) {
  return {
    event_id: 'event ' + n, season, season_week: n,
    calendar_year: 2031, year_week: 30, template_id: 'template-' + n,
    event_name: 'Open ' + n, category, tour_level: 'WORLD_TOUR',
    host_country: 'CZE', host_city: n === 2 ? 'Brno' : 'Praha', region: 'EUROPE',
    duration_in_season_weeks: 1, start_season_week: n, end_season_week: n,
    status: published ? 'completed' : 'planned',
    main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8,
    qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80,
  }
}
const examples = [
  event(1, '2030/31', 'GOLD', true),
  event(2, '2031/32', 'PLATINUM', true),
  event(3, '2031/32', 'GOLD', false),
  event(4, '2031/32', 'GOLD', true),
]
function sources(events: Event[] = examples, run = current.run ?? '', branch = current.branch) {
  const groups = new Map<string, Event[]>()
  for (const e of events) groups.set(e.season, [...(groups.get(e.season) ?? []), e])
  return {
    calendar: {
      schema_version: 'viewer_run_calendar.v1', product_run_id: run, viewer_branch_id: branch,
      season_count: groups.size, event_count: events.length,
      seasons: [...groups].map(([season, es]) => ({ season, event_count: es.length, events: es })),
    },
    history: {
      schema_version: 'viewer_tournament_history.v1', product_run_id: run,
      viewer_branch_id: branch, tournament_count: events.length,
      published_result_count: events.filter(e => e.status === 'completed').length,
      tournaments: events.map(e => ({
        event_id: e.event_id, season: e.season, season_week: e.season_week,
        event_name: e.event_name, template_id: e.template_id,
        category: e.category, tour_level: e.tour_level,
        host_country: e.host_country, host_city: e.host_city,
        region: e.region, main_draw_size: e.main_draw_size,
        qualification_draw_size: e.qualification_draw_size, seeds_count: e.seeds_count,
        qualifier_spots: e.qualifier_spots, wild_cards: e.wild_cards, byes: e.byes,
        ranking_status: e.status === 'completed' ? 'ranked' : 'planned',
        result_published: e.status === 'completed',
        champion_player_id: e.status === 'completed' ? 'winner ' + e.event_id : null,
        finalist_player_id: e.status === 'completed' ? 'finalist ' + e.event_id : null,
      })),
    },
  }
}
function SwitchLanguage() {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount(kind: 'categories' | 'champions') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <LanguageProvider>
            <ViewerContextProvider>
              <SwitchLanguage />
              <ViewerTourDeferredPage kind={kind} />
            </ViewerContextProvider>
          </LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Verified saved Viewer Tour Categories and Past Champions (mocked public GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    current.run = 'run alpha'
    current.branch = 'branch-a'
    current.foreign = false
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      Promise.resolve(sources(examples, run, current.branch).calendar))
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(sources(examples, run, current.branch).history))
  })

  it('requires an explicit Product Run before making either read', () => {
    current.run = null
    mount('champions')
    expect(screen.getByText('Nejprve vyber Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Seznam Runů' }))
      .toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('does not fetch when the selected Viewer Branch belongs to a foreign Product Run', () => {
    current.foreign = true
    mount('categories')
    expect(screen.getByRole('alert')).toHaveTextContent('neodpovídá vybranému')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows actual category totals and published counts, and links only stored events', async () => {
    mount('categories')
    const counts = await screen.findByRole('table', { name: 'Souhrn kategorií uložených turnajů' })
    expect(within(counts).getByRole('row', { name: /GOLD/ })).toHaveTextContent('3')
    expect(within(counts).getByRole('row', { name: /GOLD/ })).toHaveTextContent('2')
    expect(within(counts).getByRole('row', { name: /PLATINUM/ })).toHaveTextContent('1')
    const table = screen.getByRole('table', { name: 'Turnaje vybrané kategorie' })
    expect(within(table).getAllByRole('row')).toHaveLength(5)
    expect(within(table).getByRole('link', { name: 'Open 2' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/event%202')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('shows only already-published champions and finalists with immutable player-ID paths', async () => {
    mount('champions')
    const table = await screen.findByRole('table', { name: 'Historie publikovaných vítězů' })
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    expect(within(table).queryByRole('link', { name: 'Open 3' })).not.toBeInTheDocument()
    expect(within(table).getByRole('link', { name: 'winner event 2' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/winner%20event%202/career')
    expect(within(table).getByRole('link', { name: 'finalist event 2' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/finalist%20event%202/career')
    expect(screen.getByText(/historická ID publikovaných výsledků/)).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('filters exact saved season, category and event text without issuing further GETs', async () => {
    const user = userEvent.setup()
    mount('champions')
    await screen.findByRole('table', { name: 'Historie publikovaných vítězů' })
    await user.selectOptions(screen.getByLabelText('Sezona'), '2031/32')
    await user.selectOptions(screen.getByLabelText('Kategorie'), 'PLATINUM')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat turnaj nebo ID vítěze'), 'Open 2')
    const table = screen.getByRole('table', { name: 'Historie publikovaných vítězů' })
    expect(within(table).getByRole('link', { name: 'Open 2' })).toBeInTheDocument()
    await user.clear(screen.getByLabelText('Hledat turnaj nebo ID vítěze'))
    await user.type(screen.getByLabelText('Hledat turnaj nebo ID vítěze'), 'Open 3')
    expect(screen.getByText('Zvoleným filtrům neodpovídají žádné záznamy.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('separates a valid empty archive from a pending unpublished champion', async () => {
    const user = userEvent.setup()
    const unpublished = [event(3, '2031/32', 'GOLD', false)]
    api.getViewerRunCalendar.mockReset().mockResolvedValue(sources(unpublished).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(sources(unpublished).history)
    const first = mount('champions')
    expect(await screen.findByText('Zatím nebyl publikován žádný vítěz.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    first.unmount()

    api.getViewerRunCalendar.mockReset().mockResolvedValue(sources([]).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(sources([]).history)
    mount('categories')
    expect(await screen.findByText('V uloženém archivu nejsou žádné turnaje.')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
    void user
  })

  it('rejects mismatched calendar/results Branch and recovers only after an explicit GET retry', async () => {
    const user = userEvent.setup()
    api.getViewerRunCalendar.mockReset()
      .mockResolvedValueOnce(sources(examples, 'run alpha', 'foreign-branch').calendar)
      .mockResolvedValue(sources().calendar)
    mount('champions')
    expect(await screen.findByRole('alert')).toHaveTextContent('shodný ověřený zdroj')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Znovu načíst (GET)' }))
    expect(await screen.findByRole('table', { name: 'Historie publikovaných vítězů' }))
      .toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
    expectNoForbiddenViewerActions()
  })

  it('does not leak a late response from a previous Viewer Branch', async () => {
    let resolveOld: ((value: ReturnType<typeof sources>['calendar']) => void) | undefined
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) => {
      if (current.branch === 'branch-a') {
        return new Promise(resolve => { resolveOld = resolve })
      }
      return Promise.resolve(sources(examples, run, 'branch-b').calendar)
    })
    api.getViewerTournamentHistory.mockReset().mockImplementation((run: string) =>
      Promise.resolve(sources(examples, run, current.branch).history))
    const view = mount('champions')
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    current.branch = 'branch-b'
    await act(async () => view.refresh())
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(sources(examples, 'run alpha', 'branch-a').calendar) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('translates static UI while preserving historical event/player IDs and cached GET evidence', async () => {
    const user = userEvent.setup()
    mount('champions')
    await screen.findByRole('table', { name: 'Historie publikovaných vítězů' })
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { name: 'Past Champions' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Published past champions' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'winner event 2' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('paginates long historical champion lists and resets page when filters change', async () => {
    const all = Array.from({ length: 60 }, (_, i) => event(i + 1, '2031/32', 'GOLD', true))
    api.getViewerRunCalendar.mockReset().mockResolvedValue(sources(all).calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(sources(all).history)
    const user = userEvent.setup()
    mount('champions')
    expect(await screen.findByText('Zobrazeno 1–25 z 60')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 26–50 z 60')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat turnaj nebo ID vítěze'), 'Open 60')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open 60' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
