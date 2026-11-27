import type {ServerTask} from '../api/fullSimulationTasks'

const storageKey='squash-engine-simulation-monitor-notices-v1'
const maxKeys=100
export const isTerminalTask=(task:ServerTask)=>['stopped','target_reached','complete'].includes(task.state)
export const taskNoticeKey=(task:ServerTask)=>JSON.stringify([task.run_id,task.branch_id,task.task_id,task.parent_command_id])
type Ledger={tracked:string[];notices:string[];handled:string[]}
const empty=():Ledger=>({tracked:[],notices:[],handled:[]})
const bounded=(keys:string[])=>[...new Set(keys)].slice(-maxKeys)
export function loadMonitorNotices():Ledger{
 try{
  const value=JSON.parse(sessionStorage.getItem(storageKey)??'null')
  if(!value||!['tracked','notices','handled'].every(k=>Array.isArray(value[k])&&
    value[k].length<=maxKeys&&value[k].every((key:unknown)=>typeof key==='string')))return empty()
  return value
 }catch{return empty()}
}
export function storeMonitorNotices(value:Ledger):void{
 try{sessionStorage.setItem(storageKey,JSON.stringify(value))}catch{/* Session preference only */}
}
export function clearMonitorNotices():Ledger{
 const value=empty();storeMonitorNotices(value);return value
}
/** Local notification preferences only. Never supply task data or navigation
 * identity from storage: display only matching, currently verified terminal rows.
 * A first observation of an already terminal task does not create a notice. */
export function observeMonitorTasks(previous:Ledger,tasks:readonly ServerTask[]):Ledger{
 const tracked=new Set(previous.tracked),handled=new Set(previous.handled)
 const notices=[...previous.notices]
 for(const task of tasks){
  const key=taskNoticeKey(task)
  if(isTerminalTask(task)){
   if(tracked.has(key)&&!handled.has(key)){notices.push(key);handled.add(key)}
   tracked.delete(key)
  }else if(!handled.has(key)){
   tracked.add(key)
  }
 }
 const next={tracked:bounded([...tracked]),notices:bounded(notices),handled:bounded([...handled])}
 return JSON.stringify(next)===JSON.stringify(previous)?previous:next
}
export function dismissMonitorNotice(previous:Ledger,key:string):Ledger{
 return {...previous,notices:previous.notices.filter(item=>item!==key)}
}
