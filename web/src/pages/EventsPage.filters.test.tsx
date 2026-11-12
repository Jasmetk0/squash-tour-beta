import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventsPage } from './EventsPage'

const api = vi.hoisted(() => ({
  listEvents: vi.fn(),
  getEvent: vi.fn(),
  getRun: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../api/client', () => api)
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: 'en' }) }))

function BrowserControls(): JSX.Element {
  const navigate = useNavigate()
  const location = useLocation()
  return <>
    <output aria-label="Current query">{location.search}</output>
    <button onClick={() => navigate(-1)}>Back</button>
    <button onClick={() => navigate(1)}>Forward</button>
  </>
}

function renderPage(route: string): ReturnType<typeof render> {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[route]}>
      <BrowserControls />
      <Routes><Route path="/runs/:runId/events" element={<EventsPage />} /></Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}

const events = [
  { event_sequence: 2, event_id: 'E2', season: 2027, week: 9, template_id: 'SECOND', tournament_result: null },
  { event_sequence: 1, event_id: 'E1', season: 2027, week: 8, template_id: 'FIRST', tournament_result: null }
]

describe('EventsPage URL-backed historical filters', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events })
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2027 },
      season_state: {
        season: 2027, ordered_events: [
          { event_id: 'E1', season: 2027, week: 8, category: 'Gold', tour: 'Tour', template_id: 'FIRST' },
          { event_id: 'E2', season: 2027, week: 9, category: 'Diamond', tour: 'Tour', template_id: 'SECOND' }
        ]
      }
    })
    api.getEvent.mockImplementation(async (_runId: string, id: string) => ({ event_id: id, detail: 'saved-' + id }))
  })

  it('restores all filters and exact event from a direct URL and fresh mount', async () => {
    const url = '/runs/run-a/events?foreign=keep&filterWeek=8&filterCategory=Gold&filterText=E1&selectedEventId=E1&selectedEventSequence=1'
    const first = renderPage(url)
    let list = await screen.findByRole('list', { name: 'Events history list' })
    expect(within(list).getAllByRole('button')).toHaveLength(1)
    expect(within(list).getByRole('button', { name: /1\. E1/ })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByLabelText('Filter events by week')).toHaveValue('8')
    expect(screen.getByLabelText('Filter events by category')).toHaveValue('Gold')
    expect(screen.getByLabelText('Filter events by event or template')).toHaveValue('E1')
    expect(screen.getByRole('link', { name: 'Open dedicated event detail page' })).toHaveAttribute('href', '/runs/run-a/events/E1')
    first.unmount()

    renderPage(url)
    list = await screen.findByRole('list', { name: 'Events history list' })
    expect(within(list).getByRole('button', { name: /1\. E1/ })).toHaveAttribute('aria-current', 'true')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
  })

  it('makes the week/category shareable, preserves foreign keys and restores Back/Forward', async () => {
    const user = userEvent.setup()
    renderPage('/runs/run-a/events?foreign=keep')
    let list = await screen.findByRole('list', { name: 'Events history list' })
    await user.selectOptions(screen.getByLabelText('Filter events by week'), '8')
    await user.selectOptions(screen.getByLabelText('Filter events by category'), 'Gold')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('filterWeek=8')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('filterCategory=Gold')
    expect(within(list).getAllByRole('button')).toHaveLength(1)
    await user.click(screen.getByRole('button', { name: 'Back' }))
    expect(screen.getByLabelText('Filter events by category')).toHaveValue('')
    expect(screen.getByLabelText('Filter events by week')).toHaveValue('8')
    await user.click(screen.getByRole('button', { name: 'Forward' }))
    expect(screen.getByLabelText('Filter events by category')).toHaveValue('Gold')
    await user.click(screen.getByRole('button', { name: 'Reset filters' }))
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
    expect(screen.getByLabelText('Current query')).not.toHaveTextContent('filterWeek')
    expect(screen.getByLabelText('Current query')).not.toHaveTextContent('filterCategory')
    expect(within(list).getAllByRole('button')).toHaveLength(2)
  })

  it('replaces text edits rather than adding a history entry per keystroke', async () => {
    const user = userEvent.setup()
    renderPage('/runs/run-a/events?foreign=keep')
    await screen.findByRole('list', { name: 'Events history list' })
    await user.type(screen.getByLabelText('Filter events by event or template'), 'E1')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('filterText=E1')
    await user.click(screen.getByRole('button', { name: 'Back' }))
    // Text edit replaced the initial entry, so Back cannot return to intermediate E.
    expect(screen.getByLabelText('Filter events by event or template')).toHaveValue('E1')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
  })

  it('keeps sequence identity with reused IDs and suppresses unverifiable ID-only detail', async () => {
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [
      { event_sequence: 7, event_id: 'DUP', season: 2027, week: 9, template_id: null, tournament_result: null },
      { event_sequence: 2, event_id: 'DUP', season: 2026, week: 32, template_id: null, tournament_result: null }
    ] })
    api.getEvent.mockResolvedValue({ event_id: 'DUP', event_sequence: 7, season: 2027, detail: 'wrong-record' })
    renderPage('/runs/run-a/events?selectedEventId=DUP&selectedEventSequence=2&filterWeek=32')
    const list = await screen.findByRole('list', { name: 'Events history list' })
    expect(within(list).getByRole('button', { name: /2\. DUP/ })).toHaveAttribute('aria-current', 'true')
    expect(within(list).queryByRole('button', { name: /7\. DUP/ })).not.toBeInTheDocument()
    expect(await screen.findByText('Event detail does not match the selected event; its payload is hidden.')).toBeInTheDocument()
    expect(screen.queryByText(/wrong-record/)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open dedicated event detail page' })).not.toBeInTheDocument()
  })

  it('does not interpret missing week as null and explicitly labels unknown filters', async () => {
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [
      { event_sequence: 4, event_id: 'NO-WEEK', season: 2026, week: null, template_id: null, tournament_result: null }
    ] })
    renderPage('/runs/run-a/events?filterWeek=null&filterCategory=UNKNOWN&foreign=keep')
    expect(await screen.findByText('No persisted events match the current filters.')).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown week: null' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Unknown category: UNKNOWN' })).toBeInTheDocument()
    expect(screen.getByText(/has not silently switched to All/)).toBeInTheDocument()
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
  })

  it('drops an obsolete exact selection when a new filter excludes it', async () => {
    const user = userEvent.setup()
    renderPage('/runs/run-a/events?selectedEventId=E2&selectedEventSequence=2&foreign=keep')
    await screen.findByRole('list', { name: 'Events history list' })
    await user.selectOptions(screen.getByLabelText('Filter events by week'), '8')
    expect(screen.getByLabelText('Current query')).not.toHaveTextContent('selectedEventSequence')
    expect(screen.getByLabelText('Current query')).toHaveTextContent('foreign=keep')
    expect(screen.getByRole('button', { name: /1\. E1/ })).toHaveAttribute('aria-current', 'true')
  })
})
