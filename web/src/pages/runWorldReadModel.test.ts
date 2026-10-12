import { describe, expect, it } from 'vitest'
import { projectRunWorld } from './runWorldReadModel'

import { worldFixture } from './runWorldFixture'
describe('Run-owned World overview projection',()=>{
  it('counts real countries but explicitly refuses complete world population when a year uses fallback',()=>{
    const model=projectRunWorld(worldFixture(),'run-a','branch-a',2000)!
    expect(model.worldName).toBe('Saved FIFA Earth')
    expect(model.countries).toHaveLength(2)
    expect(model.exactPopulation).toBe(10250000)
    expect(model.knownPopulation).toBe(341250000)
    expect(model.populationComplete).toBe(false)
    expect(model.estimatedPopulationCount).toBe(1)
    expect(model.missingCountryCount).toBe(1)
    expect(model.manualCountryCount).toBe(1)
    expect(model.countries[0].population).toEqual({
      kind:'exact',value:10250000,sourceYear:2000
    })
    expect(model.countries[1].population).toEqual({
      kind:'default',value:331000000,sourceYear:2020
    })
    expect(model.countries[1].ratings.squash_access.provenance).toContain('no year attribution')
  })
  it('uses deterministic nearest population with earlier-year tie-break and never invents exactness',()=>{
    const state=worldFixture()
    const c=(state.state!.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
    c.population_by_year={'1999':100,'2001':200}
    const model=projectRunWorld(state,'run-a','branch-a',2000)!
    expect(model.countries[0].population).toEqual({kind:'nearest',value:100,sourceYear:1999})
    expect(model.populationComplete).toBe(false)
  })
  it('rejects foreign scope, ambiguous packages and duplicate/mismatched country IDs',()=>{
    expect(()=>projectRunWorld(worldFixture(),'run-a','branch-b',2000)).toThrow(/ownership/)
    const duplicate=worldFixture()
    const entities=duplicate.state!.entities as Record<string,unknown>[]
    entities.push({...entities[1]})
    expect(()=>projectRunWorld(duplicate,'run-a','branch-a',2000)).toThrow(/Duplicate/)
    const mixed=worldFixture()
    const versions=mixed.state!.package_versions as Record<string,unknown>[]
    versions.push({package_type:'World',package_id:'other',source_version:1})
    expect(()=>projectRunWorld(mixed,'run-a','branch-a',2000)).toThrow(/unambiguous/)
    expect(()=>projectRunWorld(worldFixture(),'run-a','branch-a',2051)).toThrow(/year/)
  })
  it('handles empty Run without inventing zero countries or population',()=>{
    expect(projectRunWorld({state:null,fingerprint:null},'run-a','branch-a',2000)).toBeNull()
    const empty=worldFixture()
    empty.state!.package_versions=[]
    expect(projectRunWorld(empty,'run-a','branch-a',2000)).toBeNull()
  })
})
