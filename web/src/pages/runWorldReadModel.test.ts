import { describe, expect, it } from 'vitest'
import type { RunPackageStateResponse } from '../api/types'
import { projectRunWorld } from './runWorldReadModel'

const ratings={
  squash_popularity:3,squash_access:3,development_quality:4,
  competition_quality:3,elite_support:2,squash_tradition:4
}
export function worldFixture():RunPackageStateResponse {
  return {
    fingerprint:'a'.repeat(64),
    state:{
      run_id:'run-a',branch_id:'branch-a',
      package_versions:[{
        package_type:'World',package_id:'fifa_earth',source_version:1,
        source_fingerprint:'b'.repeat(64),provenance:{}
      }],
      entities:[
        {source_package_id:'fifa_earth',source_entity_id:'world.metadata',entity_kind:'world.metadata.v1',
          provenance:'package',payload:{name:'Saved FIFA Earth',source:'readonly_package'}},
        {source_package_id:'fifa_earth',source_entity_id:'CZE',entity_kind:'world.country.v1',
          provenance:'package',payload:{
            code:'CZE',name:'Czechia',region:'EUROPE',travel_region:'CENTRAL_EUROPE',
            timezone_area:'EUROPE_CENTRAL',area_km2:78871,
            population:10500000,population_by_year:{'2000':10250000,'2020':10700000},
            ...ratings
          }},
        {source_package_id:'fifa_earth',source_entity_id:'USA',entity_kind:'world.country.v1',
          provenance:'manual',payload:{
            code:'USA',name:'United States',region:'NORTH_AMERICA',travel_region:'NORTH_AMERICA',
            population:340000000,default_population:331000000,
            ...ratings
          }}
      ]
    }
  }
}
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
