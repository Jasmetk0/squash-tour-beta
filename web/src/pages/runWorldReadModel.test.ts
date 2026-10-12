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
    expect(model.missingCountryCount).toBe(2) // legacy scalar ratings lack time-bound evidence
    expect(model.manualCountryCount).toBe(1)
    expect(model.countries[0].population).toEqual({
      kind:'exact',value:10250000,sourceYear:2000
    })
    expect(model.countries[1].population).toEqual({
      kind:'default',value:331000000,sourceYear:2020
    })
    expect(model.countries[1].ratings.squash_access.provenance).toContain('no year attribution')
  })
  it('interpolates only tagged Run ratings and preserves old unmarked v2 nearest-year',()=>{
    const f=worldFixture()
    const c=(f.state!.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
    const keys=['squash_popularity','squash_access','development_quality',
      'competition_quality','elite_support','squash_tradition']
    const at=(v:number)=>({historical_entity:'CZE',territory_mapping_note:'test',
      ratings:Object.fromEntries(keys.map(k=>[k,{value:v,method:'sourced_estimate'}]))})
    c.rating_scale='country_ratings_1_10.v2'
    c.rating_history={schema_version:'country_rating_history.v2',
      years:{'1990':at(4),'2000':at(6)}}
    expect(projectRunWorld(f,'run-a','branch-a',1995)!.countries[0].ratings.squash_popularity)
      .toMatchObject({value:4,kind:'fallback',sourceYear:1990})
    c.rating_resolution_version='country_rating_resolution.linear_v3'
    const pristine=JSON.stringify(f)
    expect(projectRunWorld(f,'run-a','branch-a',1995)!.countries[0].ratings.squash_popularity)
      .toMatchObject({value:5,kind:'interpolated',sourceYear:null,
        sourceYears:[1990,2000],sourceValues:[4,6]})
    expect(projectRunWorld(f,'run-a','branch-a',1991)!.countries[0].ratings.squash_access.value).toBe(4.2)
    expect(projectRunWorld(f,'run-a','branch-a',1990)!.countries[0].ratings.squash_access.kind).toBe('exact')
    expect(projectRunWorld(f,'run-a','branch-a',2050)!.countries[0].ratings.squash_access)
      .toMatchObject({value:6,kind:'fallback',sourceYears:[2000]})
    expect(projectRunWorld(f,'run-a','branch-a',1955)!.countries[0].ratings.squash_access)
      .toMatchObject({value:4,kind:'fallback',sourceYears:[1990]})
    expect(projectRunWorld(f,'run-a','branch-a',1995)!.countries[0].incomplete).toBe(true)
    expect(JSON.stringify(f)).toBe(pristine)
    c.rating_resolution_version='unknown'
    expect(()=>projectRunWorld(f,'run-a','branch-a',1995)).toThrow(/resolver version/)
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
