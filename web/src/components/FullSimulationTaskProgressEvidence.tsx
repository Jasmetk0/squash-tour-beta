import type {ServerTask} from '../api/fullSimulationTasks'
import {serverTaskCalendar,taskWeekOrdinal,validTaskWeek} from '../api/fullSimulationTasksCalendar'

/** Original native target only. A clock distance is not work completed or ETA.
 * Never use an original target for legacy commands with mutable targets. */
function originalDistance(task:ServerTask){
  const command=task.original_command
  if(!('schema_version' in command)||command.schema_version!=='authoritative_full_simulation_command.v2'
    ||task.schema_version!=='full_simulation_task_view.v2'||task.effective_boundary_target
    ||command.run_id!==task.run_id||command.branch_id!==task.branch_id)return null
  try{
    const calendar=serverTaskCalendar(task)
    if(!Object.entries(calendar).every(([key,value])=>
      command.execution_calendar[key as keyof typeof calendar]===value))return null
    const target=command.target_week
    if(target===null)return {kind:'closure' as const}
    const p=task.progress_evidence
    if(!p||p.kind==='unavailable'||!validTaskWeek(p.week,calendar)
      ||!validTaskWeek(task.current_week,calendar)||!validTaskWeek(target,calendar)
      ||!validTaskWeek(command.expected_start_week,calendar))return null
    const start=taskWeekOrdinal(command.expected_start_week,calendar)
    const end=taskWeekOrdinal(target,calendar)
    const current=taskWeekOrdinal(p.week,calendar)
    if(current!==taskWeekOrdinal(task.current_week,calendar)||end<start||current<start
      ||current>end||p.weeks_advanced_since_start!==current-start)return null
    return {kind:'week' as const,target,advanced:current-start,total:end-start,remaining:end-current}
  }catch{return null}
}

export function FullSimulationTaskProgressEvidence({task,cs}:{task:ServerTask;cs:boolean}){
  const distance=originalDistance(task)
  // Only task control events; not match history or a process log.
  const recent=task.events.slice(-3).reverse()
  return <section aria-label={cs?'Doložený postup úlohy':'Recorded task progress'}>
    <h4>{cs?'Cíl a postup':'Target and progress'}</h4>
    {distance?.kind==='week'?<>
      <p>{cs?'Původní nativní cíl: otevřít':'Original native target: open'} S{distance.target.season_index+1} W{distance.target.week}</p>
      {distance.total>0&&<progress aria-label={cs?'Přechody do původního cílového týdne':'Week transitions to original target'}
        value={distance.advanced} max={distance.total}/>}
      <p>{cs?'Přechody týdnů':'Week transitions'}: {distance.advanced} / {distance.total}
        {' · '}{cs?'Vzdálenost k původnímu cíli':'Distance to original target'}: {distance.remaining}</p>
      {distance.remaining===0&&<p className="status">{cs?'Cílový týden je dosažen v doloženém časovém stavu; dokončení úlohy určuje její vlastní stav.':
        'The recorded clock has reached the target week; task completion is determined by its own status.'}</p>}
      <p className="status">{cs?'Ukazatel měří pouze přechody týdnů, nikoli objem hotové práce.':
        'This measures week transitions only, not the amount of work completed.'}</p>
    </>:distance?.kind==='closure'?<p>{cs?'Původní cíl: uložené uzavření Runu. Závěrečný Save nelze odvodit z počtu týdnů.':
      'Original target: Saved Run closure. Final Save cannot be inferred from week counts.'}</p>:
      <p className="status">{cs?'Ověřená vzdálenost k původnímu cíli není dostupná.':
        'Verified distance to the original target is unavailable.'}</p>}
    <p className="status">{cs?'Odhad zbývajícího času: nedostupný z tohoto zdroje.':
      'Remaining time estimate: unavailable from this source.'}</p>
    {recent.length>0&&<details>
      <summary>{cs?'Poslední uložené řídicí události':'Latest stored control events'} ({recent.length})</summary>
      <p className="status">{cs?'Záznamy řízení úlohy, ne průběžný log zápasů nebo důkaz zdraví workeru.':
        'Task control records, not a live match log or proof of worker health.'}</p>
      <ol>{recent.map(event=><li key={event.revision}>
        #{event.revision} · <code>{event.state}</code> · <code>{event.reason}</code>
        {' · '}{new Date(event.at_unix*1000).toLocaleString(cs?'cs-CZ':'en-US')}
      </li>)}</ol>
    </details>}
  </section>
}
