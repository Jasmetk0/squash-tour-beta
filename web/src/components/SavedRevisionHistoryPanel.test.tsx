import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunBranch, RunContainer } from '../api/types'
import { renderWithRoute } from '../test/testUtils'
import { SavedRevisionHistoryPanel } from './SavedRevisionHistoryPanel'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) {
      super(message)
    }
  }
  return {
    ApiError,
    createRunBranchFromSavedRevision: vi.fn(),
    getBranchWorkingDraft: vi.fn(),
    getSavedRevision: vi.fn(),
    getSavedRevisionRecoveryActivity: vi.fn(),
    listSavedRevisionHistory: vi.fn(),
    restoreSavedRevision: vi.fn()
  }
})

vi.mock('../api/client', () => api)

const run: RunContainer = {
  run_id: 'run/a #1',
  display_name: 'Restore Run',
  storage_kind: 'custom_local',
  read_only: false,
  world_id: null,
  world_package_fingerprint: null,
  config_version: null,
  config_fingerprint: null,
  global_seed: null,
  timeline_start_season: 2000,
  timeline_end_season: 2049,
  viewer_branch_id: 'branch-two',
  official_branch_id: 'branch-two',
  status: 'active',
  metadata_json: {},
  mapped_simulation_run_count: 0
}

const branch: RunBranch = {
  branch_id: 'branch/a #1',
  run_id: run.run_id,
  display_name: 'Timeline 1',
  status: 'active',
  read_only: false,
  branch_seed: null,
  forked_from_branch_id: null,
  forked_from_checkpoint_id: null,
  forked_from_saved_revision_id: null,
  saved_head_revision_id: 'revision-two',
  head_checkpoint_id: null,
  legacy_simulation_run_id: null,
  metadata_json: {},
  is_viewer_branch: false,
  is_official: false
}

const revisions = [
  {
    revision_id: 'revision-one',
    revision_branch_id: branch.branch_id,
    sequence: 1,
    parent_revision_id: null,
    kind: 'initial_run_creation',
    payload_schema_version: 'empty_run_saved_revision_v1',
    content_hash_algorithm: 'sha256',
    content_hash: 'hash-one',
    change_summary: { summary: 'Created empty Run' },
    created_at: '2026-08-30 10:00:00',
    is_shared_revision: false,
    is_branch_head: false
  },
  {
    revision_id: 'revision-two',
    revision_branch_id: branch.branch_id,
    sequence: 2,
    parent_revision_id: 'revision-one',
    kind: 'viewer_branch_selection',
    payload_schema_version: 'run_saved_revision_v1',
    content_hash_algorithm: 'sha256',
    content_hash: 'hash-two',
    change_summary: { summary: 'Changed Viewer Branch' },
    created_at: '2026-08-30 10:05:00',
    is_shared_revision: false,
    is_branch_head: true
  }
]

const history = {
  run_id: run.run_id,
  branch_id: branch.branch_id,
  saved_head_revision_id: 'revision-two',
  saved_revisions: revisions
}

const detail = {
  ...revisions[0],
  run_id: run.run_id,
  branch_id: branch.branch_id,
  payload: {
    run: { run_id: run.run_id, viewer_branch_id: 'branch/a #1' },
    branch: { branch_id: branch.branch_id },
    content: {}
  }
}

const draft = {
  run_id: run.run_id,
  branch_id: branch.branch_id,
  draft_id: 'draft-one',
  base_saved_revision_id: 'revision-two',
  saved_viewer_branch_id: 'branch-two',
  proposed_viewer_branch_id: 'branch-two',
  current_viewer_branch_id: 'branch-two',
  status: 'clean' as const,
  change_count: 0,
  draft_version: 2,
  can_save: false
}

function renderPanel(overrides?: { run?: RunContainer; branches?: RunBranch[] }): void {
  renderWithRoute(
    <SavedRevisionHistoryPanel
      runId={run.run_id}
      run={overrides?.run ?? run}
      branches={overrides?.branches ?? [branch]}
    />,
    '/'
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  api.listSavedRevisionHistory.mockResolvedValue(history)
  api.getSavedRevisionRecoveryActivity.mockResolvedValue({
    run_id: run.run_id,
    branch_id: branch.branch_id,
    saved_head_revision_id: history.saved_head_revision_id,
    safety_checkpoints: [],
    audit_events: []
  })
  api.getSavedRevision.mockResolvedValue(detail)
  api.getBranchWorkingDraft.mockResolvedValue(draft)
  api.createRunBranchFromSavedRevision.mockResolvedValue({
    ...branch,
    branch_id: 'branch-three',
    display_name: 'Alternative history',
    forked_from_branch_id: branch.branch_id,
    forked_from_saved_revision_id: 'revision-one'
  })
  api.restoreSavedRevision.mockResolvedValue({
    run_id: run.run_id,
    branch_id: branch.branch_id,
    previous_saved_head_revision_id: 'revision-two',
    target_saved_revision_id: 'revision-one',
    previous_viewer_branch_id: 'branch-two',
    viewer_branch_id: branch.branch_id,
    safety_checkpoint: {
      checkpoint_id: 'checkpoint-one',
      saved_revision_id: 'revision-two',
      target_saved_revision_id: 'revision-one',
      restore_saved_revision_id: 'revision-three',
      kind: 'pre_restore_saved_revision',
      draft_id: 'draft-one',
      draft_version: 2,
      viewer_branch_id: 'branch-two',
      content_hash_algorithm: 'sha256',
      content_hash: 'checkpoint-hash'
    },
    saved_revision: {
      revision_id: 'revision-three',
      sequence: 3,
      parent_revision_id: 'revision-two',
      kind: 'branch_restore',
      payload_schema_version: 'run_saved_revision_v1',
      content_hash_algorithm: 'sha256',
      content_hash: 'hash-three',
      change_summary: { summary: 'Restored revision-one' }
    },
    working_draft: { ...draft, base_saved_revision_id: 'revision-three', draft_version: 3 },
    audit_event_id: 'audit-two'
  })
})

describe('SavedRevisionHistoryPanel', () => {
  it('opens a checkpoint recovery source read-only and shows its matching audit event', async () => {
    const restoredRevision = {
      revision_id: 'revision-three',
      revision_branch_id: branch.branch_id,
      sequence: 3,
      parent_revision_id: 'revision-two',
      kind: 'branch_restore',
      payload_schema_version: 'run_saved_revision_v1',
      content_hash_algorithm: 'sha256',
      content_hash: 'hash-three',
      change_summary: { summary: 'Restored revision-one' },
      created_at: '2026-08-30 10:10:00',
      is_shared_revision: false,
      is_branch_head: true
    }
    api.listSavedRevisionHistory.mockResolvedValueOnce({
      ...history,
      saved_head_revision_id: 'revision-three',
      saved_revisions: [
        revisions[0],
        { ...revisions[1], is_branch_head: false },
        restoredRevision
      ]
    })
    api.getSavedRevisionRecoveryActivity.mockResolvedValueOnce({
      run_id: run.run_id,
      branch_id: branch.branch_id,
      saved_head_revision_id: 'revision-three',
      safety_checkpoints: [
        {
          checkpoint_id: 'checkpoint-one',
          run_id: run.run_id,
          branch_id: branch.branch_id,
          saved_revision_id: 'revision-two',
          target_saved_revision_id: 'revision-one',
          restore_saved_revision_id: 'revision-three',
          kind: 'pre_restore_saved_revision',
          draft_id: 'draft-one',
          draft_version: 2,
          viewer_branch_id: 'branch-two',
          content_hash_algorithm: 'sha256',
          content_hash: 'checkpoint-hash',
          created_at: '2026-08-30 10:10:00'
        }
      ],
      audit_events: [
        {
          audit_event_id: 'audit-two',
          run_id: run.run_id,
          branch_id: branch.branch_id,
          saved_revision_id: 'revision-three',
          event_kind: 'branch_restored',
          payload: { checkpoint_id: 'checkpoint-one', explicit_confirmation: true },
          created_at: '2026-08-30 10:10:00'
        }
      ]
    })
    api.getSavedRevision.mockResolvedValueOnce({
      ...revisions[1],
      run_id: run.run_id,
      branch_id: branch.branch_id,
      payload: {
        run: { run_id: run.run_id, viewer_branch_id: 'branch-two' },
        branch: { branch_id: branch.branch_id },
        content: {}
      }
    })

    renderPanel()

    const activity = await screen.findByLabelText('Saved Revision recovery activity')
    const openCheckpoint = await screen.findByRole('button', {
      name: 'Open checkpoint recovery source'
    })
    expect(activity).toHaveTextContent('checkpoint-one')
    expect(activity).toHaveTextContent('branch_restored')
    expect(activity).toHaveTextContent('"explicit_confirmation": true')
    await userEvent.click(openCheckpoint)

    expect(await screen.findByLabelText('Saved Revision read-only preview')).toHaveTextContent(
      'revision-two'
    )
    expect(api.getSavedRevision).toHaveBeenCalledWith(
      run.run_id,
      branch.branch_id,
      'revision-two'
    )
    expect(api.createRunBranchFromSavedRevision).not.toHaveBeenCalled()
    expect(api.restoreSavedRevision).not.toHaveBeenCalled()
  })

  it('opens an older Saved Revision as read-only without issuing a mutation', async () => {
    renderPanel()

    await userEvent.click(await screen.findByRole('button', { name: /Revision 1:/ }))

    const preview = await screen.findByLabelText('Saved Revision read-only preview')
    expect(preview).toHaveTextContent('Read-only preview · nothing has been changed.')
    expect(preview).toHaveTextContent('Created empty Run')
    expect(preview).toHaveTextContent('revision-one')
    expect(preview).toHaveTextContent('"viewer_branch_id": "branch/a #1"')
    expect(api.getSavedRevision).toHaveBeenCalledWith(run.run_id, branch.branch_id, 'revision-one')
    expect(api.createRunBranchFromSavedRevision).not.toHaveBeenCalled()
    expect(api.restoreSavedRevision).not.toHaveBeenCalled()
  })

  it('creates a new Branch from the preview with the exact trimmed product contract', async () => {
    renderPanel()
    await userEvent.click(await screen.findByRole('button', { name: /Revision 1:/ }))
    await screen.findByLabelText('Saved Revision read-only preview')
    await userEvent.type(screen.getByLabelText('New Branch name from Saved Revision'), '  Alternative history  ')
    await userEvent.click(screen.getByRole('button', { name: 'Create new Branch from this revision' }))

    await waitFor(() => expect(api.createRunBranchFromSavedRevision).toHaveBeenCalledTimes(1))
    expect(api.createRunBranchFromSavedRevision).toHaveBeenCalledWith(run.run_id, {
      source_branch_id: branch.branch_id,
      source_saved_revision_id: 'revision-one',
      display_name: 'Alternative history'
    })
    expect(await screen.findByLabelText('Saved Revision Branch result')).toHaveTextContent(
      'The Viewer Branch was not changed.'
    )
    expect(api.restoreSavedRevision).not.toHaveBeenCalled()
  })

  it('requires the reviewed phrase and checkbox before submitting the exact restore snapshot', async () => {
    renderPanel()
    await userEvent.click(await screen.findByRole('button', { name: /Revision 1:/ }))
    const openRestore = await screen.findByRole('button', {
      name: 'Restore current Branch from this revision'
    })
    await waitFor(() => expect(openRestore).toBeEnabled())
    await userEvent.click(openRestore)

    const dialog = screen.getByRole('alertdialog')
    expect(dialog).toHaveTextContent('It will not delete later history.')
    expect(api.restoreSavedRevision).not.toHaveBeenCalled()
    const submit = screen.getByRole('button', { name: 'Confirm restore' })
    expect(submit).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Restore confirmation phrase'), 'RESTORE Timeline 1')
    expect(submit).toBeDisabled()
    await userEvent.click(
      screen.getByRole('checkbox', { name: 'Confirm Saved Revision restore' })
    )
    expect(submit).toBeEnabled()
    await userEvent.click(submit)

    await waitFor(() => expect(api.restoreSavedRevision).toHaveBeenCalledTimes(1))
    expect(api.restoreSavedRevision).toHaveBeenCalledWith(
      run.run_id,
      branch.branch_id,
      'revision-one',
      {
        expected_head_saved_revision_id: 'revision-two',
        expected_draft_version: 2,
        expected_current_viewer_branch_id: 'branch-two',
        explicit_confirmation: true
      }
    )
    const result = await screen.findByLabelText('Saved Revision restore result')
    expect(result).toHaveTextContent('revision-three')
    expect(result).toHaveTextContent('checkpoint-one')
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
  })

  it('blocks restore for a dirty Working Draft while keeping read-only preview available', async () => {
    api.getBranchWorkingDraft.mockResolvedValueOnce({
      ...draft,
      status: 'dirty',
      change_count: 1,
      can_save: true
    })
    renderPanel()
    await userEvent.click(await screen.findByRole('button', { name: /Revision 1:/ }))
    const preview = await screen.findByLabelText('Saved Revision read-only preview')
    expect(preview).toBeInTheDocument()
    const restore = screen.getByRole('button', {
      name: 'Restore current Branch from this revision'
    })
    await waitFor(() => expect(restore).toBeDisabled())
    expect(screen.getByText(/Save, discard, or branch the dirty Working Draft/)).toBeInTheDocument()
    expect(api.restoreSavedRevision).not.toHaveBeenCalled()
  })

  it('explains the pre-alpha boundary for sporting or legacy-backed state', async () => {
    renderPanel({ run: { ...run, world_id: 'fax-world' } })
    await userEvent.click(await screen.findByRole('button', { name: /Revision 1:/ }))
    const restore = await screen.findByRole('button', {
      name: 'Restore current Branch from this revision'
    })
    expect(restore).toBeDisabled()
    expect(screen.getByText(/only when the Saved Revision fully captures/)).toBeInTheDocument()
    expect(api.restoreSavedRevision).not.toHaveBeenCalled()
  })

  it('does not retry a conflict and requires a fresh review with the backend message', async () => {
    api.restoreSavedRevision.mockRejectedValueOnce(
      new api.ApiError(
        JSON.stringify({
          detail: {
            code: 'saved_revision_restore_version_conflict',
            message: 'Saved Revision head changed since restore preview'
          }
        }),
        409
      )
    )
    renderPanel()
    await userEvent.click(await screen.findByRole('button', { name: /Revision 1:/ }))
    const openRestore = await screen.findByRole('button', {
      name: 'Restore current Branch from this revision'
    })
    await waitFor(() => expect(openRestore).toBeEnabled())
    await userEvent.click(openRestore)
    await userEvent.type(screen.getByLabelText('Restore confirmation phrase'), 'RESTORE Timeline 1')
    await userEvent.click(
      screen.getByRole('checkbox', { name: 'Confirm Saved Revision restore' })
    )
    await userEvent.click(screen.getByRole('button', { name: 'Confirm restore' }))

    expect(
      await screen.findByText(/Saved Revision head changed since restore preview/)
    ).toBeInTheDocument()
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    expect(api.restoreSavedRevision).toHaveBeenCalledTimes(1)
  })
})
