import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ViewerCalendarEvent, ViewerRunCalendar } from '../../../api/types'
import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { writeViewerActiveProductRunId } from '../../../viewer/activeProductRun'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerTourCalendarPage } from './ViewerTourCalendarPage'

const api = vi.hoisted(() => ({
  getViewerOfficialRunContext: vi.fn(),
  getViewerRunCalendar: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../../api/client', () => api)

function context(run = 'tour run', branch = 'branch-tour') {
  return { product_run_id: run, official_branch_id: branch }
}
function fixtureEvent(number: number, season: string | number = '2032/33'): ViewerCalendarEvent {
  const code = String(number).padStart(3, '0')
  const week = number % 61 + 1
  return {
    event_id: 'event ' + code, season, season_week: week,
    calendar_year: 2032, year_week: 45, template_id: 'template-' + code,
    event_name: 'Open ' + code, category: 'Gold', tour_level: 'WORLD_TOUR',
    host_country: 'CZE', host_city: number % 2 ? 'Brno' : 'Praha', region: 'EUROPE',
    duration_in_season_weeks: 1, start_season_week: week, end_season_week: week,
    status: number % 2 ? 'planned' : 'completed',
    main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8,
    qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80
  }
}
function calendar(events = [fixtureEvent(1), fixtureEvent(2), fixtureEvent(3)],
  run = 'tour run', branch = 'branch-tour'): ViewerRunCalendar {
  const groups = new Map<string, ViewerCalendarEvent[]>()
  for (const event of events) {
    const key = String(event.season)
    groups.set(key, [...(groups.get(key) ?? []), event])
  }
  return {
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_count: groups.size, event_count: events.length,
    seasons: [...groups.entries()].map(([season, rows]) => ({ season, event_count: rows.length, events: rows }))
  }
}
function SwitchLanguage(): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <button type="button" onClick={() => setLanguage(language === 'cs' ? 'en' : 'cs')}>Switch language</button>
}
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <LanguageProvider><ViewerContextProvider><SwitchLanguage /><ViewerTourCalendarPage /></ViewerContextProvider></LanguageProvider>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return { client, ...result }
}

describe('Viewer Season Calendar saved read-only browser (mocked GET API)', () => {
  beforeEach(() => {
    localStorage.clear()
    api.getViewerOfficialRunContext.mockReset().mockResolvedValue(context())
    api.getViewerRunCalendar.mockReset().mockResolvedValue(calendar())
  })

  it('renders no selected Run without any GET or fake jump to week 24', () => {
    mount()
    expect(screen.getByRole('heading', { name: 'Sezonní kalendář' })).toBeInTheDocument()
    expect(screen.getByText('Není vybrán žádný Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vybrat Product Run' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerOfficialRunContext).not.toHaveBeenCalled()
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expect(screen.queryByText('Jump to Week demo')).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('shows actual saved events, week labels and encoded event detail routes', async () => {
    writeViewerActiveProductRunId('tour run')
    mount()
    const table = await screen.findByRole('table', { name: 'Uložené turnaje kalendáře' })
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledWith('tour run')
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith('tour run')
    expect(within(table).getAllByRole('row')).toHaveLength(4)
    expect(within(table).getByRole('link', { name: 'Open 002' }))
      .toHaveAttribute('href', '/viewer/runs/tour%20run/calendar/event%20002')
    expect(within(table).getByText('Dokončeno')).toBeInTheDocument()
    expect(within(table).getByText('Plánováno')).toBeInTheDocument()
    expect(screen.getByText('branch-tour')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít kalendář Runu' }))
      .toHaveAttribute('href', '/viewer/runs/tour%20run/calendar')
    expect(screen.queryByRole('link', { name: /W24/ })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

  it('filters by historical season, saved week, calendar status and location without new GETs', async () => {
    const c = calendar([
      fixtureEvent(1, '2031/32'),
      fixtureEvent(2, '2032/33'),
      fixtureEvent(3, '2032/33')
    ])
    api.getViewerRunCalendar.mockResolvedValue(c)
    writeViewerActiveProductRunId('tour run')
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Sezona' }), '2032/33')
    expect(screen.getByText('Zobrazeno 1–2 z 2')).toBeInTheDocument()
    await user.selectOptions(screen.getByRole('combobox', { name: 'Týden' }), '3')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('table')).toHaveTextContent('Open 002')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Stav v kalendáři' }), 'completed')
    await user.type(screen.getByRole('searchbox', { name: 'Hledat název, ID nebo místo' }), 'PraHA')
    expect(screen.getByRole('table')).toHaveTextContent('Open 002')
    await user.clear(screen.getByRole('searchbox', { name: 'Hledat název, ID nebo místo' }))
    await user.type(screen.getByRole('searchbox', { name: 'Hledat název, ID nebo místo' }), 'no-match')
    expect(screen.getByText('Žádný turnaj neodpovídá zvoleným filtrům.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('paginates 25 events, rejects invalid numeric jump and resets page on search', async () => {
    api.getViewerRunCalendar.mockResolvedValue(calendar(Array.from({ length: 64 }, (_, i) => fixtureEvent(i + 1))))
    writeViewerActiveProductRunId('tour run')
    const user = userEvent.setup()
    mount()
    const table = await screen.findByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(26)
    expect(screen.getByText('Zobrazeno 1–25 z 64')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Poslední' }))
    expect(screen.getByText('Zobrazeno 51–64 z 64')).toBeInTheDocument()
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '4')
    await user.keyboard('{Enter}')
    expect(screen.getByRole('alert')).toHaveTextContent('platné existující číslo')
    await user.clear(screen.getByRole('textbox', { name: 'Přejít na stránku' }))
    await user.type(screen.getByRole('textbox', { name: 'Přejít na stránku' }), '2')
    await user.keyboard('{Enter}')
    expect(screen.getByText('Stránka 2 / 3')).toBeInTheDocument()
    await user.type(screen.getByRole('searchbox', { name: 'Hledat název, ID nebo místo' }), 'Open 064')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('table')).toHaveTextContent('Open 064')
  })

  it('distinguishes valid empty calendar from invalid or failed source and retries only GET', async () => {
    writeViewerActiveProductRunId('tour run')
    api.getViewerRunCalendar.mockResolvedValue(calendar([]))
    const first = mount()
    expect(await screen.findByText('Tento kalendář zatím neobsahuje žádné turnaje.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    first.unmount()

    api.getViewerRunCalendar
      .mockResolvedValueOnce({ ...calendar(), viewer_branch_id: 'foreign' })
      .mockRejectedValueOnce(new Error('internal error should stay hidden'))
      .mockResolvedValueOnce(calendar())
    const user = userEvent.setup()
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('patří jinému Runu')
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (pouze GET)' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('není dostupný')
    expect(screen.queryByText('internal error should stay hidden')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Načíst znovu (pouze GET)' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(3)
  })

  it('rejects invalid context before issuing any calendar GET and retries the context', async () => {
    writeViewerActiveProductRunId('tour run')
    api.getViewerOfficialRunContext
      .mockResolvedValueOnce(context('different run'))
      .mockResolvedValueOnce(context())
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá aktuálně vybranému Product Runu')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Načíst znovu (pouze GET)' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerOfficialRunContext).toHaveBeenCalledTimes(2)
  })

  it('switches language without rerunning GET or losing search and filter selection', async () => {
    writeViewerActiveProductRunId('tour run')
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByRole('combobox', { name: 'Stav v kalendáři' }), 'completed')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { name: 'Season Calendar' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Saved calendar tournaments' })).toBeInTheDocument()
    expect(screen.getByText('Showing 1–1 of 1')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Calendar status' })).toHaveValue('completed')
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('hides stale calendar while refreshing Branch and scopes new data after switch', async () => {
    writeViewerActiveProductRunId('tour run')
    const { client } = mount()
    expect(await screen.findByText('branch-tour')).toBeInTheDocument()
    api.getViewerOfficialRunContext.mockResolvedValue(context('tour run', 'branch-b'))
    api.getViewerRunCalendar.mockResolvedValue(calendar([fixtureEvent(50)], 'tour run', 'branch-b'))
    await act(async () => {
      await client.invalidateQueries({ queryKey: ['viewer-official-run-context', 'tour run'] })
    })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    expect(screen.queryByText('branch-tour')).not.toBeInTheDocument()
    expect(await screen.findByRole('table')).toHaveTextContent('Open 050')
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('does not render delayed old-run calendar replies after changing Product Run', async () => {
    let respondOld: ((value: ViewerRunCalendar) => void) | undefined
    api.getViewerOfficialRunContext.mockImplementation((run: string) => Promise.resolve(context(run)))
    api.getViewerRunCalendar
      .mockImplementationOnce(() => new Promise(resolve => { respondOld = resolve }))
      .mockResolvedValueOnce(calendar([fixtureEvent(40)], 'second run'))
    writeViewerActiveProductRunId('tour run')
    mount()
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    act(() => writeViewerActiveProductRunId('second run'))
    expect(await screen.findByRole('table')).toHaveTextContent('Open 040')
    await act(async () => { respondOld?.(calendar()) })
    expect(screen.getByRole('table')).toHaveTextContent('Open 040')
    expect(screen.queryByText('Open 001')).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })
})
