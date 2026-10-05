import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { WorldLibraryDetailPage, WorldPackageCountriesPage, WorldPackageCountryCreatePage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ getWorldPackage: vi.fn(), getWorldPackageCountries: vi.fn(), getWorldPackageGeography: vi.fn(), getWorldPackageValidation: vi.fn(), createWorldPackageCountry: vi.fn(), cloneWorldPackage: vi.fn() }))
vi.mock('../api/client', async importOriginal => ({ ...(await importOriginal<object>()), ...api }))

describe('new-scale country creation', () => {
  it('authors explicit tenths on 1–10 without a court-count input', async () => {
    api.getWorldPackage.mockResolvedValue({ type: 'custom', source: 'custom_config', editable: true, fingerprint: 'source-head' })
    api.getWorldPackageGeography.mockResolvedValue({ regions: [{ code: 'EUR', name: 'Europe' }], travel_regions: [], timezone_areas: [] })
    api.createWorldPackageCountry.mockResolvedValue({ country_detail: { country: { code: 'AAA' } } })
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/world/custom/new']}><Routes>
        <Route path="/world/:worldId/new" element={<WorldPackageCountryCreatePage />} />
        <Route path="*" element={<p>Created</p>} />
      </Routes></MemoryRouter>
    </QueryClientProvider>)
    const popularity = await screen.findByLabelText('squash popularity')
    expect(popularity).toHaveAttribute('min', '1')
    expect(popularity).toHaveAttribute('max', '10')
    expect(popularity).toHaveAttribute('step', '0.1')
    expect(screen.queryByLabelText(/court count/i)).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Code'), { target: { value: 'AAA' } })
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'Synthetic country' } })
    fireEvent.change(screen.getByLabelText('Region'), { target: { value: 'EUR' } })
    fireEvent.change(screen.getByLabelText('Population value 2020'), { target: { value: '1000000' } })
    fireEvent.change(popularity, { target: { value: '7.4' } })
    fireEvent.submit(screen.getByRole('button', { name: /Save country/i }).closest('form')!)
    await waitFor(() => expect(api.createWorldPackageCountry).toHaveBeenCalledWith('custom', expect.objectContaining({
      rating_scale: 'country_ratings_1_10.v2', squash_popularity: 7.4, court_count: null,
    })))
  })
})

describe('built-in World cloning', () => {
  it('clones the built-in package currently being inspected, not a hard-coded FAX source', async () => {
    api.getWorldPackage.mockResolvedValue({
      world_id: 'real_world',
      name: 'Real World',
      description: 'Earth geography',
      type: 'official',
      status: 'active',
      source: 'built_in',
      editable: false,
      deletable: false,
      archivable: false,
      version: 'v1',
      fingerprint: 'real-world-head',
      country_count: 250,
      continent_count: 7,
      region_count: 10,
      travel_region_count: 10,
      timezone_area_count: 0,
      used_by_run_count: null,
      validation_status: 'valid'
    })
    api.getWorldPackageGeography.mockResolvedValue({
      world_id: 'real_world',
      continents: [],
      regions: [],
      travel_regions: [],
      timezone_areas: [],
      timezone_areas_authored: false
    })
    api.getWorldPackageValidation.mockResolvedValue({
      world_id: 'real_world',
      status: 'valid',
      error_count: 0,
      warning_count: 0,
      info_count: 0,
      checks: []
    })
    api.cloneWorldPackage.mockResolvedValue({
      ok: true,
      dry_run: false,
      source_world_id: 'real_world',
      new_world_id: 'editable_earth',
      target_path: 'config/world_packages/custom/editable_earth',
      created_files: [],
      package: null,
      validation: null,
      errors: []
    })

    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/world/real_world']}><Routes>
        <Route path="/world/:worldId" element={<WorldLibraryDetailPage />} />
      </Routes></MemoryRouter>
    </QueryClientProvider>)

    expect(await screen.findByText('Clone Built-in World')).toBeInTheDocument()
    fireEvent.change(screen.getByPlaceholderText('my_custom_world'), { target: { value: 'editable_earth' } })
    fireEvent.change(screen.getByPlaceholderText('My Custom World'), { target: { value: 'Editable Earth' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Custom World' }))

    await waitFor(() => expect(api.cloneWorldPackage).toHaveBeenCalledWith(
      'real_world',
      expect.objectContaining({ new_world_id: 'editable_earth', name: 'Editable Earth', dry_run: false })
    ))
  })
})



describe('Earth country attribute history charts', () => {
  it('renders all six attributes using every country with authored history', async () => {
    const history = (base: number) => ({
      reference_year: 2026,
      data_cutoff: '2026-10-05',
      years: {
        '1955': { ratings: {
          squash_popularity: { value: base },
          squash_access: { value: base + 0.1 },
          development_quality: { value: base + 0.2 },
          competition_quality: { value: base + 0.3 },
          elite_support: { value: base + 0.4 },
          squash_tradition: { value: base + 0.5 },
        } },
        '2026': { ratings: {
          squash_popularity: { value: base + 1 },
          squash_access: { value: base + 1.1 },
          development_quality: { value: base + 1.2 },
          competition_quality: { value: base + 1.3 },
          elite_support: { value: base + 1.4 },
          squash_tradition: { value: base + 1.5 },
        } },
      },
    })
    api.getWorldPackageCountries.mockResolvedValue({
      world_id: 'fifa_earth',
      world_name: 'FIFA Earth',
      type: 'official',
      source: 'built_in',
      read_only: true,
      country_count: 3,
      source_path: 'config/world_packages/builtin/fifa_earth/countries/index.json',
      countries: [
        { code: 'AAA', name: 'Alpha', rating_history: history(3), population: 1, region: 'EUR', squash_popularity: 4, squash_access: 4, development_quality: 4, competition_quality: 4, elite_support: 4, squash_tradition: 4, court_count: null, travel_region: null, timezone_area: null, flag_asset: null, notes: null },
        { code: 'BBB', name: 'Beta', rating_history: history(5), population: 1, region: 'EUR', squash_popularity: 6, squash_access: 6, development_quality: 6, competition_quality: 6, elite_support: 6, squash_tradition: 6, court_count: null, travel_region: null, timezone_area: null, flag_asset: null, notes: null },
        { code: 'CCC', name: 'No history', rating_history: null, population: 1, region: 'EUR', squash_popularity: 2, squash_access: 2, development_quality: 2, competition_quality: 2, elite_support: 2, squash_tradition: 2, court_count: null, travel_region: null, timezone_area: null, flag_asset: null, notes: null },
      ],
    })

    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <MemoryRouter initialEntries={['/world/fifa_earth/countries']}><Routes>
        <Route path="/world/:worldId/countries" element={<WorldPackageCountriesPage />} />
      </Routes></MemoryRouter>
    </QueryClientProvider>)

    expect(await screen.findByText('Country attribute history charts')).toBeInTheDocument()
    for (const label of ['Squash Popularity', 'Squash Access', 'Development Quality', 'Competition Quality', 'Elite Support', 'Squash Tradition']) {
      expect(screen.getByRole('img', { name: label + ' history chart' })).toBeInTheDocument()
    }
    expect(screen.getByText('2 / 3')).toBeInTheDocument()
    expect(screen.getAllByLabelText('AAA Alpha')).toHaveLength(6)
    expect(screen.getAllByLabelText('BBB Beta')).toHaveLength(6)
    expect(screen.queryByLabelText('CCC No history')).not.toBeInTheDocument()
  })
})
