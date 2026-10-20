import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import * as api from './api/client'
import App from './App'
import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from './viewer/activeRun'
import { VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY } from './viewer/activeProductRun'
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

beforeEach(() => {
  localStorage.clear()
  vi.spyOn(api, 'listRunContainers').mockResolvedValue({ run_containers: [] })
  vi.spyOn(api, 'listWorldPackages').mockResolvedValue({ packages: [] })
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  localStorage.removeItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)
})

describe('App runtime smoke', () => {
  it('opens global Home from the root route when localStorage reads are unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('localStorage unavailable')
    })

    renderAppAt('/')

    expect(screen.getByRole('heading', { name: 'Squash Engine – Domů', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Vytvořit Run +' })).toHaveAttribute('href', '/admin/runs/new')
    expect(screen.queryByLabelText('Admin active Branch')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Admin view time')).not.toBeInTheDocument()
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

    expect(screen.getByRole('heading', { name: 'Vytvořit Run', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Vytvořit samostatný Run' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Language / Jazyk'), { target: { value: 'en' } })
    expect(screen.getByRole('heading', { name: 'Create Run', level: 2 })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Unique Run name'), { target: { value: 'Private browsing world' } })
    expect(screen.getByRole('button', { name: 'Create isolated Run' })).toBeEnabled()
  })

  it('renders the Viewer match odds deferred route with an active run without runtime module errors', async () => {
    const runId = 'runtime-smoke-run'
    const branchId = 'runtime-viewer-branch'
    localStorage.setItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY, runId)
    localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, 'legacy-namespace')
    vi.spyOn(api, 'listRunContainers').mockResolvedValue({ run_containers: [{
      run_id: runId, display_name: 'Runtime world', storage_kind: 'custom_local',
      read_only: false, world_id: null, world_package_fingerprint: null,
      config_version: null, config_fingerprint: null, global_seed: 12345,
      timeline_start_season: 2000, timeline_end_season: 2049,
      official_branch_id: branchId, status: 'working', metadata_json: {},
      mapped_simulation_run_count: 0
    }] })
    vi.spyOn(api, 'getViewerOfficialRunContext').mockResolvedValue({
      product_run_id: runId, product_run_display_name: 'Runtime world',
      product_run_status: 'working', product_run_storage_kind: 'custom_local',
      product_run_read_only: false, official_branch_id: branchId,
      official_branch_display_name: 'Timeline 1', official_branch_status: 'active',
      official_branch_read_only: false, official_branch_seed: 7,
      legacy_simulation_run_id: null, head_checkpoint_id: 'saved-head',
      head_checkpoint_kind: 'saved_revision', current_season: null,
      current_week: null, current_event_id: null, current_event_sequence: null,
      resolution_version: 'viewer_official_branch_v1'
    })
    vi.spyOn(api, 'getViewerRunCalendar').mockResolvedValue({
      schema_version: 'viewer_run_calendar.v1', product_run_id: runId,
      viewer_branch_id: branchId, season_count: 0, event_count: 0, seasons: []
    })
    vi.spyOn(api, 'getViewerTournamentHistory').mockResolvedValue({
      schema_version: 'viewer_tournament_history.v1', product_run_id: runId,
      viewer_branch_id: branchId, tournament_count: 0, published_result_count: 0,
      tournaments: []
    })
    vi.spyOn(api, 'listViewerOfficialRankingHistory').mockResolvedValue({
      schema_version: 'viewer_official_ranking_history.v1', product_run_id: runId,
      viewer_branch_id: branchId, public_head_ordinal: 0, publication_count: 0,
      publications: []
    })
    vi.spyOn(api, 'getViewerFinalsRace').mockResolvedValue({
      schema_version: 'viewer_finals_race_history.v1', product_run_id: runId,
      viewer_branch_id: branchId, latest_target_season_index: null, publications: []
    })
    const legacySummary = vi.spyOn(api, 'getRunStatusSummary')

    renderAppAt('/viewer/predictions/match-odds')

    expect(await screen.findByRole('heading', { name: 'Match Odds', level: 2 })).toBeInTheDocument()
    expect(await screen.findByRole('article', { name: 'Match Odds canonical Product Run metadata summary' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Match Odds sources' })).toBeInTheDocument()
    expect(api.getViewerRunCalendar).toHaveBeenCalledWith(runId)
    expect(api.getViewerTournamentHistory).toHaveBeenCalledWith(runId)
    expect(legacySummary).not.toHaveBeenCalled()
    expectNoForbiddenViewerActions()
  })

})
