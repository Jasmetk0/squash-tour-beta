import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorldPackageCountriesPage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ getWorldPackageCountries: vi.fn() }))
const locale = vi.hoisted(() => ({ language: 'en' }))
vi.mock('../api/client', async importOriginal => ({
  ...(await importOriginal<object>()), ...api
}))
vi.mock('../i18n/LanguageContext', () => ({
  useLanguage: () => ({ language: locale.language })
}))

function country(index: number) {
  const id = String(index).padStart(3, '0')
  return {
    code: `C${id}`, name: `Country ${id}`, region: index < 20 ? 'R1' : 'R2',
    population: 100_000, area_km2: null, population_by_year: null,
    travel_region: null, timezone_area: null,
    squash_popularity: 5, squash_access: 5, development_quality: 5,
    competition_quality: 5, elite_support: 5, squash_tradition: 5,
  }
}
const countries = Array.from({ length: 53 }, (_, index) => country(index))

function mount(worldId = 'world-a') {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter initialEntries={[`/admin/world/library/${worldId}/countries`]}>
      <Routes>
        <Route path="/admin/world/library/:worldId/countries" element={<WorldPackageCountriesPage />} />
      </Routes>
    </MemoryRouter>
  </QueryClientProvider>)
}

describe('World Package country inventory', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    locale.language = 'en'
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'world-a', world_name: 'Earth copy', type: 'official',
      source: 'built_in', read_only: true, country_count: 53, countries,
    })
  })

  it('pages 53 countries and resets to first page on region/search changes without refetching', async () => {
    mount()
    expect(await screen.findByText('Country 000')).toBeInTheDocument()
    expect(screen.getByText('Showing 53 of 53 countries')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open' })).toHaveLength(50)
    expect(screen.queryByText('Country 050')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText('Country 050')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open' })).toHaveLength(3)
    expect(screen.getByText('Page 2 / 2')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by region' }),
      { target: { value: 'R1' } })
    expect(screen.getByText('Country 019')).toBeInTheDocument()
    expect(screen.queryByText('Country 020')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 20 of 53 countries')).toBeInTheDocument()
    expect(screen.getByText('Page 1 / 1')).toBeInTheDocument()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search countries' }),
      { target: { value: ' c005 ' } })
    expect(screen.getByText('Country 005')).toBeInTheDocument()
    expect(screen.queryByText('Country 006')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 53 countries')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters and sorting' }))
    expect(screen.getByText('Showing 53 of 53 countries')).toBeInTheDocument()
    expect(screen.getByText('Page 1 / 2')).toBeInTheDocument()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(1)
  })

  it('supports code sorting and recognizes empty results separately from an empty package', async () => {
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'world-a', world_name: 'Earth copy', type: 'official',
      source: 'built_in', read_only: true, country_count: 2,
      countries: [
        { ...country(1), code: 'ZZZ', name: 'Alpha' },
        { ...country(2), code: 'AAA', name: 'Zulu' },
      ],
    })
    mount()
    expect(await screen.findByText('Alpha')).toBeInTheDocument()
    const hrefs = () => screen.getAllByRole('link', { name: 'Open' }).map(el => el.getAttribute('href'))
    expect(hrefs()).toEqual([
      '/admin/world/library/world-a/countries/ZZZ',
      '/admin/world/library/world-a/countries/AAA',
    ])
    fireEvent.change(screen.getByRole('combobox', { name: 'Sort countries' }),
      { target: { value: 'code' } })
    expect(hrefs()).toEqual([
      '/admin/world/library/world-a/countries/AAA',
      '/admin/world/library/world-a/countries/ZZZ',
    ])
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search countries' }),
      { target: { value: 'missing' } })
    expect(screen.getByText('No countries match your filters.')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Open' })).not.toBeInTheDocument()
  })

  it('rejects a country inventory belonging to a different World Package', async () => {
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'foreign-world', countries, country_count: 53,
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Response does not belong')
    expect(screen.queryByText('Country 000')).not.toBeInTheDocument()
  })

  it('renders translated Czech controls and the true empty-package state', async () => {
    locale.language = 'cs'
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'world-a', world_name: 'Prázdný svět', type: 'custom',
      source: 'custom_config', read_only: false, country_count: 0, countries: [],
    })
    mount()
    expect(await screen.findByText('Balíček neobsahuje žádné země.')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Hledat země' })).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Filtrovat podle regionu' })).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 0 z 0 zemí')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další →' })).not.toBeInTheDocument()
  })
})
