import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SeasonCalendarPage } from './SeasonCalendarPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  getRun: vi.fn(),
  listEvents: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('SeasonCalendarPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
