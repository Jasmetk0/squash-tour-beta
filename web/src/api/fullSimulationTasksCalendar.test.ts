import {describe,expect,it,vi,afterEach} from 'vitest'
import {getServerTasks,validateTasks} from './fullSimulationTasks'
import {serverTaskCalendar,taskCalendarPosition,taskWeekOrdinal} from './fullSimulationTasksCalendar'
import type {TaskCalendar} from './fullSimulationTasksCalendar'
import {calendarTaskExample,taskExample} from './fullSimulationTasks.fixture'

const earth:TaskCalendar={schema_version:'run_calendar.v1',weeks_per_year:52,season_start_year_week:1,start_year:2030,season_count:64}
afterEach(()=>vi.restoreAllMocks())
const envelope=(task:unknown)=>({schema_version:'full_simulation_tasks.v1',tasks:[task]})

describe('versioned Saved task clock contract',()=>{
 it.each([52,61,80,1])('validates a W%s rollover using the supplied clock, beyond fifty seasons',w=>{
  const task=calendarTaskExample({...earth,weeks_per_year:w})
  task.original_command.expected_start_week={season_index:50,week:w}
  task.current_week={season_index:51,week:1}
  task.progress_evidence.week=task.current_week
  task.progress_evidence.weeks_advanced_since_start=1
  expect(validateTasks(envelope(task),'run','branch')).toHaveLength(1)
  expect(taskWeekOrdinal(task.current_week,task.execution_calendar!)).toBe(51*w)
  task.progress_evidence.weeks_advanced_since_start=2
  expect(()=>validateTasks(envelope(task),'run','branch')).toThrow('Invalid')
 })
 it('reads v2 from actual JSON HTTP without a supplemental mutable Run lookup',async()=>{
  const task=calendarTaskExample(earth)
  vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify(envelope(task))))
  expect((await getServerTasks('run','branch'))[0].execution_calendar).toEqual(earth)
  expect(fetch).toHaveBeenCalledTimes(1)
 })
 it.each([1,35,52])('converts original season and year correctly for offset %s',offset=>{
  const task=calendarTaskExample({...earth,season_start_year_week:offset})
  const end=taskCalendarPosition(task,{season_index:2,week:52})
  expect(end.seasonStartYear).toBe(2032)
  expect(end.seasonLabel).toBe(offset===1?'2032':'2032/2033')
  expect(end.calendarYear).toBe(offset===1?2032:2033)
  expect(end.yearWeek).toBe(offset===1?52:offset-1)
 })
 it('keeps year-week conversion exact even near the JSON integer boundary',()=>{
  const max=Number.MAX_SAFE_INTEGER
  const task=calendarTaskExample({...earth,weeks_per_year:max,season_start_year_week:max,season_count:1})
  const actual=taskCalendarPosition(task,{season_index:0,week:max})
  expect(actual.calendarYear).toBe(2031)
  expect(actual.yearWeek).toBe(max-1)
 })
 it('preserves explicit old v1 semantics without mutating the payload',()=>{
  const task=taskExample();const original=JSON.stringify(task)
  expect(serverTaskCalendar(task)).toEqual({schema_version:'legacy_fax_calendar.v0',weeks_per_year:61,
   season_start_year_week:37,start_year:2000,season_count:50})
  expect(validateTasks(envelope(task))).toHaveLength(1)
  expect(JSON.stringify(task)).toBe(original)
  const fake={...task,execution_calendar:earth}
  expect(()=>validateTasks(envelope(fake))).toThrow('Invalid legacy')
 })
 it.each([
  null, {}, {...earth,schema_version:'unknown'}, {...earth,weeks_per_year:0},
  {...earth,weeks_per_year:true}, {...earth,weeks_per_year:52.1},
  {...earth,season_start_year_week:53}, {...earth,season_start_year_week:0},
  {...earth,start_year:-1}, {...earth,season_count:0},
  {...earth,season_count:2147483648}, {...earth,weeks_per_year:Number.MAX_SAFE_INTEGER},
  {...earth,extra:1}, {...earth,schema_version:'legacy_fax_calendar.v0'},
 ])('rejects malformed explicit clocks without a FAX fallback: %j',clock=>{
  const task={...calendarTaskExample(earth),execution_calendar:clock}
  expect(()=>validateTasks(envelope(task))).toThrow('Invalid')
 })
 it.each(['missing','null','wrong_revision','wrong_progress','unknown_view','past_horizon','past_year'])(
  'rejects broken version/source/position: %s',kind=>{
   const task=calendarTaskExample(earth)
   if(kind==='missing')delete task.execution_calendar
   if(kind==='null')task.execution_calendar=null as never
   if(kind==='wrong_revision')task.calendar_revision_id='different-saved'
   if(kind==='wrong_progress')task.progress_evidence.schema_version='full_simulation_task_progress_evidence.v1'
   if(kind==='unknown_view')task.schema_version='full_simulation_task_view.v3' as never
   if(kind==='past_horizon')task.current_week={season_index:64,week:1}
   if(kind==='past_year')task.original_command.expected_start_week={season_index:0,week:53}
   expect(()=>validateTasks(envelope(task))).toThrow('Invalid')
  })
 it('validates frozen terminal evidence against the task clock, not a later Run',()=>{
  const task=calendarTaskExample({...earth,weeks_per_year:80})
  task.state='complete'
  task.current_week={season_index:63,week:80}
  task.progress_evidence={schema_version:'full_simulation_task_progress_evidence.v2',kind:'terminal_frozen',
   week:task.current_week,weeks_advanced_since_start:64*80-1,receipt_scope:null,
   completed_slot_receipts_this_week:null,committed_group_receipts_this_week:null}
  expect(validateTasks(envelope(task))).toHaveLength(1)
  expect(taskCalendarPosition(task,task.current_week).seasonLabel).toBe('2093')
  task.progress_evidence.completed_slot_receipts_this_week=1
  expect(()=>validateTasks(envelope(task))).toThrow('Invalid')
 })
})
