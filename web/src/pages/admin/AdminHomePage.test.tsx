import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminHomePage } from './AdminHomePage'
import { LanguageProvider } from '../../i18n/LanguageContext'

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
})
