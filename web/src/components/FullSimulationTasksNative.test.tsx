/** Component/API-boundary contracts; real worker acceptance is separate. */
import {QueryClient,QueryClientProvider} from '@tanstack/react-query'
import {fireEvent,render,screen,waitFor} from '@testing-library/react'
import {MemoryRouter} from 'react-router-dom'
import {beforeEach,describe,expect,it,vi} from 'vitest'
import {LanguageProvider} from '../i18n/LanguageContext'
import {NativeFullSimulationPanel} from './FullSimulationTasksNative'

const api=vi.hoisted(()=>({previewNativeTask:vi.fn(),startServerTask:vi.fn()}))
vi.mock('../api/fullSimulationTasksNative',async original=>({...await original<typeof import('../api/fullSimulationTasksNative')>(),previewNativeTask:api.previewNativeTask}))
vi.mock('../api/fullSimulationTasks',async original=>({...await original<typeof import('../api/fullSimulationTasks')>(),startServerTask:api.startServerTask}))
const clock={schema_version:'run_calendar.v1' as const,weeks_per_year:80,season_start_year_week:79,start_year:2100,season_count:2}
const preview=(request:Record<string,unknown>)=>({schema_version:'authoritative_full_simulation_preview.v2',request,execution_calendar:clock,
 start_week:{season_index:0,week:2},final_week:{season_index:1,week:80},target_week:request.target_week,
 expected_position_fingerprint:'a'.repeat(64),expected_revision_id:'original-saved',preview_fingerprint:'b'.repeat(64),
 target_semantics:request.target_week?'open_target_week':'saved_final_run_closure',manual_save_required_after_each_sporting_child:true,initial_transition_blockers:[]})
const panel=()=>render(<QueryClientProvider client={new QueryClient({defaultOptions:{mutations:{retry:false}}})}><MemoryRouter><LanguageProvider><NativeFullSimulationPanel runId="run" branchId="branch" head="head" saved/></LanguageProvider></MemoryRouter></QueryClientProvider>)
function fill(){fireEvent.change(screen.getByLabelText('Native simulation operator'),{target:{value:'Admin'}});fireEvent.change(screen.getByLabelText('Native simulation reason'),{target:{value:'Reviewed source'}})}
describe('Native task explicit review and immutable retries',()=>{
 beforeEach(()=>{vi.clearAllMocks();localStorage.setItem('squash-engine-language-v1','en');api.previewNativeTask.mockImplementation(async r=>preview(r))})
 it('starts only after separate review and explicit confirmation, preserving W80 and source',async()=>{
  api.startServerTask.mockResolvedValue({task_id:'task',parent_command_id:'parent'});panel();fill()
  fireEvent.click(screen.getByRole('button',{name:'Review server simulation'}))
  const button=await screen.findByRole('button',{name:'Start as server task'});expect(button).toBeDisabled();expect(api.startServerTask).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(button)
  await waitFor(()=>expect(api.startServerTask).toHaveBeenCalledOnce())
  expect(api.startServerTask.mock.calls[0][3]).toMatchObject({schema_version:'authoritative_full_simulation_command.v2',execution_calendar:clock,expected_revision_id:'original-saved',target_week:null,seed:231})
 })
 it('discards a delayed review after editing the target',async()=>{
  let resolve!:(value:unknown)=>void
  api.previewNativeTask.mockImplementation(r=>new Promise(done=>{resolve=value=>done(value??preview(r))}))
  panel();fill();fireEvent.click(screen.getByRole('button',{name:'Review server simulation'}))
  fireEvent.change(screen.getByLabelText('Native simulation target'),{target:{value:'week'}})
  resolve(null)
  await waitFor(()=>expect(screen.getByRole('button',{name:'Review server simulation'})).not.toBeDisabled())
  expect(screen.queryByRole('button',{name:'Start as server task'})).not.toBeInTheDocument()
 })
 it('retries the identical frozen start request after an uncertain acknowledgement',async()=>{
  api.startServerTask.mockRejectedValueOnce(new Error('connection lost')).mockResolvedValue({task_id:'task',parent_command_id:'parent'})
  panel();fill();fireEvent.click(screen.getByRole('button',{name:'Review server simulation'}))
  const button=await screen.findByRole('button',{name:'Start as server task'});fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(button)
  fireEvent.click(await screen.findByRole('button',{name:'Retry same request'}))
  await waitFor(()=>expect(api.startServerTask).toHaveBeenCalledTimes(2))
  expect(api.startServerTask.mock.calls[1]).toEqual(api.startServerTask.mock.calls[0])
 })
})
