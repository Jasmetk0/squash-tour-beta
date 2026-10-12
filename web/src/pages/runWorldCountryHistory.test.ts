import { describe,expect,it } from 'vitest'
import { worldFixture } from './runWorldFixture'
import { projectRunWorldCountryHistory } from './runWorldCountryHistory'

const keys=[
  'squash_popularity','squash_access','development_quality',
  'competition_quality','elite_support','squash_tradition'
]
function withV2(){
  const f=worldFixture()
  const country=(f.state!.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
  country.rating_scale='country_ratings_1_10.v2'
  function year(y:number,value:number,method:string){
    return {
      historical_entity:'Czech Republic',territory_mapping_note:'Stable reference boundaries',
      ratings:Object.fromEntries(keys.map(key=>[key,{
        value,method,confidence:'high',source_ids:['UN_WPP_2024'],
        observation_ids:['UN_WPP_2024#CZE'],
        rationale:'Measured source observation',anchor_years:[y]
      }]))
    }
  }
  country.rating_history={
    schema_version:'country_rating_history.v2',reference_year:2020,data_cutoff:'2026-06-01',
    years:{'2000':year(2000,4.5,'sourced_estimate'),'2020':year(2020,6.4,'sourced_estimate')}
  }
  country.population_by_year={'2000':10250000,'2010':null,'2020':10700000}
  return f
}
describe('Run World authored country history',()=>{
  it('keeps authored population anchor, explicit missing year, and fallback separate',()=>{
    const f=withV2()
    const h=projectRunWorldCountryHistory(f,'run-a','branch-a','CZE',2010)!
    expect(h.populationAnchors).toEqual([
      {year:2000,value:10250000},{year:2010,value:null},{year:2020,value:10700000}
    ])
    expect(h.selectedPopulation).toEqual({value:10250000,kind:'nearest',sourceYear:2000})
    expect(h.ratingScale).toBe(10)
    expect(h.ratingAnchors.map(y=>y.year)).toEqual([2000,2020])
    expect(h.selectedRatingSourceYear).toBe(2000)
    expect(h.ratingDataCutoff).toBe('2026-06-01')
    const evidence=h.ratingAnchors[0].ratings.squash_popularity
    expect(evidence).toMatchObject({value:4.5,method:'sourced_estimate',
      confidence:'high',sourceIds:['UN_WPP_2024'],observationIds:['UN_WPP_2024#CZE'],
      anchorYears:[2000]
    })
  })
  it('keeps authored rating anchors distinct from a versioned interpolated view',()=>{
    const f=withV2()
    const c=(f.state!.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
    c.rating_resolution_version='country_rating_resolution.linear_v3'
    const original=JSON.stringify(f)
    const h=projectRunWorldCountryHistory(f,'run-a','branch-a','CZE',2010)!
    expect(h.ratingAnchors.map(x=>x.year)).toEqual([2000,2020])
    expect(h.selectedRatingSourceYear).toBeNull()
    expect(h.selectedPopulation).toEqual({value:10250000,kind:'nearest',sourceYear:2000})
    expect(JSON.stringify(f)).toBe(original)
  })
  it('does not invent rated years beyond the evidence cutoff or derive historical scalar values',()=>{
    const h=projectRunWorldCountryHistory(withV2(),'run-a','branch-a','CZE',2050)!
    expect(h.selectedRatingSourceYear).toBe(2020)
    expect(h.ratingAnchors.map(p=>p.year)).toEqual([2000,2020])
    const legacy=projectRunWorldCountryHistory(worldFixture(),'run-a','branch-a','CZE',2025)!
    expect(legacy.ratingAnchors).toHaveLength(0)
    expect(legacy.ratingDataCutoff).toBeNull()
    expect(legacy.ratingScale).toBe(5)
    expect(legacy.selectedPopulation).toMatchObject({kind:'nearest',sourceYear:2020})
  })
  it('rejects historical evidence corruption and foreign Branch identity',()=>{
    const f=withV2()
    expect(()=>projectRunWorldCountryHistory(f,'run-a','foreign','CZE',2000)).toThrow(/ownership/)
    const c=(f.state!.entities as Record<string,unknown>[])[1].payload as Record<string,unknown>
    const history=c.rating_history as Record<string,unknown>
    const years=history.years as Record<string,unknown>
    const year=years['2000'] as Record<string,unknown>
    const ratings=year.ratings as Record<string,unknown>
    delete ratings.elite_support
    expect(()=>projectRunWorldCountryHistory(f,'run-a','branch-a','CZE',2000)).toThrow(/Incomplete/)
  })
  it('returns null for non-existent country and keeps Run snapshot unmodified',()=>{
    const f=withV2()
    const before=JSON.stringify(f)
    expect(projectRunWorldCountryHistory(f,'run-a','branch-a','ZZZ',2000)).toBeNull()
    expect(projectRunWorldCountryHistory(f,'run-a','branch-a','CZE',2000)).not.toBeNull()
    expect(JSON.stringify(f)).toBe(before)
  })
})
