import { fireEvent, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { TournamentTemplatesPage } from './TournamentTemplatesPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return {
    ApiError,
    listTournamentTemplates: vi.fn(),
    getTournamentTemplatesMetadata: vi.fn(),
    createTournamentTemplate: vi.fn(),
    updateTournamentTemplate: vi.fn(),
    deleteTournamentTemplate: vi.fn(),
    exportTournamentTemplates: vi.fn(),
    importTournamentTemplates: vi.fn()
  }
})

vi.mock('../api/client', () => api)

const template = {
  template_id: 'custom_opener_16',
  tour_level: 'WORLD_TOUR',
  category: 'CUSTOM_OPENER',
  event_name: 'Custom Opener',
  region: 'EUROPE',
  host_country: 'ENG',
  main_draw_size: 16,
  qualification_draw_size: 8,
  seeds_count: 4,
  qualifier_spots: 2,
  wild_cards: 2,
  byes: 0,
  lucky_loser_rules: { enabled: true, max_spots: 1, replacement_window: 'pre_main_draw_round_1' },
  point_distribution_ref: null,
  point_distribution: { winner: 500, finalist: 300, semifinalist: 180, quarterfinalist: 90, round_of_16: 45, round_of_32: 0 },
  event_duration_days: 5,
  qualification_duration_days: 1,
  preferred_week_type: 'standard',
  seasonal_grouping: 'custom_swing'
}

describe('TournamentTemplatesPage', () => {
  beforeEach(() => {
    api.listTournamentTemplates.mockReset()
    api.getTournamentTemplatesMetadata.mockReset()
    api.createTournamentTemplate.mockReset()
    api.updateTournamentTemplate.mockReset()
    api.deleteTournamentTemplate.mockReset()
    api.exportTournamentTemplates.mockReset()
    api.importTournamentTemplates.mockReset()

    api.listTournamentTemplates.mockResolvedValue({ templates: [template] })
    api.getTournamentTemplatesMetadata.mockResolvedValue({
      template_count: 1,
      source_path: 'config/tournament_templates/mvp_templates.json',
      referenced_by_calendar: true,
      referenced_template_ids: ['custom_opener_16']
    })
    api.createTournamentTemplate.mockImplementation(async (payload) => payload)
    api.updateTournamentTemplate.mockImplementation(async (_templateId, payload) => payload)
    api.deleteTournamentTemplate.mockResolvedValue(undefined)
    api.exportTournamentTemplates.mockResolvedValue({ templates: [template] })
    api.importTournamentTemplates.mockResolvedValue({ ok: true, dry_run: true, template_count: 1, errors: [] })
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:templates')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  it('renders existing templates and import/export controls', async () => {
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')

    expect(await screen.findByRole('heading', { name: 'Tournament Templates' })).toBeInTheDocument()
    expect(await screen.findByText('Dataset status')).toBeInTheDocument()
    expect(await screen.findByRole('cell', { name: 'custom_opener_16' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Export templates JSON' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Validate import JSON' })).toBeInTheDocument()
    expect(await screen.findByText(/Examples you may create later/i)).toBeInTheDocument()
  })

  it('filters template ID/category/tour and activity without modifying the editor or data', async () => {
    api.listTournamentTemplates.mockResolvedValue({
      templates: [
        template,
        { ...template, template_id: 'inactive_iron', category: 'IRON', tour_level: 'ELITE_TOUR', active: false },
        { ...template, template_id: 'second_world', category: 'WORLD_FINALS', active: true },
      ]
    })
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')
    expect(await screen.findByText('Showing 3 of 3 tournament templates')).toBeInTheDocument()
    const table = () => screen.getByRole('table', { name: 'Tournament template inventory' })
    expect(table().parentElement).toHaveClass('table-responsive')
    const search = screen.getByRole('searchbox', { name: 'Search tournament templates' })
    const active = screen.getByRole('combobox', { name: 'Filter active templates' })

    fireEvent.change(search, { target: { value: '  elite_tour ' } })
    expect(screen.getByText('Showing 1 of 3 tournament templates')).toBeInTheDocument()
    expect(within(table()).getByRole('cell', { name: 'inactive_iron' })).toBeInTheDocument()
    fireEvent.change(active, { target: { value: 'active' } })
    expect(screen.getByText('No tournament templates match the current filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Tournament template inventory' })).not.toBeInTheDocument()

    fireEvent.change(active, { target: { value: 'inactive' } })
    expect(within(table()).getByRole('cell', { name: 'inactive_iron' })).toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 tournament templates')).toBeInTheDocument()
    fireEvent.change(search, { target: { value: '  iron ' } })
    expect(within(table()).getByRole('cell', { name: 'inactive_iron' })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear template list filters' }))
    expect(search).toHaveValue('')
    expect(active).toHaveValue('all')
    expect(screen.getByText('Showing 3 of 3 tournament templates')).toBeInTheDocument()
    expect(api.listTournamentTemplates).toHaveBeenCalledTimes(1)
  })

  it('keeps selected editor state when its template disappears from filtered inventory', async () => {
    api.listTournamentTemplates.mockResolvedValue({
      templates: [template, { ...template, template_id: 'inactive_iron', category: 'IRON', active: false }],
    })
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')
    const table = () => screen.getByRole('table', { name: 'Tournament template inventory' })
    await screen.findByRole('cell', { name: 'custom_opener_16' })
    const row = within(table()).getByRole('cell', { name: 'custom_opener_16' }).closest('tr')
    expect(row).not.toBeNull()
    fireEvent.click(within(row as HTMLTableRowElement).getByRole('button', { name: 'Edit' }))
    expect(screen.getByRole('heading', { name: 'Edit custom_opener_16' })).toBeInTheDocument()
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter active templates' }),
      { target: { value: 'inactive' } })
    expect(within(table()).queryByRole('cell', { name: 'custom_opener_16' })).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Edit custom_opener_16' })).toBeInTheDocument()
    expect(screen.getByLabelText('Template ID')).toHaveValue('custom_opener_16')
    expect(api.updateTournamentTemplate).not.toHaveBeenCalled()
    expect(api.listTournamentTemplates).toHaveBeenCalledTimes(1)
  })

  it('distinguishes a genuinely empty registry from filtered-out records', async () => {
    api.listTournamentTemplates.mockResolvedValue({ templates: [] })
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')
    expect(await screen.findByText('No tournament templates. Create the first user-defined template with the form.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 tournament templates')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search tournament templates' }),
      { target: { value: 'absent' } })
    expect(screen.queryByText('No tournament templates match the current filters.')).not.toBeInTheDocument()
  })

  it('submits create form payload for a user-defined category', async () => {
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')

    await screen.findByRole('button', { name: 'Create template' })
    await userEvent.type(screen.getByLabelText('Template ID'), 'user diamond 32')
    await userEvent.type(screen.getByLabelText('Category'), 'USER_DIAMOND')
    await userEvent.type(screen.getByLabelText('Event/category name'), 'User Diamond')
    await userEvent.type(screen.getByLabelText('Region/default host region'), 'EUROPE')
    await userEvent.type(screen.getByLabelText('Host country default (3 letters)'), 'eng')
    fireEvent.change(screen.getByLabelText('Inline point distribution (JSON or null)'), {
      target: { value: '{"winner":1000,"finalist":650,"semifinalist":400,"quarterfinalist":200,"round_of_16":100,"round_of_32":50}' }
    })

    await userEvent.click(screen.getByRole('button', { name: 'Create template' }))

    await waitFor(() => expect(api.createTournamentTemplate).toHaveBeenCalled())
    expect(api.createTournamentTemplate.mock.calls[0][0]).toEqual(expect.objectContaining({
      template_id: 'user_diamond_32',
      category: 'USER_DIAMOND',
      event_name: 'User Diamond',
      host_country: 'ENG',
      point_distribution: expect.objectContaining({ winner: 1000 })
    }))
  })

  it('submits update form payload for an existing template', async () => {
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')

    const row = (await screen.findByRole('cell', { name: 'custom_opener_16' })).closest('tr')
    expect(row).not.toBeNull()
    await userEvent.click(within(row as HTMLTableRowElement).getByRole('button', { name: 'Edit' }))
    await userEvent.clear(screen.getByLabelText('Event/category name'))
    await userEvent.type(screen.getByLabelText('Event/category name'), 'Custom Opener Updated')
    await userEvent.click(screen.getByRole('button', { name: 'Update template' }))

    await waitFor(() => expect(api.updateTournamentTemplate).toHaveBeenCalled())
    expect(api.updateTournamentTemplate.mock.calls[0][0]).toBe('custom_opener_16')
    expect(api.updateTournamentTemplate.mock.calls[0][1]).toEqual(expect.objectContaining({ event_name: 'Custom Opener Updated' }))
  })

  it('duplicate action pre-fills a new template form', async () => {
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')

    const row = (await screen.findByRole('cell', { name: 'custom_opener_16' })).closest('tr')
    expect(row).not.toBeNull()
    await userEvent.click(within(row as HTMLTableRowElement).getByRole('button', { name: 'Duplicate' }))

    expect(screen.getByLabelText('Template ID')).toHaveValue('')
    expect(screen.getByLabelText('Event/category name')).toHaveValue('Custom Opener Copy')
    expect(await screen.findByText(/Set a unique template_id/i)).toBeInTheDocument()
  })

  it('validates import JSON through the API', async () => {
    renderWithRoute(<TournamentTemplatesPage />, '/admin/tournament-templates')

    await screen.findByRole('button', { name: 'Validate import JSON' })
    fireEvent.change(screen.getByLabelText('Tournament templates JSON'), { target: { value: JSON.stringify({ templates: [template] }) } })
    await userEvent.click(screen.getByRole('button', { name: 'Validate import JSON' }))

    await waitFor(() => expect(api.importTournamentTemplates).toHaveBeenCalled())
    expect(api.importTournamentTemplates.mock.calls[0][0]).toEqual({ dataset: { templates: [template] }, dry_run: true })
  })
})
