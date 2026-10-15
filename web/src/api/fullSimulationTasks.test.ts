import {afterEach,describe,expect,it,vi} from 'vitest'
import {continueServerTask,getServerTasks,startServerTask,validateTasks} from './fullSimulationTasks'
import {taskExample} from './fullSimulationTasks.fixture'

afterEach(()=>vi.restoreAllMocks())
describe('server task HTTP contracts',()=>{
 it('reads without POST and validates exact scope',async()=>{
  vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({schema_version:'full_simulation_tasks.v1',tasks:[taskExample()]})))
  expect((await getServerTasks('run','branch'))[0].task_id).toBe('task')
  expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/runs/run/branches/branch/'),undefined)
 })
 it.each(['scope','chain','revision','state','command','duplicate'] as const)('rejects corrupt %s',kind=>{
  const t=taskExample();const data={schema_version:'full_simulation_tasks.v1',tasks:[t]}
  if(kind==='scope')t.branch_id='other'
  if(kind==='chain')t.events[0].previous='x'
  if(kind==='revision')t.revision=2
  if(kind==='state')t.state='invented'
  if(kind==='command')t.original_command.command_id='other'
  if(kind==='duplicate')data.tasks.push(t)
  expect(()=>validateTasks(data,'run','branch')).toThrow('Invalid')
 })
 it('rejects forged or mismatched measured task progress',()=>{
  for(const invalid of [
    {completed_slot_receipts_this_week:-1},
    {committed_group_receipts_this_week:1.5},
    {weeks_advanced_since_start:7},
    {receipt_scope:null},
    {kind:'terminal_frozen'},
    {week:{season_index:1,week:1}}
  ]){
   const t=taskExample() as unknown as import('./fullSimulationTasks').ServerTask
   t.progress_evidence={...t.progress_evidence,...invalid} as never
   expect(()=>validateTasks({schema_version:'full_simulation_tasks.v1',tasks:[t]},'run','branch')).toThrow('Invalid')
  }
 })
 it('accepts a frozen historical endpoint without invented match counts',()=>{
  const t=taskExample() as unknown as import('./fullSimulationTasks').ServerTask
  t.state='stopped'
  t.current_week={season_index:0,week:2}
  t.progress_evidence={...t.progress_evidence,kind:'terminal_frozen',week:t.current_week,
   weeks_advanced_since_start:1,completed_slot_receipts_this_week:null,
   committed_group_receipts_this_week:null,receipt_scope:null}
  expect(validateTasks({schema_version:'full_simulation_tasks.v1',tasks:[t]},'run','branch')).toHaveLength(1)
 })
 it('preserves exact start input for lost-response replay',async()=>{
  const command=taskExample().original_command;const requests:unknown[]=[]
  vi.spyOn(globalThis,'fetch').mockImplementation(async(_url,options)=>{
   requests.push(JSON.parse(options!.body as string));if(requests.length===1)throw Error('offline')
   return new Response(JSON.stringify({schema_version:'full_simulation_task_ack.v1',task_id:'task',run_id:'run',branch_id:'branch',parent_command_id:'parent',request_id:'start',accepted_revision:1}))
  })
  await expect(startServerTask('run','branch','start',command)).rejects.toThrow('offline')
  expect((await startServerTask('run','branch','start',command)).task_id).toBe('task')
  expect(requests[0]).toEqual(requests[1])
 })
 it('rejects a continuation acknowledgement from another task',async()=>{
  const task=taskExample();vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(JSON.stringify({schema_version:'full_simulation_task_ack.v1',task_id:'other',run_id:'run',branch_id:'branch',parent_command_id:'parent',request_id:'recover',accepted_revision:2})))
  await expect(continueServerTask(task as never,{request_id:'recover',action:'recover',expected_revision:1,operator_label:'Op',audit_reason:'Recover'})).rejects.toThrow('identity')
 })
})
