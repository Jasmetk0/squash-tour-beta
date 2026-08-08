import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminBranchProvider } from './AdminBranchContext'
import { AdminTimeProvider, useAdminTime } from './AdminTimeContext'
import { AdminBranchSelector } from '../components/AdminBranchSelector'
import { AdminTimeControl } from '../components/AdminTimeControl'

const api = vi.hoisted(() => ({ getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), ApiError: class ApiError extends Error {} }))
vi.mock('../api/client', () => api)

const branch = (branchId: string, readOnly = false) => ({ branch_id: branchId, run_id: 'run-a', display_name: branchId, status: 'active', read_only: readOnly, branch_seed: 1, forked_from_branch_id: null, forked_from_checkpoint_id: null, head_checkpoint_id: `cp-${branchId}`, legacy_simulation_run_id: null, metadata_json: {}, is_official: branchId === 'branch-a' })
const state = (branchId: string, season: number, week: number) => ({ branch_id: branchId, run_id: 'run-a', head_checkpoint_id: `cp-${week}`, current_season: season, current_week: week, current_event_id: `event-${week}`, current_event_sequence: week, state_schema_version: '1', status: 'ready', metadata_json: {} })

function Probe(): JSX.Element {
  const time = useAdminTime()
  return <output aria-label="time probe">{JSON.stringify(time)}</output>
}

function renderTime(client = new QueryClient({ defaultOptions: { queries: { retry: false } } })): QueryClient {
  render(<QueryClientProvider client={client}><AdminBranchProvider runId="run-a"><AdminTimeProvider><AdminBranchSelector /><AdminTimeControl /><Probe /></AdminTimeProvider></AdminBranchProvider></QueryClientProvider>)
  return client
}

describe('AdminTimeProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRunContainer.mockResolvedValue({ run_id: 'run-a', official_branch_id: 'branch-a' })
    api.listRunBranches.mockResolvedValue({ run_branches: [branch('branch-a'), branch('branch-b', true)] })
    api.getBranchState.mockImplementation(async (id: string) => id === 'branch-a' ? state(id, 2004, 17) : state(id, 2007, 42))
  })

  it('derives Present from the canonical Active Branch state, including read-only branches', async () => {
    localStorage.setItem('beta_engine:viewer_context', '{"selectedSeason":"2004/05","selectedWeek":10}')
    renderTime()
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2004 · W17'))
    await userEvent.selectOptions(screen.getByLabelText('Admin active Branch'), 'branch-b')
    expect(screen.getByLabelText('Admin view time')).not.toHaveTextContent('S2004')
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2007 · W42'))
    expect(localStorage.getItem('beta_engine:viewer_context')).toBe('{"selectedSeason":"2004/05","selectedWeek":10}')
  })

  it('withholds foreign state identity and reports Time unavailable', async () => {
    api.getBranchState.mockResolvedValue({ ...state('foreign', 2099, 60), run_id: 'run-c' })
    renderTime()
    await waitFor(() => expect(screen.getByLabelText('time probe')).toHaveTextContent('"identityMismatch":true'))
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · Unavailable')
    expect(screen.getByLabelText('Admin view time')).not.toHaveTextContent('2099')
  })

  it('keeps controls rendered and Time unavailable after a query error', async () => {
    api.getBranchState.mockRejectedValue(new Error('offline'))
    renderTime()
    expect(await screen.findByText(/Admin Time unavailable: offline/)).toBeInTheDocument()
    expect(screen.getByLabelText('Admin active Branch')).toBeEnabled()
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Unavailable')
  })

  it('follows canonical cache refreshes without an imperative Time setter', async () => {
    const client = renderTime()
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('W17'))
    client.setQueryData(['admin-branch-state', 'run-a', 'branch-a'], state('branch-a', 2004, 18))
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('W18'))
    expect(screen.getByLabelText('time probe')).toHaveTextContent('cp-18')
  })
})
