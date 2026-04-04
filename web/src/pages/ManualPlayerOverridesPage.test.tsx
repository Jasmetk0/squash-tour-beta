import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ManualPlayerOverridesPage } from './ManualPlayerOverridesPage'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => ({
  listManualPlayerOverrides: vi.fn(),
  createManualPlayerOverride: vi.fn(),
  updateManualPlayerOverride: vi.fn(),
  deleteManualPlayerOverride: vi.fn()
}))

vi.mock('../api/client', () => api)

describe('ManualPlayerOverridesPage', () => {
  beforeEach(() => {
    api.listManualPlayerOverrides.mockReset()
    api.createManualPlayerOverride.mockReset()
    api.updateManualPlayerOverride.mockReset()
    api.deleteManualPlayerOverride.mockReset()

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
          attribute_overrides: null,
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
})
