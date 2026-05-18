import { fireEvent, screen, waitFor, within } from '@testing-library/react'
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
    deleteCountry: vi.fn(),
    importCountries: vi.fn(),
    exportCountriesCsv: vi.fn()
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
    api.importCountries.mockReset()
    api.exportCountriesCsv.mockReset()

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
          system_quality: 5,
          competition_density: 4.5,
          federation_quality: 4,
          court_count: 120,
          style_dna: { attrition: 0.2 }
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
    api.exportCountriesCsv.mockResolvedValue(
      'code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality,competition_density,federation_quality,court_count\n'
    )
    api.importCountries.mockResolvedValue({
      ok: true,
      dry_run: true,
      summary: { total_records: 1, new_records: 0, updated_records: 1, unchanged_records: 0 },
      errors: []
    })

    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  it('renders countries list and metadata', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')

    expect(await screen.findByRole('heading', { name: 'Countries Editor' })).toBeInTheDocument()
    expect(await screen.findByText('Dataset status')).toBeInTheDocument()
    expect(await screen.findByRole('cell', { name: 'AAA' })).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Export CSV' })).toBeInTheDocument()
    expect(await screen.findByRole('cell', { name: '4.5' })).toBeInTheDocument()
    expect(await screen.findByText(/Current saves affect future generation workflows/i)).toBeInTheDocument()
  })

  it('supports create flow', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')

    await screen.findByRole('button', { name: '+ Create Country' })
    await userEvent.click(screen.getByRole('button', { name: '+ Create Country' }))
    await userEvent.clear(screen.getByLabelText('Code (3 letters)'))
    await userEvent.type(screen.getByLabelText('Code (3 letters)'), 'bbb')
    await userEvent.clear(screen.getByLabelText('Name'))
    await userEvent.type(screen.getByLabelText('Name'), 'Beta')
    const regionInputs = screen.getAllByLabelText('Region')
    await userEvent.clear(regionInputs[1])
    await userEvent.type(regionInputs[1], 'ASIA')
    await userEvent.clear(screen.getByLabelText('Population'))
    await userEvent.type(screen.getByLabelText('Population'), '2500000')
    await userEvent.clear(screen.getByLabelText('Competition density (1..5)'))
    await userEvent.type(screen.getByLabelText('Competition density (1..5)'), '4.2')
    await userEvent.clear(screen.getByLabelText('Federation quality (1..5)'))
    await userEvent.type(screen.getByLabelText('Federation quality (1..5)'), '4')
    await userEvent.clear(screen.getByLabelText('Court count (optional)'))
    await userEvent.type(screen.getByLabelText('Court count (optional)'), '90')
    fireEvent.change(screen.getByLabelText('Style DNA (JSON numeric modifiers)'), { target: { value: '{"front_court":0.3}' } })

    await userEvent.click(screen.getByRole('button', { name: 'Create Country' }))

    await waitFor(() => expect(api.createCountry).toHaveBeenCalled())
    expect(api.createCountry.mock.calls[0][0]).toEqual(
      expect.objectContaining({
        code: 'BBB',
        name: 'Beta',
        region: 'ASIA',
        population: 2500000,
        competition_density: 4.2,
        federation_quality: 4,
        court_count: 90,
        style_dna: { front_court: 0.3 }
      })
    )
  })

  it('supports duplicate action prefilling create flow', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')

    const row = (await screen.findByRole('cell', { name: 'AAA' })).closest('tr') as HTMLElement
    await userEvent.click(within(row).getByRole('button', { name: 'Copy' }))

    expect(screen.getByLabelText('Code (3 letters)')).toHaveValue('')
    expect(screen.getByLabelText('Name')).toHaveValue('Alpha Copy')
    expect(screen.getByLabelText('Court count (optional)')).toHaveValue(120)
    expect(await screen.findByText(/Set a unique 3-letter code before saving/i)).toBeInTheDocument()
  })

  it('supports import success path via dry-run', async () => {
    renderWithRoute(<CountriesPage />, '/world/countries')
    await screen.findByRole('button', { name: 'Import / Export' })
    await userEvent.click(screen.getByRole('button', { name: 'Import / Export' }))
    await screen.findByRole('button', { name: 'Validate import (dry run)' })

    await userEvent.type(screen.getByLabelText('CSV payload'), 'code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality\nAAA,Alpha,,EUROPE,1000000,3,4,2,5')
    await userEvent.click(screen.getByRole('button', { name: 'Validate import (dry run)' }))

    await waitFor(() => expect(api.importCountries).toHaveBeenCalled())
    expect(api.importCountries.mock.calls[0][0]).toEqual(
      expect.objectContaining({ dry_run: true, csv_text: expect.stringContaining('code,name') })
    )
    expect(await screen.findByText(/Dry-run succeeded/i)).toBeInTheDocument()
  })

  it('shows import validation errors', async () => {
    api.importCountries.mockResolvedValueOnce({
      ok: false,
      dry_run: true,
      summary: { total_records: 0, new_records: 0, updated_records: 0, unchanged_records: 0 },
      errors: [{ row_number: 2, field: 'wealth_support', message: 'Input should be less than or equal to 5' }]
    })

    renderWithRoute(<CountriesPage />, '/world/countries')
    await screen.findByRole('button', { name: 'Import / Export' })
    await userEvent.click(screen.getByRole('button', { name: 'Import / Export' }))
    await screen.findByRole('button', { name: 'Validate import (dry run)' })

    await userEvent.type(screen.getByLabelText('CSV payload'), 'bad')
    await userEvent.click(screen.getByRole('button', { name: 'Validate import (dry run)' }))

    expect(await screen.findByText(/Import validation failed/i)).toBeInTheDocument()
    expect(await screen.findByText(/wealth_support/i)).toBeInTheDocument()
  })

  it('requires confirmation before destructive import apply', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderWithRoute(<CountriesPage />, '/world/countries')
    await screen.findByRole('button', { name: 'Import / Export' })
    await userEvent.click(screen.getByRole('button', { name: 'Import / Export' }))
    await screen.findByRole('button', { name: 'Apply import' })

    await userEvent.type(screen.getByLabelText('CSV payload'), 'code,name,flag_asset,region,population,wealth_support,squash_popularity,squash_tradition,system_quality\n')
    await userEvent.click(screen.getByRole('button', { name: 'Apply import' }))

    expect(confirmSpy).toHaveBeenCalled()
    expect(api.importCountries).not.toHaveBeenCalledWith(expect.objectContaining({ dry_run: false }))
    confirmSpy.mockRestore()
  })
})
