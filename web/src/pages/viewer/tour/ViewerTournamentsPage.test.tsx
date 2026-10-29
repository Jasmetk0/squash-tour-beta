import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerCalendarEvent, ViewerRunCalendar, ViewerTournamentHistory, ViewerTournamentHistoryItem } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { writeViewerActiveProductRunId } from '../../../viewer/activeProductRun'
import { ViewerTournamentsPage } from './ViewerTournamentsPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRunContext: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  getViewerTournamentHistory: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../../api/client', () => api)

const baseRun = 'run alpha'
const baseBranch = 'branch-tour'
function context(run = baseRun, branch = baseBranch) {
  return { product_run_id: run, official_branch_id: branch }
}
function item(index: number, season = '2031/32'): ViewerCalendarEvent {
  const id = 'EVT ' + String(index).padStart(3, '0')
  return {
    event_id: id, season, season_week: index % 61 + 1,
    calendar_year: 2031, year_week: 40, template_id: 'template-' + index,
    event_name: 'Open ' + String(index).padStart(3, '0'),
    category: 'GOLD', tour_level: 'WORLD_TOUR', host_country: 'CZE',
    host_city: index % 2 === 0 ? 'Brno' : 'Praha', region: 'Europe',
    duration_in_season_weeks: 1, start_season_week: index % 61 + 1,
    end_season_week: index % 61 + 1, status: 'planned', main_draw_size: 32,
    qualification_draw_size: 16, seeds_count: 8, qualifier_spots: 4,
    wild_cards: 2, byes: 0, prestige: 80
  }
}
function historyItem(e: ViewerCalendarEvent, published: boolean): ViewerTournamentHistoryItem {
  return {
    event_id: e.event_id, season: String(e.season), season_week: e.season_week,
    event_name: e.event_name, template_id: e.template_id,
    category: e.category, tour_level: e.tour_level, host_country: e.host_country,
    host_city: e.host_city, region: e.region, main_draw_size: e.main_draw_size,
    qualification_draw_size: e.qualification_draw_size, seeds_count: e.seeds_count,
    qualifier_spots: e.qualifier_spots, wild_cards: e.wild_cards, byes: e.byes,
    ranking_status: published ? 'ranked' : 'planned', result_published: published,
    champion_player_id: published ? 'winner ' + e.event_id : null,
    finalist_player_id: published ? 'finalist ' + e.event_id : null
  }
}
function catalog(events: ViewerCalendarEvent[], publishedIds: string[] = [], run = baseRun, branch = baseBranch):
  { calendar: ViewerRunCalendar; history: ViewerTournamentHistory } {
  const groups = new Map<string, ViewerCalendarEvent[]>()
  for (const event of events) {
    const key = String(event.season)
    groups.set(key, [...(groups.get(key) ?? []), event])
  }
  return {
    calendar: {
      schema_version: 'viewer_run_calendar.v1', product_run_id: run, viewer_branch_id: branch,
      season_count: groups.size, event_count: events.length,
      seasons: Array.from(groups, ([season, group]) => ({
        season, event_count: group.length, events: group
      }))
    },
    history: {
      schema_version: 'viewer_tournament_history.v1',
      product_run_id: run, viewer_branch_id: branch,
      tournament_count: events.length, published_result_count: publishedIds.length,
      tournaments: events.map(event => historyItem(event, publishedIds.includes(event.event_id)))
    }
  }
}
function SwitchLanguage() {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LanguageProvider><SwitchLanguage /><ViewerTournamentsPage /></LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { client, ...result }
}

describe('Viewer tournament archive browsing (mocked GET API, not Chromium/HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    api.getViewerOfficialRunContext.mockReset().mockResolvedValue(context())
    const fixture = catalog([item(1), item(2), item(3)], ['EVT 002'])
    api.getViewerRunCalendar.mockReset().mockResolvedValue(fixture.calendar)
    api.getViewerTournamentHistory.mockReset().mockResolvedValue(fixture.history)
  })

  it('does not fetch any source until a Product Run is selected', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Všechny turnaje' })).toBeInTheDocument()
    expect(screen.getByText(/Není vybraný žádný Product Run/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vybrat Run' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(api.getViewerTournamentHistory).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('shows all saved events, authoritative publication status, winner and encoded detail link', async () => {
    writeViewerActiveProductRunId(baseRun)
    mount()
    const table = await screen.findByRole('table', { name: 'Uložené turnaje' })
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledWith(baseRun)
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith(baseRun)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith(baseRun)
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    expect(within(table).getByRole('link', { name: 'Open 002' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/EVT%20002')
    expect(within(table).getByRole('link', { name: 'winner EVT 002' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/players/winner%20EVT%20002/career')
    expect(within(table).getAllByText('Výsledek publikován')).toHaveLength(1)
    expect(within(table).getAllByText('Zatím nepublikováno')).toHaveLength(2)
    expect(screen.getByText(baseBranch)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít turnaje Runu' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/tournaments')
    expect(screen.getByRole('link', { name: 'Otevřít kalendář Runu' })).toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar')
    expectNoForbiddenViewerActions()
  })

  it('filters by season, location, and published result rather than calendar status', async () => {
    const e1 = item(1, '2030/31')
    const e2 = item(2, '2031/32')
    const e3 = item(3, '2031/32')
    const fixture = catalog([e1, e2, e3], [e2.event_id])
    api.getViewerRunCalendar.mockResolvedValue(fixture.calendar)
    api.getViewerTournamentHistory.mockResolvedValue(fixture.history)
    writeViewerActiveProductRunId(baseRun)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Filtrovat sezonu' }), '2031/32')
    expect(screen.getByText('Zobrazeno 1–2 z 2')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Stav zveřejnění výsledku' }), 'published')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).queryByRole('link', { name: 'Open 003' })).not.toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Hledat turnaj, ID nebo místo' }), 'Brno')
    expect(screen.getByRole('table')).toHaveTextContent('Open 002')
    await user.clear(screen.getByRole('searchbox', { name: 'Hledat turnaj, ID nebo místo' }))
    await user.type(screen.getByRole('searchbox', { name: 'Hledat turnaj, ID nebo místo' }), 'no-match')
    expect(screen.getByText('Žádný turnaj neodpovídá filtrům.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('shows 25 results per page, validates jumps and resets page when filtered', async () => {
    const events = Array.from({ length: 62 }, (_, i) => item(i + 1))
    const fixture = catalog(events)
    api.getViewerRunCalendar.mockResolvedValue(fixture.calendar)
    api.getViewerTournamentHistory.mockResolvedValue(fixture.history)
    writeViewerActiveProductRunId(baseRun)
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 1–25 z 62')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(26)
    await user.click(screen.getByRole('button', { name: 'Poslední' }))
    expect(screen.getByText('Zobrazeno 51–62 z 62')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '4')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('Zadej existující celé číslo stránky')
    await user.clear(screen.getByRole('textbox', { name: 'Přejít na stránku' }))
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '2')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Hledat turnaj, ID nebo místo' }), 'Open 061')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(within(screen.getByRole('table')).getByRole('link', { name: 'Open 061' })).toBeInTheDocument()
  })

  it('distinguishes genuinely empty catalog from source errors and corrupt cross-branch data', async () => {
    writeViewerActiveProductRunId(baseRun)
    const empty = catalog([])
    api.getViewerRunCalendar.mockResolvedValue(empty.calendar)
    api.getViewerTournamentHistory.mockResolvedValue(empty.history)
    const first = mount()
    expect(await screen.findByText('Kalendář neobsahuje žádný turnaj.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    first.unmount()

    api.getViewerRunCalendar.mockResolvedValueOnce({ ...empty.calendar, viewer_branch_id: 'foreign' })
      .mockRejectedValueOnce(new Error('secret internal problem'))
      .mockResolvedValueOnce(empty.calendar)
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('si neodpovídají')
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('nejsou dostupné')
    expect(screen.queryByText('secret internal problem')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByText('Kalendář neobsahuje žádný turnaj.')).toBeInTheDocument()
  })

  it('does not request calendar/history until valid official context; retry refetches it', async () => {
    writeViewerActiveProductRunId(baseRun)
    api.getViewerOfficialRunContext.mockResolvedValueOnce(context('foreign'))
      .mockResolvedValueOnce(context())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá vybranému Product Runu')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (GET)' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledTimes(2)
  })

  it('changes CS/EN copy without new GET or resetting source/filters', async () => {
    writeViewerActiveProductRunId(baseRun)
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Stav zveřejnění výsledku' }), 'published')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { name: 'All Tournaments' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Saved tournaments' })).toBeInTheDocument()
    expect(screen.getByText('Showing 1–1 of 1')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledTimes(1)
  })

  it('rechecks changed Viewer Branch and prevents displaying old source data', async () => {
    writeViewerActiveProductRunId(baseRun)
    const { client } = mount()
    expect(await screen.findByText(baseBranch)).toBeInTheDocument()
    api.getViewerOfficialRunContext.mockResolvedValue(context(baseRun, 'branch-b'))
    const fresh = catalog([item(9)], [], baseRun, 'branch-b')
    api.getViewerRunCalendar.mockResolvedValue(fresh.calendar)
    api.getViewerTournamentHistory.mockResolvedValue(fresh.history)
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['viewer-official-run-context', baseRun] })
    })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText(baseBranch)).not.toBeInTheDocument()
    expect(await screen.findByRole('table')).toHaveTextContent('Open 009')
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('does not leak late first-Run responses after selecting another Run', async () => {
    let resolveOld: ((value: ViewerRunCalendar) => void) | undefined
    api.getViewerOfficialRunContext.mockImplementation((run: string) => Promise.resolve(context(run)))
    api.getViewerRunCalendar
      .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve }))
    const old = catalog([item(1)])
    const newer = catalog([item(42)], [], 'run beta')
    api.getViewerRunCalendar.mockResolvedValueOnce(newer.calendar)
    api.getViewerTournamentHistory.mockImplementation((run: string) =>
      Promise.resolve(run === 'run beta' ? newer.history : old.history))
    writeViewerActiveProductRunId(baseRun)
    mount()
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    act(() => writeViewerActiveProductRunId('run beta'))
    expect(await screen.findByRole('table')).toHaveTextContent('Open 042')
    await act(async () => { resolveOld?.(old.calendar) })
    expect(screen.getByRole('table')).toHaveTextContent('Open 042')
    expect(screen.queryByText('Open 001')).not.toBeInTheDocument()
  })
})
