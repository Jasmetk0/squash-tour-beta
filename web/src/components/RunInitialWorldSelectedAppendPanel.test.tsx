import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderWithRoute } from '../test/testUtils'
import { RunInitialWorldSelectedAppendPanel } from './RunInitialWorldSelectedAppendPanel'
import type { RunInitialWorldState } from '../api/runInitialWorldSetup'

const api=vi.hoisted(()=>({
  previewRunOwnedInitialWorld:vi.fn(),
  previewSelectedInitialWorldAppend:vi.fn(),
  commitSelectedInitialWorldAppend:vi.fn()
}))
vi.mock('../api/client',()=>api)
const SHA=(c:string)=>c.repeat(64)
const currentPlayers=[{
  player_id:'P-2000-BOG-0001',name:'Bogemia 1',country_code:'BOG',
  age_years_at_season_start:22,current_ability:62,potential_ability:79,
  potential_tier:'B',career_stage:'developing',attributes:{technique:55}
}]
const newPlayers=[...currentPlayers,
  {player_id:'P-2000-BOG-0002',name:'Bogemia 2',country_code:'BOG',
    age_years_at_season_start:23,current_ability:60,potential_ability:81,
    potential_tier:'B',career_stage:'developing',attributes:{technique:53}},
  {player_id:'P-2000-BOG-0003',name:'Bogemia 3',country_code:'BOG',
    age_years_at_season_start:24,current_ability:58,potential_ability:75,
    potential_tier:'B',career_stage:'developing',attributes:{technique:52}}
]
const current={
  run_id:'run-one',branch_id:'branch-one',world_package_id:'fifa_earth',
  adoption_request_fingerprint:SHA('a'),bootstrap_seed:802,
  players:currentPlayers,policies:[{policy_id:'msa-official-2000-01',best_n:15}],
  selected_appends:[]
} as RunInitialWorldState

const props={
  runId:'run-one',branchId:'branch-one',head:'head-1',draftVersion:3,
  packageFingerprint:SHA('e'),currentFingerprint:SHA('a'),
  current,enabled:true
}
function sourceState(req:{command_id:string;generation:{world_package_id:string;seed:number};best_n:number}){
  return {
    run_id:props.runId,branch_id:props.branchId,season:'2000/2001',
    source_kind:'run_world_generated_pool.v1',world_package_id:req.generation.world_package_id,
    bootstrap_seed:req.generation.seed,adopted_by_command_id:req.command_id,
    adoption_request_fingerprint:SHA('b'),world_country_content_fingerprint:SHA('c'),
    world_generation_content_fingerprint:SHA('d'),
    run_world_pool_preview_fingerprint:SHA('f'),players:newPlayers,
    policies:[{policy_id:'msa-official-2000-01',best_n:req.best_n}]
  }
}
beforeEach(()=>{
  vi.clearAllMocks()
  api.previewRunOwnedInitialWorld.mockImplementation(async (_r:string,_b:string,req:any)=>({
    preview_only:true,state:sourceState(req),fingerprint:SHA('f')
  }))
  api.previewSelectedInitialWorldAppend.mockImplementation(async (_r:string,_b:string,req:any)=>({
    preview_only:true,added_count:req.append.selected_player_ids.length,
    fingerprint:SHA('7'),
    state:{
      ...current,
      players:[...currentPlayers,...newPlayers.filter(p=>
        req.append.selected_player_ids.includes(p.player_id))],
      selected_appends:[{
        command_id:req.append.command_id,source_preview_fingerprint:SHA('f'),
        selected_player_ids:req.append.selected_player_ids,
        audit_label:req.append.audit_label,audit_reason:req.append.audit_reason
      }]
    }
  }))
  api.commitSelectedInitialWorldAppend.mockImplementation(async (_r:string,_b:string,req:any)=>{
    return (await api.previewSelectedInitialWorldAppend(_r,_b,req)).state
  })
})

describe('saved InitialWorld Add Selected',()=>{
  it('selects only new identities, server reviews and commits with exact fingerprint',async()=>{
    renderWithRoute(<RunInitialWorldSelectedAppendPanel {...props}/>, '/admin/runs/run-one')
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Selected append source size'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Selected append source size'}),'3')
    await userEvent.click(screen.getByRole('button',{name:'Preview source players (read-only)'}))
    expect(await screen.findByText(/Candidate source: 3 players/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox',{name:'Select for bulk action P-2000-BOG-0002'}))
    expect(screen.getByText(/Selected: 1. Conflicting IDs: 0/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'Verify selected addition on server (no write)'}))
    expect(await screen.findByRole('region',{name:'Verified selected append'})).toBeInTheDocument()
    expect(api.previewSelectedInitialWorldAppend).toHaveBeenCalledTimes(1)
    expect(api.commitSelectedInitialWorldAppend).not.toHaveBeenCalled()
    const request=api.previewSelectedInitialWorldAppend.mock.calls[0][2]
    expect(request.append.selected_player_ids).toEqual(['P-2000-BOG-0002'])
    expect(request.expected_head).toBe('head-1')
    expect(request.expected_package_fingerprint).toBe(SHA('e'))
    expect(request.expected_initial_world_fingerprint).toBe(SHA('a'))
    await userEvent.click(screen.getByRole('checkbox',{name:'Approve selected InitialWorld append'}))
    await userEvent.click(screen.getByRole('button',{name:'Commit selected players (Save separately)'}))
    await waitFor(()=>expect(api.commitSelectedInitialWorldAppend).toHaveBeenCalledTimes(1))
    expect(api.commitSelectedInitialWorldAppend.mock.calls[0][3]).toBe(SHA('7'))
    expect(await screen.findByText(/Selected players staged in InitialWorld/)).toBeInTheDocument()
  })

  it('detects existing IDs before server preview and never attempts commit',async()=>{
    renderWithRoute(<RunInitialWorldSelectedAppendPanel {...props}/>, '/admin/runs/run-one')
    await userEvent.clear(screen.getByRole('spinbutton',{name:'Selected append source size'}))
    await userEvent.type(screen.getByRole('spinbutton',{name:'Selected append source size'}),'3')
    await userEvent.click(screen.getByRole('button',{name:'Preview source players (read-only)'}))
    expect(await screen.findByText(/Candidate source: 3 players/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('checkbox',{name:'Select for bulk action P-2000-BOG-0001'}))
    expect(screen.getByRole('button',{name:'Verify selected addition on server (no write)'})).toBeDisabled()
    expect(screen.getByText(/These IDs already exist/)).toBeInTheDocument()
    expect(api.previewSelectedInitialWorldAppend).not.toHaveBeenCalled()
    expect(api.commitSelectedInitialWorldAppend).not.toHaveBeenCalled()
  })

  it('is disabled while the current InitialWorld is unsaved',async()=>{
    renderWithRoute(<RunInitialWorldSelectedAppendPanel {...props} enabled={false}/>, '/admin/runs/run-one')
    expect(screen.getByRole('button',{name:'Preview source players (read-only)'})).toBeDisabled()
    expect(screen.getByText(/First finish the pending Save/)).toBeInTheDocument()
    expect(api.previewRunOwnedInitialWorld).not.toHaveBeenCalled()
  })
})
