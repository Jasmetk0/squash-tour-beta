import { useEffect,useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getServerTasks } from '../api/fullSimulationTasks'
import { useLanguage } from '../i18n/LanguageContext'
import {clearMonitorNotices,dismissMonitorNotice,isTerminalTask,loadMonitorNotices,observeMonitorTasks,storeMonitorNotices,taskNoticeKey} from './simulationMonitorNotices'

const preferenceKey='squash-engine-simulation-monitor-v1'
const readPreference=()=>{
  try{return sessionStorage.getItem(preferenceKey)==='on'}catch{return false}
}
const candidateStates=new Set(['queued','active','pause_requested','ownership_unverified'])
const stateText:Record<string,[string,string]>={
  queued:['Ve frontě','Queued'],
  active:['Aktivní stav úlohy','Active task state'],
  pause_requested:['Požadována pauza','Pause requested'],
  ownership_unverified:['Vlastnictví nepotvrzeno','Ownership unverified'],
  paused:['Pozastaveno','Paused'],awaiting_operator:['Čeká na operátora','Waiting for operator'],
  recoverable:['Vyžaduje výslovné obnovení','Explicit recovery required'],failed:['Selhalo','Failed']
}

/** Opt-in, foreground-only reader. The global inventory can be expensive.
 * Share the existing global Task Center cache; never start/recover a task here.
 */
export function AdminSimulationMonitor():JSX.Element{
  const {language}=useLanguage(),cs=language==='cs'
  const [watching,setWatching]=useState(readPreference)
  const [ledger,setLedger]=useState(loadMonitorNotices)
  const q=useQuery({
    queryKey:['server-simulation-tasks',null,null],
    queryFn:()=>getServerTasks(),
    enabled:watching,retry:false,staleTime:30_000,refetchInterval:30_000,
    refetchIntervalInBackground:false,refetchOnWindowFocus:false
  })
  function toggle(){
    const next=!watching
    try{sessionStorage.setItem(preferenceKey,next?'on':'off')}catch{/* local session only */}
    if(!next)setLedger(clearMonitorNotices())
    setWatching(next)
  }
  const observed=watching&&q.isSuccess?q.data:null
  // Only successful observations can produce notices. No additional poll or
  // terminal-summary read happens until the operator follows the exact link.
  useEffect(()=>{
    if(observed&&!q.isFetching)setLedger(previous=>observeMonitorTasks(previous,observed))
  },[observed,q.isFetching])
  useEffect(()=>{if(watching)storeMonitorNotices(ledger)},[ledger,watching])
  const terminalNotices=observed?.filter(task=>isTerminalTask(task)&&ledger.notices.includes(taskNoticeKey(task)))??[]
  const candidates=observed?.filter(t=>candidateStates.has(t.state))??[]
  const needsAction=observed?.filter(t=>t.needs_operator_action)??[]
  // Do not choose between conflicting task claims or infer a running process.
  const selected=candidates.length===1?candidates[0]:
    candidates.length===0&&needsAction.length===1?needsAction[0]:null
  return <section aria-label={cs?'Sledování simulací':'Simulation monitor'} className="app-header__tasks" style={{maxWidth:"20rem",whiteSpace:"normal",overflowWrap:"anywhere"}}>
    <button type="button" aria-pressed={watching} onClick={toggle}>
      {watching?(cs?'Vypnout sledování':'Disable monitoring'):(cs?'Sledovat simulace':'Monitor simulations')}
    </button>
    {watching&&<div>
      <small className="status">{cs?'Obnova po 30 s v aktivní kartě; údaje nejsou důkazem běžícího procesu.':
        'Refresh every 30 s in the active tab; evidence is not proof of a running process.'}</small>
      {q.isError?<p role="status">{cs?'Údaje simulací nedostupné.':'Simulation evidence unavailable.'}</p>:
        !observed?<p role="status">{cs?'Načítám údaje úloh…':'Loading task evidence…'}</p>:<>
        {selected&&<div>
          <strong>{selected.run_name} / {selected.branch_name}</strong>
          <p className="status">{stateText[selected.state]?.[cs?0:1]??selected.state}
            {selected.current_week&&<> · S{selected.current_week.season_index+1} W{selected.current_week.week}</>}
            {selected.heartbeat_health==='stale'&&<> · {cs?'Zastaralý heartbeat':'Stale heartbeat'}</>}
          </p>
          <Link to={`/admin/runs/${encodeURIComponent(selected.run_id)}/simulate?branch=${encodeURIComponent(selected.branch_id)}&task=${encodeURIComponent(selected.task_id)}`}>
            {cs?'Otevřít přesnou úlohu':'Open exact task'}
          </Link>
        </div>}
        {candidates.length>1&&<p role="status">{cs?'Více kandidátů aktivní úlohy; nelze bezpečně vybrat jedinou.':
          'Multiple candidate active tasks; cannot safely select one.'}</p>}
        {needsAction.length>0&&<p>{cs?'Úlohy vyžadující zásah':'Tasks requiring action'}: {needsAction.length}</p>}
        {candidates.length===0&&needsAction.length===0&&<p>{cs?'Poslední čtení neobsahuje aktivní ani zásah vyžadující serverové úlohy.':
          'Last read contains no active or action-required server tasks.'}</p>}
        {terminalNotices.length>0&&<div aria-label={cs?'Oznámení simulací':'Simulation notices'} role="region">
          <p role="status">{cs?'Nově pozorované ukončené úlohy':'Newly observed terminal tasks'}: {terminalNotices.length}</p>
          {terminalNotices.slice(0,3).map(task=><div key={taskNoticeKey(task)}>
            <strong>{task.run_name} / {task.branch_name}</strong>
            <p>{task.state==='complete'?(cs?'Simulace dokončena':'Simulation completed'):
              task.state==='target_reached'?(cs?'Dosažen cíl simulace':'Simulation target reached'):
              (cs?'Simulace ukončena':'Simulation stopped')}</p>
            <Link to={`/admin/runs/${encodeURIComponent(task.run_id)}/simulate?branch=${encodeURIComponent(task.branch_id)}&task=${encodeURIComponent(task.task_id)}&summary=1`}>
              {cs?'Zobrazit souhrn':'View summary'}
            </Link>{' '}
            <button type="button" aria-label={(cs?'Skrýt oznámení ':'Dismiss notice ')+task.task_id}
              onClick={()=>setLedger(previous=>dismissMonitorNotice(previous,taskNoticeKey(task)))}>
              {cs?'Skrýt':'Dismiss'}</button>
          </div>)}
          {terminalNotices.length>3&&<p>{cs?'Další ukončené úlohy najdeš v centru úloh.':'See more terminal tasks in Task Center.'}</p>}
        </div>}
        <small>{cs?'Poslední načtení':'Last read'}: {new Date(q.dataUpdatedAt).toLocaleTimeString(language)}
          {q.isFetching&&<> · {cs?'Obnovuji…':'Refreshing…'}</>}</small>
      </>}
      <div><Link to="/admin/operations">{cs?'Otevřít centrum úloh':'Open Task Center'}</Link></div>
    </div>}
  </section>
}
