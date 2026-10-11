import { describe, expect, it } from 'vitest'
import {
  ageConditionConflict, generatorConditionConflict, verifiedGenerationOptions, verifiedInitialWorldPreview,
  type RunInitialWorldAdoption, type RunInitialWorldPreview, type RunWorldGenerationOptions
} from './runInitialWorldSetup'

const hash = (symbol: string) => symbol.repeat(64)
const options: RunWorldGenerationOptions = {
  schema_version: 'run_world_generation_options.v1', run_id:'r1',branch_id:'b1',
  saved_revision_id:'head1',draft_version:2,run_package_fingerprint:hash('a'),
  world_package_id:'earth',
  countries:[
    {code:'CZE',name:'Czechia',region:'EUROPE',travel_region:'CENTRAL_EUROPE'},
    {code:'SVK',name:'Slovakia',region:'EUROPE',travel_region:'CENTRAL_EUROPE'},
    {code:'USA',name:'United States',region:'NORTH_AMERICA',travel_region:'NORTH_AMERICA'}
  ],
  regions:['EUROPE','CENTRAL_EUROPE','NORTH_AMERICA'],
  geographic_regions:['EUROPE','NORTH_AMERICA'],
  travel_regions:['CENTRAL_EUROPE','NORTH_AMERICA']
}
const request: RunInitialWorldAdoption = {
  command_id:'test',generation:{world_package_id:'earth',season:'2000/2001',
    seed:42,target_pool_size:2,country_code:null,region:'EUROPE'},
  audit_label:'Test',audit_reason:'Checked conditions',official_run:false,
  best_n:15,automatic_retirement_age:46
}
function preview(countries: string[]): RunInitialWorldPreview {
  return {
    preview_only:true,fingerprint:hash('f'),
    state:{
      run_id:'r1',branch_id:'b1',season:'2000/2001',
      source_kind:'run_world_generated_pool.v1',world_package_id:'earth',
      bootstrap_seed:42,adopted_by_command_id:'test',
      adoption_request_fingerprint:hash('b'),world_country_content_fingerprint:hash('c'),
      world_generation_content_fingerprint:hash('d'),run_world_pool_preview_fingerprint:hash('e'),
      players:countries.map((code,i)=>({
        player_id:'p'+i,name:'Saved Player '+i,country_code:code,
        age_years_at_season_start:20,current_ability:50,potential_ability:70,potential_tier:'solid'
      })),
      policies:[{policy_id:'initial-best15',best_n:15}]
    }
  }
}
describe('single generator saved-world hard constraints',()=>{
  it('verifies explicit Saved HEAD and all country/region options',()=>{
    expect(verifiedGenerationOptions(options,'r1','b1','head1',2,hash('a'),'earth')).toBe(true)
    expect(verifiedGenerationOptions(options,'r1','b1','foreign',2,hash('a'),'earth')).toBe(false)
    expect(verifiedGenerationOptions(options,'r1','b1','head1',3,hash('a'),'earth')).toBe(false)
    expect(verifiedGenerationOptions({...options,countries:[options.countries[0],options.countries[0]]},
      'r1','b1','head1',2,hash('a'),'earth')).toBe(false)
  })
  it('automatic restores World default; compatible conditions have no conflict',()=>{
    expect(generatorConditionConflict('','',options)).toBeNull()
    expect(generatorConditionConflict('CZE','EUROPE',options)).toBeNull()
    expect(generatorConditionConflict('CZE','CENTRAL_EUROPE',options)).toBeNull()
    expect(generatorConditionConflict('SVK','NORTH_AMERICA',options)).toContain('does not belong')
    expect(generatorConditionConflict('ZZZ','',options)).toContain('not present')
    expect(generatorConditionConflict('','MARS',options)).toContain('not present')
    expect(generatorConditionConflict('CZE','EUROPE',null)).not.toBeNull()
  })
  it('refuses a preview player outside the reviewed region, even with matching count',()=>{
    expect(verifiedInitialWorldPreview(preview(['CZE','SVK']),'r1','b1',request,options)).toBe(true)
    expect(verifiedInitialWorldPreview(preview(['CZE','USA']),'r1','b1',request,options)).toBe(false)
    expect(verifiedInitialWorldPreview(preview(['CZE','SVK']),'r1','b1',request,null)).toBe(false)
  })
  it('refuses a preview player outside a mandatory selected country',()=>{
    const forced={...request,generation:{...request.generation,region:null,country_code:'CZE'}}
    expect(verifiedInitialWorldPreview(preview(['CZE','SVK']),'r1','b1',forced,options)).toBe(false)
    expect(verifiedInitialWorldPreview(preview(['CZE','CZE']),'r1','b1',forced,options)).toBe(true)
  })
  it('accepts automatic and single-ended age conditions but rejects impossible ranges',()=>{
    expect(ageConditionConflict('','')).toBeNull()
    expect(ageConditionConflict('18','')).toBeNull()
    expect(ageConditionConflict('','25')).toBeNull()
    expect(ageConditionConflict('18','25')).toBeNull()
    expect(ageConditionConflict('25','18')).toContain('cannot exceed')
    expect(ageConditionConflict('14','')).toContain('between 15 and 45')
    expect(ageConditionConflict('','46')).toContain('between 15 and 45')
    expect(ageConditionConflict('20.5','')).toContain('whole years')
    expect(ageConditionConflict('-1','')).not.toBeNull()
  })
  it('requires every preview player to satisfy reviewed first-week age interval',()=>{
    const ageRequest={...request,generation:{...request.generation,min_age:21,max_age:25}}
    expect(verifiedInitialWorldPreview(preview(['CZE','SVK']),'r1','b1',ageRequest,options)).toBe(false)
    const allowed={...request,generation:{...request.generation,min_age:18,max_age:25}}
    expect(verifiedInitialWorldPreview(preview(['CZE','SVK']),'r1','b1',allowed,options)).toBe(true)
    const impossible={...request,generation:{...request.generation,min_age:25,max_age:18}}
    expect(verifiedInitialWorldPreview(preview(['CZE','SVK']),'r1','b1',impossible,options)).toBe(false)
  })

})

describe('typed geography and historic region replay',()=>{
  const collision: RunWorldGenerationOptions={
    ...options,
    countries:[{code:'CZE',name:'Czechia',region:'EUROPE',travel_region:'SHARED'},
      {code:'USA',name:'United States',region:'SHARED',travel_region:'NORTH_AMERICA'}],
    regions:['EUROPE','SHARED','NORTH_AMERICA'],
    geographic_regions:['EUROPE','SHARED'],travel_regions:['SHARED','NORTH_AMERICA']
  }
  it('rejects cross-layer identical labels but retains legacy union',()=>{
    expect(generatorConditionConflict('CZE','',collision,'SHARED','')).toContain('Conflicting')
    expect(generatorConditionConflict('USA','',collision,'SHARED','')).toBeNull()
    expect(generatorConditionConflict('CZE','',collision,'','SHARED')).toBeNull()
    expect(generatorConditionConflict('USA','',collision,'','SHARED')).toContain('Conflicting')
    expect(generatorConditionConflict('CZE','SHARED',collision)).toBeNull()
  })
  it('refuses previews from the wrong region layer',()=>{
    const geographic={...request,generation:{...request.generation,region:null,geographic_region:'SHARED'}}
    const travel={...request,generation:{...request.generation,region:null,travel_region:'SHARED'}}
    expect(verifiedInitialWorldPreview(preview(['CZE','CZE']),'r1','b1',geographic,collision)).toBe(false)
    expect(verifiedInitialWorldPreview(preview(['USA','USA']),'r1','b1',geographic,collision)).toBe(true)
    expect(verifiedInitialWorldPreview(preview(['CZE','CZE']),'r1','b1',travel,collision)).toBe(true)
    expect(verifiedInitialWorldPreview(preview(['USA','USA']),'r1','b1',travel,collision)).toBe(false)
  })
})
