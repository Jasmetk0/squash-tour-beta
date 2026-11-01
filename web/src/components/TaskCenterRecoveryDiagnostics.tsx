import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { GlobalFullSimulationOperations } from '../api/types'
import type { ServerTask } from '../api/fullSimulationTasks'
import { useLanguage } from '../i18n/LanguageContext'
import {
  buildTaskCenterRecoveryDiagnostics, serializeTaskCenterRecoveryDiagnostics,
  type TaskDiagnosticPriority
} from '../pages/taskCenterRecoveryDiagnostics'

const labels={
  cs:{
    title:'Diagnostika obnovy Full Simulation',
    notice:'Dva samostatně uložené pohledy (serverové úlohy a starší pending receipts). Nejde o atomický snímek, potvrzení běžícího workeru ani oprávnění pokračovat.',
    unavailable:'Aktuální společný přehled nelze ověřit. Při načítání nebo chybě se starý výsledek nezobrazuje ani neexportuje.',
    invalid:'Záznamy nejsou vzájemně důvěryhodné:',
    task:'Serverové úlohy',attention:'Vyžadují operátora',stale:'Starý heartbeat (nikoli potvrzený pád)',
    expired:'Možné lease/recovery potíže',receipts:'Starší pending receipts',
    unmatched:'Bez prokázané serverové úlohy',ambiguous:'Nejednoznačné přiřazení',
    unverified:'Starší neověřitelné pending receipts',
    show:'Zobrazit podrobnosti',export:'Stáhnout diagnostiku JSON',
    run:'Run / Branch',state:'Uložený stav',priority:'Signál',
    command:'Původní příkaz',checkpoint:'Checkpoint',week:'Pozice',
    inspect:'Otevřít řízení ve správné Branch',
    operator_action:'Vyžaduje rozhodnutí operátora',
    stale_heartbeat:'Heartbeat je starý, aktivita procesu neověřena',
    lease_expired:'Neaktivní/obnovitelný úkol s lease metadaty',
    active_unconfirmed:'Povolený/připravený, proces nepotvrzen',
    not_active:'Není aktivní podle uloženého stavu',
    noTasks:'Žádná serverová úloha v tomto snímku.',
    caution:'Neprovádí Resume, Restart, Stop, Save ani žádné změny. Detail musí znovu ověřit přístup, Run, Branch a revizi.',
    noFresh:'Dostupné pouze po úspěšném současném načtení obou validovaných inventářů.'
  },
  en:{
    title:'Full Simulation recovery diagnostics',
    notice:'Two independently persisted inventories (server tasks and older pending receipts). Not an atomic snapshot, worker-liveness proof or continuation approval.',
    unavailable:'A current joint view is not verified. While loading or after an error, cached results are neither shown nor exported.',
    invalid:'The records cannot be reconciled safely:',
    task:'Server tasks',attention:'Need operator action',stale:'Stale heartbeat (not a proven crash)',
    expired:'Potential lease/recovery issues',receipts:'Older pending receipts',
    unmatched:'No confirmed server task',ambiguous:'Ambiguous parent matching',
    unverified:'Older receipts without recovery evidence',
    show:'Show details',export:'Download diagnostics JSON',
    run:'Run / Branch',state:'Persisted state',priority:'Signal',
    command:'Original command',checkpoint:'Checkpoint',week:'Position',
    inspect:'Open controls in exact Branch',
    operator_action:'Needs operator decision',
    stale_heartbeat:'Stale heartbeat; worker activity unverified',
    lease_expired:'Non-active/recoverable task with lease metadata',
    active_unconfirmed:'Authorized/queued; process unconfirmed',
    not_active:'Not active in persisted view',
    noTasks:'No server task in this snapshot.',
    caution:'No Resume, Restart, Stop, Save or mutation. Detail must re-check the Run, Branch, permissions and revision.',
    noFresh:'Available only when both validated inventories have loaded successfully.'
  }
} as const

function guardedFileName():string {
  return 'squash-full-simulation-task-diagnostics.json'
}

export function TaskCenterRecoveryDiagnostics({
  tasks, inventory, fresh
}:{
  tasks:readonly ServerTask[]|null
  inventory:GlobalFullSimulationOperations|null
  fresh:boolean
}):JSX.Element{
  const {language}=useLanguage()
  const t=labels[language]
  const [open,setOpen]=useState(false)
  const [priority,setPriority]=useState<TaskDiagnosticPriority|'all'>('all')
  const derived=useMemo(()=>{
    if(!fresh || !tasks || !inventory)return null
    try {return {report:buildTaskCenterRecoveryDiagnostics(tasks,inventory),error:null}}
    catch(e){return {report:null,error:e instanceof Error?e.message:'Invalid persisted evidence'}}
  },[fresh,tasks,inventory])
  const report=derived?.report
  const exportFile=()=>{
    if(!fresh || !report)return
    const bytes=serializeTaskCenterRecoveryDiagnostics(report)
    const objectURL=URL.createObjectURL(new Blob([bytes],{type:'application/json;charset=utf-8'}))
    const a=document.createElement('a')
    try{
      a.href=objectURL;a.download=guardedFileName()
      document.body.appendChild(a);a.click()
    }finally{a.remove();URL.revokeObjectURL(objectURL)}
  }
  const displayed=report?.tasks.filter(item=>priority==='all'||item.priority===priority)??[]
  return <section className="run-home-status-block" aria-label={t.title}>
    <h3>{t.title}</h3>
    <p className="status">{t.notice}</p>
    {!fresh && <p role="status">{t.unavailable}</p>}
    {fresh&&derived?.error&&<p role="alert" className="error">{t.invalid} {derived.error}</p>}
    {fresh&&report&&<>
      <p className="status">{t.task}: {report.task_count} · {t.attention}: {report.operator_action_count}
      {' · '}{t.stale}: {report.stale_heartbeat_count}
      {' · '}{t.expired}: {report.expired_lease_count}</p>
      <p className="status">{t.receipts}: {report.legacy_receipt_count}
      {' · '}{t.unmatched}: {report.unmatched_legacy_receipt_count}
      {' · '}{t.ambiguous}: {report.ambiguous_legacy_receipt_count}
      {' · '}{t.unverified}: {report.unknown_legacy_count}</p>
      <button type="button" aria-expanded={open} onClick={()=>setOpen(v=>!v)}>{t.show}</button>
      {' '}
      <button type="button" onClick={exportFile}>{t.export}</button>
      {open&&<div>
        <p className="status">{t.caution}</p>
        <label htmlFor="task-recovery-priority">{t.priority}</label>
        <select id="task-recovery-priority" value={priority}
          onChange={e=>setPriority(e.target.value as TaskDiagnosticPriority|'all')}>
          <option value="all">{t.task}</option>
          {([
            'operator_action','stale_heartbeat','lease_expired','active_unconfirmed','not_active'
          ] as TaskDiagnosticPriority[]).map(k=><option key={k} value={k}>{t[k]}</option>)}
        </select>
        {displayed.length===0?<p>{t.noTasks}</p>:
          <ul>{displayed.map(item=><li key={item.task_id}>
            <strong>{item.run_name} / {item.branch_name}</strong>
            <p>{t.state}: {item.state} · {t.priority}: {t[item.priority]}</p>
            <p>{t.command}: <code>{item.parent_command_id}</code></p>
            <p>{t.checkpoint}: <code>{item.checkpoint??'—'}</code>
              {' · '}{t.week}: {item.week?'S'+item.week.season_index+' W'+item.week.week:'—'}</p>
            <Link to={'/admin/runs/'+encodeURIComponent(item.run_id)+'/simulate?branch='
              +encodeURIComponent(item.branch_id)+'&task='+encodeURIComponent(item.task_id)}>
              {t.inspect}</Link>
          </li>)}</ul>}
      </div>}
    </>}
    {!fresh&&<p className="status">{t.noFresh}</p>}
  </section>
}
