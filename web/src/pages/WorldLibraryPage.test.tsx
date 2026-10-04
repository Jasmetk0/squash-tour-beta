import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { WorldPackageCountryCreatePage } from './WorldLibraryPage'

const api = vi.hoisted(() => ({ getWorldPackage: vi.fn(), getWorldPackageGeography: vi.fn(), createWorldPackageCountry: vi.fn() }))
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
