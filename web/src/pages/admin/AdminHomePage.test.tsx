import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminHomePage } from './AdminHomePage'
import { LanguageProvider } from '../../i18n/LanguageContext'
import { readRecentProductRuns, rememberProductRun, RECENT_PRODUCT_RUNS_STORAGE_KEY } from '../../navigation/recentProductRuns'

const api = vi.hoisted(() => ({
  listRunContainers: vi.fn(),
  listWorldPackages: vi.fn(),
  ApiError: class ApiError extends Error { status = 500 }
}))
vi.mock('../../api/client', () => api)

function renderHome(): void {
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter><LanguageProvider><AdminHomePage /></LanguageProvider></MemoryRouter>
  </QueryClientProvider>)
}

describe('pre-alpha global Home', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    api.listRunContainers.mockResolvedValue({ run_containers: [
      { run_id: 'run-a', display_name: 'Personal world', status: 'working', read_only: false },
      { run_id: 'run-b', display_name: 'FAX built-in', status: 'working', read_only: true }
    ] })
    api.listWorldPackages.mockResolvedValue({ packages: [{ world_id: 'FAX' }] })
  })

  it('shows factual counts and explicit Product Run links, never the latest legacy Run as active', async () => {
    renderHome()
    expect(await screen.findByText('Personal world')).toBeInTheDocument()
    expect(screen.getByText('FAX built-in')).toBeInTheDocument()
    expect(screen.getByText(/Uložené Runy: 2/)).toBeInTheDocument()
    expect(screen.getByText(/World balíčky: 1/)).toBeInTheDocument()
    expect(screen.getByText(/Na globální stránce není aktivní Run/)).toBeInTheDocument()
    expect(screen.queryByText('Active world')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vytvořit Run +' })).toHaveAttribute('href', '/admin/runs/new')
    expect(screen.getAllByRole('link', { name: /Otevřít Run/ })).toHaveLength(2)
  })

  it('distinguishes unavailable API metadata from a valid empty registry', async () => {
    api.listRunContainers.mockRejectedValue(new Error('Run storage offline'))
    api.listWorldPackages.mockResolvedValue({ packages: [] })
    renderHome()
    expect(await screen.findByRole('alert')).toHaveTextContent('Run storage offline')
    expect(screen.queryByText('Zatím neexistují žádné uložené Runy.')).not.toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/World balíčky: 0/)).toBeInTheDocument())
  })
  it('clears only the recent navigation hint while keeping saved Runs and other preferences', async () => {
    rememberProductRun('run-a')
    rememberProductRun('run-b')
    localStorage.setItem('saved-view-preference', 'keep-me')
    renderHome()
    expect(await screen.findByText('Personal world')).toBeInTheDocument()
    expect(screen.getByText('FAX built-in')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Vymazat nedávné návštěvy' }))
    expect(readRecentProductRuns()).toEqual([])
    expect(localStorage.getItem('saved-view-preference')).toBe('keep-me')
    expect(screen.getByRole('status', { name: '' })).toHaveTextContent('Runy zůstaly uložené.')
    expect(screen.getAllByRole('link', { name: /Otevřít Run/ })).toHaveLength(2)
    expect(screen.queryByRole('button', { name: 'Vymazat nedávné návštěvy' })).not.toBeInTheDocument()
  })

  it('refreshes recent order from a different tab without opening a Run', async () => {
    rememberProductRun('run-a')
    renderHome()
    expect(await screen.findByText('Personal world')).toBeInTheDocument()
    localStorage.setItem(RECENT_PRODUCT_RUNS_STORAGE_KEY, JSON.stringify(['run-b']))
    fireEvent(window, new StorageEvent('storage', {
      key: RECENT_PRODUCT_RUNS_STORAGE_KEY,
      storageArea: localStorage,
      newValue: JSON.stringify(['run-b'])
    }))
    expect(readRecentProductRuns()).toEqual(['run-b'])
    expect(screen.getByText('FAX built-in').closest('li')?.parentElement?.previousElementSibling).toHaveTextContent('Nedávno otevřené')
    expect(screen.getAllByRole('link', { name: /Otevřít Run/ })).toHaveLength(2)
  })

  it('reports denied removal without claiming success or hiding the recent Run', async () => {
    rememberProductRun('run-a')
    const remove = vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => { throw new Error('denied') })
    renderHome()
    expect(await screen.findByText('Personal world')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Vymazat nedávné návštěvy' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Historii se nepodařilo vymazat')
    expect(screen.queryByText(/Historie nedávných návštěv byla vymazána/)).not.toBeInTheDocument()
    expect(readRecentProductRuns()).toEqual(['run-a'])
    remove.mockRestore()
  })

  it('does not fail Home on corrupted history and uses current Run display names', async () => {
    localStorage.setItem(RECENT_PRODUCT_RUNS_STORAGE_KEY, '{broken')
    api.listRunContainers.mockResolvedValue({ run_containers: [
      { run_id: 'run-a', display_name: 'Renamed world', status: 'working', read_only: false }
    ] })
    renderHome()
    expect(await screen.findByText('Renamed world')).toBeInTheDocument()
    expect(screen.getByText(/Žádné dostupné nedávno otevřené Runy/)).toBeInTheDocument()
    expect(screen.getAllByRole('link', { name: /Otevřít Run/ })).toHaveLength(1)
  })

})
