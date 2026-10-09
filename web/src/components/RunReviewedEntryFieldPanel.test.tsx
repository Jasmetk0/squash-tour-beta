import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunReviewedEntryFieldPanel } from './RunReviewedEntryFieldPanel'
import {
  strictCapacity, verifiedEntryFieldSource, verifiedReviewedEntryField,
  verifiedStoredEntryField
} from '../api/runReviewedEntryField'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) { super(message) }
  }
  return {
    ApiError,
    getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchWorkingDraft: vi.fn(),
    getCanonicalTournamentPreparation: vi.fn(), getCanonicalTournamentEntryFieldState: vi.fn(),
    previewRunReviewedEntryField: vi.fn(), commitRunReviewedEntryField: vi.fn()
  }
})
vi.mock('../api/client', () => api)

const sha = (v: string) => v.repeat(64)
const capacity = {
  main_draw_size: 4, qualification_draw_size: 2, qualifier_spots: 1,
  wild_card_slots: 0, bye_slots: 0
}
const source = {
  schema_version: 'canonical_tournament_preparation_state.v1' as const,
  run_id: 'run-e', branch_id: 'branch-e', event_id: 'first-event',
  authority_source: 'run_owned_db_authorities.v1' as const,
  phase: 'entry_field_required' as const, next_required_action: 'build_entry_field' as const,
  ranking_snapshot_ready: true, ranking_authority_fingerprint: sha('a'),
  entry_source_kind: 'ranking_applications' as const,
  entry_field_ready: false, valid_submission_count: 7,
  valid_main_submission_count: 3, valid_qualification_submission_count: 4,
  preparation_fingerprint: sha('b'),
  blockers:['tournament_entry_field_required'],
  ready_for_match_schedule:false,
  effective_draw_fingerprint:null,
  entry_capacity_suggestion: {
    schema_version:'canonical_entry_capacity_suggestion.v1' as const,
    source:'run_owned_calendar_package.v1' as const,
    source_package_id:'calendar-2000-2001',
    source_package_version:1,source_package_fingerprint:sha('c'),
    source_event_fingerprint:sha('d'), ...capacity
  }
}
const field = {
  schema_version:'tournament_entry_field.v1' as const,
  run_id:'run-e',branch_id:'branch-e',event_id:'first-event',
  mode:'initial' as const, capacity,
  tournament_ranking_authority_fingerprint:sha('a'),
  ranking_snapshot_fingerprint:sha('e'),
  applications_fingerprint:sha('f'),
  direct_main_player_ids:['A','C','D'],
  qualification_player_ids:['B','E'],
  below_qualification_cut_player_ids:['F','G'],
  withdrawn_player_ids:[],base_field_fingerprint:null
}
const preview = {preview_only:true as const,run_id:'run-e',branch_id:'branch-e',
  event_id:'first-event',field_fingerprint:sha('1'),field}
const stored = {
  schema_version:'canonical_tournament_entry_field_state.v2' as const,
  run_id:'run-e',branch_id:'branch-e',event_id:'first-event',
  field_sequence:1,field_fingerprint:sha('1'),mode:'initial' as const,
  direct_main_player_ids:['A','C','D'],qualification_player_ids:['B','E'],
  below_qualification_cut_player_ids:['F','G'],withdrawn_player_ids:[],
  main_draw_capacity:4,active_main_entrant_count:4,effective_main_bye_count:0,
  main_diagnostics:[],draw_input_committed:false,pre_draw_repair_locked_by_draw_input:false
}
let isStored = false
beforeEach(() => {
  vi.clearAllMocks()
  isStored = false
  api.getRunContainer.mockResolvedValue({
    run_id:'run-e',storage_kind:'custom_local',read_only:false,status:'working'
  })
  api.listRunBranches.mockResolvedValue({run_branches:[{
    run_id:'run-e',branch_id:'branch-e',saved_head_revision_id:'rev-e',
    status:'active',read_only:false
  }]})
  api.getBranchWorkingDraft.mockResolvedValue({
    run_id:'run-e',branch_id:'branch-e',base_saved_revision_id:'rev-e',
    status:'clean',draft_version:2
  })
  api.getCanonicalTournamentPreparation.mockResolvedValue(source)
  api.getCanonicalTournamentEntryFieldState.mockImplementation(async () => {
    if (!isStored) throw new api.ApiError('No initial field',404)
    return stored
  })
  api.previewRunReviewedEntryField.mockResolvedValue(preview)
  api.commitRunReviewedEntryField.mockImplementation(async () => {
    isStored = true
    return field
  })
})
const show=()=>renderWithRoute(
  <RunReviewedEntryFieldPanel runId="run-e" branchId="branch-e" eventId="first-event" />,
  '/admin/runs/run-e/calendar/first-event'
)

describe('Reviewed first tournament Entry Field', () => {
  it('requires server preview and approval, persists exact player cut, then verifies database readback', async () => {
    show()
    const previewButton=await screen.findByRole('button',{name:'Preview actual Entry Field'})
    await waitFor(()=>expect(previewButton).toBeEnabled())
    expect(screen.getByText(/Valid applications:/)).toBeInTheDocument()
    expect(api.commitRunReviewedEntryField).not.toHaveBeenCalled()
    await userEvent.click(previewButton)
    expect(await screen.findByText(/Main: 3 · Qualification: 2 · Reserve: 2/)).toBeInTheDocument()
    expect(screen.getByText(/A, C, D/)).toBeInTheDocument()
    expect(screen.getByText(/B, E/)).toBeInTheDocument()
    const save=screen.getByRole('button',{name:'Commit reviewed Entry Field'})
    expect(save).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve reviewed Entry Field'}))
    await userEvent.click(save)
    await waitFor(()=>expect(api.commitRunReviewedEntryField).toHaveBeenCalledWith(
      'run-e','branch-e','first-event',preview,expect.stringMatching(/^admin-reviewed-entry-field-/)
    ))
    expect(await screen.findByText(/Persisted and reloaded Entry Field #1/)).toBeInTheDocument()
    expect(await screen.findByText(/Entry Field saved and reloaded/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Preview actual Entry Field'})).not.toBeInTheDocument()
  })

  it('blocks candidate creation when no validated submissions exist', async () => {
    api.getCanonicalTournamentPreparation.mockResolvedValueOnce({
      ...source,valid_submission_count:0,valid_main_submission_count:0,
      valid_qualification_submission_count:0
    })
    show()
    expect(await screen.findByText(/First adopt a Ranking Snapshot and persist valid player applications/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Preview actual Entry Field'})).not.toBeInTheDocument()
    expect(api.previewRunReviewedEntryField).not.toHaveBeenCalled()
  })

  it('rejects a dirty Working Draft and protects existing immutable field', async () => {
    api.getBranchWorkingDraft.mockResolvedValueOnce({
      run_id:'run-e',branch_id:'branch-e',base_saved_revision_id:'rev-e',
      status:'dirty',draft_version:4
    })
    show()
    const btn=await screen.findByRole('button',{name:'Preview actual Entry Field'})
    expect(btn).toBeDisabled()
    expect(api.previewRunReviewedEntryField).not.toHaveBeenCalled()
  })

  it('clears previous approval when changed capacity invalidates the field review', async () => {
    show()
    const btn=await screen.findByRole('button',{name:'Preview actual Entry Field'})
    await waitFor(()=>expect(btn).toBeEnabled())
    await userEvent.click(btn)
    expect(await screen.findByRole('checkbox',{name:'Approve reviewed Entry Field'})).toBeInTheDocument()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Reviewed Qualification Draw capacity'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Reviewed Qualification Draw capacity'}),'4')
    await waitFor(()=>expect(screen.queryByRole('button',{name:'Commit reviewed Entry Field'})).not.toBeInTheDocument())
    expect(api.commitRunReviewedEntryField).not.toHaveBeenCalled()
  })

  it('rejects foreign ranking source, changed partitions or invalid geometry', () => {
    expect(verifiedEntryFieldSource(source,'run-e','branch-e','first-event')).toBe(true)
    expect(verifiedEntryFieldSource(source,'run-e','different','first-event')).toBe(false)
    expect(strictCapacity({...capacity,main_draw_size:7})).toBe(false)
    expect(verifiedReviewedEntryField(preview,source,'run-e','branch-e','first-event',capacity)).toBe(true)
    expect(verifiedReviewedEntryField({...preview,field:{...field,applications_fingerprint:'stale'}},source,'run-e','branch-e','first-event',capacity)).toBe(false)
    expect(verifiedStoredEntryField(stored,preview)).toBe(true)
    expect(verifiedStoredEntryField({...stored,field_fingerprint:sha('0')},preview)).toBe(false)
  })
})
