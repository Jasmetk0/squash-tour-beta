import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { WorldLibraryDetailPage, WorldPackageCountryCreatePage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ getWorldPackage: vi.fn(), getWorldPackageGeography: vi.fn(), getWorldPackageValidation: vi.fn(), createWorldPackageCountry: vi.fn(), cloneWorldPackage: vi.fn() }))
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

