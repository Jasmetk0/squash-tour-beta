import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor } from '@testing-library/react'
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
vi.mock('../utils/apiErrors',()=>({formatApiError:(error:unknown)=>String(error)}))

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
  const rendered = render(
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
  return {client,...rendered}
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
      schema_version: payload.schema_version==='admin_health_edit_request.v2'?'admin_health_edit_preview.v2':'admin_health_edit_preview.v1',
      saved_head_revision_id: current.saved_head_revision_id,
      run_id: 'run-a',
      branch_id: 'branch-a',
      week: current.week,
      request_fingerprint: 'c'.repeat(64),
      expected_draft_version: payload.expected_draft_version,
      before_state_fingerprint: current.state_fingerprint,
      after_state: {
        schema_version: payload.schema_version==='admin_health_edit_request.v2'?'player_health_calendar_state.v2':'player_health_week_state.v1',
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
        run_id:'run-a',branch_id:'branch-a',
        payload:{content:{player_health_state:{fingerprint:'d'.repeat(64)}}},
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
    expect(screen.getByRole('button', { name: 'Confirm reviewed Health edit' })).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Confirm Health changes' }))
    await userEvent.click(screen.getByRole('button', { name: 'Confirm reviewed Health edit' }))
    await waitFor(() => expect(api.commitAdminPlayerHealthEdit).toHaveBeenCalledWith(
      'run-a',
      'branch-a',
      'P1',
      previewPayload,
      'e'.repeat(64)
    ))
    expect(await screen.findByText(/Health edit committed to the Working Draft/)).toBeInTheDocument()

    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Health Revision' })).toBeDisabled())
    await userEvent.click(screen.getByRole('checkbox', { name:'Confirm Health Save' }))
    await waitFor(() => expect(screen.getByRole('button', { name: 'Save Health Revision' })).toBeEnabled())
    await userEvent.click(screen.getByRole('button', { name: 'Save Health Revision' }))
    await waitFor(() => expect(api.savePlayerHealthRevision).toHaveBeenCalledWith('run-a', 'branch-a', {
      expected_draft_version: 1,
      expected_player_health_fingerprint: 'd'.repeat(64)
    }))
    expect(await screen.findByText('Health Saved Revision created. revision-health')).toBeInTheDocument()
  })

  it('uses current-state correction and current Week as the default onset after Week 1', async () => {
    current = view(7)
    renderPanel()

    await screen.findByText(/2000\/01 · Week 7/)
    await userEvent.click(screen.getByRole('button', { name: 'Edit current Health' }))
    expect(screen.queryByLabelText('Edit mode')).not.toBeInTheDocument()
    expect(screen.getByText('Mode: current-state correction')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Add Health record' }))

    expect(screen.getByLabelText('Onset season')).toHaveValue(1)
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
  async function prepare() {
    await userEvent.click(await screen.findByRole('button',{name:'Edit current Health'}))
    await userEvent.click(screen.getByRole('button',{name:'Add Health record'}))
    await userEvent.type(screen.getByLabelText('Condition key'),'ankle')
    await userEvent.type(screen.getByLabelText('Affected domains (comma separated)'),'movement')
    await userEvent.type(screen.getByLabelText('Provenance'),'Known medical history')
    await userEvent.type(screen.getByLabelText('Operator label'),'Admin')
    await userEvent.type(screen.getByLabelText('Reason'),'Known ankle problem')
    await userEvent.click(screen.getByRole('checkbox',{name:/reviewed the complete current Health profile/i}))
    await userEvent.click(screen.getByRole('button',{name:'Calculate Health preview'}))
  }

  it('sends actual W80 calendar and Saved proof for current-state dates',async()=>{
    current={...view(),schema_version:'admin_health_current_view.v2',saved_head_revision_id:'head',
      week:{calendar:{schema_version:'run_calendar.v1',weeks_per_year:80,season_start_year_week:80,start_year:0,season_count:300},season_index:0,week:1}}
    renderPanel()
    await userEvent.click(await screen.findByRole('button',{name:'Edit current Health'}))
    await userEvent.selectOptions(screen.getByLabelText('Edit mode'),'current_state_correction')
    await userEvent.click(screen.getByRole('button',{name:'Add Health record'}))
    expect(screen.getByLabelText('Onset week')).toHaveAttribute('max','80')
    expect(screen.getByLabelText('Onset season')).toHaveAttribute('max','300')
    await userEvent.type(screen.getByLabelText('Condition key'),'illness')
    await userEvent.type(screen.getByLabelText('Affected domains (comma separated)'),'stamina')
    await userEvent.type(screen.getByLabelText('Provenance'),'Observed symptoms')
    await userEvent.type(screen.getByLabelText('Operator label'),'Admin')
    await userEvent.type(screen.getByLabelText('Reason'),'Current facts')
    await userEvent.click(screen.getByRole('checkbox',{name:/reviewed the complete current Health profile/i}))
    await userEvent.click(screen.getByRole('button',{name:'Calculate Health preview'}))
    await screen.findByRole('heading',{name:'Review Health preview'})
    const request=api.previewAdminPlayerHealthEdit.mock.calls[0][3]
    expect(request).toMatchObject({schema_version:'admin_health_edit_request.v2',expected_saved_head:'head',expected_state_fingerprint:'a'.repeat(64)})
    expect(request.records[0].onset_week).toEqual(current.week)
  })

  it('reads the installed state after response loss without an automatic retry or Save',async()=>{
    const install=api.commitAdminPlayerHealthEdit.getMockImplementation()!
    api.commitAdminPlayerHealthEdit.mockImplementation(async(...args)=>{await install(...args);throw Error('Response lost')})
    renderPanel();await prepare()
    await screen.findByRole('heading',{name:'Review Health preview'})
    await userEvent.click(screen.getByRole('checkbox',{name:'Confirm Health changes'}))
    await userEvent.click(screen.getByRole('button',{name:'Confirm reviewed Health edit'}))
    await screen.findByRole('button',{name:'Edit current Health'})
    expect(api.commitAdminPlayerHealthEdit).toHaveBeenCalledTimes(1)
    expect(api.savePlayerHealthRevision).not.toHaveBeenCalled()
    expect(screen.getByRole('checkbox',{name:'Confirm Health Save'})).not.toBeChecked()
  })

  it('discards a late preview after source drift and requires new consent after change-back',async()=>{
    let finish!:(value:unknown)=>void
    const calculate=api.previewAdminPlayerHealthEdit.getMockImplementation()!
    api.previewAdminPlayerHealthEdit.mockImplementation((...args)=>new Promise(resolve=>{finish=async()=>resolve(await calculate(...args))}))
    const {client}=renderPanel();await prepare()
    await waitFor(()=>expect(api.previewAdminPlayerHealthEdit).toHaveBeenCalledTimes(1))
    await act(async()=>client.setQueryData(['admin-player-health','run-a','branch-a','P1',undefined],{...view(),draft_version:1}))
    await waitFor(()=>expect(screen.getByRole('button',{name:'Edit current Health'})).toBeInTheDocument())
    await act(async()=>client.setQueryData(['admin-player-health','run-a','branch-a','P1',undefined],view()))
    await act(async()=>finish(null))
    expect(screen.queryByRole('heading',{name:'Review Health preview'})).not.toBeInTheDocument()
    expect(api.commitAdminPlayerHealthEdit).not.toHaveBeenCalled()
  })

  it('revokes reviewed confirmation when the current proof changes',async()=>{
    const {client}=renderPanel();await prepare()
    await screen.findByRole('heading',{name:'Review Health preview'})
    await userEvent.click(screen.getByRole('checkbox',{name:'Confirm Health changes'}))
    await act(async()=>client.setQueryData(['admin-player-health','run-a','branch-a','P1',undefined],{...view(),draft_version:1}))
    await waitFor(()=>expect(screen.queryByRole('button',{name:'Confirm reviewed Health edit'})).not.toBeInTheDocument())
    expect(api.commitAdminPlayerHealthEdit).not.toHaveBeenCalled()
  })

  it('uses Czech copy for the health operation',async()=>{
    renderPanel({locale:'cs'})
    expect(await screen.findByRole('button',{name:'Upravit zdraví'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Upravit zdraví'}))
    expect(screen.getByRole('button',{name:'Přidat zdravotní záznam'})).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Připravit náhled zdraví'})).toBeDisabled()
  })

  it('reads state after a lost Save response and revokes Save consent without retrying',async()=>{
    current={...view(1,1),health_component_fingerprint:'d'.repeat(64)};saveReady=true
    api.savePlayerHealthRevision.mockImplementation(async()=>{
      saveReady=false;current={...current,draft_version:2};throw Error('Save response lost')
    })
    renderPanel()
    await screen.findByRole('button',{name:'Edit current Health'})
    await userEvent.click(screen.getByRole('checkbox',{name:'Confirm Health Save'}))
    const save=screen.getByRole('button',{name:'Save Health Revision'})
    await waitFor(()=>expect(save).toBeEnabled());await userEvent.click(save)
    await waitFor(()=>expect(api.savePlayerHealthRevision).toHaveBeenCalledTimes(1))
    await waitFor(()=>expect(screen.getByText('Current Health is already captured by the Saved Revision.')).toBeInTheDocument())
    expect(screen.getByRole('checkbox',{name:'Confirm Health Save'})).not.toBeChecked()
    expect(screen.getByRole('button',{name:'Save Health Revision'})).toBeDisabled()
  })

  it('rejects a Save receipt for different content and requires fresh consent',async()=>{
    current={...view(1,1),health_component_fingerprint:'d'.repeat(64)};saveReady=true
    api.savePlayerHealthRevision.mockResolvedValue({saved_revision:{run_id:'run-a',branch_id:'branch-a',revision_id:'bad',payload:{content:{player_health_state:{fingerprint:'wrong'}}}}})
    renderPanel();await screen.findByRole('button',{name:'Edit current Health'})
    await userEvent.click(screen.getByRole('checkbox',{name:'Confirm Health Save'}))
    const save=screen.getByRole('button',{name:'Save Health Revision'})
    await waitFor(()=>expect(save).toBeEnabled());await userEvent.click(save)
    expect(await screen.findByRole('alert')).toHaveTextContent('Save receipt differs')
    expect(screen.getByRole('checkbox',{name:'Confirm Health Save'})).not.toBeChecked()
    expect(screen.queryByText(/Health Saved Revision created/)).not.toBeInTheDocument()
  })

})
