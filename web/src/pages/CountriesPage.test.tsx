import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CountriesPage } from './CountriesPage'
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
    listCountries: vi.fn(),
    getCountriesMetadata: vi.fn(),
    createCountry: vi.fn(),
    updateCountry: vi.fn(),
    deleteCountry: vi.fn()
  }
})

vi.mock('../api/client', () => api)

describe('CountriesPage', () => {
  beforeEach(() => {
    api.listCountries.mockReset()
    api.getCountriesMetadata.mockReset()
    api.createCountry.mockReset()
    api.updateCountry.mockReset()
    api.deleteCountry.mockReset()

    api.listCountries.mockResolvedValue({
      countries: [
        {
          code: 'AAA',
          name: 'Alpha',
          flag_asset: null,
          region: 'EUROPE',
          population: 1_000_000,
          wealth_support: 3,
          squash_popularity: 4,
          squash_tradition: 2,
          system_quality: 5
        }
      ]
    })
    api.getCountriesMetadata.mockResolvedValue({
      dataset_status: 'temporary_seed_demo',
      country_count: 1,
      source_path: 'config/world/countries.json'
    })
    api.createCountry.mockImplementation(async (payload) => payload)
    api.updateCountry.mockImplementation(async (_code, payload) => payload)
    api.deleteCountry.mockResolvedValue(undefined)
  })

  it('renders countries list and metadata', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')

    expect(await screen.findByRole('heading', { name: 'Countries Editor' })).toBeInTheDocument()
    expect(await screen.findByText('Dataset status')).toBeInTheDocument()
    expect(await screen.findByRole('cell', { name: 'AAA' })).toBeInTheDocument()
  })

  it('supports create flow', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')

    await screen.findByRole('button', { name: 'Create country' })
    await userEvent.clear(screen.getByLabelText('Code (3 letters)'))
    await userEvent.type(screen.getByLabelText('Code (3 letters)'), 'bbb')
    await userEvent.clear(screen.getByLabelText('Name'))
    await userEvent.type(screen.getByLabelText('Name'), 'Beta')
    await userEvent.clear(screen.getByLabelText('Region'))
    await userEvent.type(screen.getByLabelText('Region'), 'ASIA')
    await userEvent.clear(screen.getByLabelText('Population'))
    await userEvent.type(screen.getByLabelText('Population'), '2500000')

    await userEvent.click(screen.getByRole('button', { name: 'Create country' }))

    await waitFor(() => expect(api.createCountry).toHaveBeenCalled())
    expect(api.createCountry.mock.calls[0][0]).toEqual(
      expect.objectContaining({ code: 'BBB', name: 'Beta', region: 'ASIA', population: 2500000 })
    )
  })

  it('supports edit flow', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')

    const row = (await screen.findByRole('cell', { name: 'AAA' })).closest('tr') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Edit' }))

    const nameInput = screen.getByLabelText('Name')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Alpha Updated')
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }))

    await waitFor(() =>
      expect(api.updateCountry).toHaveBeenCalledWith('AAA', expect.objectContaining({ name: 'Alpha Updated' }))
    )
  })

  it('supports delete flow', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    renderWithRoute(<CountriesPage />, '/world/countries')

    const row = (await screen.findByRole('cell', { name: 'AAA' })).closest('tr') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Edit' }))

    await userEvent.click(screen.getByRole('button', { name: 'Delete country' }))

    await waitFor(() => expect(api.deleteCountry).toHaveBeenCalled())
    expect(api.deleteCountry.mock.calls[0][0]).toBe('AAA')
    confirmSpy.mockRestore()
  })

  it('renders validation/error feedback from API failures', async () => {
    api.createCountry.mockRejectedValue(new api.ApiError('validation failed', 422))
    renderWithRoute(<CountriesPage />, '/world/countries')

    await screen.findByRole('button', { name: 'Create country' })
    await userEvent.clear(screen.getByLabelText('Code (3 letters)'))
    await userEvent.type(screen.getByLabelText('Code (3 letters)'), 'bad')
    await userEvent.clear(screen.getByLabelText('Name'))
    await userEvent.type(screen.getByLabelText('Name'), 'Bad Country')
    await userEvent.clear(screen.getByLabelText('Region'))
    await userEvent.type(screen.getByLabelText('Region'), 'EUROPE')
    await userEvent.click(screen.getByRole('button', { name: 'Create country' }))

    expect(await screen.findByText(/Backend validation rejected the payload./i)).toBeInTheDocument()
  })
})
