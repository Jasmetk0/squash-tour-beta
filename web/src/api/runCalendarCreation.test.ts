import { describe, expect, it } from 'vitest'
import { validateCalendarCreationPreview } from './runCalendarCreation'

const input = {weeks_per_year:52, season_start_year_week:35, start_year:2030, season_count:3}
const result = () => ({
  schema_version:'run_calendar_configuration_preview.v1', read_only:true, run_created:false,
  run_calendar:{schema_version:'run_calendar.v1', ...input},
  first_week:{season_index:0,season_week:1,calendar_year:2030,year_week:35,season_label:'2030/2031',week_ordinal:0},
  last_week:{season_index:2,season_week:52,calendar_year:2033,year_week:34,season_label:'2032/2033',week_ordinal:155},
  sporting_calendar_supported:false, limitations:['sporting_calendar_execution_not_supported_yet']
})
describe('calendar creation preview contract', () => {
  it('accepts the actual reviewed range and either horizon representation', () => {
    const value = result()
    expect(validateCalendarCreationPreview(value,input)).toBe(value)
    expect(validateCalendarCreationPreview(value,{
      weeks_per_year:52,season_start_year_week:35,start_year:2030,last_season_start_year:2032
    })).toBe(value)
  })
  it('rejects a different clock, false mutation claims and inconsistent endpoints', () => {
    const value = result()
    for (const invalid of [
      null, {...value,read_only:false}, {...value,run_created:true},
      {...value,run_calendar:{...value.run_calendar,weeks_per_year:61}},
      {...value,first_week:{...value.first_week,calendar_year:2000}},
      {...value,last_week:{...value.last_week,year_week:52}},
      {...value,last_week:{...value.last_week,week_ordinal:122}},
      {...value,last_week:{...value.last_week,season_label:'2033/2034'}},
      {...value,limitations:[]}, {...value,sporting_calendar_supported:'true'},
    ]) expect(() => validateCalendarCreationPreview(invalid,input)).toThrow()
  })
})
