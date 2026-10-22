import { BoundaryDescription } from './FullSimulationBoundaryTargets'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { continueServerTask, getServerTasks, startServerTask } from '../api/fullSimulationTasks'
import type { ContinueTask, ServerTask } from '../api/fullSimulationTasks'
import type { AuthoritativeFullSimulationCommandPayload } from '../api/types'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { FullSimulationSummary } from './FullSimulationSummary'
import { FullSimulationWeekScheduleReview } from './FullSimulationWeekScheduleReview'

const copy={
 en:{title:'Server simulation tasks',start:'Start as server task',ack:'Server task accepted',refresh:'Refresh task evidence',
  truth:'A task with a live worker can continue after this page closes; a saved task or lease alone does not prove execution. Save and approvals stay manual. After a server restart, inspect and explicitly recover the task.',
  loading:'Loading server tasks…',empty:'No server tasks in this scope.',operator:'Task operator',reason:'Task audit reason',
  resume:'Explicitly resume server task',recover:'Explicitly recover server task',retry:'Retry same request',cancel:'Cancel retry and refresh',
  manual:'Operator action required. Resolve the checkpoint in Run Admin, then explicitly continue this task. Save is manual.',
  health:'Last worker heartbeat',recent:'Recently observed; work may be blocked',stale:'Stale; healthy execution is unconfirmed',inactive:'No valid worker ownership',
  checkpoint:'Current operator checkpoint',lastCheckpoint:'Last recorded checkpoint (not a current blocker)',pauseCheckpoint:'Current safe-pause checkpoint (not an operator blocker)',calendarPrep:'Review this season’s Calendar in Run Management',calendarPrepNote:'Review the actual blockers. Calendar source authoring, an explicit Run/Branch copy and Save are separate actions; never assume a missing Calendar means an empty week.',driverDetail:'Driver evidence',blockers:'Recorded blockers',currentBlockers:'Current blockers',open:'Open exact Run / Branch',original:'Original command',detail:'Stored terminal summary',
  ownership_unverified:'Another server instance owns the lease; inspect heartbeat and wait for release or expiry',queued:'Queued',active:'Active task state (worker health unverified)',pause_requested:'Pausing at safe boundary',paused:'Safely paused',awaiting_operator:'Waiting for operator',
  stopped:'Stopped',target_reached:'Target reached',complete:'Complete',failed:'Failed; inspect before recovery',recoverable:'Interrupted; explicit recovery required',
  measured:'Stored Branch receipts in current week',slots:'Completed match slots',groups:'Committed match groups',advanced:'Week transitions since task start',
  frozen:'Historical end week, frozen at termination',unavailable:'Historical end week unavailable; not inferred from the current Branch',
  needsCount:'Operator action required',liveCount:'Queued / executing / pause requested (health unconfirmed)',otherCount:'Other task states',
  search:'Find a server task',searchHint:'Run, Branch, task, parent command or checkpoint',filter:'Task category',
  allTasks:'All tasks',attentionTasks:'Operator action required',liveTasks:'Queued / active / pausing',otherTasks:'Other states',
  clearFilters:'Clear filters',shown:'Displayed tasks',noMatches:'No tasks match the current search and category. Clear the filters to see all stored tasks.',pinned:'Linked task stays visible regardless of filters.',
  desired:'Requested task state',lease:'Lease expiry (not proof of a live worker)',selected:'Task selected from the link',missing:'The linked task was not found in this Run / Branch.',contextChanged:'The reviewed request belongs to a different Run, Branch or command. Return to that context to retry; this screen will not redirect it.'},
 cs:{title:'Serverové simulační úlohy',start:'Spustit jako serverovou úlohu',ack:'Serverová úloha přijata',refresh:'Obnovit údaje úloh',
  truth:'Úloha se živým workerem může pokračovat i po zavření stránky; samotný záznam ani lease běh nedokazují. Save a schválení zůstávají ruční. Po restartu serveru úlohu zkontrolujte a výslovně obnovte.',
  loading:'Načítám serverové úlohy…',empty:'V tomto kontextu nejsou serverové úlohy.',operator:'Operátor úlohy',reason:'Důvod akce úlohy',
  resume:'Výslovně pokračovat v serverové úloze',recover:'Výslovně obnovit serverovou úlohu',retry:'Zopakovat stejný požadavek',cancel:'Zrušit opakování a obnovit údaje',
  manual:'Je nutná akce operátora. Vyřešte checkpoint ve správě Runu a pak výslovně pokračujte v této úloze. Save zůstává ruční.',
  health:'Poslední odezva workeru',recent:'Nedávno zaznamenána; práce může být blokovaná',stale:'Zastaralá; zdravý běh není potvrzen',inactive:'Bez platného vlastnictví workeru',
  checkpoint:'Aktuální checkpoint operátora',lastCheckpoint:'Poslední zaznamenaný checkpoint (není aktuální překážkou)',pauseCheckpoint:'Aktuální checkpoint bezpečného pozastavení (nejde o blokaci operátora)',calendarPrep:'Prověřit kalendář aktuální sezony ve správě Runu',calendarPrepNote:'Řiďte se skutečnými blokacemi. Vytvoření zdrojového kalendáře, výslovné zkopírování do Runu/větve a Save jsou oddělené kroky; chybějící kalendář neznamená prázdný týden.',driverDetail:'Podklady serverového průchodu',blockers:'Zaznamenané překážky',currentBlockers:'Aktuální překážky',open:'Otevřít přesný Run / větev',original:'Původní příkaz',detail:'Uložený závěrečný souhrn',
  ownership_unverified:'Lease vlastní jiná instance serveru; zkontrolujte odezvu a vyčkejte na uvolnění nebo expiraci',queued:'Ve frontě',active:'Aktivní stav úlohy (zdraví workeru nepotvrzeno)',pause_requested:'Pozastavuji na bezpečné hranici',paused:'Bezpečně pozastaveno',awaiting_operator:'Čeká na operátora',
  stopped:'Ukončeno',target_reached:'Cíl dosažen',complete:'Dokončeno',failed:'Chyba; před obnovou zkontrolujte stav',recoverable:'Přerušeno; nutná výslovná obnova',
  measured:'Uložené výsledkové záznamy větve v aktuálním týdnu',slots:'Dokončené zápasové sloty',groups:'Potvrzené zápasové skupiny',advanced:'Týdenních přechodů od začátku úlohy',
  frozen:'Historický koncový týden uložený při ukončení',unavailable:'Historický koncový týden není dostupný; aktuální stav větve jej nenahrazuje',
  needsCount:'Vyžaduje zásah operátora',liveCount:'Fronta / běží / pozastavuje (zdraví procesu nepotvrzeno)',otherCount:'Ostatní stavy úloh',
  search:'Najít serverovou úlohu',searchHint:'Run, větev, úloha, původní příkaz nebo checkpoint',filter:'Kategorie úloh',
  allTasks:'Všechny úlohy',attentionTasks:'Vyžaduje zásah operátora',liveTasks:'Ve frontě / aktivní / pozastavuje se',otherTasks:'Ostatní stavy',
  clearFilters:'Zrušit filtry',shown:'Zobrazené úlohy',noMatches:'Hledání a kategorie neodpovídá žádná úloha. Zrušením filtrů zobrazíte všechny uložené úlohy.',pinned:'Úloha vybraná z odkazu zůstává viditelná bez ohledu na filtry.',
  desired:'Požadovaný stav úlohy',lease:'Konec platnosti lease (nikoli důkaz živého workeru)',selected:'Úloha vybraná z odkazu',missing:'Odkazovaná úloha nebyla nalezena v tomto Runu / větvi.',contextChanged:'Schválený požadavek patří jinému Runu, větvi nebo příkazu. Pro opakování se vraťte do původního kontextu; tato obrazovka jej nepřesměruje.'}
} as const
export function useServerTasks(run?:string,branch?:string,enabled=true){
 return useQuery({queryKey:['server-simulation-tasks',run??null,branch??null],queryFn:()=>getServerTasks(run,branch),retry:false,refetchInterval:2000,enabled})
}
type StartRequest = {
 runId:string; branchId:string; requestId:string; command:AuthoritativeFullSimulationCommandPayload
}
export function StartServerTask({runId,branchId,command,disabled,onAccepted}:{runId:string;branchId:string;command:AuthoritativeFullSimulationCommandPayload;disabled:boolean;onAccepted:()=>void}){
 const {language}=useLanguage();const t=copy[language];const client=useQueryClient()
 const currentContext=useRef({runId,branchId,commandId:command.command_id})
 currentContext.current={runId,branchId,commandId:command.command_id}
 // A retry replays *all* original values, even if props change while offline.
 const [frozen,setFrozen]=useState<StartRequest|null>(null)
 const sameContext=!frozen||(frozen.runId===runId&&frozen.branchId===branchId&&frozen.command.command_id===command.command_id)
 const mutation=useMutation({
  mutationFn:(snapshot:StartRequest)=>startServerTask(snapshot.runId,snapshot.branchId,snapshot.requestId,snapshot.command),
  onSuccess:async (_ack,snapshot)=>{
   await client.invalidateQueries({queryKey:['server-simulation-tasks']})
   const current=currentContext.current
   if(current.runId===snapshot.runId&&current.branchId===snapshot.branchId&&current.commandId===snapshot.command.command_id)onAccepted()
  }
 })
 return <div><p>{t.truth}</p>
  <button type="button" disabled={(disabled&&!frozen)||!sameContext||mutation.isPending||mutation.isSuccess} onClick={()=>{
   const snapshot=frozen??{runId,branchId,requestId:'server-start-'+command.command_id.slice(0,100),
    command:{...command,expected_start_week:{...command.expected_start_week}}}
   setFrozen(snapshot);mutation.mutate(snapshot)
  }}>{mutation.isError?t.retry:t.start}</button>
  {!sameContext&&<p role="alert">{t.contextChanged}</p>}
  {mutation.data&&sameContext&&<p role="status">{t.ack}: <code>{mutation.data.task_id}</code> · <code>{mutation.data.parent_command_id}</code></p>}
  {mutation.error&&sameContext&&<p role="alert">{formatApiError(mutation.error)}</p>}
 </div>
}
const checkpointGuidance = (checkpoint:string|null,language:'cs'|'en') => {
 const code=checkpoint??''
 if(code==='week_schedule_extension_approved')return language==='cs'?'Rozšířený rozpis je výslovně schválený. Pro pokračování stejné úlohy zadejte operátora a důvod; nic se nespustí automaticky.':'The extended week schedule was explicitly approved. Provide operator and reason to resume the same task; execution never starts automatically.'
 if(code==='group_phase_review_required')return language==='cs'?'Tento turnaj má dosud nevyřešenou skupinovou fázi. V administraci nejprve odehrajte skupinové zápasy, výslovně potvrďte tabulky a vytvořte postupující a knockout pavouk. Potom můžete obnovit stejnou serverovou úlohu; výsledky se nesmějí domýšlet ani schvalovat automaticky.':'This tournament has an unresolved group phase. Play real group matches in Run Admin, explicitly confirm standings and freeze the entrants/knockout bracket. Then explicitly resume this same server task; no results or approvals are invented.'
 if(code==='group_postphase_review_required')return language==='cs'?'Skupinová fáze vyžaduje další výslovné rozhodnutí: tabulky, případné pořadí při shodě, postupující, knockout nebo bodování. Zkontrolujte přesné překážky v této větvi; pak výslovně pokračujte ve stejné úloze.':'The group phase requires an explicit decision about standings, ties, entrants, knockout or points. Inspect this Branch’s actual blockers, then explicitly resume the same task.'
 if(code==='week_schedule_review_required')return language==='cs'?'Původní příkaz nesmí nové zápasy převzít automaticky. Prohlédněte skutečný výsledek inspekce níže: pouze při prokázaném append-only rozšíření můžete nové sloty výslovně schválit; při blokaci postupujte podle konkrétního důvodu. Schválení ani prohlídka úlohu nespouští.':'The original command cannot silently absorb new matches. Inspect the actual evidence below: only a proven append-only suffix may be explicitly approved; a blocked inspection requires resolving its specific reason. Inspection or approval never resumes the task.'
 if(code==='target_changed_before_completion')return language==='cs'?'Cíl se změnil před konečným potvrzením dosažení. Výslovně pokračujte ve stejné úloze k jejímu aktuálnímu cíli.':'The target changed before completion was committed. Explicitly continue the same task toward its current target.'
 if(code==='target_boundary_review_required')return language==='cs'?'Cílová hranice se změnila. Znovu prověřte kanonický plán a výslovně změňte cíl, pak pokračujte ve stejné úloze.':'The target boundary changed. Review the canonical schedule and explicitly change the target, then continue the same task.'
 if(code.includes('save_required'))return language==='cs'?'Proveďte výslovný Save v této větvi. Poté pokračujte ve stejné serverové úloze.':'Explicitly Save this Branch, then continue this same server task.'
 if(code.includes('review_required'))return language==='cs'?'Zkontrolujte a výslovně schvalte Season Transition nebo závěrečné uzavření Runu. Poté pokračujte ve stejné úloze.':'Review and explicitly approve the Season Transition or final Run closure, then continue the same task.'
 if(code==='entry_process_required')return language==='cs'?'Vyřešte aktuální Entry rozhodnutí v této větvi; úloha je za vás nepotvrdí.':'Resolve the current Entry decision in this Branch; the task will not approve it for you.'
 return language==='cs'?'Zkontrolujte přípravu týdne, plán a uvedené překážky v konzoli této větve. Poté výslovně pokračujte.':'Inspect this Branch’s week preparation, schedule and reported blockers in the console, then explicitly continue.'
}

function storedDriverEvidence(task:ServerTask){
 const data=task.progress
 if(!data || data.schema_version!=='authoritative_full_simulation_progress.v1')return null
 return {
  detail:typeof data.detail==='string' && data.detail.trim()?data.detail:null,
  checkpoint:typeof data.checkpoint==='string'?data.checkpoint:null,
  blockers:Array.isArray(data.blockers)?data.blockers.filter((v):v is string=>typeof v==='string' && v.length>0):[]
 }
}

// A navigation hint, never an authority to copy, approve or resume a task.
// The task contract has no Run calendar start year/season mapping: do not invent
// a calendarSeason query parameter from a fixed 2000 baseline.
export function taskCalendarHandoff(task:ServerTask):string|null{
 if(task.state!=='awaiting_operator'||!['week_preparation_required','season_preparation_required','week61_preparation_required','final_week_preparation_required'].includes(task.checkpoint??'')||
   !task.current_week)return null
 return `/admin/runs/${encodeURIComponent(task.run_id)}/manage?branch=${encodeURIComponent(task.branch_id)}`
}
function TaskCard({task,focused=false}:{task:ServerTask;focused?:boolean}){
 const {language}=useLanguage();const t=copy[language];const client=useQueryClient()
 const [operator,setOperator]=useState('');const [reason,setReason]=useState('');const [pending,setPending]=useState<{target:ServerTask;body:ContinueTask}|null>(null)
 const action=task.state==='recoverable'||task.state==='failed'?'recover':'resume'
 // A paused task can retain historical checkpoint evidence. Only operator_paused
 // is itself the current pause boundary; an older blocker is not current.
 const currentCheckpoint=task.state==='awaiting_operator'?task.checkpoint:null
 const safePauseCheckpoint=task.state==='paused'&&task.checkpoint==='operator_paused'?task.checkpoint:null
 const requiresNewWeekReview=task.state==='awaiting_operator'&&currentCheckpoint==='week_schedule_review_required'
 const driver=storedDriverEvidence(task)
 const calendarHandoff=taskCalendarHandoff(task)
 const isCurrentDriverBlocker=task.state==='awaiting_operator' && driver?.checkpoint===task.checkpoint
 const mutation=useMutation({
  mutationFn:(snapshot:{target:ServerTask;body:ContinueTask})=>continueServerTask(snapshot.target,snapshot.body),
  onSuccess:async (_ack,snapshot)=>{
   setPending(current=>current?.body.request_id===snapshot.body.request_id?null:current)
   setReason('')
   await client.invalidateQueries({queryKey:['server-simulation-tasks']})
   await client.invalidateQueries({queryKey:['authoritative-full-simulation-pending',snapshot.target.run_id,snapshot.target.branch_id]})
  }
 })
 const terminal=['stopped','target_reached','complete'].includes(task.state)
 return <li className="server-simulation-tasks__item" data-task-id={task.task_id} aria-current={focused?'location':undefined}>
  {focused&&<p role="status">{t.selected}: <code>{task.task_id}</code></p>}
  <strong>{task.run_name} / {task.branch_name}</strong> · <span>{t[task.state as keyof typeof t]??task.state}</span>
  <p><code>{task.task_id}</code> · {t.original}: <code>{task.parent_command_id}</code></p>
  {task.desired_state!==task.state&&<p>{t.desired}: <code>{task.desired_state}</code></p>}
  <p>{t.health}: {t[task.heartbeat_health]}{task.heartbeat_unix>0 && <> · {new Date(task.heartbeat_unix*1000).toLocaleString(language)}</>}</p>
  {task.lease_expires_at_unix!==null&&<p>{t.lease}: {new Date(task.lease_expires_at_unix*1000).toLocaleString(language)}</p>}
  {task.effective_boundary_target && <p><BoundaryDescription target={task.effective_boundary_target}/></p>}
  {task.current_week && <p>S{task.current_week.season_index} W{task.current_week.week}</p>}
  <p>{task.progress_evidence.kind==='terminal_frozen'?t.frozen:task.progress_evidence.kind==='unavailable'?t.unavailable:t.measured}</p>
  {task.progress_evidence.weeks_advanced_since_start!==null && <p>{t.advanced}: {task.progress_evidence.weeks_advanced_since_start}</p>}
  {task.progress_evidence.kind==='live_branch' && <p>{t.slots}: {task.progress_evidence.completed_slot_receipts_this_week} · {t.groups}: {task.progress_evidence.committed_group_receipts_this_week}</p>}
  {currentCheckpoint && <p>{t.checkpoint}: <code>{currentCheckpoint}</code></p>}
  {safePauseCheckpoint && <p>{t.pauseCheckpoint}: <code>{safePauseCheckpoint}</code></p>}
  {task.checkpoint&&!currentCheckpoint&&!safePauseCheckpoint && <details><summary>{t.lastCheckpoint}</summary><code>{task.checkpoint}</code></details>}
  {driver && (driver.detail||driver.blockers.length>0||driver.checkpoint) && <details open={isCurrentDriverBlocker}>
   <summary>{t.driverDetail}{isCurrentDriverBlocker?' · '+t.currentBlockers:''}</summary>
   {driver.detail&&<p>{driver.detail}</p>}
   {driver.blockers.length>0&&<><p>{isCurrentDriverBlocker?t.currentBlockers:t.blockers}:</p>
    <ul>{driver.blockers.map((blocker,i)=><li key={i}><code>{blocker}</code></li>)}</ul></>}
   {driver.checkpoint && driver.checkpoint!==currentCheckpoint&&<p>{t.lastCheckpoint}: <code>{driver.checkpoint}</code></p>}
  </details>}
  {task.error && <p role="alert">{task.error}</p>}
  {calendarHandoff && <p><Link to={calendarHandoff}>{t.calendarPrep}</Link> · {t.calendarPrepNote}</p>}
  {task.needs_operator_action && <>{requiresNewWeekReview
   ? <p role="alert">{checkpointGuidance(task.checkpoint,language)}</p>
   : <><p>{t.manual}</p>{task.state==='awaiting_operator' && <p>{checkpointGuidance(currentCheckpoint,language)}</p>}
   <label>{t.operator}<input value={operator} disabled={!!pending} onChange={e=>setOperator(e.target.value)}/></label>
   <label>{t.reason}<input value={reason} disabled={!!pending} onChange={e=>setReason(e.target.value)}/></label>
   <button type="button" disabled={!operator.trim()||!reason.trim()||mutation.isPending} onClick={()=>{
     const snapshot=pending??{target:task,body:{request_id:crypto.randomUUID(),action,expected_revision:task.revision,operator_label:operator.trim(),audit_reason:reason.trim()}}
     setPending(snapshot);mutation.mutate(snapshot)
   }}>{pending?t.retry:action==='recover'?t.recover:t.resume}</button>
   {pending && !mutation.isPending && <button type="button" onClick={()=>{setPending(null);mutation.reset();void client.invalidateQueries({queryKey:['server-simulation-tasks']})}}>{t.cancel}</button>}
  </>}</>}
  {mutation.error && <p role="alert">{formatApiError(mutation.error)}</p>}
  {requiresNewWeekReview && <FullSimulationWeekScheduleReview runId={task.run_id} branchId={task.branch_id} taskId={task.task_id} taskRevision={task.revision}/>}
  <Link to={`/admin/runs/${encodeURIComponent(task.run_id)}/simulate?branch=${encodeURIComponent(task.branch_id)}&task=${encodeURIComponent(task.task_id)}`}>{t.open}</Link>
  {terminal && <details><summary>{t.detail}</summary><FullSimulationSummary runId={task.run_id} branchId={task.branch_id} commandId={task.parent_command_id}/></details>}
 </li>
}
export function FullSimulationServerTasks({runId,branchId}:{runId?:string;branchId?:string}){
 const {language}=useLanguage();const t=copy[language];const query=useServerTasks(runId,branchId)
 const [searchParams]=useSearchParams()
 const focusedTaskId=runId&&branchId?searchParams.get('task'):null
 const [search,setSearch]=useState('')
 const [category,setCategory]=useState<'all'|'attention'|'live'|'other'>('all')
 // A filter from a different Run/Branch must not hide this scope's tasks.
 useEffect(()=>{setSearch('');setCategory('all')},[runId,branchId])
 const normalized=search.trim().toLocaleLowerCase()
 const liveStates=['queued','active','pause_requested']
 const taskPriority=(task:ServerTask)=>
   task.task_id===focusedTaskId?-1:task.needs_operator_action?0:liveStates.includes(task.state)?1:2
 const tasks=query.data?[...query.data].sort((a,b)=>taskPriority(a)-taskPriority(b)):undefined
 const needingAction=tasks?.filter(task=>task.needs_operator_action).length??0
 const liveOrQueued=tasks?.filter(task=>!task.needs_operator_action&&liveStates.includes(task.state)).length??0
 const otherStates=(tasks?.length??0)-needingAction-liveOrQueued
 const displayed=tasks?.filter(task=>{
  if(focusedTaskId===task.task_id)return true
  const categoryMatch=category==='all'||(category==='attention'&&task.needs_operator_action)||
   (category==='live'&&!task.needs_operator_action&&liveStates.includes(task.state))||
   (category==='other'&&!task.needs_operator_action&&!liveStates.includes(task.state))
  if(!categoryMatch)return false
  const terms=[task.run_id,task.run_name,task.branch_id,task.branch_name,
   task.task_id,task.parent_command_id,task.checkpoint??''].join(' ').toLocaleLowerCase()
  return terms.includes(normalized)
 })
 const filtered=Boolean(normalized||category!=='all')
 return <section className="server-simulation-tasks" aria-label={t.title}><h3>{t.title}</h3><p>{t.truth}</p>
  <button type="button" onClick={()=>void query.refetch()} disabled={query.isFetching}>{t.refresh}</button>
  <div className="server-simulation-tasks__filters">
   <label>{t.search}<input type="search" aria-label={t.search} placeholder={t.searchHint} value={search} onChange={e=>setSearch(e.target.value)}/></label>
   <label>{t.filter}<select aria-label={t.filter} value={category} onChange={e=>setCategory(e.target.value as 'all'|'attention'|'live'|'other')}>
    <option value="all">{t.allTasks}</option><option value="attention">{t.attentionTasks}</option>
    <option value="live">{t.liveTasks}</option><option value="other">{t.otherTasks}</option>
   </select></label>
   {filtered&&<button type="button" onClick={()=>{setSearch('');setCategory('all')}}>{t.clearFilters}</button>}
  </div>
  {query.isPending && <p role="status">{t.loading}</p>}
  {query.error && <p role="alert">{formatApiError(query.error)}</p>}
  {query.isSuccess&&Boolean(tasks?.length)&&<p role="status">{t.needsCount}: {needingAction} · {t.liveCount}: {liveOrQueued} · {t.otherCount}: {otherStates}</p>}
  {query.isSuccess&&focusedTaskId&&!query.data.some(task=>task.task_id===focusedTaskId)&&<p role="alert">{t.missing} <code>{focusedTaskId}</code></p>}
  {query.isSuccess&&filtered&&<p className="status">{t.shown}: {displayed?.length??0} / {tasks?.length??0}</p>}
  {query.isSuccess&&filtered&&focusedTaskId&&displayed?.some(task=>task.task_id===focusedTaskId)&&<p className="status">{t.pinned}</p>}
  {query.isSuccess && (displayed?.length?<ul className="server-simulation-tasks__list">{displayed.map(task=><TaskCard key={JSON.stringify([task.run_id,task.branch_id,task.task_id])} task={task} focused={task.task_id===focusedTaskId}/>)}</ul>:<p>{tasks?.length?t.noMatches:t.empty}</p>)}
 </section>
}
