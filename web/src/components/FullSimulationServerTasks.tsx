import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { continueServerTask, getServerTasks, startServerTask } from '../api/fullSimulationTasks'
import type { ContinueTask, ServerTask } from '../api/fullSimulationTasks'
import type { AuthoritativeFullSimulationCommandPayload } from '../api/types'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { FullSimulationSummary } from './FullSimulationSummary'

const copy={
 en:{title:'Server simulation tasks',start:'Start as server task',ack:'Server task accepted',refresh:'Refresh task evidence',
  truth:'The server executes this task after this page closes. Save and season approvals remain manual. After a server restart, inspect and explicitly recover the task.',
  loading:'Loading server tasks…',empty:'No server tasks in this scope.',operator:'Task operator',reason:'Task audit reason',
  resume:'Explicitly resume server task',recover:'Explicitly recover server task',retry:'Retry same request',cancel:'Cancel retry and refresh',
  manual:'Operator action required. Resolve the checkpoint in Run Admin, then explicitly continue this task. Save is manual.',
  health:'Last worker heartbeat',recent:'Recently observed; work may be blocked',stale:'Stale; healthy execution is unconfirmed',inactive:'No valid worker ownership',
  checkpoint:'Last checkpoint',open:'Open exact Run / Branch',original:'Original command',detail:'Stored terminal summary',
  ownership_unverified:'Another server instance owns the lease; inspect heartbeat and wait for release or expiry',queued:'Queued',active:'Executing on server',pause_requested:'Pausing at safe boundary',paused:'Safely paused',awaiting_operator:'Waiting for operator',
  stopped:'Stopped',target_reached:'Target reached',complete:'Complete',failed:'Failed; inspect before recovery',recoverable:'Interrupted; explicit recovery required'},
 cs:{title:'Serverové simulační úlohy',start:'Spustit jako serverovou úlohu',ack:'Serverová úloha přijata',refresh:'Obnovit údaje úloh',
  truth:'Server pokračuje i po zavření této stránky. Save a sezonní schválení zůstávají ruční. Po restartu serveru úlohu zkontrolujte a výslovně obnovte.',
  loading:'Načítám serverové úlohy…',empty:'V tomto kontextu nejsou serverové úlohy.',operator:'Operátor úlohy',reason:'Důvod akce úlohy',
  resume:'Výslovně pokračovat v serverové úloze',recover:'Výslovně obnovit serverovou úlohu',retry:'Zopakovat stejný požadavek',cancel:'Zrušit opakování a obnovit údaje',
  manual:'Je nutná akce operátora. Vyřešte checkpoint ve správě Runu a pak výslovně pokračujte v této úloze. Save zůstává ruční.',
  health:'Poslední odezva workeru',recent:'Nedávno zaznamenána; práce může být blokovaná',stale:'Zastaralá; zdravý běh není potvrzen',inactive:'Bez platného vlastnictví workeru',
  checkpoint:'Poslední checkpoint',open:'Otevřít přesný Run / větev',original:'Původní příkaz',detail:'Uložený závěrečný souhrn',
  ownership_unverified:'Lease vlastní jiná instance serveru; zkontrolujte odezvu a vyčkejte na uvolnění nebo expiraci',queued:'Ve frontě',active:'Běží na serveru',pause_requested:'Pozastavuji na bezpečné hranici',paused:'Bezpečně pozastaveno',awaiting_operator:'Čeká na operátora',
  stopped:'Ukončeno',target_reached:'Cíl dosažen',complete:'Dokončeno',failed:'Chyba; před obnovou zkontrolujte stav',recoverable:'Přerušeno; nutná výslovná obnova'}
} as const
export function useServerTasks(run?:string,branch?:string,enabled=true){
 return useQuery({queryKey:['server-simulation-tasks',run??null,branch??null],queryFn:()=>getServerTasks(run,branch),retry:false,refetchInterval:2000,enabled})
}
export function StartServerTask({runId,branchId,command,disabled,onAccepted}:{runId:string;branchId:string;command:AuthoritativeFullSimulationCommandPayload;disabled:boolean;onAccepted:()=>void}){
 const {language}=useLanguage();const t=copy[language];const client=useQueryClient()
 // Stable across dropped responses and page remounts for this original command.
 const requestId='server-start-'+command.command_id.slice(0,100)
 const [frozen,setFrozen]=useState<AuthoritativeFullSimulationCommandPayload|null>(null)
 const mutation=useMutation({mutationFn:()=>startServerTask(runId,branchId,requestId,frozen??command),onSuccess:async()=>{
   await client.invalidateQueries({queryKey:['server-simulation-tasks']});onAccepted()
 }})
 return <div><p>{t.truth}</p>
  <button type="button" disabled={(disabled&&!frozen)||mutation.isPending||mutation.isSuccess} onClick={()=>{setFrozen(frozen??command);mutation.mutate()}}>{mutation.isError?t.retry:t.start}</button>
  {mutation.data && <p role="status">{t.ack}: <code>{mutation.data.task_id}</code> · <code>{mutation.data.parent_command_id}</code></p>}
  {mutation.error && <p role="alert">{formatApiError(mutation.error)}</p>}
 </div>
}
const checkpointGuidance = (checkpoint:string|null,language:'cs'|'en') => {
 const code=checkpoint??''
 if(code.includes('save_required'))return language==='cs'?'Proveďte výslovný Save v této větvi. Poté pokračujte ve stejné serverové úloze.':'Explicitly Save this Branch, then continue this same server task.'
 if(code.includes('review_required'))return language==='cs'?'Zkontrolujte a výslovně schvalte Season Transition nebo závěrečné uzavření Runu. Poté pokračujte ve stejné úloze.':'Review and explicitly approve the Season Transition or final Run closure, then continue the same task.'
 if(code==='entry_process_required')return language==='cs'?'Vyřešte aktuální Entry rozhodnutí v této větvi; úloha je za vás nepotvrdí.':'Resolve the current Entry decision in this Branch; the task will not approve it for you.'
 return language==='cs'?'Zkontrolujte přípravu týdne, plán a uvedené překážky v konzoli této větve. Poté výslovně pokračujte.':'Inspect this Branch’s week preparation, schedule and reported blockers in the console, then explicitly continue.'
}
function TaskCard({task}:{task:ServerTask}){
 const {language}=useLanguage();const t=copy[language];const client=useQueryClient()
 const [operator,setOperator]=useState('');const [reason,setReason]=useState('');const [pending,setPending]=useState<ContinueTask|null>(null)
 const action=task.state==='recoverable'||task.state==='failed'?'recover':'resume'
 const mutation=useMutation({mutationFn:(body:ContinueTask)=>continueServerTask(task,body),onSuccess:async()=>{
  setPending(null);setReason('');await client.invalidateQueries({queryKey:['server-simulation-tasks']});
  await client.invalidateQueries({queryKey:['authoritative-full-simulation-pending',task.run_id,task.branch_id]})
 }})
 const terminal=['stopped','target_reached','complete'].includes(task.state)
 return <li data-task-id={task.task_id}>
  <strong>{task.run_name} / {task.branch_name}</strong> · <span>{t[task.state as keyof typeof t]??task.state}</span>
  <p><code>{task.task_id}</code> · {t.original}: <code>{task.parent_command_id}</code></p>
  <p>{t.health}: {t[task.heartbeat_health]}{task.heartbeat_unix>0 && <> · {new Date(task.heartbeat_unix*1000).toLocaleString(language)}</>}</p>
  {task.current_week && <p>S{task.current_week.season_index} W{task.current_week.week}</p>}
  {task.checkpoint && <p>{t.checkpoint}: <code>{task.checkpoint}</code></p>}
  {task.error && <p role="alert">{task.error}</p>}
  {task.needs_operator_action && <><p>{t.manual}</p>{task.state==='awaiting_operator' && <p>{checkpointGuidance(task.checkpoint,language)}</p>}
   <label>{t.operator}<input value={operator} disabled={!!pending} onChange={e=>setOperator(e.target.value)}/></label>
   <label>{t.reason}<input value={reason} disabled={!!pending} onChange={e=>setReason(e.target.value)}/></label>
   <button type="button" disabled={!operator.trim()||!reason.trim()||mutation.isPending} onClick={()=>{
     const body=pending??{request_id:crypto.randomUUID(),action,expected_revision:task.revision,operator_label:operator.trim(),audit_reason:reason.trim()}
     setPending(body);mutation.mutate(body)
   }}>{pending?t.retry:action==='recover'?t.recover:t.resume}</button>
   {pending && !mutation.isPending && <button type="button" onClick={()=>{setPending(null);mutation.reset();void client.invalidateQueries({queryKey:['server-simulation-tasks']})}}>{t.cancel}</button>}
  </>}
  {mutation.error && <p role="alert">{formatApiError(mutation.error)}</p>}
  <Link to={`/admin/runs/${encodeURIComponent(task.run_id)}/simulate?branch=${encodeURIComponent(task.branch_id)}&task=${encodeURIComponent(task.task_id)}`}>{t.open}</Link>
  {terminal && <details><summary>{t.detail}</summary><FullSimulationSummary runId={task.run_id} branchId={task.branch_id} commandId={task.parent_command_id}/></details>}
 </li>
}
export function FullSimulationServerTasks({runId,branchId}:{runId?:string;branchId?:string}){
 const {language}=useLanguage();const t=copy[language];const query=useServerTasks(runId,branchId)
 return <section aria-label={t.title}><h3>{t.title}</h3><p>{t.truth}</p>
  <button type="button" onClick={()=>void query.refetch()} disabled={query.isFetching}>{t.refresh}</button>
  {query.isPending && <p role="status">{t.loading}</p>}
  {query.error && <p role="alert">{formatApiError(query.error)}</p>}
  {query.isSuccess && (query.data.length?<ul>{query.data.map(task=><TaskCard key={task.task_id} task={task}/>)}</ul>:<p>{t.empty}</p>)}
 </section>
}
