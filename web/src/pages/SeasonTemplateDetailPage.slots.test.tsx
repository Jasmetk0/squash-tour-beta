import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsSeasonTemplateDetailPage } from './SeasonTemplateDetailPage'

const api = vi.hoisted(() => ({ getSeasonTemplates: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function slot(slot_id: string, season_week_start: number, tournament_name: string, has_qualification: boolean) {
  return {
    slot_id, tournament_name, category: 'DIAMOND', host_country: 'ENG', region: 'EUROPE',
    season_week_start, season_week_end: season_week_start, duration_weeks: 1,
    has_qualification, qualifying_week_start: has_qualification ? season_week_start - 1 : null,
    main_draw_week_start: season_week_start, source_template_id: 'source',
    notes: null,
  }
}

const slots = [
  slot('zulu', 20, 'Zulu Open', false),
  slot('alpha', 5, 'Alpha Open', true),
  slot('bravo', 5, 'Bravo Open', true),
]

function mount(id = 'source-template') {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={[`/admin/tour-seasons/season-templates/${encodeURIComponent(id)}`]}>
        <Routes>
          <Route path="/admin/tour-seasons/season-templates/:templateId" element={<AdminTourSeasonsSeasonTemplateDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Season template slot inventory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonTemplates.mockResolvedValue({
      templates: [{
        template_id: 'source-template', name: 'Reference template',
        description: 'Read-only example', season_count_supported: null,
        week_count: 61, slot_count: 3, status: 'read_only_foundation',
        source: 'derived_preview:tournament_templates', slots,
      }],
      source_path: 'season-template.json', status: 'read_only_foundation'
    })
  })

  it('filters by name and qualification without overwriting the original source summary', async () => {
    mount()
    expect(await screen.findByText('Showing 3 of 3 template slots')).toBeInTheDocument()
    const table = () => screen.getByRole('table', { name: 'Season template slots table' })
    expect(table().parentElement).toHaveClass('table-responsive')
    expect(screen.getByText('total slots: 3')).toBeInTheDocument()
    const qualifier = screen.getByRole('checkbox', { name: 'Slots with qualification only' })
    fireEvent.click(qualifier)
    expect(screen.getByText('Showing 2 of 3 template slots')).toBeInTheDocument()
    expect(within(table()).queryByText('Zulu Open')).not.toBeInTheDocument()
    expect(screen.getByText('slots with qualification: 2')).toBeInTheDocument()

    const search = screen.getByRole('searchbox', { name: 'Search season template slots' })
    fireEvent.change(search, { target: { value: '  BRAVO ' } })
    expect(screen.getByText('Showing 1 of 3 template slots')).toBeInTheDocument()
    expect(within(table()).getByText('Bravo Open')).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'zulu' } })
    expect(screen.getByText('No template slots match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season template slots table' })).not.toBeInTheDocument()
    expect(screen.getByText('total slots: 3')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear slot filters' }))
    expect(search).toHaveValue('')
    expect(qualifier).not.toBeChecked()
    expect(screen.getByText('Showing 3 of 3 template slots')).toBeInTheDocument()
    expect(api.getSeasonTemplates).toHaveBeenCalledTimes(1)
  })

  it('orders by first week with stable ID tie-break and restores source order', async () => {
    mount()
    expect(await screen.findByText('Showing 3 of 3 template slots')).toBeInTheDocument()
    const order = () => within(screen.getByRole('table', { name: 'Season template slots table' }))
      .getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent)
    expect(order()).toEqual(['zulu', 'alpha', 'bravo'])
    const sort = screen.getByRole('combobox', { name: 'Slot order' })
    fireEvent.change(sort, { target: { value: 'week' } })
    expect(order()).toEqual(['alpha', 'bravo', 'zulu'])
    fireEvent.click(screen.getByRole('button', { name: 'Clear slot filters' }))
    expect(sort).toHaveValue('source')
    expect(order()).toEqual(['zulu', 'alpha', 'bravo'])
    expect(api.getSeasonTemplates).toHaveBeenCalledTimes(1)
  })

  it('distinguishes empty source slots from filter results and absent templates', async () => {
    api.getSeasonTemplates.mockResolvedValue({
      templates: [{
        template_id: 'source-template', name: 'No slots', description: '',
        season_count_supported: null, week_count: 61, slot_count: 0,
        status: 'read_only_foundation', source: 'derived_preview:tournament_templates', slots: [],
      }],
      source_path: null, status: 'read_only_foundation',
    })
    mount()
    expect(await screen.findByText('This season template has no slots.')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search season template slots' }),
      { target: { value: 'anything' } })
    expect(screen.queryByText('No template slots match the current filters.')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 template slots')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Season template slots table' })).not.toBeInTheDocument()
  })
})
