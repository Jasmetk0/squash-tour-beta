import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../../i18n/LanguageContext'
import { createTestQueryClient, expectNoForbiddenViewerActions } from '../../../test/viewerTestUtils'
import { ViewerContextProvider } from '../../../viewer/ViewerContext'
import { ViewerTourCalendarPage } from './ViewerTourCalendarPage'

const api = vi.hoisted(() => ({ getViewerRunCalendar: vi.fn() }))
const selected = vi.hoisted(() => ({ run: 'run alpha', branch: 'viewer-a' }))
vi.mock('../../../api/client', () => ({ ...api, ApiError: class ApiError extends Error {} }))
vi.mock('../../../viewer/useActiveViewerProductRunId', () => ({
  useActiveViewerProductRunId: () => selected.run
}))
vi.mock('../../../viewer/useViewerOfficialRunContext', () => ({
  useViewerOfficialRunContext: (run: string) => ({
    data: { product_run_id: run, official_branch_id: selected.branch },
    isPending: false, isFetching: false, isError: false, refetch: vi.fn()
  })
}))

function event(n: number, season: string, status: 'planned' | 'completed') {
  return {
    event_id: 'event ' + n, season, season_week: n,
    calendar_year: 2031, year_week: 30, template_id: 'template-' + n,
    event_name: 'Open ' + n, category: 'Gold', tour_level: 'WORLD_TOUR',
    host_country: 'CZE', host_city: n === 2 ? 'Brno' : 'Praha', region: 'EUROPE',
    duration_in_season_weeks: 1, start_season_week: n, end_season_week: n,
    status, main_draw_size: 32, qualification_draw_size: 16, seeds_count: 8,
    qualifier_spots: 4, wild_cards: 2, byes: 0, prestige: 80
  }
}
const events = [
  event(1, '2030/31', 'planned'),
  event(2, '2031/32', 'completed'),
  event(3, '2031/32', 'planned')
]
function calendar(run = selected.run, branch = selected.branch) {
  return {
    schema_version: 'viewer_run_calendar.v1', product_run_id: run,
    viewer_branch_id: branch, season_count: 2, event_count: 3,
    seasons: [
      { season: '2030/31', event_count: 1, events: [events[0]] },
      { season: '2031/32', event_count: 2, events: events.slice(1) }
    ]
  }
}
function Nav(): JSX.Element {
  const location = useLocation()
  const navigate = useNavigate()
  return <>
    <output aria-label="URL">{location.pathname}{location.search}</output>
    <button type="button" onClick={() => navigate(-1)}>Back</button>
    <button type="button" onClick={() => navigate(1)}>Forward</button>
  </>
}
function mount(url = '/viewer/tour/calendar?keep=one&keep=two') {
  const client = createTestQueryClient()
  function App(): JSX.Element {
    return (
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={[url]}>
          <LanguageProvider><ViewerContextProvider><Nav /><ViewerTourCalendarPage /></ViewerContextProvider></LanguageProvider>
        </MemoryRouter>
      </QueryClientProvider>
    )
  }
  const view = render(<App />)
  return { ...view, refresh: () => view.rerender(<App />) }
}
function params(): URLSearchParams {
  const txt = screen.getByLabelText('URL').textContent ?? ''
  return new URLSearchParams(txt.split('?')[1] ?? '')
}

describe('Viewer saved calendar URL browsing (mocked GET, not real HTTP/SQLite)', () => {
  beforeEach(() => {
    localStorage.clear()
    selected.run = 'run alpha'
    selected.branch = 'viewer-a'
    api.getViewerRunCalendar.mockReset()
      .mockImplementation((run: string) => Promise.resolve(calendar(run)))
  })

  it('restores season/week/status/search from URL without inventing a different event', async () => {
    mount('/viewer/tour/calendar?vcSeason=2031%2F32&vcWeek=2&vcStatus=completed&vcQ=Brno&keep=one&keep=two')
    const table = await screen.findByRole('table', { name: 'Uložené turnaje kalendáře' })
    expect(screen.getByLabelText('Sezona')).toHaveValue('2031/32')
    expect(screen.getByLabelText('Týden')).toHaveValue('2')
    expect(screen.getByLabelText('Stav v kalendáři')).toHaveValue('completed')
    expect(screen.getByLabelText('Hledat název, ID nebo místo')).toHaveValue('Brno')
    expect(within(table).getAllByRole('row')).toHaveLength(2)
    expect(within(table).getByRole('link', { name: 'Open 2' }))
      .toHaveAttribute('href', '/viewer/runs/run%20alpha/calendar/event%202')
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expectNoForbiddenViewerActions()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
  })

  it('supports history navigation and clears stale weeks atomically when season changes', async () => {
    const user = userEvent.setup()
    mount()
    await screen.findByRole('table')
    await user.selectOptions(screen.getByLabelText('Sezona'), '2031/32')
    await user.selectOptions(screen.getByLabelText('Týden'), '2')
    expect(params().get('vcWeek')).toBe('2')
    await user.selectOptions(screen.getByLabelText('Sezona'), '2030/31')
    expect(params().get('vcSeason')).toBe('2030/31')
    expect(params().get('vcWeek')).toBe(null)
    expect(screen.getByText('Zobrazeno 1–1 z 1')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByLabelText('Sezona')).toHaveValue('2031/32')
    expect(screen.getByLabelText('Týden')).toHaveValue('2')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByLabelText('Sezona')).toHaveValue('2030/31')
    expect(screen.getByLabelText('Týden')).toHaveValue('all')
  })

  it('rejects unknown season, noncanonical week and invalid status without falling back to all', async () => {
    const user = userEvent.setup()
    mount('/viewer/tour/calendar?track=yes&vcSeason=unknown&vcWeek=02&vcStatus=undefined')
    expect(await screen.findByRole('alert')).toHaveTextContent('neplatnou nebo nedostupnou')
    expect(screen.getByLabelText('Sezona')).toHaveValue('unknown')
    expect(screen.getByLabelText('Týden')).toHaveValue('02')
    expect(screen.getByLabelText('Stav v kalendáři')).toHaveValue('undefined')
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(params().toString()).toBe('track=yes')
    expect(await screen.findByRole('table')).toBeInTheDocument()
  })

  it('resets URL-scoped selections across Viewer Branch and Run changes', async () => {
    const view = mount('/viewer/tour/calendar?keep=yes&vcSeason=2031%2F32&vcWeek=2&vcStatus=completed')
    expect(await screen.findByRole('table')).toBeInTheDocument()
    selected.branch = 'viewer-b'
    await act(async () => view.refresh())
    await waitFor(() => expect(screen.getByText('viewer-b')).toBeInTheDocument())
    await waitFor(() => expect(params().get('vcSeason')).toBe(null))
    expect(params().get('vcWeek')).toBe(null)
    expect(params().get('vcStatus')).toBe(null)
    expect(params().get('keep')).toBe('yes')
    expect(screen.getByText('Zobrazeno 1–3 z 3')).toBeInTheDocument()
    selected.run = 'run beta'
    await act(async () => view.refresh())
    expect(await screen.findByText('run beta')).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(3)
    expectNoForbiddenViewerActions()
  })

  it('restores text input after remount without issuing a new GET per character', async () => {
    const user = userEvent.setup()
    const url = '/viewer/tour/calendar?vcStatus=planned'
    const first = mount(url)
    expect(await screen.findByRole('table')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Hledat název, ID nebo místo'), 'Praha')
    expect(params().get('vcQ')).toBe('Praha')
    expect(api.getViewerRunCalendar).toHaveBeenCalledTimes(1)
    first.unmount()
    mount('/viewer/tour/calendar?vcStatus=planned&vcQ=Praha')
    expect(await screen.findByRole('table')).toHaveTextContent('Open 3')
    expect(screen.getByLabelText('Hledat název, ID nebo místo')).toHaveValue('Praha')
  })

  it('rejects duplicate owned filters without discarding unrelated URL parameters', async () => {
    mount('/viewer/tour/calendar?vcWeek=2&vcWeek=3&keep=one&keep=two')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Vymazat filtry' }))
    expect(await screen.findByRole('table')).toBeInTheDocument()
    expect(params().getAll('keep')).toEqual(['one', 'two'])
    expect([...params().keys()]).toEqual(['keep', 'keep'])
  })

})
