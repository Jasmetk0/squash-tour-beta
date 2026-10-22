import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminTourSeasonsComparePage } from './CalendarComparePage'

const api = vi.hoisted(() => ({
  applyCalendarTemplateToPlanningCalendar: vi.fn(),
  compareCalendarTemplateDryRun: vi.fn(),
  getSeasonRegistry: vi.fn(),
  getSeasonTemplates: vi.fn(),
  listCalendarTemplates: vi.fn(),
  listPlanningSeasonCalendars: vi.fn(),
}))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

function response(source_template_id: string, target_season_label: string, target_source = 'planning_calendar') {
  return {
    source_template_id, target_season_label, target_source,
    dry_run: true, mutation_performed: false, status: 'ok', policy: 'copy_missing_only',
    target_fingerprint: 'fingerprint', source_template_fingerprint: 'source-fp',
    target_calendar_fingerprint: 'calendar-fp', target_calendar_exists: true,
    diff_fingerprint: 'diff-fp',
    summary: {
      same_count: 0, missing_from_target_count: 1, only_in_target_count: 0,
      conflict_count: 0, locked_target_preserved_count: 0,
      selected_source_event_count: 1, source_event_count: 1, target_event_count: 0,
    },
    items: [],
    safety: { read_only: true, mutation_performed: false, apply_endpoint_enabled: true, message: 'Review only' },
  }
}

function mount() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter><AdminTourSeasonsComparePage /></MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('Calendar Compare review must match the currently selected inputs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getSeasonRegistry.mockResolvedValue({ start_season: '2000/01', end_season: '2049/50', season_count: 50, week_count: 61 })
    api.getSeasonTemplates.mockResolvedValue({ templates: [] })
    api.listCalendarTemplates.mockResolvedValue({ templates: [
      { id: 'source-a', name: 'Template A' },
      { id: 'source-b', name: 'Template B' },
    ] })
    api.listPlanningSeasonCalendars.mockResolvedValue({ calendars: [
      { normalized_season_label: '2006/07', season_label: '2006/07', events: [], status: 'draft' },
      { normalized_season_label: '2007/08', season_label: '2007/08', events: [], status: 'draft' },
    ] })
    api.compareCalendarTemplateDryRun.mockImplementation(async (input: {
      source_template_id: string; target_season_label: string; target_source?: string
    }) => response(input.source_template_id, input.target_season_label, input.target_source))
  })

  async function establishReviewedDiff() {
    mount()
    const mode = await screen.findByRole('combobox', { name: 'Target source' })
    fireEvent.change(mode, { target: { value: 'planning_calendar' } })
    const source = screen.getByRole('combobox', { name: 'Source template' })
    const target = await screen.findByRole('combobox', { name: 'Planning calendar' })
    await waitFor(() => expect(source).toHaveValue('source-a'))
    fireEvent.click(screen.getByRole('button', { name: 'Run backend compare dry-run' }))
    expect(await screen.findByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).toBeInTheDocument()
    return { mode, source, target }
  }

  it('invalidates reviewed apply when the source template or season changes', async () => {
    const { source, target } = await establishReviewedDiff()
    fireEvent.change(source, { target: { value: 'source-b' } })
    expect(screen.queryByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent('differs from the reviewed dry-run')
    fireEvent.change(source, { target: { value: 'source-a' } })
    expect(screen.getByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).toBeInTheDocument()
    fireEvent.change(target, { target: { value: '2007/08' } })
    expect(screen.queryByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).not.toBeInTheDocument()
    expect(api.applyCalendarTemplateToPlanningCalendar).not.toHaveBeenCalled()
  })

  it('does not allow a planning-calendar review to be applied in payload mode', async () => {
    const { mode } = await establishReviewedDiff()
    fireEvent.change(mode, { target: { value: 'payload' } })
    expect(screen.queryByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).not.toBeInTheDocument()
    expect(api.applyCalendarTemplateToPlanningCalendar).not.toHaveBeenCalled()
  })

  it('does not trust a backend response identifying a different source or target', async () => {
    api.compareCalendarTemplateDryRun.mockResolvedValue(response('unexpected-source', '2006/07'))
    mount()
    fireEvent.change(await screen.findByRole('combobox', { name: 'Target source' }),
      { target: { value: 'planning_calendar' } })
    await waitFor(() => expect(screen.getByRole('combobox', { name: 'Source template' })).toHaveValue('source-a'))
    fireEvent.click(screen.getByRole('button', { name: 'Run backend compare dry-run' }))
    expect(await screen.findByText('Review only')).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Apply reviewed diff to planning calendar' })).not.toBeInTheDocument()
    expect(api.applyCalendarTemplateToPlanningCalendar).not.toHaveBeenCalled()
  })
})
