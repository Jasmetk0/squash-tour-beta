import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  AdminHealthEditRequest,
  AdminPlayerHealthView,
  PlayerHealthSavePreview
} from '../api/types'
import { PlayerHealthAdminPanel } from './PlayerHealthAdminPanel'

const api = vi.hoisted(() => ({
  getAdminPlayerHealth: vi.fn(),
  previewAdminPlayerHealthEdit: vi.fn(),
  commitAdminPlayerHealthEdit: vi.fn(),
  previewPlayerHealthSave: vi.fn(),
  savePlayerHealthRevision: vi.fn()
}))

vi.mock('../api/client', () => api)

function view(week = 1, draftVersion = 0): AdminPlayerHealthView {
  return {
    schema_version: 'admin_health_current_view.v1',
    run_id: 'run-a',
    branch_id: 'branch-a',
    week: { season_index: 0, week },
    player: { player_id: 'P1', records: [], permanent_consequences: [] },
    state_fingerprint: 'a'.repeat(64),
    health_component_fingerprint: 'b'.repeat(64),
    draft_version: draftVersion
  }
}

function savePreview(canSave = false, draftVersion = 0): PlayerHealthSavePreview {
  return {
    run_id: 'run-a',
    branch_id: 'branch-a',
    draft_version: draftVersion,
    draft_status: canSave ? 'dirty' : 'clean',
    health_component_fingerprint: canSave ? 'd'.repeat(64) : 'b'.repeat(64),
    changed_since_saved_head: canSave,
    can_save: canSave
  }
}

function renderPanel(props?: Partial<React.ComponentProps<typeof PlayerHealthAdminPanel>>) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <PlayerHealthAdminPanel
        runId="run-a"
        branchId="branch-a"
        branchReadOnly={false}
        playerId="P1"
        {...props}
      />
    </QueryClientProvider>
  )
}

describe('PlayerHealthAdminPanel', () => {
  let current: AdminPlayerHealthView
  let saveReady: boolean

  beforeEach(() => {
    vi.clearAllMocks()
    current = view()
    saveReady = false
    api.getAdminPlayerHealth.mockImplementation(async () => current)
    api.previewPlayerHealthSave.mockImplementation(async () => savePreview(saveReady, saveReady ? 1 : 0))
    api.previewAdminPlayerHealthEdit.mockImplementation(async (_run: string, _branch: string, _player: string, payload: AdminHealthEditRequest) => ({
      schema_version: 'admin_health_edit_preview.v1',
      run_id: 'run-a',
      branch_id: 'branch-a',
      week: current.week,
      request_fingerprint: 'c'.repeat(64),
      expected_draft_version: payload.expected_draft_version,
      before_state_fingerprint: current.state_fingerprint,
      after_state: {
        schema_version: 'player_health_week_state.v1',
        run_id: 'run-a',
        branch_id: 'branch-a',
        week: current.week,
        players: [{ player_id: 'P1', records: payload.records, permanent_consequences: payload.permanent_consequences }],
        source_initial_world_fingerprint: 'world',
        predecessor_fingerprint: null,
        stage_provenance: 'admin-health-preview'
      },
      before_component_fingerprint: current.health_component_fingerprint,
      after_component_fingerprint: 'd'.repeat(64),
      preview_fingerprint: 'e'.repeat(64)
    }))
    api.commitAdminPlayerHealthEdit.mockImplementation(async (_run: string, _branch: string, _player: string, payload: AdminHealthEditRequest) => {
      current = {
        ...current,
        player: { player_id: 'P1', records: payload.records, permanent_consequences: payload.permanent_consequences },
        state_fingerprint: 'f'.repeat(64),
        health_component_fingerprint: 'd'.repeat(64),
        draft_version: 1
      }
      saveReady = true
      return {
        schema_version: 'admin_health_edit_result.v1',
        run_id: 'run-a',
        branch_id: 'branch-a',
        command_id: payload.command_id,
        week: current.week,
        player_id: 'P1',
        state_fingerprint: current.state_fingerprint,
        health_component_fingerprint: current.health_component_fingerprint,
        draft_version: 1,
        already_applied: false
      }
    })
    api.savePlayerHealthRevision.mockResolvedValue({
      run_id: 'run-a',
      branch_id: 'branch-a',
      previous_viewer_branch_id: 'branch-a',
      viewer_branch_id: 'branch-a',
      saved_revision: {
        revision_id: 'revision-health',
        sequence: 2,
        parent_revision_id: 'revision-1',
        kind: 'player_health_state',
        payload_schema_version: '1',
        content_hash_algorithm: 'sha256',
        content_hash: 'hash',
        change_summary: {}
      },
      working_draft: {
        run_id: 'run-a',
        branch_id: 'branch-a',
        draft_id: 'draft',
        base_saved_revision_id: 'revision-health',
        saved_viewer_branch_id: 'branch-a',
        proposed_viewer_branch_id: 'branch-a',
        current_viewer_branch_id: 'branch-a',
        status: 'clean',
        change_count: 0,
        draft_version: 2,
        can_save: false
      },
      audit_event_id: 'audit-health'
    })
  })

  it('reviews a Week-1 pre-start Health input, commits it, then saves a recoverable revision', async () => {
    renderPanel()

    expect(await screen.findByText('No Injury or Illness records are present at this Week.')).toBeInTheDocument()
    expect(screen.getByText(/2000\/01 · Week 1/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Edit current Health' }))
    expect(screen.getByLabelText('Edit mode')).toHaveValue('pre_start_input')
    await userEvent.click(screen.getByRole('button', { name: 'Add Health record' }))

    await userEvent.type(screen.getByLabelText('Condition key'), 'ankle')
    await userEvent.clear(screen.getByLabelText('Severity 0–100'))
    await userEvent.type(screen.getByLabelText('Severity 0–100'), '25')
    await userEvent.type(screen.getByLabelText('Affected domains (comma separated)'), 'movement, stamina, movement')
    await userEvent.type(screen.getByLabelText('Provenance'), 'Reviewed pre-start medical history')
    await userEvent.type(screen.getByLabelText('Operator label'), 'Admin')
    await userEvent.type(screen.getByLabelText('Reason'), 'Known ankle issue before Run start')
    await userEvent.click(screen.getByRole('checkbox', { name: /reviewed the complete current Health profile/i }))

    await userEvent.click(screen.getByRole('button', { name: 'Calculate Health preview' }))
    await waitFor(() => expect(api.previewAdminPlayerHealthEdit).toHaveBeenCalledTimes(1))
    const previewPayload = api.previewAdminPlayerHealthEdit.mock.calls[0][3] as AdminHealthEditRequest
    expect(previewPayload.mode).toBe('pre_start_input')
    expect(previewPayload.expected_draft_version).toBe(0)
    expect(previewPayload.records).toHaveLength(1)
    expect(previewPayload.records[0]).toEqual(expect.objectContaining({
      kind: 'Injury',
      condition_key: 'ankle',
      severity: 25,
      affected_domains: ['movement', 'stamina'],
      started_before_run: true,
      onset_week: null
    }))

    expect(await screen.findByRole('heading', { name: 'Review Health preview' })).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Confirm reviewed Health edit' }))
    await waitFor(() => expect(api.commitAdminPlayerHealthEdit).toHaveBeenCalledWith(
      'run-a',
      'branch-a',
      'P1',
      previewPayload,
      'e'.repeat(64)
    ))
    expect(await screen.findByText(/Health edit committed to the Working Draft/)).toBeInTheDocument()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Health Revision' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Save Health Revision' }))
    await waitFor(() => expect(api.savePlayerHealthRevision).toHaveBeenCalledWith('run-a', 'branch-a', {
      expected_draft_version: 1,
      expected_player_health_fingerprint: 'd'.repeat(64)
    }))
    expect(await screen.findByText('Health Saved Revision revision-health created.')).toBeInTheDocument()
  })

  it('uses current-state correction and current Week as the default onset after Week 1', async () => {
    current = view(7)
    renderPanel()

    await screen.findByText(/2000\/01 · Week 7/)
    await userEvent.click(screen.getByRole('button', { name: 'Edit current Health' }))
    expect(screen.queryByLabelText('Edit mode')).not.toBeInTheDocument()
    expect(screen.getByText('Mode: current-state correction')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Add Health record' }))

    expect(screen.getByLabelText('Onset season (1–50)')).toHaveValue(1)
    expect(screen.getByLabelText('Onset week')).toHaveValue(7)
    await userEvent.type(screen.getByLabelText('Condition key'), 'illness')
    await userEvent.selectOptions(screen.getByLabelText('Type'), 'Illness')
    await userEvent.type(screen.getByLabelText('Affected domains (comma separated)'), 'stamina')
    await userEvent.type(screen.getByLabelText('Provenance'), 'Current symptoms')
    await userEvent.type(screen.getByLabelText('Operator label'), 'Admin')
    await userEvent.type(screen.getByLabelText('Reason'), 'Current illness correction')
    await userEvent.click(screen.getByRole('checkbox', { name: /reviewed the complete current Health profile/i }))
    await userEvent.click(screen.getByRole('button', { name: 'Calculate Health preview' }))

    await waitFor(() => expect(api.previewAdminPlayerHealthEdit).toHaveBeenCalledTimes(1))
    const payload = api.previewAdminPlayerHealthEdit.mock.calls[0][3] as AdminHealthEditRequest
    expect(payload.mode).toBe('current_state_correction')
    expect(payload.records[0].onset_week).toEqual({ season_index: 0, week: 7 })
    expect(payload.records[0].started_before_run).toBe(false)
  })

  it('keeps mutation controls disabled on a read-only Branch', async () => {
    api.previewPlayerHealthSave.mockResolvedValue(savePreview(true, 1))
    renderPanel({ branchReadOnly: true })

    expect(await screen.findByRole('button', { name: 'Edit current Health' })).toBeDisabled()
    expect(screen.getByText(/Active Admin Branch is read-only/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Health Revision' })).toBeDisabled())
    expect(api.previewAdminPlayerHealthEdit).not.toHaveBeenCalled()
    expect(api.savePlayerHealthRevision).not.toHaveBeenCalled()
  })
})
