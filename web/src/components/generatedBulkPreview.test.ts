import { describe, it, expect } from 'vitest'
import { prepareGeneratedBulkPlan, prepareGeneratedBulkAutomaticPlan } from './generatedBulkPreview'
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
      {playerId:'p1',name:'A',before:64,after:66,beforeLocked:false,afterLocked:true},
      {playerId:'p2',name:'B',before:44,after:66,beforeLocked:false,afterLocked:true}
    ])
    expect(result.nextLocks).toEqual([
      {player_id:'p1',field:'attributes.movement',value:60},
      {player_id:'p1',field:'attributes.technique',value:66},
      {player_id:'p2',field:'attributes.technique',value:66}
    ])
    expect(JSON.stringify(players)).toBe(original)
    expect(beforeLocks).toEqual([{player_id:'p1',field:'attributes.movement',value:60}])
  })
  it('treats the same unlocked value as a new lock, separately from a numeric edit', () => {
    const result=prepareGeneratedBulkPlan(players,['p1','p2'],'current_ability',70,[])
    expect(result.unchangedCount).toBe(0)
    expect(result.changes).toEqual([
      {playerId:'p1',name:'A',before:70,after:70,beforeLocked:false,afterLocked:true},
      {playerId:'p2',name:'B',before:63,after:70,beforeLocked:false,afterLocked:true}
    ])
    expect(result.nextLocks).toEqual([
      {player_id:'p1',field:'current_ability',value:70},
      {player_id:'p2',field:'current_ability',value:70}
    ])
  })
  it('distinguishes existing identical locks, new same-value locks and real changes', () => {
    const source=players.map(p=>({...p,attributes:{...p.attributes,technique:64}}))
    const verified=[
      {player_id:'p1',field:'attributes.technique' as const,value:64},
      {player_id:'p1',field:'attributes.movement' as const,value:60}
    ]
    const pristine=JSON.stringify(source), locksBefore=JSON.stringify(verified)
    const plan=prepareGeneratedBulkPlan(source,['p2','p1'],'attributes.technique',64,verified)
    expect(plan.unchangedCount).toBe(1)
    expect(plan.changes).toEqual([
      {playerId:'p2',name:'B',before:64,after:64,beforeLocked:false,afterLocked:true}
    ])
    expect(plan.nextLocks).toEqual([
      verified[1],verified[0],{player_id:'p2',field:'attributes.technique',value:64}
    ])
    expect(JSON.stringify(source)).toBe(pristine)
    expect(JSON.stringify(verified)).toBe(locksBefore)
    const trueNoOp=prepareGeneratedBulkPlan(source,['p1'],'attributes.technique',64,verified)
    expect(trueNoOp.changes).toEqual([])
    expect(trueNoOp.unchangedCount).toBe(1)
    expect(trueNoOp.nextLocks).toEqual([verified[1],verified[0]])
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
    const duplicate=[{player_id:'p1',field:'attributes.technique' as const,value:64},
      {player_id:'p1',field:'attributes.technique' as const,value:64}]
    expect(()=>prepareGeneratedBulkPlan(players,['p1'],'attributes.technique',64,duplicate))
      .toThrow(/Duplicate/)
  })
})

describe('bulk Automatic unlock planning', () => {
  const locks = [
    {player_id:'p1',field:'attributes.technique' as const,value:65},
    {player_id:'p1',field:'attributes.movement' as const,value:60},
    {player_id:'p2',field:'attributes.technique' as const,value:45}
  ]
  it('removes only selected field locks and never invents an automatic numeric value', () => {
    const original=JSON.stringify(players), evidence=JSON.stringify(locks)
    const plan=prepareGeneratedBulkAutomaticPlan(players,['p2'],'attributes.technique',locks)
    expect(plan).toMatchObject({mode:'automatic',selectedCount:1,unchangedCount:0})
    expect(plan.changes).toEqual([{playerId:'p2',name:'B',before:44,after:null,beforeLocked:true,afterLocked:false}])
    expect(plan.nextLocks).toEqual([locks[1], locks[0]])
    expect(JSON.stringify(players)).toBe(original)
    expect(JSON.stringify(locks)).toBe(evidence)
  })
  it('reports selected already-Automatic fields as no-ops and preserves all others', () => {
    const plan=prepareGeneratedBulkAutomaticPlan(players,['p1','p2'],'current_ability',locks)
    expect(plan.changes).toEqual([])
    expect(plan.unchangedCount).toBe(2)
    expect(plan.nextLocks).toEqual([locks[1], locks[0], locks[2]])
  })
  it('fails closed on missing, duplicate, oversized or unsupported selection', () => {
    for(const ids of [[],['p1','p1'],['unknown'],Array.from({length:1001},()=> 'p1')])
      expect(()=>prepareGeneratedBulkAutomaticPlan(players,ids,'attributes.technique',locks)).toThrow()
    expect(()=>prepareGeneratedBulkAutomaticPlan(players,['p1'],'height' as never,locks)).toThrow()
    expect(()=>prepareGeneratedBulkAutomaticPlan([...players,players[0]],['p1'],
      'attributes.technique',locks)).toThrow()
    const duplicate=[...locks,locks[0]]
    expect(()=>prepareGeneratedBulkAutomaticPlan(players,['p1'],
      'attributes.technique',duplicate)).toThrow(/Duplicate/)
  })
})
