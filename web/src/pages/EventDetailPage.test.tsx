import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { EventDetailPage } from './EventDetailPage'

const api = vi.hoisted(() => ({
  getEvent: vi.fn(),
  ApiError: class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
}))

vi.mock('../api/client', () => api)

function renderEventDetailRoute(route: string): void {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/runs/:runId/events/:eventId" element={<EventDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('EventDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders event detail from direct URL with metadata and payload', async () => {
    api.getEvent.mockResolvedValue({
      event_sequence: 11,
      event_id: 'E11',
      season: 2028,
      week: 4,
      template_id: 'psa-gold',
      tournament_result: { champion_id: 'P-1' }
    })

    renderEventDetailRoute('/runs/run-a/events/E11')

    expect(await screen.findByRole('heading', { name: 'Event detail' })).toBeInTheDocument()
    expect(await screen.findByText(/champion_id/)).toBeInTheDocument()
    expect(screen.getAllByText('E11').length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: 'Raw event payload' })).toBeInTheDocument()
    expect(api.getEvent).toHaveBeenCalledWith('run-a', 'E11')
    expect(screen.getByRole('link', { name: /Back to events history/i })).toHaveAttribute('href', '/runs/run-a/events')
  })

  it('shows readable missing-event behavior for invalid event IDs', async () => {
    api.getEvent.mockRejectedValue(new api.ApiError('event not found', 404))

    renderEventDetailRoute('/runs/run-a/events/UNKNOWN')

    expect(await screen.findByText('Event UNKNOWN was not found for this run.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Back to events history/i })).toHaveAttribute('href', '/runs/run-a/events')
  })
})
