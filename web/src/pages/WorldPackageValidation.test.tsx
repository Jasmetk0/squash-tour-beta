import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { RouterProvider, createMemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorldLibraryDetailPage } from './WorldLibraryPage'

const locale = vi.hoisted(() => ({ language: 'en' }))
const api = vi.hoisted(() => ({
  getWorldPackage: vi.fn(),
  getWorldPackageGeography: vi.fn(),
  getWorldPackageValidation: vi.fn(),
}))
vi.mock('../i18n/LanguageContext', () => ({ useLanguage: () => ({ language: locale.language }) }))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api
}))

const checks = [
  { code: 'COUNTRY_CODE', severity: 'error', status: 'failed',
    message: 'Invalid country code', path: 'countries/AAA.json', field: 'code' },
  { code: 'REGION_LINK', severity: 'warning', status: 'warning',
    message: 'Region missing', path: 'countries/BBB.json', field: 'region' },
  { code: 'COUNTRY_COUNT', severity: 'info', status: 'passed',
    message: 'Country count checked', path: null, field: null },
]

function mount() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <RouterProvider router={createMemoryRouter([{ path: '/world/:worldId', element: <WorldLibraryDetailPage /> }], { initialEntries: ['/world/custom'] })} />
  </QueryClientProvider>)
}

describe('World Package validation diagnostics', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    locale.language = 'en'
    api.getWorldPackage.mockResolvedValue({
      world_id: 'custom', name: 'Custom World', type: 'custom', source: 'custom_config',
      editable: false, status: 'active', used_by_run_count: null,
      country_count: 3, continent_count: 0, region_count: 0, travel_region_count: 0,
      timezone_area_count: 0, fingerprint: 'test', version: 'v1',
    })
    api.getWorldPackageGeography.mockResolvedValue({
      world_id: 'custom', continents: [], regions: [], travel_regions: [],
      timezone_areas: [], timezone_areas_authored: false,
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'custom', status: 'errors', error_count: 1, warning_count: 1,
      info_count: 1, checks,
    })
  })

  it('filters actual diagnostics by severity and source text without changing totals or refetching', async () => {
    mount()
    expect(await screen.findByText('Invalid country code')).toBeInTheDocument()
    const search = screen.getByRole('searchbox', { name: 'Search validation checks' })
    const severity = screen.getByRole('combobox', { name: 'Validation severity' })
    const table = () => screen.getByRole('table', { name: 'World package validation checks' })

    expect(within(table()).getAllByRole('row')).toHaveLength(4)
    expect(table().parentElement).toHaveClass('table-responsive')
    expect(screen.getByText('Showing 3 of 3 validation checks')).toBeInTheDocument()

    fireEvent.change(severity, { target: { value: 'warning' } })
    expect(within(table()).getByText('Region missing')).toBeInTheDocument()
    expect(within(table()).queryByText('Invalid country code')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 validation checks')).toBeInTheDocument()

    fireEvent.change(search, { target: { value: ' countries/BBB.JSON ' } })
    expect(within(table()).getByText('REGION_LINK')).toBeInTheDocument()
    fireEvent.change(search, { target: { value: 'country_code' } })
    expect(screen.getByText('No validation checks match your filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'World package validation checks' })).not.toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 3 validation checks')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear validation filters' }))
    expect(search).toHaveValue('')
    expect(severity).toHaveValue('all')
    expect(within(table()).getAllByRole('row')).toHaveLength(4)
    expect(screen.getByRole('button', { name: 'Clear validation filters' })).toBeDisabled()
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
    expect(screen.getByText('Overall status:')).toBeInTheDocument()
    expect(screen.getByText('Errors:')).toBeInTheDocument()
  })

  it('sorts errors first while preserving original order on request, without refetching', async () => {
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'custom', status: 'errors', error_count: 1, warning_count: 1,
      info_count: 1, checks: [...checks].reverse(),
    })
    mount()
    expect(await screen.findByText('Country count checked')).toBeInTheDocument()
    const codes = () => within(screen.getByRole('table', { name: 'World package validation checks' }))
      .getAllByRole('row').slice(1).map(row => within(row).getAllByRole('cell')[0].textContent)
    expect(codes()).toEqual(['COUNTRY_CODE', 'REGION_LINK', 'COUNTRY_COUNT'])
    const sort = screen.getByRole('combobox', { name: 'Validation order' })
    fireEvent.change(sort, { target: { value: 'source' } })
    expect(codes()).toEqual(['COUNTRY_COUNT', 'REGION_LINK', 'COUNTRY_CODE'])
    fireEvent.click(screen.getByRole('button', { name: 'Clear validation filters' }))
    expect(sort).toHaveValue('severity')
    expect(codes()).toEqual(['COUNTRY_CODE', 'REGION_LINK', 'COUNTRY_COUNT'])
    expect(api.getWorldPackageValidation).toHaveBeenCalledTimes(1)
  })

  it('translates diagnostic UI to Czech while preserving original diagnostic evidence', async () => {
    locale.language = 'cs'
    mount()
    expect(await screen.findByText('Invalid country code')).toBeInTheDocument()
    expect(screen.getByText('Celkový stav:')).toBeInTheDocument()
    expect(screen.getByText('Chyby:')).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 3 z 3 validačních kontrol')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'Validační kontroly World Package' })
    expect(within(table).getByRole('columnheader', { name: 'Závažnost' })).toBeInTheDocument()
    expect(within(table).getByText('Chyba')).toBeInTheDocument()
    expect(within(table).getByText('Selhalo')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Pořadí kontrol' })).toHaveValue('severity')
    const severity = screen.getByRole('combobox', { name: 'Závažnost kontroly' })
    fireEvent.change(severity, { target: { value: 'warning' } })
    expect(within(table).getByText('Region missing')).toBeInTheDocument()
    expect(within(table).queryByText('Invalid country code')).not.toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 1 z 3 validačních kontrol')).toBeInTheDocument()
  })

  it('rejects validation results whose World ID is not the opened package', async () => {
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'foreign-world', status: 'errors', error_count: 1, warning_count: 1,
      info_count: 1, checks,
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Validation response does not belong to this World Package.'
    )
    expect(screen.queryByText('Invalid country code')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'World package validation checks' })).not.toBeInTheDocument()
  })

  it('distinguishes a source with no validation checks from filtered-out results', async () => {
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'custom', status: 'valid', error_count: 0, warning_count: 0,
      info_count: 0, checks: [],
    })
    mount()
    expect(await screen.findByText('No validation checks were returned for this World Package.')).toBeInTheDocument()
    expect(screen.getByText('Showing 0 of 0 validation checks')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search validation checks' }),
      { target: { value: 'NO_MATCH' } })
    expect(screen.queryByText('No validation checks match your filters.')).not.toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'World package validation checks' })).not.toBeInTheDocument()
  })
})
