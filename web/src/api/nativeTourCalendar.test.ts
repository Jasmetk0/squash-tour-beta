import {describe,it,expect} from 'vitest'
import {tourWeekOffset,scheduleTourEdition} from './nativeTourCalendar'
import type {TourWeek} from './calendarTour'

const clock=(W:number,O:number,seasons=3):TourWeek['calendar']=>({
  schema_version:'run_calendar.v1',weeks_per_year:W,
  season_start_year_week:O,start_year:2030,season_count:seasons,
})
const at=(calendar:TourWeek['calendar'],season_index:number,week:number):TourWeek=>({
  calendar,season_index,week,
})

describe('Run-native cross-season Edition planning',()=>{
  it.each([[52,1],[61,37],[80,1]])('uses the actual W=%i and O=%i rather than legacy week 61',(W,O)=>{
    const c=clock(W,O),before=at(c,0,W-1)
    const next=tourWeekOffset(before,2)
    expect(next).toEqual(at(c,1,1))
    expect(scheduleTourEdition(before,1,1)).toEqual({
      week:at(c,1,1),announcement_week:at(c,0,W),
    })
    expect(scheduleTourEdition(at(c,0,W),1,2)).toEqual({
      week:at(c,1,2),announcement_week:at(c,1,1),
    })
    expect(scheduleTourEdition(at(c,0,W-2),1,1)).toEqual({
      week:at(c,1,1),announcement_week:at(c,0,W-1),
    })
  })
  it('checks the actual Run horizon and never wraps or silently extends',()=>{
    const c=clock(52,1,1)
    expect(tourWeekOffset(at(c,0,51),2)).toBeNull()
    expect(scheduleTourEdition(at(c,0,50),0,52)?.week.week).toBe(52)
    expect(scheduleTourEdition(at(c,0,51),0,52)).toBeNull()
    expect(scheduleTourEdition(at(c,0,52),1,1)).toBeNull()
    expect(scheduleTourEdition(at(c,0,49),0,51)?.announcement_week.week).toBe(50)
  })
  it('rejects stale, malformed, unsafe and immediate/same-week dates',()=>{
    const c=clock(80,30)
    const current=at(c,0,79)
    expect(scheduleTourEdition(current,0,80)).toBeNull()
    expect(scheduleTourEdition(current,0,79)).toBeNull()
    expect(scheduleTourEdition(current,1,1)?.announcement_week).toEqual(at(c,0,80))
    for(const invalid of [NaN,Infinity,-1,1.5,Number.MAX_SAFE_INTEGER+1]){
      expect(scheduleTourEdition(current,invalid,1)).toBeNull()
      expect(scheduleTourEdition(current,1,invalid)).toBeNull()
    }
    expect(tourWeekOffset({...current,week:81},1)).toBeNull()
    expect(tourWeekOffset({...current,calendar:{...c,weeks_per_year:0}},1)).toBeNull()
    expect(tourWeekOffset(current,-1)).toBeNull()
  })
})
