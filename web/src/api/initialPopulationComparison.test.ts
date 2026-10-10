import {afterEach, describe, expect, it, vi} from 'vitest'
import {getInitialPopulationComparison, getInitialPopulationPlayers, runInitialPopulationComparison} from './client'
const payload = {world_ids: ['fifa_earth','atp_earth'] as [string,string],season: '2000/01',player_count: 2,seeds: [101]}
const saved = {schema_version: 'player_lab_initial_population_comparison.v1',session_id: 'session',request: {...payload,season: '2000/2001'},sources: payload.world_ids.map(world_id=>({world_id})),aggregates: payload.world_ids.map(world_id=>({world_id})),runs: payload.world_ids.map(world_id=>({world_id,seed: 101,summary: {player_count: 2}}))}
function response(data: unknown) {vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok: true,text: async()=>JSON.stringify(data)}))}
afterEach(()=>vi.unstubAllGlobals())
describe('Saved population API identity guards',()=>{
  it('accepts the explicit Earth pair and normalized season', async()=>{
    response(saved)
    expect(await runInitialPopulationComparison(payload)).toEqual(saved)
  })
  it('rejects silent FAX substitution', async()=>{
    response({...saved,sources: [{world_id: 'official_fax_world'},{world_id: 'atp_earth'}]})
    await expect(runInitialPopulationComparison(payload)).rejects.toThrow('identity mismatch')
  })
  it('rejects an unrelated session on saved reopen', async()=>{
    response(saved)
    await expect(getInitialPopulationComparison('other-session')).rejects.toThrow('identity mismatch')
  })
  it('rejects players from another seed or saved gameplay fingerprint', async()=>{
    response({session_id: 'session',world_id: 'fifa_earth',seed: 101,gameplay_fingerprint: 'stale',players: []})
    await expect(getInitialPopulationPlayers('session','fifa_earth',101,'expected')).rejects.toThrow('identity mismatch')
    await expect(getInitialPopulationPlayers('session','fifa_earth',202)).rejects.toThrow('identity mismatch')
  })
})
