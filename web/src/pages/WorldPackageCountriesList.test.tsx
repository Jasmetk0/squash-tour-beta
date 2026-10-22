import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { Link, MemoryRouter, Route, Routes } from 'react-router-dom'
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
      <Link to="/admin/world/library/world-b/countries">Switch World Package</Link>
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
    expect(screen.getByRole('table', { name: 'World Package countries table' }).parentElement).toHaveClass('table-responsive')
    expect(screen.getByText(/Unassigned travel region: 53 · Unassigned timezone area: 53/)).toBeInTheDocument()
    expect(screen.getByText(/An unassigned value is not necessarily an error/)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open' })).toHaveLength(50)
    expect(screen.queryByText('Country 050')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Next →' }))
    expect(screen.getByText('Country 050')).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: 'Open' })).toHaveLength(3)
    expect(screen.getByText(/Page 2 \/ 2/)).toBeInTheDocument()

    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by region' }),
      { target: { value: 'R1' } })
    expect(screen.getByText('Country 019')).toBeInTheDocument()
    expect(screen.queryByText('Country 020')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 20 of 53 countries')).toBeInTheDocument()
    expect(screen.getByText(/Page 1 \/ 1/)).toBeInTheDocument()

    fireEvent.change(screen.getByRole('searchbox', { name: 'Search countries' }),
      { target: { value: ' c005 ' } })
    expect(screen.getByText('Country 005')).toBeInTheDocument()
    expect(screen.queryByText('Country 006')).not.toBeInTheDocument()
    expect(screen.getByText('Showing 1 of 53 countries')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters and sorting' }))
    expect(screen.getByText('Showing 53 of 53 countries')).toBeInTheDocument()
    expect(screen.getByText(/Page 1 \/ 2/)).toBeInTheDocument()
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

  it('sorts countries by descending population with deterministic ties', async () => {
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'world-a', world_name: 'Earth copy', type: 'official',
      source: 'built_in', read_only: true, country_count: 3,
      countries: [
        { ...country(1), code: 'AAA', name: 'Alpha', population: 1_000_000 },
        { ...country(2), code: 'ZZZ', name: 'Zulu', population: 2_000_000 },
        { ...country(3), code: 'BBB', name: 'Beta', population: 2_000_000 },
      ],
    })
    mount()
    expect(await screen.findByText('Alpha')).toBeInTheDocument()
    const hrefs = () => screen.getAllByRole('link', { name: 'Open' }).map(el => el.getAttribute('href'))
    expect(hrefs()).toEqual([
      '/admin/world/library/world-a/countries/AAA',
      '/admin/world/library/world-a/countries/BBB',
      '/admin/world/library/world-a/countries/ZZZ',
    ])
    fireEvent.change(screen.getByRole('combobox', { name: 'Sort countries' }),
      { target: { value: 'population' } })
    expect(hrefs()).toEqual([
      '/admin/world/library/world-a/countries/BBB',
      '/admin/world/library/world-a/countries/ZZZ',
      '/admin/world/library/world-a/countries/AAA',
    ])
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(1)
  })

  it('filters unassigned travel/timezone areas without altering the source inventory', async () => {
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'world-a', world_name: 'Editable world', type: 'custom',
      source: 'custom_config', read_only: false, country_count: 3,
      countries: [
        { ...country(1), travel_region: 'Central', timezone_area: 'Europe A' },
        { ...country(2), travel_region: null, timezone_area: 'Europe A' },
        { ...country(3), travel_region: null, timezone_area: null },
      ],
    })
    mount()
    expect(await screen.findByText('Country 001')).toBeInTheDocument()
    expect(screen.getByText(/Unassigned travel region: 2 · Unassigned timezone area: 1/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Unassigned travel region' }))
    expect(screen.getByText('Showing 2 of 3 countries')).toBeInTheDocument()
    expect(screen.queryByText('Country 001')).not.toBeInTheDocument()
    expect(screen.getByText('Country 002')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: 'Unassigned timezone area' }))
    expect(screen.getByText('Showing 1 of 3 countries')).toBeInTheDocument()
    expect(screen.queryByText('Country 002')).not.toBeInTheDocument()
    expect(screen.getByText('Country 003')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Clear filters and sorting' }))
    expect(screen.getByText('Showing 3 of 3 countries')).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Unassigned travel region' })).not.toBeChecked()
    expect(screen.getByRole('checkbox', { name: 'Unassigned timezone area' })).not.toBeChecked()
    expect(api.getWorldPackageCountries).toHaveBeenCalledTimes(1)
  })

  it('resets filters after navigating to a different package with a different country roster', async () => {
    api.getWorldPackageCountries.mockImplementation(async (worldId: string) => worldId === 'world-b'
      ? {
          world_id: 'world-b', world_name: 'Different World', type: 'official',
          source: 'built_in', read_only: true, country_count: 1,
          countries: [country(0)],
        }
      : {
          world_id: 'world-a', world_name: 'Earth copy', type: 'official',
          source: 'built_in', read_only: true, country_count: 53, countries,
        })
    mount()
    expect(await screen.findByText('Country 000')).toBeInTheDocument()
    fireEvent.change(screen.getByRole('searchbox', { name: 'Search countries' }),
      { target: { value: 'Country 050' } })
    fireEvent.change(screen.getByRole('combobox', { name: 'Filter by region' }),
      { target: { value: 'R2' } })
    expect(screen.queryByText('Country 000')).not.toBeInTheDocument()
    expect(screen.getByText('Country 050')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('link', { name: 'Switch World Package' }))
    expect(await screen.findByText('Different World')).toBeInTheDocument()
    expect(screen.getByRole('searchbox', { name: 'Search countries' })).toHaveValue('')
    expect(screen.getByRole('combobox', { name: 'Filter by region' })).toHaveValue('')
    expect(screen.getByText('Country 000')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open' }))
      .toHaveAttribute('href', '/admin/world/library/world-b/countries/C000')
    expect(api.getWorldPackageCountries).toHaveBeenCalledWith('world-b')
  })

  it('rejects a country inventory belonging to a different World Package', async () => {
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'foreign-world', countries, country_count: 53,
    })
    mount()
    expect(await screen.findByRole('alert')).toHaveTextContent('Response does not belong')
    expect(screen.queryByText('Country 000')).not.toBeInTheDocument()
  })

  it('translates actual table headers and country open links without modifying values', async () => {
    locale.language = 'cs'
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'world-a', world_name: 'Český svět', type: 'official',
      source: 'built_in', read_only: true, country_count: 1,
      countries: [country(0)],
    })
    mount()
    expect(await screen.findByText('Country 000')).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Země ve World Package' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Kvalita rozvoje' })).toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Populace' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Otevřít' }))
      .toHaveAttribute('href', '/admin/world/library/world-a/countries/C000')
    expect(screen.getByText(/Strana 1 \/ 1/)).toBeInTheDocument()
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
    expect(screen.getByRole('checkbox', { name: 'Bez cestovního regionu' })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: 'Bez časové oblasti' })).toBeInTheDocument()
    expect(screen.getByText('Zobrazeno 0 z 0 zemí')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Řazení zemí' })).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Země ve World Package' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Další →' })).not.toBeInTheDocument()
  })
})
