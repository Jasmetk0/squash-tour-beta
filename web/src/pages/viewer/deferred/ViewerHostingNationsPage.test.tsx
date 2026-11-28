import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider, useLanguage } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerCountriesDeferredPage } from './ViewerCountriesDeferredPage'

const api = vi.hoisted(() => ({ getViewerRunCalendar: vi.fn() }))
const active = vi.hoisted(() => ({
  run: 'run alpha' as string | null,
  branch: 'branch-a', foreignContext: false,
}))
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => active.run,
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: {
      product_run_id: active.foreignContext ? 'foreign-run' : run,
      official_branch_id: active.branch,
    },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn(),
  }),
}))
function event(index: number, country = 'CZE', season = '2031/32', status = 'completed') {
  return {
    event_id: 'event ' + index, season, season_week: index,
    calendar_year: 2031, year_week: 30,
    template_id: 'template-' + index, event_name: 'Open ' + index,
    category: 'GOLD', tour_level: 'WORLD_TOUR',
    host_country: country, host_city: 'Brno', region: 'Europe',
    duration_in_season_weeks: 1, start_season_week: index, end_season_week: index,
    status, main_draw_size: 32, qualification_draw_size: 16,
    seeds_count: 8, qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80,
  }
}
type Event = ReturnType<typeof event>
const sample = [
  event(1, 'CZE', '2030/31', 'completed'),
  event(2, 'CZE', '2031/32', 'planned'),
  event(3, 'EGY', '2031/32', 'completed'),
  event(4, 'CZE', '2031/32', 'completed'),
]
function calendar(events: Event[] = sample, run = active.run ?? '', branch = active.branch) {
  const seasons = new Map<string, Event[]>()
  for (const e of events) seasons.set(e.season, [...(seasons.get(e.season) ?? []), e])
  return {
    schema_version: 'viewer_run_calendar.v1',
    product_run_id: run, viewer_branch_id: branch,
    season_count: seasons.size, event_count: events.length,
    seasons: [...seasons].map(([season, list]) => ({ season, event_count: list.length, events: list })),
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
            <ViewerCountriesDeferredPage kind="hosting" />
          </LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}

describe('Hosting Nations from verified public Saved calendar (mocked GET)', () => {
  beforeEach(() => {
    localStorage.clear()
    active.run = 'run alpha'; active.branch = 'branch-a'; active.foreignContext = false
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      Promise.resolve(calendar(sample, run, active.branch)))
  })

  it('never fetches without a selected Product Run', () => {
    active.run = null
    mount()
    expect(screen.getByText('Není vybraný Product Run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vybrat Run' })).toHaveAttribute('href', '/viewer/runs')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

  it('rejects foreign Run context before loading the calendar', () => {
    active.foreignContext = true
    mount()
    expect(screen.getByRole('alert')).toHaveTextContent('Nelze ověřit Viewer Branch')
    expect(api.getViewerRunCalendar).not.toHaveBeenCalled()
  })

  it('groups actual calendar events by host country without treating planned tournaments as completed', async () => {
    mount()
    const table = await screen.findByRole('table', {
      name: 'Počty uložených turnajů podle pořadatelské země',
    })
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    const czech = within(table).getByRole('row', { name: /CZE/ })
    expect(within(czech).getAllByRole('cell')[1]).toHaveTextContent('3')
    expect(within(czech).getAllByRole('cell')[2]).toHaveTextContent('2')
    expect(within(czech).getAllByRole('cell')[3]).toHaveTextContent('2')
    expect(within(czech).getByRole('link', { name: 'CZE' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/countries/CZE')
    expect(within(czech).getByRole('link', { name: 'Open 4' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/event%204')
    expect(screen.getByText('branch-a')).toBeInTheDocument()
    expect(screen.getByText(/Pořádání není důkaz odehrání zápasu/)).toBeInTheDocument()
    expect(screen.getByText(/včetně zrušených při výběru všech stavů/)).toBeInTheDocument()
    expect(within(table).getByRole('columnheader', { name: 'Nejpozdější turnaj podle rozpisu' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    expectNoForbiddenViewerActions()
  })

  it('filters season, actual event status and country code without extra requests', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Sezona'), '2031/32')
    await user.selectOptions(screen.getByLabelText('Stav turnaje'), 'planned')
    let table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('link', { name: 'CZE' })).toBeInTheDocument()
    expect(within(table).getAllByRole('cell')[2]).toHaveTextContent('0')
    await user.type(screen.getByLabelText('Hledat kód země'), 'EGY')
    expect(screen.getByText('Zvoleným filtrům neodpovídají žádné pořadatelské země.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('does not fabricate hosting entries when a valid saved calendar is empty', async () => {
    api.getViewerRunCalendar.mockReset().mockResolvedValue(calendar([]))
    mount()
    expect(await screen.findByText('Uložený kalendář zatím neobsahuje turnaje.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('rejects cross-branch, duplicate events and invalid host country, with explicit GET recovery', async () => {
    const valid = calendar()
    const user = userEvent.setup()
    api.getViewerRunCalendar.mockReset()
      .mockResolvedValueOnce({ ...valid, viewer_branch_id: 'foreign-branch' })
      .mockResolvedValueOnce({
        ...valid, event_count: 5,
        seasons: valid.seasons.map(s => ({
          ...s, event_count: s.event_count + (s.season === '2031/32' ? 1 : 0),
          events: s.season === '2031/32' ? [...s.events, s.events[0]] : s.events,
        })),
      })
      .mockResolvedValueOnce({
        ...valid, seasons: valid.seasons.map(s => ({
          ...s, events: s.events.map(e => e.event_id === 'event 2' ? { ...e, host_country: '' } : e),
        })),
      })
      .mockResolvedValueOnce(valid)
    mount()
    for (let i = 0; i < 3; i++) {
      expect(await screen.findByRole('alert')).toHaveTextContent('neodpovídá ověřenému')
      expect(screen.queryByRole('table')).not.toBeInTheDocument()
      await user.click(screen.getByRole('button', { name: 'Znovu načíst (GET)' }))
    }
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(4)
    expectNoForbiddenViewerActions()
  })

  it('keeps a delayed old Viewer Branch response out of the current directory', async () => {
    let resolveOld: ((value: ReturnType<typeof calendar>) => void) | undefined
    api.getViewerRunCalendar.mockReset().mockImplementation((run: string) =>
      active.branch === 'branch-a'
        ? new Promise(resolve => { resolveOld = resolve })
        : Promise.resolve(calendar(sample, run, 'branch-b')))
    const view = mount()
    await waitFor(() => expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1))
    active.branch = 'branch-b'
    await act(async () => { view.refresh() })
    expect(await screen.findByText('branch-b')).toBeInTheDocument()
    await act(async () => { resolveOld?.(calendar(sample, 'run alpha', 'branch-a')) })
    expect(screen.queryByText('branch-a')).not.toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(2)
  })

  it('translates UI without changing country/event codes or refetching data', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.click(screen.getByRole('button', { name: 'Switch language' }))
    expect(screen.getByRole('heading', { level: 2, name: 'Hosting Nations' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Saved event counts by hosting country' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'CZE' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('paginates long country lists and resets page when filters change', async () => {
    const many = Array.from({ length: 31 }, (_, i) =>
      event(i + 1, 'C' + String(i).padStart(2, '0'), '2031/32', 'planned'))
    api.getViewerRunCalendar.mockReset().mockResolvedValue(calendar(many))
    const user = userEvent.setup()
    mount()
    expect(await screen.findByText('Zobrazeno 1–25 z 31')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Další' }))
    expect(screen.getByText('Zobrazeno 26–31 z 31')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat kód země'), 'C30')
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'C30' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další' })).not.toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })
})
