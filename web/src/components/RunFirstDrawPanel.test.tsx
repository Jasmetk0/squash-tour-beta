import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { RunFirstDrawPanel } from './RunFirstDrawPanel'
import {
  canReviewInitialDrawInput, verifiedCommittedDrawInput, verifiedGeneratedFirstDraw
} from '../api/runFirstDrawReview'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) { super(message) }
  }
  return {
    ApiError,
    getRunContainer: vi.fn(), listRunBranches: vi.fn(), getBranchWorkingDraft: vi.fn(),
    getCanonicalTournamentPreparation: vi.fn(), getCanonicalTournamentEntryFieldState: vi.fn(),
    getCanonicalTournamentDrawState: vi.fn(), getCanonicalTournamentDrawAuthority: vi.fn(),
    commitCanonicalTournamentDrawInput: vi.fn(), generateCanonicalTournamentDraw: vi.fn()
  }
})
vi.mock('../api/client', () => api)

const sha = (x: string) => x.repeat(64)
const field = {
  schema_version: 'canonical_tournament_entry_field_state.v2' as const,
  run_id:'product', branch_id:'timeline', event_id:'first',
  field_sequence:1, field_fingerprint:sha('a'), mode:'initial' as const,
  direct_main_player_ids:['P1','P2','P3'], qualification_player_ids:[],
  below_qualification_cut_player_ids:[], withdrawn_player_ids:[],
  main_draw_capacity:4,active_main_entrant_count:3,effective_main_bye_count:1,
  main_diagnostics:[],draw_input_committed:false,pre_draw_repair_locked_by_draw_input:false
}
const preparation = {
  schema_version:'canonical_tournament_preparation_state.v1' as const,
  run_id:'product',branch_id:'timeline',event_id:'first',
  authority_source:'run_owned_db_authorities.v1' as const,
  phase:'draw_input_ready' as const,
  next_required_action:'review_pre_draw_or_commit_draw_input' as const,
  preparation_fingerprint:sha('b'),
  blockers:[],entry_field_ready:true,entry_field_fingerprint:sha('a'),
  ranking_snapshot_ready:true,wild_card_required:false,wild_card_ready:true,
  entry_source_kind:'ranking_applications' as const,
  ready_for_match_schedule:false,effective_draw_fingerprint:null
}
const initialState = {
  schema_version:'canonical_tournament_draw_state.v1' as const,
  run_id:'product',branch_id:'timeline',event_id:'first',
  field_sequence:1,field_fingerprint:sha('a'),main_draw_capacity:4,
  active_main_entrant_count:3,effective_main_bye_count:1,
  draw_input_committed:false,draw_input_fingerprint:null,draw_seed:null,
  main_seed_count:null,qualification_seed_count:null,
  initial_draw_generated:false,draw_authority_fingerprint:null,
  draw_algorithm_version:null,main_slot_count:null,main_node_count:null,
  main_bye_count:null,qualification_section_count:null,qualification_section_sizes:[],
  main_diagnostics:[]
}
const inputState = {
  ...initialState,draw_input_committed:true,draw_input_fingerprint:sha('c'),
  draw_seed:12345,main_seed_count:2,qualification_seed_count:0
}
const generatedState = {
  ...inputState,initial_draw_generated:true,draw_authority_fingerprint:sha('d'),
  draw_algorithm_version:'protected_seed_shuffle.v1',main_slot_count:4,
  main_node_count:3,main_bye_count:1,qualification_section_count:0,
  qualification_section_sizes:[]
}
const drawAuthority = {
  schema_version:'tournament_draw_authority.v1' as const,
  algorithm_version:'protected_seed_shuffle.v1' as const,
  run_id:'product',branch_id:'timeline',event_id:'first',
  generated_by_command_id:'generated-command',draw_input_fingerprint:sha('c'),
  main:{
    draw_type:'main' as const, bracket_size:4,
    seed_positions:[[1,1],[2,3]] as Array<[number,number]>,
    slots:[
      {slot_index:1,entrant_kind:'player' as const,player_id:'P1',
        placeholder_id:null,seed_number:1,is_seed_protected:true},
      {slot_index:2,entrant_kind:'bye' as const,player_id:null,
        placeholder_id:null,seed_number:null,is_seed_protected:false},
      {slot_index:3,entrant_kind:'player' as const,player_id:'P2',
        placeholder_id:null,seed_number:2,is_seed_protected:true},
      {slot_index:4,entrant_kind:'player' as const,player_id:'P3',
        placeholder_id:null,seed_number:null,is_seed_protected:false}
    ],
    nodes:[],bye_slot_indexes:[1],qualifier_placeholder_slots:[]
  },
  qualification:null,qualification_sections:[]
}
let currentDraw: typeof initialState | typeof inputState | typeof generatedState
let currentPrep: typeof preparation | Record<string,unknown>
let currentField: typeof field | null
let freshSourceChanged: boolean
beforeEach(() => {
  vi.clearAllMocks()
  currentDraw=initialState
  currentPrep=preparation
  currentField=field
  freshSourceChanged=false
  api.getRunContainer.mockResolvedValue({
    run_id:'product',storage_kind:'custom_local',read_only:false,status:'working'
  })
  api.listRunBranches.mockResolvedValue({run_branches:[{
    run_id:'product',branch_id:'timeline',status:'active',read_only:false,
    saved_head_revision_id:'rev-1'
  }]})
  api.getBranchWorkingDraft.mockResolvedValue({
    run_id:'product',branch_id:'timeline',base_saved_revision_id:'rev-1',
    status:'clean',draft_version:1
  })
  api.getCanonicalTournamentPreparation.mockImplementation(async () =>
    freshSourceChanged ? {...currentPrep,preparation_fingerprint:sha('0')} : currentPrep
  )
  api.getCanonicalTournamentEntryFieldState.mockImplementation(async () => {
    if (!currentField) throw new api.ApiError('No Entry Field',404)
    return currentField
  })
  api.getCanonicalTournamentDrawState.mockImplementation(async () => {
    if (!currentField) throw new api.ApiError('No Draw authority',404)
    return currentDraw
  })
  api.getCanonicalTournamentDrawAuthority.mockResolvedValue(drawAuthority)
  api.commitCanonicalTournamentDrawInput.mockImplementation(async () => {
    currentDraw=inputState
    currentPrep={...preparation,phase:'draw_generation_ready',
      next_required_action:'generate_draw'}
    return inputState
  })
  api.generateCanonicalTournamentDraw.mockImplementation(async () => {
    currentDraw=generatedState
    currentPrep={...preparation,phase:'draw_ready',next_required_action:'none'}
    return generatedState
  })
})
const show=()=>renderWithRoute(
  <RunFirstDrawPanel runId="product" branchId="timeline" eventId="first" />,
  '/admin/runs/product/calendar/first'
)

describe('First true Run-owned immutable tournament bracket', () => {
  it('freezes only reviewed Draw Input, then separately draws and re-reads real players and BYEs', async () => {
    show()
    const reviewInput=await screen.findByRole('button',{name:'Review first Draw Input'})
    await waitFor(()=>expect(reviewInput).toBeEnabled())
    await userEvent.click(reviewInput)
    expect(screen.getByText(/Freeze Entry Field #1/)).toBeInTheDocument()
    expect(api.commitCanonicalTournamentDrawInput).not.toHaveBeenCalled()
    let save=screen.getByRole('button',{name:'Commit reviewed Draw Input'})
    expect(save).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve Draw Input'}))
    await userEvent.click(save)
    await waitFor(()=>expect(api.commitCanonicalTournamentDrawInput).toHaveBeenCalledWith(
      'product','timeline','first',expect.objectContaining({
        expected_field_fingerprint:sha('a'),draw_seed:12345
      })
    ))
    expect(await screen.findByText(/Draw Input saved: seed 12345/)).toBeInTheDocument()
    const reviewGeneration=await screen.findByRole('button',{name:'Review initial bracket generation'})
    await waitFor(()=>expect(reviewGeneration).toBeEnabled())
    await userEvent.click(reviewGeneration)
    expect(api.generateCanonicalTournamentDraw).not.toHaveBeenCalled()
    const generate=screen.getByRole('button',{name:'Generate reviewed initial Draw'})
    expect(generate).toBeDisabled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve initial bracket generation'}))
    await userEvent.click(generate)
    await waitFor(()=>expect(api.generateCanonicalTournamentDraw).toHaveBeenCalledWith(
      'product','timeline','first',expect.objectContaining({
        expected_draw_input_fingerprint:sha('c')
      })
    ))
    expect(await screen.findByText(/Saved initial bracket/)).toBeInTheDocument()
    expect(screen.getByText(/Actual Main slots: 4 · BYEs: 1/)).toBeInTheDocument()
    expect(screen.getByText('P1')).toBeInTheDocument()
    expect(screen.getByText('P2')).toBeInTheDocument()
    expect(screen.getByText('P3')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Review initial bracket generation'})).not.toBeInTheDocument()
  })

  it('blocks Draw Input when Wild Card authority has not been reviewed', async () => {
    currentPrep={...preparation,wild_card_required:true,wild_card_ready:false,
      blockers:['tournament_wild_card_review_required'],
      next_required_action:'review_wild_cards'}
    show()
    expect(await screen.findByText(/Complete the existing Wild Card review/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Review first Draw Input'})).toBeDisabled()
    expect(api.commitCanonicalTournamentDrawInput).not.toHaveBeenCalled()
  })

  it('blocks when Working Draft is dirty or saved Run is not writable', async () => {
    api.getBranchWorkingDraft.mockResolvedValue({
      run_id:'product',branch_id:'timeline',base_saved_revision_id:'rev-1',
      status:'dirty',draft_version:2
    })
    show()
    expect(await screen.findByText(/Requires an active writable Run/)).toBeInTheDocument()
    expect(await screen.findByRole('button',{name:'Review first Draw Input'})).toBeDisabled()
  })

  it('refuses stale preparation on confirmation before any authoritative write', async () => {
    show()
    const button=await screen.findByRole('button',{name:'Review first Draw Input'})
    await waitFor(()=>expect(button).toBeEnabled())
    await userEvent.click(button)
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve Draw Input'}))
    freshSourceChanged=true
    await userEvent.click(screen.getByRole('button',{name:'Commit reviewed Draw Input'}))
    expect(await screen.findByText(/Draw Input source changed/)).toBeInTheDocument()
    expect(api.commitCanonicalTournamentDrawInput).not.toHaveBeenCalled()
  })

  it('reopens an already-generated initial Draw without allowing a second initial Draw', async () => {
    currentDraw=generatedState
    currentPrep={...preparation,phase:'draw_ready',next_required_action:'none'}
    show()
    expect(await screen.findByText(/Saved initial bracket/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Review first Draw Input'})).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Review initial bracket generation'})).not.toBeInTheDocument()
    expect(api.commitCanonicalTournamentDrawInput).not.toHaveBeenCalled()
  })

  it('fails closed on mismatched field, seed or fabricated/duplicate slot identities', () => {
    expect(canReviewInitialDrawInput(preparation,field,initialState,
      'product','timeline','first')).toBe(true)
    expect(canReviewInitialDrawInput(preparation,{...field,field_fingerprint:sha('1')},initialState,
      'product','timeline','first')).toBe(false)
    expect(verifiedCommittedDrawInput(inputState,field,'product','timeline','first',12345)).toBe(true)
    expect(verifiedCommittedDrawInput(inputState,field,'product','timeline','first',2)).toBe(false)
    expect(verifiedGeneratedFirstDraw(generatedState,drawAuthority,field,sha('c'),
      'product','timeline','first')).toBe(true)
    expect(verifiedGeneratedFirstDraw(generatedState,{
      ...drawAuthority,main:{...drawAuthority.main,
        slots:[drawAuthority.main.slots[0],drawAuthority.main.slots[0],
          drawAuthority.main.slots[2],drawAuthority.main.slots[3]]}
    },field,sha('c'),'product','timeline','first')).toBe(false)
  })
})
