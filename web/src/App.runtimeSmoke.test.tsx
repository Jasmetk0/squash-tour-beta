import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function renderAppAt(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

afterEach(() => {
  vi.restoreAllMocks()
})

describe('App runtime smoke', () => {
  it('renders the landing route when localStorage reads are unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })

    renderAppAt('/')

    expect(screen.getByRole('heading', { name: 'Squash Tour Beta Engine', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Browse the generated squash world/i })).toBeInTheDocument()
  })

  it('renders the admin simulate route when remembered-run storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })

    renderAppAt('/admin/simulate')

    expect(screen.getByRole('heading', { name: 'Simulate', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open Runs' })).toBeInTheDocument()
  })

  it('renders the admin create-run route when remembered-run storage is unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })

    renderAppAt('/admin/runs/new')

    expect(screen.getByRole('heading', { name: 'Dashboard', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Create and open run/i })).toBeInTheDocument()
  })
})
