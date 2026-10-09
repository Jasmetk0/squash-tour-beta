import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunPackageSetupPanel } from './RunPackageSetupPanel'
import type { RunBranch, RunContainer } from '../api/types'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) { super(message) }
  }
  return {
    ApiError,
    listWorldPackages: vi.fn(),
    getBranchWorkingDraft: vi.fn(),
    getRunPackageState: vi.fn(),
    previewRunSourcePackage: vi.fn(),
    confirmRunSourcePackage: vi.fn(),
    saveRunPackageWorkingDraft: vi.fn()
  }
})
vi.mock('../api/client', () => api)

const run = {
  run_id: 'test-product-run', display_name: 'Sandbox', storage_kind: 'custom_local',
  read_only: false, status: 'working',
  timeline_start_season: 2000, timeline_end_season: 2049,
  world_id: null, world_package_fingerprint: null,
  global_seed: null, config_version: null, config_fingerprint: null,
  official_branch_id: 'branch-a', metadata_json: {}, mapped_simulation_run_count: 0
} as const
const branch = {
  run_id: 'test-product-run', branch_id: 'branch-a', display_name: 'Timeline 1',
  status: 'active', read_only: false, saved_head_revision_id: 'rev-a',
  branch_seed: null, forked_from_branch_id: null, forked_from_checkpoint_id: null,
  head_checkpoint_id: null, legacy_simulation_run_id: null, metadata_json: {}, is_official: true
} as const
const sha = (char: string) => char.repeat(64)
const preview = {
  run_id: run.run_id, branch_id: branch.branch_id, saved_head_revision_id: 'rev-a',
  draft_version: 0, current_state_fingerprint: null, preview_fingerprint: sha('a'),
  document: { package_type: 'World', package_id: 'fifa_earth', source_version: 1, entities: [{}] },
  additions: ['fifa_earth/CZE'], unchanged: [], updates: [], not_included: [],
  unresolved: [], automatically_resolvable: [], invalid: [], conflicts: []
}
let currentVersion = 0
let currentFingerprint: string | null = null

beforeEach(() => {
  vi.clearAllMocks()
  currentVersion = 0
  currentFingerprint = null
  api.listWorldPackages.mockResolvedValue({ packages: [
    { world_id: 'fifa_earth', name: 'FIFA Earth', status: 'active' },
    { world_id: 'atp_earth', name: 'ATP Earth', status: 'active' }
  ] })
  api.getBranchWorkingDraft.mockImplementation(async () => ({
    run_id: run.run_id, branch_id: branch.branch_id,
    base_saved_revision_id: 'rev-a', draft_version: currentVersion,
    status: currentVersion === 0 ? 'clean' : 'dirty'
  }))
  api.getRunPackageState.mockImplementation(async () => ({
    state: currentFingerprint ? { run_id: run.run_id, branch_id: branch.branch_id, package_versions: [{ package_id: 'fifa_earth' }] } : null,
    fingerprint: currentFingerprint
  }))
  api.previewRunSourcePackage.mockResolvedValue(preview)
  api.confirmRunSourcePackage.mockImplementation(async () => {
    currentVersion = 1
    currentFingerprint = sha('b')
    return {
      state: { run_id: run.run_id, branch_id: branch.branch_id },
      state_fingerprint: currentFingerprint, draft_version: 1,
      already_applied: false, command_id: 'test-command'
    }
  })
  api.saveRunPackageWorkingDraft.mockResolvedValue({
    run_id: run.run_id, branch_id: branch.branch_id,
    saved_revision: { revision_id: 'rev-b' },
    working_draft: { run_id: run.run_id, branch_id: branch.branch_id,
      base_saved_revision_id: 'rev-b', status: 'clean' }
  })
})

function render(overrideRun: RunContainer = run, overrideBranch: RunBranch | null = branch) {
  return renderWithRoute(<RunPackageSetupPanel run={overrideRun} branch={overrideBranch} />, '/admin/runs/test-product-run')
}

describe('canonical World / Calendar setup in Run Home', () => {
  it('previews, confirms to the Working Draft, then explicitly saves a new revision', async () => {
    render()
    await userEvent.click(await screen.findByRole('button', { name: 'Preview copy' }))
    await waitFor(() => expect(api.previewRunSourcePackage).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 'world', 'fifa_earth'
    ))
    expect(await screen.findByText(/New: 1/)).toBeInTheDocument()
    expect(api.confirmRunSourcePackage).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Confirm source copy' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm copy to Working Draft' }))
    await waitFor(() => expect(api.confirmRunSourcePackage).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 'world', 'fifa_earth',
      expect.objectContaining({
        expected_head_revision_id: 'rev-a', expected_draft_version: 0,
        expected_state_fingerprint: null,
        expected_preview_fingerprint: sha('a'), conflict_resolutions: {}
      })
    ))
    expect(api.saveRunPackageWorkingDraft).not.toHaveBeenCalled()
    expect(await screen.findByText(/Copy is currently in the Working Draft/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Confirm save revision' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save copied packages' }))
    await waitFor(() => expect(api.saveRunPackageWorkingDraft).toHaveBeenCalledWith(run.run_id, branch.branch_id, 1))
    expect(await screen.findByText(/Saved Revision created/)).toBeInTheDocument()
  })

  it('uses the canonical Calendar source season and refuses stale or conflicting previews', async () => {
    api.previewRunSourcePackage.mockResolvedValueOnce({
      ...preview, document: { ...preview.document, package_type: 'Calendar', package_id: 'calendar-2000-2001' },
      conflicts: ['calendar-2000-2001:event:local_divergence']
    })
    render()
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Source kind' }), 'calendar')
    await userEvent.click(await screen.findByRole('button', { name: 'Preview copy' }))
    await waitFor(() => expect(api.previewRunSourcePackage).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 'calendar', '2000-2001'
    ))
    expect(await screen.findByText(/Copy blocked:/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Confirm source copy' }))
    expect(screen.getByRole('button', { name: 'Confirm copy to Working Draft' })).toBeDisabled()
    expect(api.confirmRunSourcePackage).not.toHaveBeenCalled()
  })

  it('fails closed on wrong-Branch previews and read-only Run status', async () => {
    api.previewRunSourcePackage.mockResolvedValueOnce({ ...preview, branch_id: 'different-branch' })
    render()
    await userEvent.click(await screen.findByRole('button', { name: 'Preview copy' }))
    expect(await screen.findByText(/Source preview identity or contract is invalid/)).toBeInTheDocument()
    expect(api.confirmRunSourcePackage).not.toHaveBeenCalled()
  })

  it('blocks mutations on a protected Product Run', async () => {
    render({ ...run, read_only: true })
    expect(await screen.findByRole('button', { name: 'Preview copy' })).toBeDisabled()
    expect(screen.getByText(/Protected Runs cannot import packages/)).toBeInTheDocument()
  })
})
