import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsSeasonTemplatesPage } from './SeasonTemplatesPage'

const api = vi.hoisted(() => ({
  getSeasonTemplates: vi.fn(),
  listCalendarTemplates: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api,
}))

function template(id: string, name: string, status: 'draft' | 'active' | 'archived', eventCount: number) {
  return {
    id, name, status, description: '', template_fingerprint: `hash-${id}`,
    events: Array.from({ length: eventCount }, (_, i) => ({ id: `e${i}` })),
  }
}

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><AdminTourSeasonsSeasonTemplatesPage /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Persisted calendar template inventory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonTemplates.mockResolvedValue({ templates: [], source_path: null, status: 'read_only' })
    api.listCalendarTemplates.mockResolvedValue({
      templates: [
        template('zulu_source', 'Zulu', 'active', 1),
        template('alpha_source', 'Alpha', 'draft', 5),
        template('bravo_source', 'Bravo', 'archived', 3),
      ],
      source_path: 'config/calendar_templates', schema_version: 'v1', status: 'ok',
    })
  })

  it('searches trimmed case-insensitive names and IDs without changing the backend list', async () => {
    mount()
    expect(await screen.findByText('Zulu')).toBeInTheDocument()
    expect(screen.getByText('Showing 3 of 3 persisted calendar templates')).toBeInTheDocument()
    const table = () => screen.getByRole('table', { name: 'Persisted calendar templates table' })
    expect(table().parentElement).toHaveClass('table-responsive')
    const search = screen.getByRole('searchbox', { name: 'Search persisted templates' })

    fireEvent.change(search, { target: { value: ' aLpHa ' } })
    expect(within(table()).getByText('Alpha')).toBeInTheDocument()
    expect(within(table()).queryByText('Zulu')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 persisted calendar templates')).toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'BRAVO_SOURCE' } })
    expect(within(table()).getByText('Bravo')).toBeInTheDocument()
    expect(within(table()).queryByText('Alpha')).not.toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'absent' } })
    expect(screen.getByText('No persisted calendar templates match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Persisted calendar templates table' })).not.toBeInTheDocument()
    expect(api.listCalendarTemplates).toHaveBeenCalledTimes(1)
  })

  it('combines exact status and event-count sorting and restores registry order', async () => {
    mount()
    expect(await screen.findByText('Zulu')).toBeInTheDocument()
    const links = () => screen.getAllByRole('link', { name: 'Open persisted calendar template' })
      .map(link => link.getAttribute('href'))
    expect(links()).toEqual([
      '/admin/tour-seasons/season-templates/calendar/zulu_source',
      '/admin/tour-seasons/season-templates/calendar/alpha_source',
      '/admin/tour-seasons/season-templates/calendar/bravo_source',
    ])
    const sort = screen.getByRole('combobox', { name: 'Sort calendar templates' })
    const status = screen.getByRole('combobox', { name: 'Filter calendar template status' })
    fireEvent.change(sort, { target: { value: 'name' } })
    expect(links()).toEqual([
      '/admin/tour-seasons/season-templates/calendar/alpha_source',
      '/admin/tour-seasons/season-templates/calendar/bravo_source',
      '/admin/tour-seasons/season-templates/calendar/zulu_source',
    ])
    fireEvent.change(sort, { target: { value: 'events' } })
    expect(links()[0]).toBe('/admin/tour-seasons/season-templates/calendar/alpha_source')
    fireEvent.change(status, { target: { value: 'archived' } })
    expect(links()).toEqual(['/admin/tour-seasons/season-templates/calendar/bravo_source'])
    expect(screen.getByText('Showing 1 of 3 persisted calendar templates')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear template filters' }))
    expect(sort).toHaveValue('source')
    expect(status).toHaveValue('all')
    expect(links()[0]).toBe('/admin/tour-seasons/season-templates/calendar/zulu_source')
    expect(screen.getByRole('button', { name: 'Clear template filters' })).toBeDisabled()
    expect(api.listCalendarTemplates).toHaveBeenCalledTimes(1)
  })

  it('distinguishes an empty registry from filters hiding existing templates', async () => {
    api.listCalendarTemplates.mockResolvedValue({
      templates: [], source_path: null, schema_version: 'v1', status: 'ok',
    })
    mount()
    expect(await screen.findByText('No persisted Admin calendar templates exist yet.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 persisted calendar templates')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search persisted templates' }),
      { target: { value: 'nothing' } })
    expect(screen.queryByText('No persisted calendar templates match the current filters.')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Persisted calendar templates table' })).not.toBeInTheDocument()
  })
})
