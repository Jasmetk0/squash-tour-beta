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
    getRunWorldGenerationOptions: vi.fn(),
    previewRunOwnedInitialWorld: vi.fn(),
    getRunGenerationProposals: vi.fn(),
    saveRunGenerationProposal: vi.fn(),
    loadRunGenerationProposal: vi.fn(),
    deleteRunGenerationProposal: vi.fn(),
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
  api.getRunGenerationProposals.mockResolvedValue({proposals:[]})
  api.getRunPackageState.mockResolvedValue({
    state: { run_id: 'first-run', branch_id: 'timeline-1',
      package_versions: [
        { package_type: 'World', package_id: 'fifa_earth' },
        { package_type: 'Calendar', package_id: 'calendar-2000-2001' }
      ] },
    fingerprint: sha('e')
  })
  api.getRunWorldGenerationOptions.mockImplementation(async (
    _run: string, _branch: string, world: string, head: string, draft: number, fingerprint: string
  ) => ({
    schema_version: 'run_world_generation_options.v1',
    run_id: 'first-run', branch_id: 'timeline-1',
    saved_revision_id: head, draft_version: draft,
    run_package_fingerprint: fingerprint, world_package_id: world,
    countries: [
      { code:'CZE', name:'Czechia', region:'EUROPE', travel_region:'CENTRAL_EUROPE' },
      { code:'SVK', name:'Slovakia', region:'EUROPE', travel_region:'CENTRAL_EUROPE' },
      { code:'USA', name:'United States', region:'NORTH_AMERICA', travel_region:'NORTH_AMERICA' }
    ],
    regions: ['CENTRAL_EUROPE','EUROPE','NORTH_AMERICA'],
    geographic_regions: ['EUROPE','NORTH_AMERICA'],
    travel_regions: ['CENTRAL_EUROPE','NORTH_AMERICA']
  }))
  api.getBranchWorkingDraft.mockImplementation(async () => ({
    run_id: 'first-run', branch_id: 'timeline-1',
    base_saved_revision_id: 'revision-1',
    // Production component adoption leaves the generic Working Draft clean.
    draft_version: draftVersion, status: 'clean'
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
    adopted = true
    return reviewedState
  })
  api.previewRunInitialWorldSave.mockImplementation(async () => ({
    run_id: 'first-run', branch_id: 'timeline-1',
    saved_head_revision_id: 'revision-1', draft_version: draftVersion,
    initial_world_fingerprint: sha('f'), has_unsaved_changes: !saved, can_save: !saved
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
  it('previews exact whole-batch country quotas with an automatic remainder and no implicit Save', async () => {
    render()
    await userEvent.clear(screen.getByRole('spinbutton', {name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton', {name:'Number of generated players'}), '2')
    await userEvent.click(await screen.findByRole('button', {name:'Add country quota'}))
    expect(screen.getByRole('spinbutton', {name:'Exact quota CZE'})).toBeInTheDocument()
    await userEvent.clear(screen.getByRole('spinbutton', {name:'Exact quota CZE'}))
    await userEvent.type(screen.getByRole('spinbutton', {name:'Exact quota CZE'}), '1')
    expect(screen.getByLabelText('Country quota summary')).toHaveTextContent('2 total')
    expect(screen.getByLabelText('Country quota summary')).toHaveTextContent('1 exact')
    expect(screen.getByLabelText('Country quota summary')).toHaveTextContent('1 automatic')
    await userEvent.click(screen.getByRole('button', {name:'Preview generated players'}))
    await waitFor(() => expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1', expect.objectContaining({
        generation: expect.objectContaining({
          country_quotas: [{country_code:'CZE',count:1}],
          naming_policy:'country_serial.v1',
          target_pool_size:2
        })
      })
    ))
    expect(await screen.findByText('Review 2 players')).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('blocks contradictory exact quotas before invoking production preview',async()=>{
    render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(await screen.findByRole('button',{name:'Add country quota'}))
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Exact quota CZE'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Exact quota CZE'}),'3')
    expect(screen.getByText(/Exact country quotas exceed the total number of players/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Preview generated players'})).toBeDisabled()
    expect(api.previewRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('persists a reviewed unadopted proposal and restores exactly without regenerating',async()=>{
    const view=render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(await screen.findByRole('button',{name:'Preview generated players'}))
    await userEvent.click(screen.getByRole('checkbox',{name:'Keep p-1'}))
    await userEvent.clear(screen.getByRole('textbox',{name:'Generation proposal name'}))
    await userEvent.type(screen.getByRole('textbox',{name:'Generation proposal name'}),'My test proposal')
    const request=api.previewRunOwnedInitialWorld.mock.calls[0][2]
    const stored={
      schema_version:'run_generation_proposal.v1',run_id:'first-run',
      branch_id:'timeline-1',proposal_id:'proposal-1',label:'My test proposal',
      saved_revision_id:'revision-1',draft_version:0,
      package_fingerprint:sha('e'),preview_fingerprint:sha('f'),
      source_seed:20261009,next_seed:20261010,selected_keep_ids:['p-1'],
      pending_field_locks:[],request,
      preview:{preview_only:true,state:buildState(request),fingerprint:sha('f')}
    }
    api.saveRunGenerationProposal.mockResolvedValue(stored)
    await userEvent.click(screen.getByRole('button',{name:'Save generation proposal'}))
    await waitFor(()=>expect(api.saveRunGenerationProposal).toHaveBeenCalledWith(
      'first-run','timeline-1',expect.objectContaining({
        source_seed:20261009,selected_keep_ids:['p-1'],next_seed:20261010,
        preview_fingerprint:sha('f')
      })
    ))
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
    view.unmount()
    api.getRunGenerationProposals.mockResolvedValue({proposals:[{
      proposal_id:'proposal-1',label:'My test proposal',saved_revision_id:'revision-1',
      draft_version:0,package_fingerprint:sha('e'),preview_fingerprint:sha('f')
    }]})
    api.loadRunGenerationProposal.mockResolvedValue(stored)
    render()
    await screen.findByRole('option',{name:/My test proposal/})
    await userEvent.selectOptions(
      screen.getByRole('combobox',{name:'Select saved generation proposal'}),
      'proposal-1'
    )
    await userEvent.click(screen.getByRole('button',{name:'Open saved proposal'}))
    expect(await screen.findByText(/Exact saved review restored from SQLite/)).toBeInTheDocument()
    expect(screen.getByRole('checkbox',{name:'Keep p-1'})).toBeChecked()
    expect(screen.getByText('Review 2 players')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Adopt generated players'})).toBeDisabled()
    expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(1)
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('recovers an unsaved component after reload with a clean generic Draft', async () => {
    adopted = true
    reviewedState = buildState({ command_id: 'existing', generation: { world_package_id: 'fifa_earth', seed: 7 }, best_n: 15 })
    render()
    await userEvent.click(await screen.findByRole('button', { name: 'Review existing InitialWorld save' }))
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve InitialWorld revision save' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save InitialWorld revision' }))
    await waitFor(() => expect(api.saveRunOwnedInitialWorld).toHaveBeenCalledWith('first-run', 'timeline-1', 0, sha('f')))
    expect(api.previewRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('does not offer another Save for an already saved InitialWorld', async () => {
    adopted = true; saved = true
    reviewedState = buildState({ command_id: 'existing', generation: { world_package_id: 'fifa_earth', seed: 7 }, best_n: 15 })
    render()
    await waitFor(() => expect(api.previewRunInitialWorldSave).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: 'Review existing InitialWorld save' })).not.toBeInTheDocument()
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

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
    // The inspector is read-only: displaying one player must not change the reviewed
    // two-player adoption request, Saved HEAD, or preview fingerprint.
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Filter generated player country' }), 'CZE')
    expect(screen.getByText(/Showing 1 \/ 2/)).toBeInTheDocument()
    expect(screen.getByText(/Display filters never change the reviewed cohort/)).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve InitialWorld adoption' }))
    await userEvent.click(screen.getByRole('button', { name: 'Adopt generated players' }))
    await waitFor(() => expect(api.adoptRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1', expect.objectContaining({ command_id: expect.any(String) }), sha('f'),
      { head: 'revision-1', draftVersion: 0, packageFingerprint: sha('e') }
    ))
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(await screen.findByRole('checkbox', { name: 'Approve InitialWorld revision save' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save InitialWorld revision' }))
    await waitFor(() => expect(api.saveRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1', 0, sha('f')
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
  it('applies region to the actual reviewed production request and verifies all players', async () => {
    render()
    await userEvent.click(await screen.findByRole('combobox', { name: 'Player generation geographic region' }))
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Player generation geographic region' }), 'EUROPE')
    await userEvent.clear(screen.getByRole('spinbutton', { name: 'Number of generated players' }))
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Number of generated players' }), '2')
    await userEvent.click(screen.getByRole('button', { name: 'Preview generated players' }))
    await waitFor(() => expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run', 'timeline-1', expect.objectContaining({
        generation: expect.objectContaining({ geographic_region: 'EUROPE', target_pool_size: 2 })
      })
    ))
    expect(await screen.findByText('Jan A')).toBeInTheDocument()
    expect(screen.getByText('Every player satisfies the hard conditions.', { exact: false })).toBeInTheDocument()
  })

  it('blocks incompatible country and region before sending even a preview', async () => {
    render()
    await screen.findByRole('option', { name: 'CZE — Czechia' })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Player generation sport country' }), 'CZE')
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Player generation geographic region' }), 'NORTH_AMERICA')
    expect(screen.getByRole('alert')).toHaveTextContent('Conflicting geographic/travel conditions')
    expect(screen.getByRole('button', { name: 'Preview generated players' })).toBeDisabled()
    expect(api.previewRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('refuses a preview violating a hard sport-country constraint', async () => {
    render()
    await screen.findByRole('option', { name: 'CZE — Czechia' })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Player generation sport country' }), 'CZE')
    await userEvent.clear(screen.getByRole('spinbutton', { name: 'Number of generated players' }))
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Number of generated players' }), '2')
    await userEvent.click(screen.getByRole('button', { name: 'Preview generated players' }))
    expect(await screen.findByText(/InitialWorld preview is inconsistent/)).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('validates country-only preview and retains the exact reviewed country at commit', async () => {
    render()
    await screen.findByRole('option', { name: 'CZE — Czechia' })
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Player generation sport country' }), 'CZE')
    await userEvent.clear(screen.getByRole('spinbutton', { name: 'Number of generated players' }))
    await userEvent.type(screen.getByRole('spinbutton', { name: 'Number of generated players' }), '1')
    const req = {command_id:'country-preview',generation:{world_package_id:'fifa_earth',seed:20261009},best_n:15}
    api.previewRunOwnedInitialWorld.mockImplementationOnce(async (_run: string, _branch: string, request: Parameters<typeof buildState>[0]) => {
      reviewedState = {...buildState(req), adopted_by_command_id:request.command_id, players:[players[0]]}
      return { preview_only:true, state:reviewedState, fingerprint:sha('f') }
    })
    await userEvent.click(screen.getByRole('button', { name: 'Preview generated players' }))
    expect(await screen.findByText('Jan A')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox', { name: 'Approve InitialWorld adoption' }))
    await userEvent.click(screen.getByRole('button', { name: 'Adopt generated players' }))
    await waitFor(() => expect(api.adoptRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run','timeline-1',
      expect.objectContaining({generation:expect.objectContaining({country_code:'CZE',target_pool_size:1})}),
      sha('f'),{head:'revision-1',draftVersion:0,packageFingerprint:sha('e')}
    ))
  })

  it('prevents preview on conflicting or out-of-model first-season age conditions', async () => {
    render()
    await screen.findByRole('option',{name:'CZE — Czechia'})
    const low=screen.getByRole('spinbutton',{name:'Player generation minimum age'})
    const high=screen.getByRole('spinbutton',{name:'Player generation maximum age'})
    await userEvent.type(low,'30')
    await userEvent.type(high,'20')
    expect(screen.getByText(/Minimum age cannot exceed maximum age/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Preview generated players'})).toBeDisabled()
    expect(api.previewRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.clear(low)
    await userEvent.type(low,'14')
    expect(screen.getByText(/whole years between 15 and 45/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Preview generated players'})).toBeDisabled()
  })

  it('binds a reviewed age range to the original request and rejects stale preview after changing it',async()=>{
    render()
    await screen.findByRole('option',{name:'CZE — Czechia'})
    await userEvent.type(screen.getByRole('spinbutton',{name:'Player generation minimum age'}),'18')
    await userEvent.type(screen.getByRole('spinbutton',{name:'Player generation maximum age'}),'25')
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(screen.getByRole('button',{name:'Preview generated players'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run','timeline-1',
      expect.objectContaining({generation:expect.objectContaining({min_age:18,max_age:25,target_pool_size:2})})
    ))
    expect(await screen.findByText('Jan A')).toBeInTheDocument()
    expect(screen.getByText(/Every player satisfies the hard conditions/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve InitialWorld adoption'}))
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Player generation maximum age'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Player generation maximum age'}),'22')
    expect(screen.queryByRole('button',{name:'Adopt generated players'})).not.toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('rejects a generated preview containing an age outside the hard age interval',async()=>{
    render()
    await screen.findByRole('option',{name:'CZE — Czechia'})
    await userEvent.type(screen.getByRole('spinbutton',{name:'Player generation minimum age'}),'21')
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(screen.getByRole('button',{name:'Preview generated players'}))
    expect(await screen.findByText(/InitialWorld preview is inconsistent/)).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('previews 1000 distinct players and requires separate explicit Adopt and Save',async()=>{
    render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'1000')
    expect(screen.getByRole('button',{name:'Preview generated players'})).toBeEnabled()
    const cohort=Array.from({length:1000},(_,i)=>({
      ...players[0],player_id:'p-'+String(i).padStart(4,'0'),name:'Czechia '+i
    }))
    api.previewRunOwnedInitialWorld.mockImplementationOnce(async (_run:string,_branch:string,req:Parameters<typeof buildState>[0])=>{
      reviewedState={...buildState(req),players:cohort}
      return {preview_only:true,state:reviewedState,fingerprint:sha('f')}
    })
    await userEvent.click(screen.getByRole('button',{name:'Preview generated players'}))
    expect(await screen.findByText('Review 1000 players')).toBeInTheDocument()
    expect(screen.getByText(/Page 1 \/ 20/)).toBeInTheDocument()
    expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run','timeline-1',expect.objectContaining({
        generation:expect.objectContaining({target_pool_size:1000})
      })
    )
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve InitialWorld adoption'}))
    await userEvent.click(screen.getByRole('button',{name:'Adopt generated players'}))
    await waitFor(()=>expect(api.adoptRunOwnedInitialWorld).toHaveBeenCalledTimes(1))
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('edits an individual source field only after server review and never autosaves',async()=>{
    render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(await screen.findByRole('button',{name:'Preview generated players'}))
    await userEvent.click(screen.getByRole('button',{name:'Edit generated player p-1'}))
    expect(screen.getByRole('region',{name:'Generated player field editor'})).toBeInTheDocument()
    const ability=screen.getByRole('spinbutton',{name:'Preview field current_ability'})
    await userEvent.clear(ability)
    await userEvent.type(ability,'78')
    await userEvent.click(screen.getByRole('button',{name:'Lock preview field current_ability'}))
    expect(screen.getByText(/Pending field locks must be previewed/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve InitialWorld adoption'}))
    expect(screen.getByRole('button',{name:'Adopt generated players'})).toBeDisabled()
    api.previewRunOwnedInitialWorld.mockImplementationOnce(async (
      _run:string,_branch:string,request:Parameters<typeof buildState>[0]
    )=>{
      reviewedState={...buildState(request),players:[
        {...players[0],current_ability:78,attributes:{technique:55}},
        {...players[1]}
      ]}
      return {preview_only:true,state:reviewedState,fingerprint:sha('f')}
    })
    await userEvent.click(screen.getByRole('button',{name:'Apply field locks to preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(2))
    expect(api.previewRunOwnedInitialWorld.mock.calls[1][2].generation.field_locks).toEqual([
      {player_id:'p-1',field:'current_ability',value:78}
    ])
    expect(await screen.findByRole('button',{name:'Edit generated player p-1'})).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Edit generated player p-1'}))
    expect(screen.getByRole('button',{name:'Automatic preview field current_ability'})).toBeEnabled()
    await userEvent.click(screen.getByRole('button',{name:'Automatic preview field current_ability'}))
    expect(screen.getByRole('button',{name:'Adopt generated players'})).toBeDisabled()
  })

  it('selects session Keep without changing original review, then previews a real-source-bound reroll',async()=>{
    render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(await screen.findByRole('button',{name:'Preview generated players'}))
    expect(await screen.findByRole('checkbox',{name:'Keep p-1'})).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Keep p-1'}))
    expect(screen.getByText(/Selecting Keep changes no players until regeneration/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve InitialWorld adoption'}))
    expect(screen.getByRole('button',{name:'Adopt generated players'})).toBeDisabled()
    await userEvent.click(screen.getByRole('button',{name:'Regenerate remaining – new preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(2))
    const second=api.previewRunOwnedInitialWorld.mock.calls[1][2]
    expect(second.generation).toEqual(expect.objectContaining({
      seed:20261010,keep_from_seed:20261009,
      keep_from_preview_fingerprint:sha('d'),keep_player_ids:['p-1'],
      target_pool_size:2
    }))
    expect(await screen.findByText(/Verified session Keep regenerations: 1/)).toBeInTheDocument()
    expect(screen.getByRole('checkbox',{name:'Keep p-1'})).toBeChecked()
    expect(screen.getByText(/Showing 2 \/ 2/)).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    // A second pass uses the first pass as the exact reviewed source. Keep
    // remains selected; neither earlier pass modifies the Run or saves it.
    await userEvent.click(screen.getByRole('button',{name:'Regenerate remaining – new preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(3))
    const third=api.previewRunOwnedInitialWorld.mock.calls[2][2]
    expect(third.generation).toEqual(expect.objectContaining({
      seed:20261011,keep_from_seed:20261010,
      keep_from_preview_fingerprint:sha('d'),keep_player_ids:['p-1'],
      keep_history:[{
        seed:20261010,keep_from_seed:20261009,
        keep_from_preview_fingerprint:sha('d'),keep_player_ids:['p-1']
      }]
    }))
    expect(await screen.findByText(/Verified session Keep regenerations: 2/)).toBeInTheDocument()
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve InitialWorld adoption'}))
    await userEvent.click(screen.getByRole('button',{name:'Adopt generated players'}))
    await waitFor(()=>expect(api.adoptRunOwnedInitialWorld).toHaveBeenCalledWith(
      'first-run','timeline-1',expect.objectContaining({
        generation:expect.objectContaining({keep_player_ids:['p-1'],seed:20261011,keep_history:expect.any(Array)})
      }),sha('f'),{head:'revision-1',draftVersion:0,packageFingerprint:sha('e')}
    ))
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('edits and returns Automatic after two Keep passes using authenticated v2 steps',async()=>{
    render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(await screen.findByRole('button',{name:'Preview generated players'}))
    await userEvent.click(screen.getByRole('checkbox',{name:'Keep p-1'}))
    await userEvent.click(screen.getByRole('button',{name:'Regenerate remaining – new preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(2))
    await userEvent.click(screen.getByRole('button',{name:'Regenerate remaining – new preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(3))
    await userEvent.click(screen.getByRole('button',{name:'Edit generated player p-1'}))
    const ability=screen.getByRole('spinbutton',{name:'Preview field current_ability'})
    await userEvent.clear(ability)
    await userEvent.type(ability,'78')
    await userEvent.click(screen.getByRole('button',{name:'Lock preview field current_ability'}))
    expect(screen.getByRole('button',{name:'Adopt generated players'})).toBeDisabled()
    api.previewRunOwnedInitialWorld.mockImplementationOnce(async (
      _run:string,_branch:string,request:Parameters<typeof buildState>[0]
    )=>{
      reviewedState={...buildState(request),players:[
        {...players[0],current_ability:78},players[1]
      ]}
      return {preview_only:true,state:reviewedState,fingerprint:sha('f')}
    })
    await userEvent.click(screen.getByRole('button',{name:'Apply field locks to preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(4))
    const applied=api.previewRunOwnedInitialWorld.mock.calls[3][2]
    expect(applied.generation.session_schema_version).toBe('run_world_generation_session.v2')
    expect(applied.generation.session_origin_request.keep_history).toHaveLength(1)
    expect(applied.generation.session_origin_fingerprint).toBe(sha('d'))
    expect(applied.generation.session_steps).toEqual([{
      kind:'edit',source_preview_fingerprint:sha('d'),seed:20261011,
      keep_player_ids:[],field_locks:[{player_id:'p-1',field:'current_ability',value:78}]
    }])
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button',{name:'Edit generated player p-1'}))
    await userEvent.click(screen.getByRole('button',{name:'Automatic preview field current_ability'}))
    await userEvent.click(screen.getByRole('button',{name:'Apply field locks to preview'}))
    await waitFor(()=>expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(5))
    const automatic=api.previewRunOwnedInitialWorld.mock.calls[4][2]
    expect(automatic.generation.field_locks).toEqual([])
    expect(automatic.generation.session_steps[1].automatic_fields).toEqual([
      {player_id:'p-1',field:'current_ability'}
    ])
    expect(automatic.generation.session_steps).toHaveLength(2)
    expect(automatic.generation.session_steps[1].kind).toBe('edit')
    expect(api.saveRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

  it('blocks Keep of all players and reroll with the same seed',async()=>{
    render()
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Number of generated players'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Number of generated players'}),'2')
    await userEvent.click(await screen.findByRole('button',{name:'Preview generated players'}))
    await userEvent.click(await screen.findByRole('checkbox',{name:'Keep p-1'}))
    await userEvent.click(screen.getByRole('checkbox',{name:'Keep p-2'}))
    expect(screen.getByRole('button',{name:'Regenerate remaining – new preview'})).toBeDisabled()
    expect(screen.getByText(/Keeping every player leaves nothing to regenerate/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox',{name:'Keep p-2'}))
    const seed=screen.getByRole('spinbutton',{name:'Session Keep regeneration seed'})
    await userEvent.clear(seed)
    await userEvent.type(seed,'20261009')
    expect(screen.getByText(/A different seed is required/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Regenerate remaining – new preview'})).toBeDisabled()
    expect(api.previewRunOwnedInitialWorld).toHaveBeenCalledTimes(1)
    expect(api.adoptRunOwnedInitialWorld).not.toHaveBeenCalled()
  })

})
