import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
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
    fingerprint: 'f'.repeat(64),
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
    expect(screen.getByText('No World Packages match your search or type filter.')).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'World packages table' })).not.toBeInTheDocument()

    fireEvent.change(search, { target: { value: '' } })
    expect(screen.getByText('Training Sandbox')).toBeInTheDocument()
    expect(api.listWorldPackages).toHaveBeenCalledTimes(1)
  })

  it('uses Czech labels and keeps a genuinely empty registry distinct from no search results', async () => {
    locale.language = 'cs'
    api.listWorldPackages.mockResolvedValue({ packages: [] })
    mount()
    expect(await screen.findByText('Zobrazeno 0 z 0 World Packages')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Hledat World Package' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Typ World Package' })).toBeInTheDocument()
    expect(screen.getByText(/No World Packages were returned by the registry/)).toBeInTheDocument()
    expect(screen.queryByText(/Žádné World Packages neodpovídají/)).not.toBeInTheDocument()
  })
})
