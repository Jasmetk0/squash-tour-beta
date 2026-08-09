import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SeasonCalendarPage } from './SeasonCalendarPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn()
}))
const adminTime = vi.hoisted(() => ({ viewed: vi.fn() }))

vi.mock('../api/client', () => api)
vi.mock('../admin/useAdminViewedSeasonState', () => ({ useAdminViewedSeasonState: adminTime.viewed }))

const presentView = () => ({ historical: false, seasonState: null, unavailable: false, failed: false, query: { isLoading: false }, time: null })
const pastView = (checkpointId = 'cp-old', season = 2005) => ({
  historical: true, unavailable: false, failed: false, query: { isLoading: false },
  time: { viewCheckpointId: checkpointId, selectedCheckpoint: { kind: 'current_state_capture' }, selectPresent: vi.fn() },
  seasonState: { season, completed_event_ids: ['A'], next_event_index: 1, ordered_events: [
    { event_id: 'A', season, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'TA' },
    { event_id: 'B', season, week: 12, tour: 'WORLD', category: 'PLATINUM', template_id: 'TB' },
    { event_id: 'C', season, week: 12, tour: 'ELITE', category: 'SILVER', template_id: 'TC' }
  ] }
})

describe('SeasonCalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    adminTime.viewed.mockImplementation(presentView)
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2029, seed: 7, next_event_index: 1, total_events: 4, completed_event_ids: ['E2'] },
      season_state: {
        season: 2029,
        next_event_index: 1,
        completed_event_ids: ['E2'],
        ordered_events: [
          { event_id: 'E2', season: 2029, week: 4, tour: 'WORLD', category: 'PLATINUM', template_id: 'TEMP-C' },
          { event_id: 'E1', season: 2029, week: 2, tour: 'ELITE', category: 'GOLD', template_id: 'TEMP-A' },
          { event_id: 'E3', season: 2029, week: 8, tour: 'WORLD', category: 'SILVER', template_id: 'TEMP-B' },
          { event_id: 'E4', season: 2029, week: 10, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-D' }
        ]
      }
    })
    api.listEvents.mockResolvedValue({
      run_id: 'run-a',
      events: [
        { event_sequence: 2, event_id: 'E2', season: 2029, week: 4, template_id: 'TEMP-C', tournament_result: { ok: true } }
      ]
    })
  })

  it('renders historical checkpoint SeasonState without current Run or Events reads', async () => {
    adminTime.viewed.mockReturnValue(pastView())
    renderWithRoute(<SeasonCalendarPage />, '/admin/runs/run-a/calendar')
    expect(await screen.findByText('Past')).toBeInTheDocument()
    expect(screen.getByText('cp-old')).toBeInTheDocument()
    expect(screen.getAllByText('2005').length).toBeGreaterThan(0)
    expect(screen.getByText('1/3')).toBeInTheDocument()
    const items = within(screen.getByRole('list', { name: 'Season calendar ordered list' })).getAllByRole('listitem')
    expect(items[0]).toHaveTextContent('A'); expect(items[0]).toHaveTextContent('Completed')
    expect(items[1]).toHaveTextContent('B'); expect(items[1]).toHaveTextContent('Next')
    expect(items[2]).toHaveTextContent('C'); expect(items[2]).toHaveTextContent('Upcoming')
    expect(within(screen.getByRole('heading', { name: 'Next event focus' }).closest('article')!).getByText('B')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'history' })).not.toBeInTheDocument()
    expect(api.getRun).not.toHaveBeenCalled(); expect(api.listEvents).not.toHaveBeenCalled()
  })

  it('does not label old checkpoint content as a newly selected checkpoint while loading', async () => {
    let current = pastView('cp-old', 2005)
    adminTime.viewed.mockImplementation(() => current)
    function Harness() { const [, rerender] = useState(0); return <><button onClick={() => { current = { ...pastView('cp-newer', 2006), seasonState: null, query: { isLoading: true } }; rerender(value => value + 1) }}>Switch</button><SeasonCalendarPage /></> }
    renderWithRoute(<Harness />, '/admin/runs/run-a/calendar')
    expect(await screen.findByText('cp-old')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Switch' }))
    expect(screen.getByText('Loading historical calendar...')).toBeInTheDocument()
    expect(screen.queryByText('cp-old')).not.toBeInTheDocument()
    expect(screen.queryByText('cp-newer')).not.toBeInTheDocument()
  })

  it.each([
    ['unavailable', 'Historical calendar is not available for this checkpoint.'],
    ['failed', 'Failed to load historical calendar state.']
  ])('shows a safe historical %s state without Present fallback', async (kind, heading) => {
    const selectPresent = vi.fn()
    adminTime.viewed.mockReturnValue({ ...pastView(), seasonState: null, unavailable: kind === 'unavailable', failed: kind === 'failed', time: { viewCheckpointId: 'cp-old', selectedCheckpoint: { kind: 'fork' }, selectPresent } })
    renderWithRoute(<SeasonCalendarPage />, '/admin/runs/run-a/calendar')
    expect(await screen.findByRole('heading', { name: heading })).toBeInTheDocument()
    expect(screen.getByText(/cp-old/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Run Home' })).toHaveAttribute('href', '/admin/runs/run-a')
    await userEvent.click(screen.getByRole('button', { name: 'Return to Present' })); expect(selectPresent).toHaveBeenCalled()
    expect(api.getRun).not.toHaveBeenCalled(); expect(api.listEvents).not.toHaveBeenCalled()
  })

  it('renders ordered calendar from run season state and preserves backend order', async () => {
    renderWithRoute(<SeasonCalendarPage />, '/runs/run-a/calendar')

    expect(await screen.findByRole('heading', { name: 'Season calendar' })).toBeInTheDocument()

    const list = await screen.findByRole('list', { name: 'Season calendar ordered list' })
    const items = within(list).getAllByRole('listitem')
    const text = items.map((item) => item.textContent ?? '')

    expect(text[0]).toContain('E2')
    expect(text[1]).toContain('E1')
    expect(text[2]).toContain('E3')
    expect(text[3]).toContain('E4')
    expect(await screen.findByText('1/4')).toBeInTheDocument()
    const nextEventSection = screen.getByRole('heading', { name: 'Next event focus' }).closest('article')
    expect(nextEventSection).not.toBeNull()
    const nextEventLink = within(nextEventSection as HTMLElement).getByRole('link', { name: 'E1' })
    expect(nextEventLink).toHaveAttribute('href', '/runs/run-a/calendar/E1')
  })

  it('renders completed, next, and upcoming markers with planned-event links and optional history hints', async () => {
    renderWithRoute(<SeasonCalendarPage />, '/runs/run-a/calendar')

    const list = await screen.findByRole('list', { name: 'Season calendar ordered list' })
    const items = within(list).getAllByRole('listitem')

    expect(items[0]).toHaveTextContent('Completed')
    expect(items[1]).toHaveTextContent('Next')
    expect(items[2]).toHaveTextContent('Upcoming')

    expect(within(items[0]).getByRole('link', { name: 'E2' })).toHaveAttribute('href', '/runs/run-a/calendar/E2')
    expect(within(items[0]).getByRole('link', { name: 'history' })).toHaveAttribute('href', '/runs/run-a/events/E2')
    expect(within(items[1]).getByRole('link', { name: 'E1' })).toHaveAttribute('href', '/runs/run-a/calendar/E1')
    expect(within(items[1]).getByRole('link', { name: 'W2' })).toHaveAttribute('href', '/runs/run-a/weeks/2')
  })

  it('filters by week/category/text without re-sorting matching entries', async () => {
    renderWithRoute(<SeasonCalendarPage />, '/runs/run-a/calendar')
    const list = await screen.findByRole('list', { name: 'Season calendar ordered list' })

    await userEvent.selectOptions(screen.getByLabelText('Filter by category'), 'GOLD')
    let items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(2)
    expect(items[0]).toHaveTextContent('E1')
    expect(items[1]).toHaveTextContent('E4')

    await userEvent.selectOptions(screen.getByLabelText('Filter by week'), '10')
    items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(1)
    expect(items[0]).toHaveTextContent('E4')

    await userEvent.clear(screen.getByLabelText('Filter by event or template'))
    await userEvent.type(screen.getByLabelText('Filter by event or template'), 'temp-d')
    items = within(list).getAllByRole('listitem')
    expect(items).toHaveLength(1)
    expect(items[0]).toHaveTextContent('E4')
  })
})
