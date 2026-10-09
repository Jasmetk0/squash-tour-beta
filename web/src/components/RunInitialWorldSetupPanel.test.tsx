import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { RunBranch, RunContainer } from '../api/types'
import { RunInitialWorldSetupPanel } from './RunInitialWorldSetupPanel'
import { renderWithRoute } from '../test/testUtils'

const api = vi.hoisted(() => {
  class ApiError extends Error {
    constructor(message: string, public status: number) { super(message) }
  }
  return {
    ApiError,
    getRunPackageState: vi.fn(),
    getBranchWorkingDraft: vi.fn(),
    getRunOwnedInitialWorld: vi.fn(),
    previewRunOwnedInitialWorld: vi.fn(),
    adoptRunOwnedInitialWorld: vi.fn(),
    previewRunInitialWorldSave: vi.fn(),
    saveRunOwnedInitialWorld: vi.fn()
  }
})
vi.mock('../api/client', () => api)

const run: RunContainer = {
  run_id: 'first-run', display_name: 'First Run', storage_kind: 'custom_local',
  read_only: false, status: 'working',
  timeline_start_season: 2000, timeline_end_season: 2049,
  world_id: null, world_package_fingerprint: null,
  global_seed: null, config_version: null, config_fingerprint: null,
  official_branch_id: null, metadata_json: {}, mapped_simulation_run_count: 0
}
const branch: RunBranch = {
  run_id: 'first-run', branch_id: 'timeline-1', display_name: 'Timeline 1',
  status: 'active', read_only: false, saved_head_revision_id: 'revision-1',
  branch_seed: null, forked_from_branch_id: null, forked_from_checkpoint_id: null,
  head_checkpoint_id: null, legacy_simulation_run_id: null, metadata_json: {},
  is_official: false
}
const sha = (symbol: string) => symbol.repeat(64)
let adopted = false
let draftVersion = 0
let saved = false
const players = [
  { player_id: 'p-1', name: 'Jan A', country_code: 'CZE',
    age_years_at_season_start: 20, current_ability: 80,
    potential_ability: 100, potential_tier: 'solid' },
  { player_id: 'p-2', name: 'Lukas B', country_code: 'SVK',
    age_years_at_season_start: 19, current_ability: 70,
    potential_ability: 105, potential_tier: 'strong' }
]
let reviewedState: Record<string, unknown>
function buildState(request: {
  command_id: string
  generation: { world_package_id: string; seed: number }
  best_n: number
}) {
  return {
    run_id: 'first-run', branch_id: 'timeline-1', season: '2000/2001',
    source_kind: 'run_world_generated_pool.v1',
    world_package_id: request.generation.world_package_id,
    bootstrap_seed: request.generation.seed,
    adopted_by_command_id: request.command_id,
    adoption_request_fingerprint: sha('a'),
    world_country_content_fingerprint: sha('b'),
    world_generation_content_fingerprint: sha('c'),
    run_world_pool_preview_fingerprint: sha('d'),
    players, policies: [{ policy_id: 'msa-official-2000-01', best_n: request.best_n }]
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  adopted = false; draftVersion = 0; saved = false
  reviewedState = {}
  api.getRunPackageState.mockResolvedValue({
    state: { run_id: 'first-run', branch_id: 'timeline-1',
      package_versions: [
        { package_type: 'World', package_id: 'fifa_earth' },
        { package_type: 'Calendar', package_id: 'calendar-2000-2001' }
      ] },
    fingerprint: sha('e')
  })
  api.getBranchWorkingDraft.mockImplementation(async () => ({
    run_id: 'first-run', branch_id: 'timeline-1',
    base_saved_revision_id: 'revision-1',
    draft_version: draftVersion, status: saved || !adopted ? 'clean' : 'dirty'
  }))
  api.getRunOwnedInitialWorld.mockImplementation(async () => {
    if (!adopted) throw new api.ApiError('not found', 404)
    return reviewedState
  })
  api.previewRunOwnedInitialWorld.mockImplementation(async (_run: string, _branch: string, request: Parameters<typeof buildState>[0]) => {
    reviewedState = buildState(request)
    return { preview_only: true, state: reviewedState, fingerprint: sha('f') }
  })
  api.adoptRunOwnedInitialWorld.mockImplementation(async () => {
    adopted = true; draftVersion = 1
    return reviewedState
  })
  api.previewRunInitialWorldSave.mockImplementation(async () => ({
    run_id: 'first-run', branch_id: 'timeline-1',
    saved_head_revision_id: 'revision-1', draft_version: draftVersion,
    initial_world_fingerprint: sha('f'), can_save: true
  }))
  api.saveRunOwnedInitialWorld.mockImplementation(async () => {
    saved = true
    return {
      saved_revision: { revision_id: 'revision-2' },
      working_draft: {
        run_id: 'first-run', branch_id: 'timeline-1',
        base_saved_revision_id: 'revision-2', status: 'clean'
      }
    }
  })
})

function render(overrideRun: RunContainer = run, overrideBranch: RunBranch | null = branch) {
  return renderWithRoute(<RunInitialWorldSetupPanel run={overrideRun} branch={overrideBranch} />, '/admin/runs/first-run')
}

describe('Run-owned first-season player setup', () => {
  it('reviews true generated players, adopts only that fingerprint and separately saves a revision', async () => {
    render()
    await userEvent.clear(screen.getByRole('spinbutton', { name: 'Number of generated players' }))
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Number of generated players' }), '2')
    await userEvent.click(await screen.findByRole('button', { name: 'Preview generated players' }))
    await waitFor(() => expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1',
      expect.objectContaining({
        generation: { world_package_id: 'fifa_earth', season: '2000/2001', seed: 20261009, target_pool_size: 2 },
        official_run: false, best_n: 15, automatic_retirement_age: 46
      })
    ))
    expect(await screen.findByText('Jan A')).toBeInTheDocument()
    expect(screen.getByText('Lukas B')).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve InitialWorld adoption' }))
    await userEvent.click(screen.getByRole('button', { name: 'Adopt generated players' }))
    await waitFor(() => expect(api.adoptRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1', expect.objectContaining({ command_id: expect.any(String) }), sha('f')
    ))
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Approve InitialWorld revision save' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save InitialWorld revision' }))
    await waitFor(() => expect(api.saveRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1', 1, sha('f')
    ))
  })

  it('refuses a mismatched Run-owned World preview without adopting', async () => {
    api.previewRunOwnedInitialWorld.mockResolvedValueOnce({
      preview_only: true,
      fingerprint: sha('f'),
      state: { ...buildState({ command_id: 'wrong', generation: { world_package_id: 'atp_earth', seed: 20261009 }, best_n: 15 }) }
    })
    render()
    await userEvent.clear(screen.getByRole('spinbutton', { name: 'Number of generated players' }))
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Number of generated players' }), '2')
    await userEvent.click(await screen.findByRole('button', { name: 'Preview generated players' }))
    expect(await screen.findByText(/InitialWorld preview is inconsistent/)).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('blocks generation for a protected Run', async () => {
    render({ ...run, read_only: true })
    expect(await screen.findByRole('button', { name: 'Preview generated players' })).toBeDisabled()
  })

  it('does not overwrite an already adopted InitialWorld', async () => {
    adopted = true
    reviewedState = buildState({ command_id: 'existing', generation: { world_package_id: 'fifa_earth', seed: 7 }, best_n: 15 })
    render()
    expect(await screen.findByText(/InitialWorld exists: 2 players/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Preview generated players' })).toBeDisabled()
    expect(api.previewRunOwnedInitialWorld).not.toHaveBeenCalled()
  })
})
