import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminCalendarTemplateNewPage } from './CalendarTemplateNewPage'

const api = vi.hoisted(() => ({ createCalendarTemplate: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api,
}))
vi.mock('./CalendarTemplateEditor', () => ({
  CalendarTemplateEditor: ({ onSubmit }: { onSubmit: (payload: unknown) => void }) =>
    <button type="button" onClick={() => onSubmit({
      id: 'new event?', name: 'Created Template', description: '', status: 'draft', events: [],
    })}>Submit mock template</button>,
  emptyCalendarTemplateFormValue: () => ({ id: '', name: '', description: '', status: 'draft', events: [] }),
}))

function ResultRoute() {
  const location = useLocation()
  return <p data-testid="created-location">{location.pathname}</p>
}

function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  client.setQueryData(['calendar-templates'], { templates: [], source_path: null })
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/admin/tour-seasons/season-templates/calendar/new']}>
        <Routes>
          <Route path="/admin/tour-seasons/season-templates/calendar/new" element={<AdminCalendarTemplateNewPage />} />
          <Route path="/admin/tour-seasons/season-templates/calendar/:templateId" element={<ResultRoute />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
  return client
}

describe('Persisted Admin calendar template creation inventory refresh', () => {
  beforeEach(() => vi.clearAllMocks())

  it('invalidates the cached template list on successful creation and safely navigates', async () => {
    api.createCalendarTemplate.mockResolvedValue({ template: { id: 'new event?' } })
    const client = mount()
    expect(client.getQueryState(['calendar-templates'])?.isInvalidated).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: 'Submit mock template' }))
    expect(await screen.findByTestId('created-location')).toHaveTextContent(
      '/admin/tour-seasons/season-templates/calendar/new%20event%3F'
    )
    expect(client.getQueryState(['calendar-templates'])?.isInvalidated).toBe(true)
    expect(api.createCalendarTemplate).toHaveBeenCalledTimes(1)
  })

  it('leaves the existing list cache intact when creation is rejected', async () => {
    api.createCalendarTemplate.mockRejectedValue(new Error('request denied'))
    const client = mount()
    fireEvent.click(screen.getByRole('button', { name: 'Submit mock template' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Create failed: request denied')
    expect(client.getQueryState(['calendar-templates'])?.isInvalidated).toBe(false)
    expect(screen.getByRole('button', { name: 'Submit mock template' })).toBeInTheDocument()
  })
})
