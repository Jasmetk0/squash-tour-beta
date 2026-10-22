import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminCalendarTemplateDetailPage } from './CalendarTemplateDetailPage'

const api = vi.hoisted(() => ({ getCalendarTemplate: vi.fn(), updateCalendarTemplate: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api,
}))
vi.mock('./CalendarTemplateEditor', () => ({
  CalendarTemplateEditor: () => <div>Editor still available</div>,
  formValueFromTemplate: () => ({}),
}))

function event(id: string, name: string, firstWeek: number, locked: boolean) {
  return {
    id, name, category_code: 'DIAMOND', weeks: [firstWeek], qualification_weeks: [],
    locked, country_code: 'ENG', city: 'London', venue: null,
  }
}

const events = [
  event('zulu', 'Zulu Open', 20, true),
  event('alpha', 'Alpha Open', 3, false),
  event('bravo', 'Bravo Open', 3, true),
]

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/admin/tour-seasons/season-templates/calendar/source']}>
        <Routes>
          <Route path="/admin/tour-seasons/season-templates/calendar/:templateId"
            element={<AdminCalendarTemplateDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Persisted calendar template event inspection', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getCalendarTemplate.mockResolvedValue({
      template: {
        id: 'source', name: 'Source template', description: '', status: 'draft',
        events, created_at: null, updated_at: null, template_fingerprint: null,
      },
      source_path: 'calendar-templates.json', schema_version: 'v1', status: 'ok',
    })
  })

  it('filters event name, lock state and restores the entire list without editing data', async () => {
    mount()
    expect(await screen.findByText('Showing 3 of 3 persisted template events')).toBeInTheDocument()
    expect(screen.getByText('Editor still available')).toBeInTheDocument()
    const table = () => screen.getByRole('table', { name: 'Persisted calendar template events' })
    expect(table().parentElement).toHaveClass('table-responsive')

    const search = screen.getByRole('searchbox', { name: 'Search persisted template events' })
    const locked = screen.getByRole('combobox', { name: 'Event lock filter' })
    fireEvent.change(search, { target: { value: ' BRAVO ' } })
    expect(within(table()).getByText('Bravo Open')).toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 persisted template events')).toBeInTheDocument()
    fireEvent.change(locked, { target: { value: 'unlocked' } })
    expect(screen.getByText('No persisted calendar events match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Persisted calendar template events' })).not.toBeInTheDocument()
    expect(screen.getByText('Editor still available')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear event filters' }))
    expect(search).toHaveValue('')
    expect(locked).toHaveValue('all')
    expect(screen.getByText('Showing 3 of 3 persisted template events')).toBeInTheDocument()
    expect(api.getCalendarTemplate).toHaveBeenCalledTimes(1)
    expect(api.updateCalendarTemplate).not.toHaveBeenCalled()
  })

  it('sorts by first main week with deterministic ID tie-break without mutating source order', async () => {
    mount()
    expect(await screen.findByText('Zulu Open')).toBeInTheDocument()
    const names = () => within(screen.getByRole('table', { name: 'Persisted calendar template events' }))
      .getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent)
    expect(names()).toEqual(['Zulu Open', 'Alpha Open', 'Bravo Open'])
    fireEvent.change(screen.getByRole('combobox', { name: 'Event ordering' }),
      { target: { value: 'week' } })
    expect(names()).toEqual(['Alpha Open', 'Bravo Open', 'Zulu Open'])
    fireEvent.click(screen.getByRole('button', { name: 'Clear event filters' }))
    expect(names()).toEqual(['Zulu Open', 'Alpha Open', 'Bravo Open'])
  })

  it('shows true zero-events message even when search is active', async () => {
    api.getCalendarTemplate.mockResolvedValue({
      template: { id: 'source', name: 'Empty template', status: 'draft', description: '', events: [] },
      source_path: null, schema_version: 'v1', status: 'ok',
    })
    mount()
    expect(await screen.findByText('This persisted Admin calendar template has no events.')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search persisted template events' }),
      { target: { value: 'unavailable' } })
    expect(screen.getByText('Showing 0 of 0 persisted template events')).toBeInTheDocument()
    expect(screen.queryByText('No persisted calendar events match the current filters.')).not.toBeInTheDocument()
  })
})
