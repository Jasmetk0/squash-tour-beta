import {describe,expect,it} from 'vitest'
import {parsePeriod,projectCountryPeriod,selectedSportPoint,sportLabel} from './runCountryRecordPeriods'
import type {RunCountryRecordResult,RunCountryRecords} from '../api/types'

const event=(id:string,season:string,week:number,champion:string,finalist:string,host='CZE'):
  RunCountryRecordResult=>({
    event_id:id,event_name:'Event '+id,season,season_week:week,host_country:host,
    champion_player_id:champion,champion_name:champion,champion_country:'CZE',
    finalist_player_id:finalist,finalist_name:finalist,finalist_country:'CZE',
  })
const data=():RunCountryRecords=>{
  const rows=[
    event('first','2000/2001',5,'P1','P2'),
    event('late','2001/2002',61,'P2','P1'),
    event('early','2002/2003',1,'P1','P2'),
    event('future','2002/2003',10,'P2','P1')]
  return {schema_version:'run_country_records.v1',source:'reachable_saved_revision',
    run_id:'run',branch_id:'fork',revision_branch_id:'original',
    saved_revision_id:'ancestor',country_code:'CZE',calendar_status:'ready',
    published_result_count:rows.length,country_titles:4,country_finalists:4,
    hosted_published_results:4,player_results:rows,hosted_results:rows}
}
describe('Master v80 Country Records sport periods and tied holders',()=>{
  it('whole history stops at displayed simulation point, independent of geography year',()=>{
    const through=selectedSportPoint(2002,1)!
    expect(through).toEqual({season:2,week:1})
    expect(selectedSportPoint(null,1)).toBeNull()
    expect(selectedSportPoint(2002,0)).toBeNull()
    const period=parsePeriod(new URLSearchParams('year=2050&tab=records'),through)!
    const view=projectCountryPeriod(data(),'CZE',period)
    expect(view.athletes.map(x=>x.event_id)).toEqual(['first','late','early'])
    expect(view.titles).toBe(3)
    expect(view.hosted).toHaveLength(3)
    expect(sportLabel(view.to)).toBe('2002/2003 · Week 1')
    expect(view.champions.map(x=>[x.id,x.count])).toEqual([['P1',2]])
    expect(view.finalists.map(x=>[x.id,x.count])).toEqual([['P1',3],['P2',3]])
  })
  it('season and custom periods are inclusive across Week 61 / 1 and clamp future',()=>{
    const through={season:2,week:3}
    const season=parsePeriod(new URLSearchParams('rperiod=season&rseason=2'),through)!
    expect(projectCountryPeriod(data(),'CZE',season).athletes.map(x=>x.event_id)).toEqual(['early'])
    const custom=parsePeriod(new URLSearchParams(
      'rperiod=custom&rfromSeason=1&rfromWeek=61&rtoSeason=2&rtoWeek=61'),through)!
    expect(custom.to).toEqual(through)
    const view=projectCountryPeriod(data(),'CZE',custom)
    expect(view.athletes.map(x=>x.event_id)).toEqual(['late','early'])
    expect(view.champions.map(x=>[x.id,x.count])).toEqual([['P1',1],['P2',1]])
    expect(view.finalists.map(x=>[x.id,x.count])).toEqual([['P1',2],['P2',2]])
  })
  it('does not pretend a future season or backwards period is available',()=>{
    const through={season:2,week:3}
    expect(parsePeriod(new URLSearchParams('rperiod=season&rseason=3'),through)).toBeNull()
    expect(parsePeriod(new URLSearchParams(
      'rperiod=custom&rfromSeason=2&rfromWeek=4'),through)).toBeNull()
    expect(parsePeriod(new URLSearchParams(
      'rperiod=custom&rfromSeason=1&rfromWeek=2&rtoSeason=0&rtoWeek=61'),through)).toBeNull()
    expect(parsePeriod(new URLSearchParams('rperiod=garbled'),through)).toBeNull()
    expect(parsePeriod(new URLSearchParams('rperiod=custom&rfromWeek=62'),through)).toBeNull()
  })
  it('does not invent zero-holder winner or tolerate corrupt sport identity',()=>{
    const source=data()
    const selected=parsePeriod(new URLSearchParams('rperiod=season&rseason=0'),
      {season:0,week:1})!
    const empty=projectCountryPeriod(source,'CZE',selected)
    expect(empty.titles).toBe(0)
    expect(empty.champions).toEqual([])
    expect(empty.finalists).toEqual([])
    source.player_results[0].season='garbage'
    expect(()=>projectCountryPeriod(source,'CZE',selected)).toThrow(/unsupported historical/)
    expect(()=>projectCountryPeriod(data(),'USA',selected)).toThrow(/invalid/)
  })
})
