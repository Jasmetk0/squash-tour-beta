import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminHomePage } from './AdminHomePage'

const api = vi.hoisted(() => ({
  getCountriesMetadata: vi.fn(),
  getTournamentTemplatesMetadata: vi.fn(),
  listRuns: vi.fn(),
}))

vi.mock('../../api/client', () => api)

function renderAdminHome(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <AdminHomePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminHomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getCountriesMetadata.mockResolvedValue({ country_count: 7 })
    api.getTournamentTemplatesMetadata.mockResolvedValue({ template_count: 3 })
    api.listRuns.mockResolvedValue({
      runs: [
        {
          run_id: 'run alpha',
          season: 2034,
          progress: { total_events: 12, completed_event_count: 5 },
        },
      ],
    })
  })

  it('renders existing dashboard copy and admin links', async () => {
    renderAdminHome()

    expect(screen.getByRole('heading', { level: 2, name: 'Admin Engine Dashboard' })).toBeInTheDocument()
    expect(screen.getByText('Operational workspace for building, editing, validating, regenerating, and simulating worlds.')).toBeInTheDocument()
    expect(screen.getByText('Dashboard cards use available backend metadata where present and explicit placeholders where backend status is not exposed yet.')).toBeInTheDocument()

    for (const [label, href] of [
      ['World', '/admin/world'],
      ['Players', '/admin/players'],
      ['Tour & Seasons', '/admin/tour-seasons'],
      ['Runs', '/admin/runs'],
      ['Simulate', '/admin/simulate'],
      ['Diagnostics', '/admin/diagnostics'],
    ]) {
      const link = screen.getAllByRole('link').find((element) => element.textContent?.includes(label))
      expect(link).toHaveAttribute('href', href)
    }

    expect(await screen.findByText('run alpha')).toBeInTheDocument()
  })
})
