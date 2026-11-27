import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {render,screen,within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {NativeTaskSummary} from './FullSimulationTasksNative'
import type {NativeTerminalSummary} from '../api/fullSimulationTasksNative'
import {calendarTaskExample} from '../api/fullSimulationTasks.fixture'

const api=vi.hoisted(()=>({nativeTaskSummary:vi.fn()}))
vi.mock('../api/fullSimulationTasksNative',async original=>({...await original<object>(),...api}))
vi.mock('../i18n/LanguageContext',()=>({useLanguage:()=>({language:'en'})}))
const clock={schema_version:'run_calendar.v1' as const,weeks_per_year:52,season_start_year_week:1,start_year:2025,season_count:3}
const task=calendarTaskExample(clock)
const summary:NativeTerminalSummary={
 schema_version:'full_simulation_terminal_summary.v3',status:'stopped',run_id:task.run_id,
 branch_id:task.branch_id,command_id:task.parent_command_id,start_week:{season_index:0,week:1},
 end_week:{season_index:0,week:25},original_final_week:{season_index:2,week:52},
 effective_target_week:{season_index:1,week:1},execution_calendar:clock,
 initial_saved_revision_id:'initial',terminal_saved_revision_id:'terminal',persisted_child_command_count:42,
 reason:'operator_stop',target_reached:false,
 completed_tournaments:Array.from({length:23},(_,i)=>'edition-'+String(i+1).padStart(2,'0')),
 summary_fingerprint:'a'.repeat(64)
}
function mount(){
 render(<QueryClientProvider client={new QueryClient({defaultOptions:{queries:{retry:false}}})}>
  <MemoryRouter><NativeTaskSummary task={task}/></MemoryRouter>
 </QueryClientProvider>)
}
describe('stored native summary',()=>{
 beforeEach(()=>{vi.clearAllMocks();api.nativeTaskSummary.mockResolvedValue(summary)})
 it('shows original historical positions, reason, saved IDs and locally browsable Editions',async()=>{
  mount()
  expect(await screen.findByRole('heading',{name:'Stopped by operator'})).toBeInTheDocument()
  const region=screen.getByRole('region',{name:'Stored native summary'})
  expect(region).toHaveAttribute('data-run-navigation-readonly')
  expect(region).toHaveTextContent('Actual startS1 W01')
  expect(region).toHaveTextContent('Actual endS1 W25')
  expect(region).toHaveTextContent('Target weekS2 W01')
  expect(region).toHaveTextContent('Terminal Saved Revisionterminal')
  expect(region).toHaveTextContent('Tournament names, winners, ranking changes and watched events are unavailable')
  const list=within(region).getByRole('list',{name:'Confirmed Editions'})
  expect(within(list).getAllByRole('listitem')).toHaveLength(20)
  await userEvent.click(within(region).getByRole('button',{name:'Next'}))
  expect(within(region).getAllByRole('listitem')).toHaveLength(3)
  expect(screen.getByText('edition-23')).toBeInTheDocument()
  await userEvent.type(within(region).getByRole('searchbox'),'edition-01')
  expect(within(region).getAllByRole('listitem')).toHaveLength(1)
  expect(screen.getByText('edition-01')).toBeInTheDocument()
  expect(api.nativeTaskSummary).toHaveBeenCalledTimes(1)
 })
 it('does not continue displaying an old summary after failed refresh',async()=>{
  api.nativeTaskSummary.mockResolvedValueOnce(summary).mockRejectedValueOnce(Error('offline'))
  mount()
  await screen.findByRole('heading',{name:'Stopped by operator'})
  await userEvent.click(screen.getByRole('button',{name:'Refresh summary'}))
  expect(await screen.findByRole('alert')).toHaveTextContent('offline')
  expect(screen.queryByRole('list',{name:'Confirmed Editions'})).not.toBeInTheDocument()
 })
})
