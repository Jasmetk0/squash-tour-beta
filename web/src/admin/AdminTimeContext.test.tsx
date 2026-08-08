import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { AdminBranchProvider } from './AdminBranchContext'
import { AdminTimeProvider, useAdminTime } from './AdminTimeContext'
import { AdminBranchSelector } from '../components/AdminBranchSelector'
import { AdminTimeControl } from '../components/AdminTimeControl'

const api = vi.hoisted(() => ({ getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchState: vi.fn(), listBranchCheckpoints: vi.fn(), ApiError: class ApiError extends Error {} }))
vi.mock('../api/client', () => api)

const branch = (branchId: string, readOnly = false) => ({ branch_id: branchId, run_id: 'run-a', display_name: branchId, status: 'active', read_only: readOnly, branch_seed: 1, forked_from_branch_id: null, forked_from_checkpoint_id: null, head_checkpoint_id: `cp-${branchId}`, legacy_simulation_run_id: null, metadata_json: {}, is_official: branchId === 'branch-a' })
const state = (branchId: string, season: number, week: number) => ({ branch_id: branchId, run_id: 'run-a', head_checkpoint_id: `cp-${week}`, current_season: season, current_week: week, current_event_id: `event-${week}`, current_event_sequence: week, state_schema_version: '1', status: 'ready', metadata_json: {} })
const checkpoint = (id: string, branchId: string, sequence: number, season: number, week: number) => ({ checkpoint_id: id, run_id: 'run-a', branch_id: branchId, parent_checkpoint_id: null, sequence, kind: 'completed_week', season, week, event_id: `event-${week}`, event_sequence: week, command_id: 'command', command_kind: 'simulate_week', command_boundary: 'after', config_version: null, config_fingerprint: null, world_id: 'world', world_fingerprint: null, global_seed: 1, branch_seed: 1, seed_namespace: {}, payload_schema_version: '1', content_hash_algorithm: 'sha256', content_hash: `hash-${id}`, payload: {} })

function Probe(): JSX.Element {
  const time = useAdminTime()
  return <>
    <output aria-label="time probe">{JSON.stringify(time)}</output>
    <button type="button" onClick={() => time.selectCheckpoint('foreign-checkpoint')}>Select foreign checkpoint</button>
  </>
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
    api.listBranchCheckpoints.mockImplementation(async ({ branch_id }: { branch_id: string }) => ({ branch_checkpoints: branch_id === 'branch-a' ? [checkpoint('cp-17', branch_id, 101, 2004, 17), checkpoint('cp-old', branch_id, 100, 2003, 31)] : [checkpoint('cp-42', branch_id, 200, 2007, 42), checkpoint('cp-b-old', branch_id, 199, 2006, 12)] }))
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

  it('selects a real historical checkpoint without changing the Branch HEAD and normalizes the head to Present', async () => {
    renderTime()
    await screen.findByRole('option', { name: /#100/ })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'cp-old')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Past · S2003 · W31')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"headCheckpointId":"cp-17"')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'cp-17')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2004 · W17')
  })

  it('resets immediately to Present when the Active Branch changes', async () => {
    renderTime()
    await screen.findByRole('option', { name: /#100/ })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'cp-old')
    await userEvent.selectOptions(screen.getByLabelText('Admin active Branch'), 'branch-b')
    expect(screen.getByLabelText('Admin view time')).not.toHaveTextContent('S2003')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present')
  })

  it('discards Past selection after Branch A to B to A instead of resurrecting it', async () => {
    api.getBranchState.mockImplementation(async (id: string) => id === 'branch-a'
      ? { ...state(id, 2007, 42), head_checkpoint_id: 'cp-a-head' }
      : { ...state(id, 2008, 12), head_checkpoint_id: 'cp-b-head' })
    api.listBranchCheckpoints.mockImplementation(async ({ branch_id }: { branch_id: string }) => ({ branch_checkpoints: branch_id === 'branch-a'
      ? [checkpoint('cp-a-head', branch_id, 20, 2007, 42), checkpoint('cp-a-old', branch_id, 10, 2005, 31)]
      : [checkpoint('cp-b-head', branch_id, 30, 2008, 12), checkpoint('cp-b-old', branch_id, 25, 2006, 20)] }))
    renderTime()
    await screen.findByRole('option', { name: /#10 · S2005 · W31/ })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'cp-a-old')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Past · S2005 · W31')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"viewCheckpointId":"cp-a-old"')

    await userEvent.selectOptions(screen.getByLabelText('Admin active Branch'), 'branch-b')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present')
    expect(screen.getByLabelText('Admin view time')).not.toHaveTextContent('S2005')
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2008 · W12'))

    await userEvent.selectOptions(screen.getByLabelText('Admin active Branch'), 'branch-a')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present')
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2007 · W42'))
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"mode":"present"')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"viewCheckpointId":"cp-a-head"')
    expect(screen.getByLabelText('time probe')).not.toHaveTextContent('"viewCheckpointId":"cp-a-old"')
  })

  it('keeps a historical View fixed while the canonical Branch HEAD advances', async () => {
    api.getBranchState.mockResolvedValue({ ...state('branch-a', 2007, 42), head_checkpoint_id: 'cp-head' })
    api.listBranchCheckpoints.mockResolvedValue({ branch_checkpoints: [
      checkpoint('cp-head', 'branch-a', 101, 2007, 42),
      checkpoint('cp-old', 'branch-a', 100, 2005, 31),
    ] })
    const client = renderTime()
    await screen.findByRole('option', { name: /#100 · S2005 · W31/ })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Admin Time context' }), 'cp-old')

    expect(screen.getByLabelText('time probe')).toHaveTextContent('"mode":"checkpoint"')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"viewCheckpointId":"cp-old"')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"headCheckpointId":"cp-head"')

    client.setQueryData(['admin-branch-state', 'run-a', 'branch-a'], {
      ...state('branch-a', 2007, 43), head_checkpoint_id: 'cp-new',
    })

    await waitFor(() => expect(screen.getByLabelText('time probe')).toHaveTextContent('"headCheckpointId":"cp-new"'))
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"presentSeason":2007')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"presentWeek":43')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"mode":"checkpoint"')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"viewCheckpointId":"cp-old"')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"viewSeason":2005')
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"viewWeek":31')
    expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Past · S2005 · W31')
  })

  it('rejects checkpoint identities outside the current validated set', async () => {
    api.listBranchCheckpoints.mockResolvedValue({ branch_checkpoints: [
      checkpoint('cp-valid', 'branch-a', 5, 2003, 10),
      checkpoint('foreign-checkpoint', 'branch-b', 99, 2099, 60),
      { ...checkpoint('foreign-run', 'branch-a', 98, 2098, 59), run_id: 'run-foreign' },
    ] })
    renderTime()
    await waitFor(() => expect(api.listBranchCheckpoints).toHaveBeenCalled())
    await userEvent.click(screen.getByRole('button', { name: 'Select foreign checkpoint' }))
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"mode":"present"')
    expect(screen.getByLabelText('time probe')).not.toHaveTextContent('2099')
    expect(screen.queryByRole('option', { name: /#99/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /#98/ })).not.toBeInTheDocument()
  })

  it('keeps Present available when checkpoint history fails', async () => {
    api.getBranchState.mockResolvedValue({ ...state('branch-a', 2007, 42), head_checkpoint_id: 'cp-head' })
    api.listBranchCheckpoints.mockRejectedValue(new Error('checkpoint service offline'))
    renderTime()
    await waitFor(() => expect(screen.getByLabelText('Admin view time')).toHaveTextContent('Present · S2007 · W42'))
    expect(screen.getByLabelText('time probe')).toHaveTextContent('"isAvailable":true')
    expect(await screen.findByText(/Historical checkpoints unavailable: checkpoint service offline/)).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Present — Branch HEAD' })).toBeInTheDocument()
  })

  it('filters invalid checkpoint identities and orders valid history by descending sequence', async () => {
    api.listBranchCheckpoints.mockResolvedValue({ branch_checkpoints: [
      checkpoint('cp-five', 'branch-a', 5, 2001, 5),
      checkpoint('cp-twenty', 'branch-a', 20, 2002, 20),
      checkpoint('cp-ten', 'branch-a', 10, 2001, 10),
      checkpoint('cp-foreign-branch', 'branch-b', 30, 2099, 30),
      { ...checkpoint('cp-foreign-run', 'branch-a', 40, 2099, 40), run_id: 'run-b' },
      checkpoint('', 'branch-a', 50, 2099, 50),
      checkpoint('cp-invalid-sequence', 'branch-a', Number.NaN, 2099, 60),
    ] })
    renderTime()
    await screen.findByRole('option', { name: /#20/ })
    const options = Array.from(screen.getByRole('combobox', { name: 'Admin Time context' }).querySelectorAll('option')).map(option => option.textContent)
    expect(options).toEqual([
      'Present — Branch HEAD',
      expect.stringMatching(/^#20 /),
      expect.stringMatching(/^#10 /),
      expect.stringMatching(/^#5 /),
    ])
  })
})
