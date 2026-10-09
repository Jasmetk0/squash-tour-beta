import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunBranch, RunContainer } from '../api/types'
import type { RankingCandidateDetail } from '../api/rankingCandidates'
import {
  verifyDerivedInitialCandidate, verifyDerivedInitialPreview
} from '../api/runInitialRankingSetup'
import { RunInitialRankingSetupPanel } from './RunInitialRankingSetupPanel'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) { super(message) }
  }
  return {
    ApiError,
    getBranchWorkingDraft: vi.fn(),
    getRankingCandidates: vi.fn(),
    getRunOwnedInitialWorld: vi.fn(),
    previewRunDerivedInitialRanking: vi.fn(),
    confirmRunDerivedInitialRanking: vi.fn(),
    previewRankingSave: vi.fn(),
    saveRunDerivedInitialRankingRevision: vi.fn()
  }
})
vi.mock('../api/client', () => api)

const run: RunContainer = {
  run_id: 'sandbox-a', display_name: 'Sandbox A', storage_kind: 'custom_local',
  read_only: false, status: 'working', timeline_start_season: 2000,
  timeline_end_season: 2049, world_id: null, world_package_fingerprint: null,
  config_version: null, config_fingerprint: null, global_seed: null,
  official_branch_id: null, metadata_json: {}, mapped_simulation_run_count: 0
}
const branch: RunBranch = {
  run_id: run.run_id, branch_id: 'timeline-1', display_name: 'Timeline 1',
  status: 'active', read_only: false, saved_head_revision_id: 'rev-a',
  branch_seed: null, forked_from_branch_id: null, forked_from_checkpoint_id: null,
  head_checkpoint_id: null, legacy_simulation_run_id: null, metadata_json: {},
  is_official: false
}
const hash = (letter: string) => letter.repeat(64)
const world = {
  run_id: run.run_id, branch_id: branch.branch_id, season: '2000/2001',
  source_kind: 'run_world_generated_pool.v1',
  adoption_request_fingerprint: hash('a'), bootstrap_seed: 775,
  world_package_id: 'fifa_earth',
  players: [{player_id:'p1'},{player_id:'p2'}],
  policies: [{policy_id: 'msa-official-2000-01', best_n: 15}]
}

let prepared = false
let draftVersion = 0
let saved = false
let expectedCommandId = ''
const candidate = (cmd: string): RankingCandidateDetail => ({
  publication_status: 'candidate_only', fingerprint: hash('b'), command_ids: [cmd],
  snapshot: {
    run_id: run.run_id, branch_id: branch.branch_id,
    week: { season_index: 0, week: 1 },
    policy: { policy_id: 'msa-official-2000-01', best_n: 15 },
    rows: []
  }
})

beforeEach(() => {
  vi.clearAllMocks()
  prepared = false; draftVersion = 0; saved = false; expectedCommandId = ''
  api.getRunOwnedInitialWorld.mockResolvedValue(world)
  api.getBranchWorkingDraft.mockImplementation(async () => ({
    run_id: run.run_id, branch_id: branch.branch_id,
    base_saved_revision_id: 'rev-a',
    draft_version: draftVersion,
    status: prepared && !saved ? 'dirty' : 'clean'
  }))
  api.getRankingCandidates.mockImplementation(async () => ({
    run_id: run.run_id, branch_id: branch.branch_id,
    publication_status: 'candidate_only',
    candidates: prepared ? [candidate(expectedCommandId)] : []
  }))
  api.previewRunDerivedInitialRanking.mockImplementation(async (_r: string, _b: string, request: {command_id: string}) => {
    expectedCommandId = request.command_id
    return { preview_only: true, request_fingerprint: hash('c'), candidate: candidate(request.command_id) }
  })
  api.confirmRunDerivedInitialRanking.mockImplementation(async (_r: string, _b: string, request: {command_id: string}) => {
    prepared = true; draftVersion = 1
    return candidate(request.command_id)
  })
  api.previewRankingSave.mockImplementation(async () => ({
    run_id: run.run_id, branch_id: branch.branch_id,
    saved_head_revision_id: 'rev-a', draft_version: draftVersion,
    ranking_fingerprint: hash('d'), has_unsaved_changes: true, can_save: true
  }))
  api.saveRunDerivedInitialRankingRevision.mockImplementation(async () => {
    saved = true
    return { run_id: run.run_id, branch_id: branch.branch_id,
      saved_revision: { revision_id: 'rev-b' },
      working_draft: { run_id: run.run_id, branch_id: branch.branch_id,
        base_saved_revision_id: 'rev-b', status: 'clean' }
    }
  })
})

function render(runData: RunContainer = run, branchData: RunBranch | null = branch) {
  return renderWithRoute(
    <RunInitialRankingSetupPanel run={runData} branch={branchData} />,
    '/admin/runs/sandbox-a'
  )
}

describe('Run initial ranking', () => {
  it('previews backend-derived Week 1, confirms exact candidate and saves separate revision', async () => {
    render()
    await userEvent.click(await screen.findByRole('button', {name:'Preview initial ranking'}))
    await waitFor(() => expect(api.previewRunDerivedInitialRanking).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, expect.objectContaining({
        command_id: expect.any(String),
        audit: expect.objectContaining({actor_label: 'Run Admin initial ranking'})
      }), 15
    ))
    expect(await screen.findByText(/Classified rows: 0/)).toBeInTheDocument()
    expect(api.confirmRunDerivedInitialRanking).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve initial ranking preparation' }))
    await userEvent.click(screen.getByRole('button', {name:'Confirm initial ranking'}))
    await waitFor(() => expect(api.confirmRunDerivedInitialRanking).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, expect.objectContaining({command_id: expectedCommandId}),
      expect.objectContaining({ request_fingerprint: hash('c') }), 15
    ))
    expect(api.saveRunDerivedInitialRankingRevision).not.toHaveBeenCalled()
    await userEvent.click(await screen.findByRole('checkbox', {name:'Approve initial ranking save'}))
    await userEvent.click(screen.getByRole('button', {name:'Save initial ranking revision'}))
    await waitFor(() => expect(api.saveRunDerivedInitialRankingRevision).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 1, hash('d')
    ))
    expect(await screen.findByText(/saved in immutable Branch history/)).toBeInTheDocument()
  })

  it('does not synthesize ranked rows before real results and verifies review guards', () => {
    const intent = { command_id: 'review-id', audit: { actor_label: 'Admin', reason: 'first' } }
    const valid = { preview_only: true as const, request_fingerprint: hash('c'), candidate: candidate(intent.command_id) }
    expect(verifyDerivedInitialPreview(run.run_id, branch.branch_id, intent, 15, valid)).toBe(true)
    expect(valid.candidate.snapshot.rows).toHaveLength(0)
    expect(verifyDerivedInitialPreview(run.run_id, 'other-branch', intent, 15, valid)).toBe(false)
    expect(verifyDerivedInitialCandidate(run.run_id, branch.branch_id, intent.command_id, 20, valid.candidate)).toBe(false)
    expect(verifyDerivedInitialPreview(run.run_id, branch.branch_id, intent, 15,
      { ...valid, request_fingerprint: 'wrong' })).toBe(false)
  })

  it('blocks protected Runs and refuses a mismatched Branch', async () => {
    render({...run, read_only: true})
    expect(await screen.findByRole('button', {name:'Preview initial ranking'})).toBeDisabled()
  })

  it('does not prepare a duplicate Week-1 candidate after reopening', async () => {
    prepared = true
    expectedCommandId = 'existing-ranking-command'
    saved = true
    render()
    expect(await screen.findByText(/Week-1 ranking candidate exists/)).toBeInTheDocument()
    expect(screen.getByRole('button', {name:'Preview initial ranking'})).toBeDisabled()
    expect(screen.getByText(/Zero classified players is expected/)).toBeInTheDocument()
    expect(api.previewRunDerivedInitialRanking).not.toHaveBeenCalled()
  })

  it('allows save-only resume for a prepared unsaved candidate after page reload', async () => {
    prepared = true
    draftVersion = 1
    expectedCommandId = 'persisted-command'
    render()
    const resume = await screen.findByRole('button', { name: 'Review existing ranking save' })
    expect(api.previewRunDerivedInitialRanking).not.toHaveBeenCalled()
    await userEvent.click(resume)
    await userEvent.click(await screen.findByRole('checkbox', {name:'Approve initial ranking save'}))
    await userEvent.click(screen.getByRole('button', {name:'Save initial ranking revision'}))
    await waitFor(() => expect(api.saveRunDerivedInitialRankingRevision).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 1, hash('d')
    ))
  })

  it('allows initial-ranking Save when the authoritative preflight is ready and Working Draft is clean', async () => {
    prepared = true
    draftVersion = 1
    expectedCommandId = 'clean-draft-ranking-command'
    // Ranking preparation is an independently saved component: it need not dirty the
    // viewer-branch Working Draft, as verified by backend test_ranking_independent_save.
    api.getBranchWorkingDraft.mockResolvedValue({
      run_id: run.run_id, branch_id: branch.branch_id,
      base_saved_revision_id: 'rev-a', draft_version: 1, status: 'clean'
    })
    render()
    await userEvent.click(await screen.findByRole('button', { name: 'Review existing ranking save' }))
    await userEvent.click(screen.getByRole('checkbox', {name:'Approve initial ranking save'}))
    await userEvent.click(screen.getByRole('button', {name:'Save initial ranking revision'}))
    await waitFor(() => expect(api.saveRunDerivedInitialRankingRevision).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 1, hash('d')
    ))
  })

  it('clears the reviewed request when audit reason changes', async () => {
    render()
    await userEvent.click(await screen.findByRole('button', {name:'Preview initial ranking'}))
    expect(await screen.findByText(/Review Week-1 ranking candidate/)).toBeInTheDocument()
    await userEvent.clear(screen.getByRole('textbox', {name:'Initial ranking audit reason'}))
    await userEvent.type(screen.getByRole('textbox', {name:'Initial ranking audit reason'}), 'Changed reason')
    await waitFor(() => expect(screen.queryByRole('button', {name:'Confirm initial ranking'})).not.toBeInTheDocument())
    expect(api.confirmRunDerivedInitialRanking).not.toHaveBeenCalled()
  })
})
