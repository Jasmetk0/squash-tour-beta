import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunBranch, RunContainer } from '../api/types'
import { renderWithRoute } from '../test/testUtils'
import { RunBranchReadinessPanel } from './RunBranchReadinessPanel'

const api = vi.hoisted(() => ({
  getAuthoritativeSimulationPosition: vi.fn(),
  getSavedRevision: vi.fn(),
  getPreAlphaFaxEntryValidationPolicyGate: vi.fn()
}))
vi.mock('../api/client', () => api)

const run: RunContainer = {
  run_id: 'run/a',
  display_name: 'Pre-alpha',
  storage_kind: 'custom_local',
  read_only: false,
  world_id: null,
  world_package_fingerprint: null,
  config_version: null,
  config_fingerprint: null,
  global_seed: null,
  timeline_start_season: 2000,
  timeline_end_season: 2049,
  viewer_branch_id: 'original',
  official_branch_id: 'original',
  status: 'active',
  metadata_json: {},
  mapped_simulation_run_count: 0
}
const baseBranch: RunBranch = {
  branch_id: 'original',
  run_id: run.run_id,
  display_name: 'Timeline 1',
  status: 'active',
  read_only: false,
  branch_seed: null,
  forked_from_branch_id: null,
  forked_from_checkpoint_id: null,
  forked_from_saved_revision_id: null,
  saved_head_revision_id: 'save-one',
  head_checkpoint_id: null,
  legacy_simulation_run_id: null,
  metadata_json: {},
  is_viewer_branch: true,
  is_official: false
}
const alternative: RunBranch = {
  ...baseBranch,
  branch_id: 'fork #2',
  display_name: 'Timeline 2',
  saved_head_revision_id: 'save-two',
  forked_from_branch_id: 'original',
  is_viewer_branch: false
}
const pos = (branchId: string) => ({
  run_id: run.run_id,
  branch_id: branchId,
  current_week: { season_index: 1, week: 2 },
  current_slot_kind: null,
  current_slot_id: null,
  slot_ordinal: null,
  unresolved_group_ids: [],
  eligible_match_ids: [],
  blocked_match_ids: [],
  current_slot_complete: true,
  supported_tournament_complete: false,
  week_ready_for_transition: false,
  transition_blockers: ['Calendar event awaiting explicit completion'],
  terminal_sporting_fingerprint: null,
  position_fingerprint: 'a'.repeat(64)
})
const revision = (branch: RunBranch) => ({
  run_id: run.run_id,
  branch_id: branch.branch_id,
  revision_id: branch.saved_head_revision_id,
  revision_branch_id: branch.branch_id,
  is_branch_head: true,
  content_hash: 'b'.repeat(64),
  content_hash_algorithm: 'sha256',
  kind: 'season_transition',
  sequence: 62
})
const gate = (branchId: string) => ({
  schema_version: 'pre_alpha_fax_entry_validation_policy_gate.v1',
  policy_id: 'automatic_application_eligibility_deadline.v1',
  policy_status: 'unresolved',
  master_status: 'open',
  blocks_unattended_release: true,
  current_slot_kind: 'entry',
  current_slot_ordinal: null,
  gate_fingerprint: 'c'.repeat(64),
  run_id: run.run_id,
  branch_id: branchId,
  current_week: { season_index: 1, week: 2 },
  current_position_fingerprint: 'a'.repeat(64),
  current_blocker_code: 'application_validation_policy_unresolved'
})
function render(branches: RunBranch[] = [baseBranch, alternative], activeRun = run) {
  return renderWithRoute(
    <RunBranchReadinessPanel run={activeRun} branches={branches} />,
    '/admin/runs/run%2Fa/branches'
  )
}
beforeEach(() => {
  vi.resetAllMocks()
  api.getAuthoritativeSimulationPosition.mockImplementation((_runId: string, branchId: string) =>
    Promise.resolve(pos(branchId))
  )
  api.getSavedRevision.mockImplementation((_runId: string, branchId: string) =>
    Promise.resolve(revision(branchId === 'original' ? baseBranch : alternative))
  )
  api.getPreAlphaFaxEntryValidationPolicyGate.mockImplementation((_runId: string, branchId: string) =>
    Promise.resolve(gate(branchId))
  )
})

describe('RunBranchReadinessPanel', () => {
  it('renders independent saved heads and canonical 2001/02 positions with scoped simulation links', async () => {
    render()
    const original = await screen.findByLabelText('Operating status for original')
    const fork = screen.getByLabelText('Operating status for fork #2')
    await waitFor(() => expect(within(fork).getByText('2001/2002')).toBeInTheDocument())
    expect(within(original).getByText('Viewer Branch')).toBeInTheDocument()
    expect(within(original).getByText('save-one')).toBeInTheDocument()
    expect(within(fork).getByText('save-two')).toBeInTheDocument()
    expect(within(fork).getByText('W2 / 61')).toBeInTheDocument()
    expect(within(fork).getByText('Calendar event awaiting explicit completion')).toBeInTheDocument()
    expect(within(fork).getByRole('link', { name: /Inspect authoritative simulation/ })).toHaveAttribute(
      'href', '/admin/runs/run%2Fa/simulate?branch=fork%20%232'
    )
    expect(api.getAuthoritativeSimulationPosition).toHaveBeenCalledWith('run/a', 'fork #2')
    expect(api.getSavedRevision).toHaveBeenCalledWith('run/a', 'fork #2', 'save-two')
    expect(api.getPreAlphaFaxEntryValidationPolicyGate).not.toHaveBeenCalled()
  })

  it('never replaces a mismatched authoritative position with legacy season/week data', async () => {
    api.getAuthoritativeSimulationPosition.mockResolvedValueOnce(pos('foreign')).mockResolvedValueOnce(pos('fork #2'))
    render()
    const original = await screen.findByLabelText('Operating status for original')
    await waitFor(() => expect(within(original).getAllByText('Not verified').length).toBeGreaterThan(0))
    expect(within(original).getByText(/position has a mismatched or invalid Run/)).toBeInTheDocument()
    expect(within(original).queryByRole('link', { name: /Inspect authoritative simulation/ })).not.toBeInTheDocument()
  })

  it('blocks readiness when saved head returns another Branch or revision', async () => {
    api.getSavedRevision.mockImplementation((_runId: string, branchId: string) =>
      Promise.resolve({ ...revision(branchId === 'original' ? baseBranch : alternative), branch_id: 'foreign' })
    )
    render([baseBranch])
    const card = await screen.findByLabelText('Operating status for original')
    expect(await within(card).findByText(/Saved revision head identity or head status is inconsistent/)).toBeInTheDocument()
    expect(within(card).queryByRole('link', { name: /Inspect authoritative simulation/ })).not.toBeInTheDocument()
  })

  it('shows the unresolved application-validation gate only at an Entry slot', async () => {
    api.getAuthoritativeSimulationPosition.mockImplementation((_runId: string, branchId: string) =>
      Promise.resolve({ ...pos(branchId), current_slot_kind: 'entry' })
    )
    render([baseBranch])
    const card = await screen.findByLabelText('Operating status for original')
    expect(await within(card).findByText(/automatic eligibility policy remains unresolved/)).toBeInTheDocument()
    expect(api.getPreAlphaFaxEntryValidationPolicyGate).toHaveBeenCalledWith(run.run_id, 'original')
    expect(within(card).getByRole('link', { name: /Inspect authoritative simulation/ })).toBeInTheDocument()
  })

  it('fails closed on a stale entry gate fingerprint or an unavailable authoritative endpoint', async () => {
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...pos('original'), current_slot_kind: 'entry'
    })
    api.getPreAlphaFaxEntryValidationPolicyGate.mockResolvedValue({
      ...gate('original'), current_position_fingerprint: '0'.repeat(64)
    })
    render([baseBranch])
    const card = await screen.findByLabelText('Operating status for original')
    expect(await within(card).findByText(/Entry-validation policy identity is inconsistent/)).toBeInTheDocument()
    expect(within(card).queryByRole('link', { name: /Inspect authoritative simulation/ })).not.toBeInTheDocument()
  })

  it.each([
    { policy_status: 'resolved' },
    { master_status: 'decided' },
    { blocks_unattended_release: false },
    { current_slot_kind: 'match' },
    { current_blocker_code: 'current_slot_not_entry' },
    { gate_fingerprint: '' }
  ])('fails closed on contradictory entry policy metadata: %j', async changed => {
    api.getAuthoritativeSimulationPosition.mockResolvedValue({
      ...pos('original'), current_slot_kind: 'entry'
    })
    api.getPreAlphaFaxEntryValidationPolicyGate.mockResolvedValue({
      ...gate('original'), ...changed
    })
    render([baseBranch])
    const card = await screen.findByLabelText('Operating status for original')
    expect(await within(card).findByText(/Entry-validation policy identity is inconsistent/)).toBeInTheDocument()
    expect(within(card).queryByRole('link', { name: /Inspect authoritative simulation/ })).not.toBeInTheDocument()
  })

  it('marks empty and read-only Branches unavailable without asserting safe execution', async () => {
    render([
      { ...baseBranch, branch_id: 'empty', saved_head_revision_id: null },
      { ...alternative, read_only: true }
    ])
    const empty = await screen.findByLabelText('Operating status for empty')
    expect(within(empty).getByText(/Branch has no saved head revision/)).toBeInTheDocument()
    expect(within(empty).getByText(/No saved revision; authoritative position cannot be inspected/)).toBeInTheDocument()
    const readonly = await screen.findByLabelText('Operating status for fork #2')
    expect(within(readonly).getByText(/Branch is read-only/)).toBeInTheDocument()
    expect(within(readonly).queryByRole('link', { name: /Inspect authoritative simulation/ })).not.toBeInTheDocument()
  })

  it('keeps all lookups read-only and explicitly refreshes scoped status', async () => {
    render([baseBranch])
    await screen.findByText('Calendar event awaiting explicit completion')
    expect(api.getAuthoritativeSimulationPosition).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Refresh Branch operating status' }))
    await waitFor(() => expect(api.getAuthoritativeSimulationPosition).toHaveBeenCalledTimes(2))
    expect(api.getSavedRevision).toHaveBeenCalledWith(run.run_id, 'original', 'save-one')
  })
})
