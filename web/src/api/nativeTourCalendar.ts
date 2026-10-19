/** Exact Run-owned Tour Edition dates. Never use legacy 61-week RankingWeek arithmetic. */
import type {TourWeek} from './calendarTour'

export type EditionSchedule={week:TourWeek;announcement_week:TourWeek}

/** Null means outside the fixed Run horizon or a malformed/untrusted clock. */
export function tourWeekOffset(source:TourWeek, delta:number):TourWeek|null {
  const c=source.calendar
  if (![c.weeks_per_year,c.season_start_year_week,c.start_year,c.season_count,
         source.season_index,source.week,delta].every(Number.isSafeInteger)
    ||c.weeks_per_year<1||c.season_count<1||c.start_year<0
    ||c.season_start_year_week<1||c.season_start_year_week>c.weeks_per_year
    ||source.season_index<0||source.season_index>=c.season_count
    ||source.week<1||source.week>c.weeks_per_year||delta<0) return null
  const origin=source.season_index*c.weeks_per_year+source.week-1
  const target=origin+delta
  if(!Number.isSafeInteger(origin)||!Number.isSafeInteger(target)
    ||target>=c.weeks_per_year*c.season_count) return null
  return {calendar:c,season_index:Math.floor(target/c.weeks_per_year),
    week:target%c.weeks_per_year+1}
}

/** Announce on the immediately following real Week Transition, and require
 * an entire additional week before the Edition can operate. */
export function scheduleTourEdition(
  source:TourWeek, seasonIndex:number, week:number,
):EditionSchedule|null {
  const c=source.calendar
  if(!Number.isSafeInteger(seasonIndex)||!Number.isSafeInteger(week)
    ||seasonIndex<0||seasonIndex>=c.season_count
    ||week<1||week>c.weeks_per_year) return null
  const offset=(seasonIndex-source.season_index)*c.weeks_per_year
    +week-source.week
  const announcement=tourWeekOffset(source,1)
  const target=tourWeekOffset(source,offset)
  if(offset<2||!announcement||!target
    ||target.season_index!==seasonIndex||target.week!==week) return null
  return {week:target,announcement_week:announcement}
}
