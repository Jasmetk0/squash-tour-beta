import {describe,expect,it} from 'vitest'
import {
  countryRosterReturnPath,readCountryRosterPermalink,safeCountryRosterReturn,
  writeCountryRosterPermalink,
} from './countrySavedRosterPermalink'
const scope=JSON.stringify(['run','branch-a','rev-a','CZE'])
const base=new URLSearchParams('tab=records&year=2025&q=Europe')
const state={search:'Alpha',status:'active',includePrepared:true,page:2}

describe('Country Saved roster URL round trips',()=>{
  it('round-trips a filtered page without losing existing World query/year',()=>{
    const params=writeCountryRosterPermalink(base,scope,state)
    expect(params.get('tab')).toBe('players')
    expect(params.get('year')).toBe('2025')
    expect(params.get('q')).toBe('Europe')
    expect(params.get('spPage')).toBe('3')
    expect(readCountryRosterPermalink(params,scope)).toEqual(state)
    const path=countryRosterReturnPath('run','CZE',params)
    expect(path).toContain('/admin/runs/run/world/countries/CZE?')
    expect(safeCountryRosterReturn(path,'run','CZE','branch-a','rev-a')).toBe(path)
  })
  it('never restores filters, prepared prospect consent or page from a different HEAD',()=>{
    const params=writeCountryRosterPermalink(base,scope,state)
    expect(readCountryRosterPermalink(params,JSON.stringify([
      'run','branch-b','rev-b','CZE',
    ]))).toEqual({search:'',status:'',includePrepared:false,page:0})
    expect(readCountryRosterPermalink(params,JSON.stringify([
      'run','branch-a','rev-a','ENG',
    ])).includePrepared).toBe(false)
    const reset=writeCountryRosterPermalink(params,scope,{
      search:'',status:'',includePrepared:false,page:0,
    })
    expect(reset.get('spSearch')).toBeNull()
    expect(reset.get('spStatus')).toBeNull()
    expect(reset.get('spPrepared')).toBeNull()
    expect(reset.get('spPage')).toBeNull()
    expect(reset.get('year')).toBe('2025')
  })
  it('rejects invalid URL page indices and oversized/untrimmed filters',()=>{
    for(const raw of ['0','-1','01',' 2','1.0','1000001','foo','10000000']){
      const params=writeCountryRosterPermalink(base,scope,state)
      params.set('spPage',raw)
      expect(readCountryRosterPermalink(params,scope).page).toBe(0)
    }
    const bad=writeCountryRosterPermalink(base,scope,state)
    bad.set('spSearch','x'.repeat(121))
    bad.set('spStatus',' active ')
    bad.set('spPrepared','yes')
    expect(readCountryRosterPermalink(bad,scope)).toMatchObject({
      search:'',status:'',includePrepared:false,
    })
  })
  it('rejects external redirects, other Run/country, historical source and non-country paths',()=>{
    const path=countryRosterReturnPath('run','CZE',
      writeCountryRosterPermalink(base,scope,state))
    for(const invalid of [
      'https://evil.test'+path,'//evil.test'+path,
      '/admin/runs/other/world/countries/CZE?tab=players',
      '/admin/runs/run/world/countries/ENG?tab=players',
      '/admin/runs/run/players?tab=players',
      '/admin/runs/run/world/countries/CZE?tab=records',
      '/admin/runs/run/world/countries/CZE?tab=players&revision=old',
      '/admin/runs/run/world/countries/CZE?tab=players#override',
      '/admin/runs/run/world/countries/CZE',
      path+'#fragment',
      'x'.repeat(2501),
    ])expect(safeCountryRosterReturn(invalid,'run','CZE','branch-a','rev-a')).toBeNull()
    expect(safeCountryRosterReturn(path,'run','ENG','branch-a','rev-a')).toBeNull()
    expect(safeCountryRosterReturn(path,'run',null,'branch-a','rev-a')).toBeNull()
    expect(safeCountryRosterReturn(path,'run','CZE','branch-b','rev-a')).toBeNull()
    expect(safeCountryRosterReturn(path,'run','CZE','branch-a','rev-b')).toBeNull()
    expect(safeCountryRosterReturn(path,'run','CZE',null,'rev-a')).toBeNull()
    expect(safeCountryRosterReturn(path,'run','CZE','branch-a',null)).toBeNull()
    const duplicate = new URL(path,'https://country-roster.local')
    duplicate.searchParams.append('spScope',scope)
    expect(safeCountryRosterReturn(duplicate.pathname+duplicate.search,
      'run','CZE','branch-a','rev-a')).toBeNull()
    const noScope = new URL(path,'https://country-roster.local')
    noScope.searchParams.delete('spScope')
    expect(safeCountryRosterReturn(noScope.pathname+noScope.search,
      'run','CZE','branch-a','rev-a')).toBeNull()
  })
})