import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { SeasonCalendarPreview } from './SeasonCalendarPreview'

const api = vi.hoisted(() => ({ getSeasonCalendar: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function event(n: number) {
  return {
    event_id: `event-${n}`, event_name: `Open ${n}`, status: 'planned',
    season_week: n, start_season_week: n, category: 'OPEN', host_country: 'CZE',
    region: 'EUROPE', template_id: `template-${n}`, ranking_status: 'unranked',
  }
}
function response(events: ReturnType<typeof event>[]) {
  return {
    calendar: { events },
    summary: { event_count: events.length, persisted: true, first_event_week: events[0]?.season_week ?? null,
      last_event_week: events.length ? events[events.length - 1].season_week : null },
    validation_warnings: [],
  }
}
function mount(label = '2000/01') {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><SeasonCalendarPreview seasonLabelRaw={label} /></MemoryRouter>
  </QueryClientProvider>)
}

describe('Season calendar preview information fidelity', () => {
  beforeEach(() => vi.clearAllMocks())

  it('limits the table to ten but reports the true total count', async () => {
    api.getSeasonCalendar.mockResolvedValue(response(Array.from({ length: 12 }, (_, i) => event(i + 1))))
    mount()
    const table = await screen.findByRole('table', { name: 'Season calendar preview first events' })
    expect(table.parentElement).toHaveClass('table-responsive')
    expect(within(table).getAllByRole('row')).toHaveLength(11)
    expect(within(table).getByText('Open 10')).toBeInTheDocument()
    expect(within(table).queryByText('Open 11')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 10 of 12 calendar events. Full calendar tooling remains in Seasons.')).toBeInTheDocument()
    expect(api.getSeasonCalendar).toHaveBeenCalledTimes(1)
  })

  it('reports a nonempty short preview without claiming exactly ten events', async () => {
    api.getSeasonCalendar.mockResolvedValue(response([event(1)]))
    mount()
    expect(await screen.findByText('Showing 1 of 1 calendar events. Full calendar tooling remains in Seasons.')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Season calendar preview first events' })).toBeInTheDocument()
  })

  it('separates a loaded zero-event calendar from an unavailable calendar', async () => {
    api.getSeasonCalendar.mockResolvedValue(response([]))
    mount()
    expect(await screen.findByText('Calendar contains no events.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 calendar events. Full calendar tooling remains in Seasons.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season calendar preview first events' })).not.toBeInTheDocument()
    expect(screen.queryByText('No calendar exists yet for this season.')).not.toBeInTheDocument()
  })
})
