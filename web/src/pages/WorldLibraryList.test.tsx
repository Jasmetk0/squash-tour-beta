import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorldLibraryPage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ listWorldPackages: vi.fn() }))
const locale = vi.hoisted(() => ({ language: 'en' }))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api
}))
vi.mock('../i18n/LanguageContext', () => ({
  useLanguage: () => ({ language: locale.language })
}))

function packageRow(worldId: string, name: string, type: 'official' | 'custom') {
  return {
    world_id: worldId, name, type, status: 'active', editable: type === 'custom',
    country_count: 250, continent_count: 7, region_count: 10, travel_region_count: 10,
    timezone_area_count: 7, used_by_run_count: null, version: 'v1',
    fingerprint: 'f'.repeat(64), validation_status: 'unknown',
  }
}

function mount() {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><WorldLibraryPage /></MemoryRouter>
  </QueryClientProvider>)
}

describe('World Package library local filters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    locale.language = 'en'
    api.listWorldPackages.mockResolvedValue({
      packages: [
        packageRow('fax_world', 'FAX World', 'official'),
        packageRow('north_earth', 'North Earth', 'official'),
        packageRow('training_world', 'Training Sandbox', 'custom'),
      ],
    })
  })

  it('filters by trimmed case-insensitive name, ID and source type without changing inventory', async () => {
    mount()
    expect(await screen.findByText('FAX World')).toBeInTheDocument()
    expect(screen.getByText('Showing 3 of 3 World Packages')).toBeInTheDocument()

    const search = screen.getByRole('searchbox', { name: 'Search World Packages' })
    fireEvent.change(search, { target: { value: ' FaX ' } })
    expect(screen.getByText('FAX World')).toBeInTheDocument()
    expect(screen.queryByText('North Earth')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 World Packages')).toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'NORTH_EARTH' } })
    expect(screen.getByText('North Earth')).toBeInTheDocument()
    expect(screen.queryByText('FAX World')).not.toBeInTheDocument()

    fireEvent.change(search, { target: { value: '' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'World Package type' }),
      { target: { value: 'custom' } })
    expect(screen.getByText('Training Sandbox')).toBeInTheDocument()
    expect(screen.queryByText('FAX World')).not.toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'not-present' } })
    expect(screen.getByText('No World Packages match your search or filters.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'World packages table' })).not.toBeInTheDocument()

    fireEvent.change(search, { target: { value: '' } })
    expect(screen.getByText('Training Sandbox')).toBeInTheDocument()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(1)
  })

  it('filters archive status, sorts deterministically and resets all controls without refetching', async () => {
    api.listWorldPackages.mockResolvedValue({
      packages: [
        { ...packageRow('last_id', 'Zulu', 'official'), country_count: 70 },
        { ...packageRow('first_id', 'Alpha', 'custom'), country_count: 50, status: 'archived' },
        { ...packageRow('other_id', 'Beta', 'custom'), country_count: 20 },
      ],
    })
    mount()
    expect(await screen.findByText('Zulu')).toBeInTheDocument()
    const links = () => screen.getAllByRole('link', { name: 'Open World Package' })
      .map(link => link.getAttribute('href'))
    expect(links()).toEqual(['/admin/world/library/last_id', '/admin/world/library/first_id',
      '/admin/world/library/other_id'])

    const status = screen.getByRole('combobox', { name: 'World Package status' })
    const sort = screen.getByRole('combobox', { name: 'Sort World Packages' })
    const type = screen.getByRole('combobox', { name: 'World Package type' })

    fireEvent.change(sort, { target: { value: 'name' } })
    expect(links()).toEqual(['/admin/world/library/first_id', '/admin/world/library/other_id',
      '/admin/world/library/last_id'])

    fireEvent.change(sort, { target: { value: 'countries' } })
    expect(links()).toEqual(['/admin/world/library/last_id', '/admin/world/library/first_id',
      '/admin/world/library/other_id'])

    fireEvent.change(status, { target: { value: 'archived' } })
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.queryByText('Beta')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 World Packages')).toBeInTheDocument()

    fireEvent.change(type, { target: { value: 'built_in' } })
    expect(screen.getByText('No World Packages match your search or filters.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters and sorting' }))
    expect(status).toHaveValue('all')
    expect(sort).toHaveValue('registry')
    expect(type).toHaveValue('all')
    expect(links()).toEqual(['/admin/world/library/last_id', '/admin/world/library/first_id',
      '/admin/world/library/other_id'])
    expect(screen.getByRole('button', { name: 'Clear filters and sorting' })).toBeDisabled()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(1)
  })

  it('separates validated from unknown packages and intersects editable-source filters', async () => {
    api.listWorldPackages.mockResolvedValue({
      packages: [
        { ...packageRow('valid_builtin', 'Built-in valid', 'official'), validation_status: 'valid' },
        { ...packageRow('unknown_custom', 'Custom unverified', 'custom'), validation_status: 'unknown' },
        { ...packageRow('valid_custom', 'Custom valid', 'custom'), validation_status: 'valid' },
      ],
    })
    mount()
    expect(await screen.findByText('Custom unverified')).toBeInTheDocument()
    const table = screen.getByRole('table', { name: 'World packages table' })
    expect(within(table).getAllByText('Valid')).toHaveLength(2)
    expect(within(table).getByText('Unknown')).toBeInTheDocument()
    expect(screen.getByText(/does not necessarily indicate an error/)).toBeInTheDocument()

    const validation = screen.getByRole('combobox', { name: 'World Package validation' })
    const onlyEditable = screen.getByRole('checkbox', { name: 'Editable sources only' })
    fireEvent.change(validation, { target: { value: 'valid' } })
    expect(screen.getByText('Built-in valid')).toBeInTheDocument()
    expect(screen.getByText('Custom valid')).toBeInTheDocument()
    expect(screen.queryByText('Custom unverified')).not.toBeInTheDocument()
    fireEvent.click(onlyEditable)
    expect(screen.getByText('Custom valid')).toBeInTheDocument()
    expect(screen.queryByText('Built-in valid')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 3 World Packages')).toBeInTheDocument()
    fireEvent.change(validation, { target: { value: 'unknown' } })
    expect(screen.getByText('Custom unverified')).toBeInTheDocument()
    expect(screen.queryByText('Custom valid')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters and sorting' }))
    expect(validation).toHaveValue('all')
    expect(onlyEditable).not.toBeChecked()
    expect(screen.getByText('Showing 3 of 3 World Packages')).toBeInTheDocument()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(1)
  })

  it('localizes package table and describes empty Run creation correctly', async () => {
    locale.language = 'cs'
    mount()
    expect(await screen.findByText('FAX World')).toBeInTheDocument()
    expect(screen.getByText(/Run může vzniknout i prázdný/)).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Použito v Runech' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Ověření' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Pouze upravitelné zdroje' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Ověření World Package' })).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Otevřít World Package' })).toHaveLength(3)
    expect(screen.getAllByText('Vestavěný')).toHaveLength(2)
    expect(screen.getByText('Upravitelný zdroj')).toBeInTheDocument()
  })

  it('uses Czech labels and keeps a genuinely empty registry distinct from no search results', async () => {
    locale.language = 'cs'
    api.listWorldPackages.mockResolvedValue({ packages: [] })
    mount()
    expect(await screen.findByText('Zobrazeno 0 z 0 World Packages')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Hledat World Package' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Typ World Package' })).toBeInTheDocument()
    expect(screen.getByText('Registr zatím nevrátil žádné World Packages.')).toBeInTheDocument()
    expect(screen.queryByText(/Žádné World Packages neodpovídají/)).not.toBeInTheDocument()
  })
})
