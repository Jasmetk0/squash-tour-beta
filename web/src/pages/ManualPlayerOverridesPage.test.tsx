import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ManualPlayerOverridesPage } from './ManualPlayerOverridesPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listManualPlayerOverrides: vi.fn(),
  createManualPlayerOverride: vi.fn(),
  updateManualPlayerOverride: vi.fn(),
  deleteManualPlayerOverride: vi.fn(),
  exportManualPlayerOverridesCsv: vi.fn(),
  importManualPlayerOverrides: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('ManualPlayerOverridesPage', () => {
  beforeEach(() => {
    vi.stubGlobal('confirm', vi.fn(() => true))
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:mock'), revokeObjectURL: vi.fn() })
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    api.listManualPlayerOverrides.mockReset()
    api.createManualPlayerOverride.mockReset()
    api.updateManualPlayerOverride.mockReset()
    api.deleteManualPlayerOverride.mockReset()
    api.exportManualPlayerOverridesCsv.mockReset()
    api.importManualPlayerOverrides.mockReset()

    api.listManualPlayerOverrides.mockResolvedValue({
      overrides: [
        {
          override_id: 'aaa-manual-2027',
          season: 2027,
          country_code: 'AAA',
          player_name: 'Manual Talent',
          age: 18,
          profile_tier: 'elite',
          quality_band_override: null,
          attribute_overrides: { technique: 80, movement: null, physical: null, mental: null },
          hidden_trait_overrides: null,
          is_exceptional: true,
          enabled: true,
          notes: null
        }
      ]
    })
    api.createManualPlayerOverride.mockImplementation(async (payload) => payload)
    api.updateManualPlayerOverride.mockImplementation(async (_id, payload) => payload)
    api.deleteManualPlayerOverride.mockResolvedValue(undefined)
    api.exportManualPlayerOverridesCsv.mockResolvedValue('override_id,season\naaa-manual-2027,2027\n')
    api.importManualPlayerOverrides.mockResolvedValue({
      ok: true,
      dry_run: true,
      summary: { total_records: 1, new_records: 0, updated_records: 1, unchanged_records: 0 },
      errors: []
    })
  })

  it('renders list and supports create/edit/delete', async () => {
    renderWithRoute(<ManualPlayerOverridesPage />, '/world/manual-player-overrides')

    expect(await screen.findByRole('heading', { name: 'Manual Player Overrides' })).toBeInTheDocument()
    const row = (await screen.findByRole('cell', { name: 'aaa-manual-2027' })).closest('tr') as HTMLElement

    await userEvent.click(within(row).getByRole('button', { name: 'Edit' }))
    await userEvent.clear(screen.getByLabelText('Player name'))
    await userEvent.type(screen.getByLabelText('Player name'), 'Updated Talent')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() => expect(api.updateManualPlayerOverride).toHaveBeenCalled())

    await userEvent.click(screen.getByRole('button', { name: 'Delete override' }))
    await waitFor(() => expect(api.deleteManualPlayerOverride).toHaveBeenCalled())

    await userEvent.click(screen.getByRole('button', { name: 'New' }))
    await userEvent.type(screen.getByLabelText('Override ID'), 'new-id')
    await userEvent.type(screen.getByLabelText('Country code'), 'BBB')
    await userEvent.type(screen.getByLabelText('Player name'), 'New Player')
    await userEvent.click(screen.getByRole('button', { name: 'Create override' }))

    await waitFor(() => expect(api.createManualPlayerOverride).toHaveBeenCalled())
  })

  it('supports duplicate override flow safely', async () => {
    renderWithRoute(<ManualPlayerOverridesPage />, '/world/manual-player-overrides')

    const row = (await screen.findByRole('cell', { name: 'aaa-manual-2027' })).closest('tr') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Duplicate override' }))

    expect(screen.getByLabelText('Override ID')).toHaveValue('')
    expect(screen.getByLabelText('Player name')).toHaveValue('Manual Talent')
    expect(screen.getByText('Duplicate template loaded. Enter a new unique Override ID before saving.')).toBeInTheDocument()
  })

  it('shows import/export actions and apply confirm flow', async () => {
    renderWithRoute(<ManualPlayerOverridesPage />, '/world/manual-player-overrides')

    expect(await screen.findByRole('button', { name: 'Export overrides CSV' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Export overrides CSV' }))
    await waitFor(() => expect(api.exportManualPlayerOverridesCsv).toHaveBeenCalled())

    await userEvent.type(screen.getByPlaceholderText('Paste manual overrides CSV here'), 'override_id,season\naaa,2027')
    await userEvent.click(screen.getByRole('button', { name: 'Validate import (dry run)' }))
    await waitFor(() =>
      expect(api.importManualPlayerOverrides).toHaveBeenCalledWith(
        { csv_text: 'override_id,season\naaa,2027', dry_run: true },
        expect.anything()
      )
    )

    api.importManualPlayerOverrides.mockResolvedValueOnce({
      ok: true,
      dry_run: false,
      summary: { total_records: 1, new_records: 1, updated_records: 0, unchanged_records: 0 },
      errors: []
    })
    await userEvent.click(screen.getByRole('button', { name: 'Apply import' }))
    await waitFor(() =>
      expect(api.importManualPlayerOverrides).toHaveBeenCalledWith(
        { csv_text: 'override_id,season\naaa,2027', dry_run: false },
        expect.anything()
      )
    )
    expect(globalThis.confirm).toHaveBeenCalled()
  })

  it('shows import validation errors', async () => {
    api.importManualPlayerOverrides.mockResolvedValueOnce({
      ok: false,
      dry_run: true,
      summary: { total_records: 0, new_records: 0, updated_records: 0, unchanged_records: 0 },
      errors: [{ row_number: 2, field: 'override_id', message: 'duplicate override_id' }]
    })

    renderWithRoute(<ManualPlayerOverridesPage />, '/world/manual-player-overrides')

    await userEvent.type(screen.getByPlaceholderText('Paste manual overrides CSV here'), 'bad csv')
    await userEvent.click(screen.getByRole('button', { name: 'Validate import (dry run)' }))

    expect(await screen.findByText('Import validation failed.')).toBeInTheDocument()
    expect(screen.getByText('row 2 · field override_id · duplicate override_id')).toBeInTheDocument()
  })
})
