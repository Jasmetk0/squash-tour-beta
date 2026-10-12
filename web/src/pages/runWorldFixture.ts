import type { RunPackageStateResponse } from '../api/types'
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
