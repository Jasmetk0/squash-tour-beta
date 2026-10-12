import {describe,expect,it} from 'vitest'
import {worldFixture} from './runWorldFixture'
import {calendarSeasonIndex,projectCountryTournaments} from './runWorldCountryTournaments'
function calendar(host='CZE'){
  const f=worldFixture()
  const versions=f.state!.package_versions as Record<string,unknown>[]
  const entities=f.state!.entities as Record<string,unknown>[]
  for(const season of ['2000/2001','2001/2002']){
    const id='calendar-'+season.replace('/','-')
    versions.push({package_type:'Calendar',package_id:id,source_version:1})
    entities.push({source_package_id:id,source_entity_id:'calendar.metadata',
      entity_kind:'calendar.metadata.v1',payload:{season}})
    entities.push({source_package_id:id,source_entity_id:'event-'+season,
      entity_kind:'calendar.event.v1',payload:{
        event_id:'event-'+season,season,season_week:8,event_name:'Brno Open '+season,
        host_country:host,host_city:'Brno',status:'planned',category:'World Tour',
        template_snapshot:{host_country:'USA'}}})
  }
  return f
}
describe('Saved country tournament editions',()=>{
  it('supports actual calendar season spellings, not World data year',()=>{
    expect(calendarSeasonIndex('2000/2001')).toBe(0)
    expect(calendarSeasonIndex('2000/01')).toBe(0)
    expect(calendarSeasonIndex('2001/2002')).toBe(1)
    expect(calendarSeasonIndex(2001)).toBe(1)
    expect(calendarSeasonIndex('2000/2003')).toBeNull()
    expect(calendarSeasonIndex('2050/2051')).toBeNull()
  })
  it('selects edition host country, preserved source and multiple seasons without mutation',()=>{
    const f=calendar()
    const before=JSON.stringify(f)
    const result=projectCountryTournaments(f,'run-a','branch-a','CZE')!
    expect(result.calendarCount).toBe(2)
    expect(result.editions.map(e=>[e.seasonIndex,e.week,e.city,e.status])).toEqual([
      [0,8,'Brno','planned'],[1,8,'Brno','planned']])
    expect(JSON.stringify(f)).toBe(before)
    expect(projectCountryTournaments(f,'run-a','branch-a','USA')!.editions).toEqual([])
  })
  it('distinguishes missing Calendar from no country hosts and ignores template host',()=>{
    expect(projectCountryTournaments(worldFixture(),'run-a','branch-a','CZE')!.calendarCount).toBe(0)
    const f=calendar('USA')
    expect(projectCountryTournaments(f,'run-a','branch-a','CZE')!.calendarCount).toBe(2)
    expect(projectCountryTournaments(f,'run-a','branch-a','CZE')!.editions).toHaveLength(0)
    expect(projectCountryTournaments(f,'run-a','branch-a','USA')!.editions).toHaveLength(2)
  })
  it('fails closed on wrong Run/Branch, corrupt fingerprint, season and duplicate identities',()=>{
    const f=calendar()
    expect(()=>projectCountryTournaments(f,'run-a','wrong','CZE')).toThrow(/ownership/)
    expect(()=>projectCountryTournaments({...f,fingerprint:'no'},'run-a','branch-a','CZE')).toThrow(/incomplete/)
    const entities=f.state!.entities as Record<string,unknown>[]
    const event=entities.find(e=>e.entity_kind==='calendar.event.v1')!
    ;(event.payload as Record<string,unknown>).season='2010/2011'
    expect(()=>projectCountryTournaments(f,'run-a','branch-a','CZE')).toThrow(/invalid/)
    ;(event.payload as Record<string,unknown>).season='2000/2001'
    entities.push({...event})
    expect(()=>projectCountryTournaments(f,'run-a','branch-a','CZE')).toThrow(/duplicate/)
  })
})
