import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunBranch, RunContainer } from '../api/types'
import type { RankingCandidateDetail } from '../api/rankingCandidates'
import {
  validWeekOnePublicationCandidate, verifiedInitialRankingPublication,
  verifiedViewerInitialRanking
} from '../api/runInitialRankingPublication'
import { RunInitialRankingPublicationPanel } from './RunInitialRankingPublicationPanel'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) { super(message) }
  }
  return {
    ApiError,
    getBranchWorkingDraft: vi.fn(),
    getRankingCandidates: vi.fn(),
    getViewerOfficialRanking: vi.fn(),
    previewRankingSave: vi.fn(),
    publishRunInitialRanking: vi.fn(),
    saveRunDerivedInitialRankingRevision: vi.fn()
  }
})
vi.mock('../api/client', () => api)

const hash = (letter: string) => letter.repeat(64)
const run: RunContainer = {
  run_id: 'sandbox-publish', display_name: 'Publish sandbox',
  storage_kind: 'custom_local', read_only: false, status: 'working',
  timeline_start_season: 2000, timeline_end_season: 2049,
  world_id: null, world_package_fingerprint: null, config_version: null,
  config_fingerprint: null, global_seed: null, official_branch_id: 'timeline-1',
  metadata_json: {}, mapped_simulation_run_count: 0
}
const branch: RunBranch = {
  run_id: run.run_id, branch_id: 'timeline-1', display_name: 'Timeline 1',
  status: 'active', read_only: false, saved_head_revision_id: 'rev-1',
  branch_seed: null, forked_from_branch_id: null, forked_from_checkpoint_id: null,
  head_checkpoint_id: null, legacy_simulation_run_id: null,
  metadata_json: {}, is_official: true
}
const candidate: RankingCandidateDetail = {
  publication_status: 'candidate_only', fingerprint: hash('a'), command_ids: ['prepared-1'],
  snapshot: { run_id: run.run_id, branch_id: branch.branch_id,
    week: { season_index: 0, week: 1 },
    policy: { policy_id: 'msa-initial', best_n: 15 },
    rows: [] }
}
let published = false
let saved = false
let unsavedBeforePublish = false

beforeEach(() => {
  vi.clearAllMocks()
  published = false
  saved = false
  unsavedBeforePublish = false
  api.getRankingCandidates.mockResolvedValue({
    run_id: run.run_id, branch_id: branch.branch_id,
    publication_status: 'candidate_only', candidates: [candidate]
  })
  api.getBranchWorkingDraft.mockResolvedValue({
    run_id: run.run_id, branch_id: branch.branch_id,
    base_saved_revision_id: 'rev-1', status: 'clean', draft_version: 0
  })
  api.previewRankingSave.mockImplementation(async () => ({
    run_id: run.run_id, branch_id: branch.branch_id,
    ranking_fingerprint: published ? hash('b') : hash('c'),
    saved_head_revision_id: 'rev-1', draft_version: 0,
    has_unsaved_changes: (published && !saved) || unsavedBeforePublish,
    can_save: (published && !saved) || unsavedBeforePublish
  }))
  api.getViewerOfficialRanking.mockImplementation(async () => {
    if (!saved) throw new api.ApiError('No Saved Revision publication', 409)
    return {
      schema_version: 'viewer_official_ranking.v1',
      product_run_id: run.run_id, viewer_branch_id: branch.branch_id,
      season_index: 0, week: 1, week_ordinal: 0,
      snapshot_fingerprint: hash('a'), policy_id: 'msa-initial',
      best_n: 15, row_count: 0, rows: []
    }
  })
  api.publishRunInitialRanking.mockImplementation(async () => {
    published = true
    return {
      schema_version: 'initial_official_ranking_publication.v1',
      run_id: run.run_id, branch_id: branch.branch_id,
      week: { season_index: 0, week: 1 },
      ranking_fingerprint: hash('a'), exact_retry: false
    }
  })
  api.saveRunDerivedInitialRankingRevision.mockImplementation(async () => {
    saved = true
    return {
      run_id: run.run_id, branch_id: branch.branch_id,
      saved_revision: { revision_id: 'rev-2' },
      working_draft: { run_id: run.run_id, branch_id: branch.branch_id,
        base_saved_revision_id: 'rev-2', status: 'clean' }
    }
  })
})

function render(runData: RunContainer = run, branchData: RunBranch | null = branch) {
  return renderWithRoute(
    <RunInitialRankingPublicationPanel run={runData} branch={branchData} />,
    '/admin/runs/sandbox-publish'
  )
}

describe('Initial-ranking publication and Viewer Save', () => {
  it('publishes exact saved Week-1 candidate, saves the new public state, and verifies Viewer', async () => {
    render()
    await userEvent.click(await screen.findByRole('button', { name: 'Review initial publication' }))
    expect(screen.getByText(/does not itself create the Viewer-visible Saved Revision/)).toBeInTheDocument()
    expect(api.publishRunInitialRanking).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve initial publication' }))
    await userEvent.click(screen.getByRole('button', { name: 'Publish initial ranking' }))
    await waitFor(() => expect(api.publishRunInitialRanking).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, hash('a')
    ))
    expect(api.saveRunDerivedInitialRankingRevision).not.toHaveBeenCalled()
    await userEvent.click(await screen.findByRole('button', { name: 'Review unsaved published ranking state' }))
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve published ranking revision save' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save published ranking revision' }))
    await waitFor(() => expect(api.saveRunDerivedInitialRankingRevision).toHaveBeenCalledWith(
      run.run_id, branch.branch_id, 0, hash('b')
    ))
    expect(await screen.findByText(/Viewer readback verified/)).toBeInTheDocument()
  })

  it('refuses publication until ranking preparation has a clean Saved Revision', async () => {
    unsavedBeforePublish = true
    render()
    expect(await screen.findByText(/Ranking state differs from its latest Saved Revision/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review initial publication' })).toBeDisabled()
    expect(api.publishRunInitialRanking).not.toHaveBeenCalled()
  })

  it('enforces a protected Run and does not claim the non-Viewer Branch is visible', async () => {
    render({ ...run, read_only: true })
    expect(await screen.findByRole('button', { name: 'Review initial publication' })).toBeDisabled()
  })

  it('warns if Admin Branch differs from Viewer Branch', async () => {
    render({ ...run, official_branch_id: 'another-timeline' })
    expect(await screen.findByText(/Different Branch — this publication will not yet appear in Viewer/)).toBeInTheDocument()
    expect(api.getViewerOfficialRanking).not.toHaveBeenCalled()
  })

  it('rejects duplicate or out-of-scope Week-1 candidates and invalid published responses', () => {
    expect(validWeekOnePublicationCandidate(candidate, run.run_id, branch.branch_id)).toBe(true)
    expect(validWeekOnePublicationCandidate(candidate, run.run_id, 'another')).toBe(false)
    expect(validWeekOnePublicationCandidate({
      ...candidate, snapshot: { ...candidate.snapshot, week: { season_index: 0, week: 2 } }
    }, run.run_id, branch.branch_id)).toBe(false)
    expect(verifiedInitialRankingPublication({
      schema_version: 'initial_official_ranking_publication.v1',
      run_id: run.run_id, branch_id: branch.branch_id,
      week: { season_index: 0, week: 1 }, ranking_fingerprint: hash('a'),
      exact_retry: false
    }, run.run_id, branch.branch_id, hash('b'))).toBe(false)
    expect(verifiedViewerInitialRanking({
      schema_version: 'viewer_official_ranking.v1', product_run_id: run.run_id,
      viewer_branch_id: 'another', season_index: 0, week: 1, week_ordinal: 0,
      snapshot_fingerprint: hash('a'), policy_id: 'msa', best_n: 15,
      row_count: 0, rows: []
    }, run.run_id, branch.branch_id, hash('a'))).toBe(false)
  })

  it('supports save-only recovery after reopening an already published unsaved ranking', async () => {
    published = true
    render()
    expect(await screen.findByText(/Ranking state differs from its latest Saved Revision/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Review initial publication' })).toBeDisabled()
    await userEvent.click(await screen.findByRole('button', { name: 'Review unsaved published ranking state' }))
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve published ranking revision save' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save published ranking revision' }))
    await waitFor(() => expect(api.saveRunDerivedInitialRankingRevision).toHaveBeenCalled())
    expect(api.publishRunInitialRanking).not.toHaveBeenCalled()
  })
})
