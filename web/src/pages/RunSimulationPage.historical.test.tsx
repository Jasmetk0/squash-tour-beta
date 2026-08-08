import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminBranchProvider } from '../admin/AdminBranchContext'
import { AdminTimeProvider } from '../admin/AdminTimeContext'
import { AdminTimeControl } from '../components/AdminTimeControl'
import { RunSimulationPage } from './RunSimulationPage'

const api = vi.hoisted(() => ({
  ApiError: class ApiError extends Error {},
  getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), listBranchCheckpoints: vi.fn(), getBranchCheckpoint: vi.fn(),
  simulateNextMatchOnBranch: vi.fn(), simulateNextRoundOnBranch: vi.fn(), simulateNextWeekOnBranch: vi.fn(), simulateNextTournamentOnBranch: vi.fn(), simulateFullSeasonOnBranch: vi.fn(), simulateWorldTourFinalsOnBranch: vi.fn(),
}))
vi.mock('../api/client', () => api)

const oldCheckpoint = { checkpoint_id: 'cp-old', run_id: 'run-a', branch_id: 'branch-a', parent_checkpoint_id: null, sequence: 10, kind: 'completed_week', season: 2005, week: 31, event_id: 'event-old', event_sequence: 31, command_id: 'old-command', command_kind: 'simulate_week', command_boundary: 'after', config_version: null, config_fingerprint: null, world_id: 'world', world_fingerprint: null, global_seed: 1, branch_seed: 1, seed_namespace: {}, payload_schema_version: '1', content_hash_algorithm: 'sha256', content_hash: 'old-hash', payload: {} }
const headCheckpoint = (id: string) => ({ ...oldCheckpoint, checkpoint_id: id, sequence: id === 'cp-head' ? 11 : 12, kind: 'current_state_capture', season: 2007, week: id === 'cp-head' ? 42 : 43, event_id: 'event-head' })

function renderSimulation(): void {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/admin/runs/run-a/simulate']}><Routes><Route path="/admin/runs/:runId/simulate" element={<AdminBranchProvider runId="run-a"><AdminTimeProvider><AdminTimeControl /><RunSimulationPage /></AdminTimeProvider></AdminBranchProvider>} /></Routes></MemoryRouter></QueryClientProvider>)
}

beforeEach(() => {
  vi.clearAllMocks()
  let advanced = false
  api.getRunContainer.mockResolvedValue({ run_id: 'run-a', display_name: 'Run A', status: 'active', read_only: false, storage_kind: 'custom_local', official_branch_id: 'branch-a' })
  api.listRunBranches.mockImplementation(async () => ({ run_branches: [{ branch_id: 'branch-a', run_id: 'run-a', display_name: 'Branch A', status: 'active', read_only: false, branch_seed: 1, legacy_simulation_run_id: 'legacy-a', forked_from_branch_id: null, forked_from_checkpoint_id: null, head_checkpoint_id: advanced ? 'cp-new' : 'cp-head', metadata_json: {}, is_official: true }] }))
  api.getBranchState.mockImplementation(async () => ({ branch_id: 'branch-a', run_id: 'run-a', head_checkpoint_id: advanced ? 'cp-new' : 'cp-head', current_season: 2007, current_week: advanced ? 43 : 42, current_event_id: 'event-head', current_event_sequence: advanced ? 43 : 42, state_schema_version: '1', status: 'active', metadata_json: {} }))
  api.listBranchCheckpoints.mockImplementation(async () => ({ branch_checkpoints: [headCheckpoint(advanced ? 'cp-new' : 'cp-head'), oldCheckpoint] }))
  api.getBranchCheckpoint.mockImplementation(async (id: string) => headCheckpoint(id))
  api.simulateNextMatchOnBranch.mockImplementation(async () => { advanced = true; return { product_run_id: 'run-a', branch_id: 'branch-a', legacy_simulation_run_id: 'legacy-a', previous_head_checkpoint_id: 'cp-head', new_head_checkpoint_id: 'cp-new', official_branch_changed: false, simulation_result: { mode: 'simulate_next_match' } } })
})

describe('RunSimulationPage historical Time integration', () => {
  it('keeps Present simulation eligible when checkpoint history listing fails', async () => {
    api.listBranchCheckpoints.mockRejectedValue(new Error('checkpoint history unavailable'))
    renderSimulation()
    expect(await screen.findByText(/Historical checkpoints unavailable: checkpoint history unavailable/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Next Match' })).toBeEnabled())
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2007 · W42')
    expect(screen.queryByText(/Simulation blocked/)).not.toBeInTheDocument()
  })

  it('advances the real HEAD while the historical View remains selected', async () => {
    renderSimulation()
    await screen.findByRole('option', { name: /#10 · S2005 · W31/ })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'cp-old')
    await userEvent.click(await screen.findByRole('button', { name: 'Next Match' }))
    const commandId = screen.getByLabelText('Simulation command ID').textContent
    await userEvent.type(screen.getByLabelText('Simulation audit reason'), 'historical view safety')
    await userEvent.click(screen.getByLabelText('Confirm simulation'))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm Simulate Next Match' }))

    await waitFor(() => expect(api.simulateNextMatchOnBranch).toHaveBeenCalledWith('run-a', 'branch-a', { expected_head_checkpoint_id: 'cp-head', command_id: commandId, audit_reason: 'historical view safety', explicit_confirmation: true }))
    await waitFor(() => expect(screen.getByText(/advanced branch-a from cp-head to cp-new/)).toBeInTheDocument())
    await waitFor(() => expect(screen.getAllByText('cp-new').length).toBeGreaterThanOrEqual(1))
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Past · S2005 · W31')
    expect(screen.getByRole('combobox', { name: 'Admin Time context' })).toHaveValue('cp-old')
    expect(screen.getByText(/Past · S2005 · W31 · cp-old/)).toBeInTheDocument()

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'present')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2007 · W43')
  })
})
