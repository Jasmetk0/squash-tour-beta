import {render,screen,within} from '@testing-library/react'
import {describe,expect,it} from 'vitest'
import type {ServerTask} from '../api/fullSimulationTasks'
import {calendarTaskExample,taskExample} from '../api/fullSimulationTasks.fixture'
import {FullSimulationTaskProgressEvidence} from './FullSimulationTaskProgressEvidence'

function native(weeks=52):ServerTask{
  const clock={schema_version:'run_calendar.v1' as const,weeks_per_year:weeks,
    season_start_year_week:1,start_year:2025,season_count:3}
  const task=calendarTaskExample(clock)
  task.original_command={...task.original_command,schema_version:'authoritative_full_simulation_command.v2',
    run_id:task.run_id,branch_id:task.branch_id,seed:1,execution_calendar:clock,
    expected_start_week:{season_index:0,week:weeks-1},target_week:{season_index:1,week:3}}
  task.current_week={season_index:1,week:1}
  task.progress_evidence={...task.progress_evidence,week:task.current_week,weeks_advanced_since_start:2}
  return task
}
describe('recorded server task progress',()=>{
  it.each([52,61,80])('uses the original W%s clock across a season boundary',weeks=>{
    render(<FullSimulationTaskProgressEvidence task={native(weeks)} cs={false}/>)
    expect(screen.getByRole('progressbar')).toHaveAttribute('value','2')
    expect(screen.getByRole('progressbar')).toHaveAttribute('max','4')
    expect(screen.getByText(/Week transitions: 2 \/ 4/)).toHaveTextContent('Distance to original target: 2')
    expect(screen.getByText(/Remaining time estimate: unavailable/)).toBeInTheDocument()
    expect(screen.getByText(/not the amount of work completed/)).toBeInTheDocument()
  })
  it('does not declare completion when the target week is reached while paused',()=>{
    const task=native()
    task.state='paused'
    task.current_week={season_index:1,week:3}
    task.progress_evidence={...task.progress_evidence,week:task.current_week,weeks_advanced_since_start:4}
    render(<FullSimulationTaskProgressEvidence task={task} cs={false}/>)
    expect(screen.getByRole('progressbar')).toHaveAttribute('value','4')
    expect(screen.getByText(/task completion is determined by its own status/)).toBeInTheDocument()
  })
  it('does not invent progress for a full Run closure or legacy task',()=>{
    const task=native()
    if('schema_version' in task.original_command)task.original_command.target_week=null
    const {rerender}=render(<FullSimulationTaskProgressEvidence task={task} cs={false}/>)
    expect(screen.getByText(/Final Save cannot be inferred/)).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    rerender(<FullSimulationTaskProgressEvidence task={taskExample() as unknown as ServerTask} cs={false}/>)
    expect(screen.getByText(/Verified distance to the original target is unavailable/)).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })
  it('fails closed for missing or inconsistent recorded progress',()=>{
    const task=native()
    task.progress_evidence.weeks_advanced_since_start=3
    const {rerender}=render(<FullSimulationTaskProgressEvidence task={task} cs={true}/>)
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
    expect(screen.getByText(/Ověřená vzdálenost k původnímu cíli není dostupná/)).toBeInTheDocument()
    const unavailable=native()
    unavailable.current_week=null
    unavailable.progress_evidence={...unavailable.progress_evidence,kind:'unavailable',week:null,
      weeks_advanced_since_start:null,completed_slot_receipts_this_week:null,
      committed_group_receipts_this_week:null,receipt_scope:null}
    rerender(<FullSimulationTaskProgressEvidence task={unavailable} cs={false}/>)
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })
  it('shows only the latest three stored task control records without mutating them',()=>{
    const task=native()
    task.events=Array.from({length:4},(_,i)=>({...task.events[0],revision:i+1,reason:'reason-'+(i+1)}))
    render(<FullSimulationTaskProgressEvidence task={task} cs={false}/>)
    const region=screen.getByRole('region',{name:'Recorded task progress'})
    expect(within(region).getByText('Latest stored control events (3)')).toBeInTheDocument()
    const details=region.querySelector('details')!
    details.open=true
    expect(within(region).getAllByRole('listitem').map(x=>x.textContent)).toEqual([
      expect.stringContaining('reason-4'),expect.stringContaining('reason-3'),expect.stringContaining('reason-2')])
    expect(within(region).queryByText('reason-1')).not.toBeInTheDocument()
    expect(task.events.map(e=>e.revision)).toEqual([1,2,3,4])
  })
})
