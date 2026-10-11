import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import * as api from './api/client'
import App from './App'
import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from './viewer/activeRun'
import { expectNoForbiddenViewerActions } from './test/viewerTestUtils'

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
  cleanup()
  vi.restoreAllMocks()
  localStorage.removeItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)
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

  it('renders the Viewer match odds deferred route with an active run without runtime module errors', async () => {
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'runtime-smoke-run')
    vi.spyOn(api, 'getRunStatusSummary').mockResolvedValue({
      run_id: 'runtime-smoke-run',
      season: 2034,
      seed: 12345,
      progress: { next_event_index: 0, total_events: 0, completed_event_count: 0 },
      history_counts: { events: 0, ranking_snapshots: 0, race_snapshots: 0 },
      finals: { qualification_available: false, result_available: false },
      rollover: null,
      source: null,
      lineage: { child_run_count: 0 },
    })
    vi.spyOn(api, 'listEvents').mockResolvedValue({ run_id: 'runtime-smoke-run', events: [] })
    vi.spyOn(api, 'listRankingSnapshots').mockResolvedValue({ run_id: 'runtime-smoke-run', snapshots: [] })
    vi.spyOn(api, 'listRaceSnapshots').mockResolvedValue({ run_id: 'runtime-smoke-run', snapshots: [] })
    vi.spyOn(api, 'getFinalsSummary').mockResolvedValue({
      run_id: 'runtime-smoke-run',
      season: 2034,
      qualification: null,
      result: null,
    })

    renderAppAt('/viewer/predictions/match-odds')

    expect(await screen.findByRole('heading', { name: 'Match Odds', level: 2 })).toBeInTheDocument()
    expect(await screen.findByRole('article', { name: 'Match Odds active run metadata summary' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Match Odds sources' })).toBeInTheDocument()
    expectNoForbiddenViewerActions()
  })

})
