import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import App from './App'

const api = vi.hoisted(() => ({
  getCountriesMetadata: vi.fn().mockResolvedValue({ country_count: 0 }),
  getTournamentTemplatesMetadata: vi.fn().mockResolvedValue({ template_count: 0 }),
  listRuns: vi.fn().mockResolvedValue({ runs: [] }),
  getViewerRankingTable: vi.fn().mockRejectedValue(new Error('not connected in test')),
  getRun: vi.fn().mockRejectedValue(new Error('not connected in test')),
  listEvents: vi.fn().mockResolvedValue({ run_id: 'run-a', events: [] }),
  listRankingSnapshots: vi.fn().mockResolvedValue({ snapshots: [] }),
  listRaceSnapshots: vi.fn().mockResolvedValue({ snapshots: [] })
}))

vi.mock('./api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./api/client')>()
  return {
    ...actual,
    ...api
  }
})

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

function interactiveLabels(): string[] {
  return [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')].map((element) => element.textContent?.trim() ?? '')
}

describe('Viewer Phase 1A routes and safety', () => {
  it('renders MSA homepage scaffold sections', async () => {
    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: /MSA Squash/, level: 2 })).toBeInTheDocument()
    for (const section of [
      'Featured Tournament Hero',
      'Other Tournaments This Week',
      'Top 10 Rankings',
      'Race to Finals',
      'Featured Matches',
      'Predictions & Upset Watch',
      'Storylines'
    ]) {
      expect(screen.getByRole('heading', { name: section })).toBeInTheDocument()
    }
  })

  it('updates local Viewer context with Jump to Week', async () => {
    const user = userEvent.setup()
    renderAppAt('/viewer/tour/calendar')

    expect(await screen.findByRole('button', { name: 'Season 2004/05 · W10' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Jump to W24' }))
    expect(screen.getByRole('button', { name: 'Season 2004/05 · W24' })).toBeInTheDocument()
  })

  it('does not render forbidden mutating Viewer buttons or links on shell pages', async () => {
    renderAppAt('/viewer')

    expect(await screen.findByRole('heading', { name: /MSA Squash/, level: 2 })).toBeInTheDocument()
    const forbidden = /^(Simulate|Generate|Persist|Apply|Execute|Delete|Edit|Import|Rollover|Rebuild|Override|Save changes|Commit|Regenerate|Repair|Merge|Overwrite)$/i
    expect(interactiveLabels().filter((label) => forbidden.test(label))).toEqual([])
  })

  it('renders read-only Viewer Finals without simulation action', async () => {
    renderAppAt('/viewer/runs/run-a/finals')

    expect(await screen.findByRole('heading', { name: 'World Tour Finals' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Simulate World Tour Finals/i })).not.toBeInTheDocument()
  })


  it('preserves the real run-scoped Viewer season calendar page', async () => {
    api.getRun.mockResolvedValue({
      run: { run_id: 'run-a', season: 2029, seed: 7, next_event_index: 0, total_events: 1, completed_event_ids: [] },
      season_state: {
        season: 2029,
        next_event_index: 0,
        completed_event_ids: [],
        ordered_events: [{ event_id: 'E1', season: 2029, week: 2, tour: 'WORLD', category: 'GOLD', template_id: 'TEMP-A' }]
      }
    })
    api.listEvents.mockResolvedValue({ run_id: 'run-a', events: [] })

    renderAppAt('/viewer/runs/run-a/calendar')

    expect(await screen.findByRole('heading', { name: 'Season calendar' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Ordered season calendar' })).toBeInTheDocument()
    expect(await screen.findByRole('list', { name: 'Season calendar ordered list' })).toHaveTextContent('E1')
    expect(screen.queryByText('Demo card for future calendar/event cards.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Jump to W24' })).not.toBeInTheDocument()
  })

  it('renders read-only Viewer planned event detail without commissioner controls', async () => {
    renderAppAt('/viewer/runs/run-a/calendar/event-a')

    expect(await screen.findByRole('heading', { name: 'Planned Event' })).toBeInTheDocument()
    const controls = interactiveLabels().join(' ')
    expect(controls).not.toMatch(/wildcard|withdrawal|late replacement/i)
  })

  it('routes shared shortcuts to same pages/components', async () => {
    renderAppAt('/viewer/countries/ranking')
    expect(await screen.findByRole('heading', { name: 'Country Ranking' })).toBeInTheDocument()

    renderAppAt('/viewer/players/compare')
    expect(await screen.findByRole('heading', { name: 'Player Comparison' })).toBeInTheDocument()

    renderAppAt('/viewer/predictions/match-predictor')
    expect(await screen.findByRole('heading', { name: 'Match Predictor' })).toBeInTheDocument()
  })

  it('Admin routes still render', async () => {
    renderAppAt('/admin')

    expect(await screen.findByRole('heading', { name: 'Admin Engine Dashboard' })).toBeInTheDocument()
    const adminNav = screen.getByRole('navigation', { name: 'Admin / Engine Mode navigation' })
    expect(within(adminNav).getByRole('link', { name: 'World' })).toHaveAttribute('href', '/admin/world')
    expect(within(adminNav).getByRole('link', { name: 'Simulate' })).toHaveAttribute('href', '/admin/simulate')
  })
})
