import { describe, it, expect } from 'vitest'
import { prepareGeneratedBulkPlan } from './generatedBulkPreview'
import type { RunInitialWorldPlayer } from '../api/runInitialWorldSetup'

const players: RunInitialWorldPlayer[] = [
  {player_id:'p2',name:'B',country_code:'CZE',age_years_at_season_start:22,
    current_ability:63,potential_ability:83,potential_tier:'B',
    attributes:{technique:44,movement:50}},
  {player_id:'p1',name:'A',country_code:'USA',age_years_at_season_start:25,
    current_ability:70,potential_ability:84,potential_tier:'A',
    attributes:{technique:64,movement:60}}
]
describe('authoritative-bound bulk field planning', () => {
  it('creates unique ordered per-player diffs and preserves unrelated verified locks', () => {
    const original=JSON.stringify(players)
    const beforeLocks=[{player_id:'p1',field:'attributes.movement' as const,value:60}]
    const result=prepareGeneratedBulkPlan(players,['p2','p1'],
      'attributes.technique',66,beforeLocks)
    expect(result).toMatchObject({selectedCount:2,unchangedCount:0,field:'attributes.technique'})
    expect(result.changes).toEqual([
      {playerId:'p1',name:'A',before:64,after:66},
      {playerId:'p2',name:'B',before:44,after:66}
    ])
    expect(result.nextLocks).toEqual([
      {player_id:'p1',field:'attributes.movement',value:60},
      {player_id:'p1',field:'attributes.technique',value:66},
      {player_id:'p2',field:'attributes.technique',value:66}
    ])
    expect(JSON.stringify(players)).toBe(original)
    expect(beforeLocks).toEqual([{player_id:'p1',field:'attributes.movement',value:60}])
  })
  it('detects no-ops and keeps all other reviewed fields untouched', () => {
    const result=prepareGeneratedBulkPlan(players,['p1','p2'],'current_ability',70,[])
    expect(result.unchangedCount).toBe(1)
    expect(result.changes).toEqual([{playerId:'p2',name:'B',before:63,after:70}])
    expect(result.nextLocks).toEqual([{player_id:'p2',field:'current_ability',value:70}])
  })
  it('fails closed for unsupported fields, invalid values, duplicate, missing and oversized selections', () => {
    for(const n of [0,100,-1,5.5,NaN]) {
      expect(()=>prepareGeneratedBulkPlan(players,['p1'],'attributes.technique',n,[])).toThrow()
    }
    expect(()=>prepareGeneratedBulkPlan(players,['p1'],'height' as never,50,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan(players,[], 'current_ability',60,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan(players,['p1','p1'],'current_ability',60,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan(players,['p1','p3'],'current_ability',60,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan([...players,players[0]],['p1'],'current_ability',60,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan(players,Array.from({length:1001},()=> 'p1'),
      'current_ability',60,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan(players,['p1'],'attributes.physical',60,[])).toThrow()
    expect(()=>prepareGeneratedBulkPlan(players,['p1'],'current_ability',89,[])).toThrow(/conflicts/)
    expect(()=>prepareGeneratedBulkPlan(players,['p1'],'potential_ability',40,[])).toThrow(/conflicts/)
  })
})
