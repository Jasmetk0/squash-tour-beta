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
