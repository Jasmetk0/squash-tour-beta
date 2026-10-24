import {useEffect,useRef,useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {Link} from 'react-router-dom'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import {nativeClosureAction,nativeClosureReview,nativeTaskCommand,nativeTaskControl,nativeTaskSummary,nativeSeasonReview,nativeSeasonApprove,previewNativeTask} from '../api/fullSimulationTasksNative'
import type {NativeClosureAction,NativeClosureReview,NativeTaskPreview,NativeSeasonReview} from '../api/fullSimulationTasksNative'
import type {ServerTask} from '../api/fullSimulationTasks'
import {StartServerTask} from './FullSimulationServerTasks'

export function NativeFullSimulationPanel({runId,branchId,head,saved}:{runId:string;branchId:string;head:string;saved:boolean}){
 const cs=useLanguage().language==='cs'
 const [target,setTarget]=useState('run'),[season,setSeason]=useState('1'),[week,setWeek]=useState('1')
 const [seed,setSeed]=useState('231'),[operator,setOperator]=useState(''),[reason,setReason]=useState('')
 const [preview,setPreview]=useState<NativeTaskPreview|null>(null),[error,setError]=useState<string|null>(null),[busy,setBusy]=useState(false),[consent,setConsent]=useState(false)
 const generation=useRef(0),scope=useRef('')
 const context=[runId,branchId,head].join('|')
 if(scope.current!==context){scope.current=context;generation.current++}
 const edit=()=>{generation.current++;setPreview(null);setConsent(false);setError(null)}
 const review=async()=>{
  const stamp=++generation.current;setBusy(true);setError(null);setPreview(null);setConsent(false)
  try{
   const value=await previewNativeTask({schema_version:'authoritative_full_simulation_command.v2',run_id:runId,branch_id:branchId,
    command_id:'native-full-'+crypto.randomUUID(),seed:Number(seed),operator_label:operator.trim(),audit_reason:reason.trim(),
    target_week:target==='run'?null:{season_index:Number(season)-1,week:Number(week)}})
   if(generation.current===stamp&&scope.current===context)setPreview(value)
  }catch(e){if(generation.current===stamp)setError(formatApiError(e))}
  finally{if(scope.current===context)setBusy(false)}
 }
 return <section aria-label="Native Full Simulation">
  <h3>{cs?'Full Simulation · kalendář Runu':'Full Simulation · Run calendar'}</h3>
  <p>{cs?'Server odehraje podporované sportovní operace. Při ručním rozhodnutí nebo neuložené změně počká na zásah a výslovné pokračování stejné úlohy.':'The server executes supported sporting operations. Manual decisions and unsaved changes wait for operator action and explicit continuation of the same task.'}</p>
  {!saved&&<p>{cs?'Před náhledem proveďte ruční Save.':'Save manually before reviewing.'}</p>}
  <label>{cs?'Cíl':'Target'}<select aria-label="Native simulation target" value={target} onChange={e=>{setTarget(e.target.value);edit()}}>
   <option value="run">{cs?'Původní konec Runu':'Original Run end'}</option><option value="week">{cs?'Otevření zvoleného týdne':'Open selected week'}</option>
  </select></label>
  {target==='week'&&<><label>{cs?'Pořadí sezony (od 1)':'Season number (from 1)'}<input aria-label="Native target season" value={season} type="number" min="1" onChange={e=>{setSeason(e.target.value);edit()}}/></label>
   <label>{cs?'Týden sezony':'Season week'}<input aria-label="Native target week" value={week} type="number" min="1" onChange={e=>{setWeek(e.target.value);edit()}}/></label></>}
  <label>Seed<input aria-label="Native simulation seed" value={seed} onChange={e=>{setSeed(e.target.value);edit()}}/></label>
  <label>{cs?'Operátor':'Operator'}<input aria-label="Native simulation operator" maxLength={128} value={operator} onChange={e=>{setOperator(e.target.value);edit()}}/></label>
  <label>{cs?'Důvod':'Reason'}<input aria-label="Native simulation reason" maxLength={1000} value={reason} onChange={e=>{setReason(e.target.value);edit()}}/></label>
  <button disabled={busy||!saved||!operator.trim()||!reason.trim()||!/^\d+$/.test(seed)||!Number.isSafeInteger(Number(seed))||
   (target==='week'&&(!Number.isSafeInteger(Number(season))||Number(season)<1||!Number.isSafeInteger(Number(week))||Number(week)<1))}
   onClick={()=>void review()}>{cs?'Zkontrolovat serverovou simulaci':'Review server simulation'}</button>
  {error&&<p role="alert">{error}</p>}
  {preview&&scope.current===context&&<div>
   <p>W{preview.execution_calendar.weeks_per_year} · {cs?'Počáteční rok':'Start year'} {preview.execution_calendar.start_year} · {cs?'Počátek sezony v týdnu roku':'Season starts at year week'} {preview.execution_calendar.season_start_year_week} · {cs?'Sezon':'Seasons'} {preview.execution_calendar.season_count}</p>
   <p>{cs?'Původní Saved zdroj':'Original Saved source'}: <code>{preview.expected_revision_id}</code></p>
   <p>{cs?'Cíl':'Target'}: {preview.target_week?`S${preview.target_week.season_index+1} W${preview.target_week.week}`:cs?'Uložené uzavření Runu':'Saved Run closure'}</p>
   <label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>{cs?'Výslovně potvrzuji tento rozsah a serverové spuštění.':'I explicitly confirm this scope and server execution.'}</label>
   <StartServerTask runId={runId} branchId={branchId} command={nativeTaskCommand(preview)} disabled={!consent||!saved} onAccepted={()=>{setConsent(false)}}/>
  </div>}
 </section>
}

export function NativeTaskActions({task}:{task:ServerTask}){
 const cs=useLanguage().language==='cs',client=useQueryClient()
 const [operator,setOperator]=useState(''),[reason,setReason]=useState(''),[review,setReview]=useState<NativeClosureReview|null>(null)
 const [approved,setApproved]=useState(false),[consent,setConsent]=useState(false),[saved,setSaved]=useState(false)
 const [error,setError]=useState<string|null>(null),[reading,setReading]=useState(false)
 const [seasonReview,setSeasonReview]=useState<NativeSeasonReview|null>(null)
 const active=useRef(task);active.current=task
 type Request={kind:'approve'|'save'|'season-approve';body:NativeClosureAction}|{kind:'pause'|'stop';id:string;operator:string;reason:string}
 const [frozen,setFrozen]=useState<Request|null>(null)
 const mutation=useMutation({mutationFn:async(snapshot:Request)=>{
  const result='body' in snapshot
   ?snapshot.kind==='season-approve'?await nativeSeasonApprove(task,snapshot.body):await nativeClosureAction(task.run_id,task.branch_id,task.parent_command_id,snapshot.kind,snapshot.body)
   :await nativeTaskControl(task.run_id,task.branch_id,task.parent_command_id,snapshot.kind,snapshot.operator,snapshot.reason,snapshot.id)
  return {result,snapshot}
 },onSuccess:async({snapshot})=>{
  setFrozen(null);setConsent(false)
  if(snapshot.kind==='approve'||snapshot.kind==='season-approve')setApproved(true)
  if(snapshot.kind==='save')setSaved(true)
  await client.invalidateQueries({queryKey:['server-simulation-tasks']})
 }})
 const reviewContext=[task.revision,task.state,task.checkpoint].join('|')
 useEffect(()=>{if(!frozen){setReview(null);setSeasonReview(null);setApproved(false);setSaved(false);setConsent(false)}},[reviewContext])
 const submit=(kind:Request['kind'])=>{
  const snapshot:Request=frozen??(kind==='approve'||kind==='save'||kind==='season-approve'
   ?{kind,body:{request_id:crypto.randomUUID(),review_fingerprint:(kind==='season-approve'?seasonReview!:review!).review_fingerprint,operator_label:operator.trim(),audit_reason:reason.trim(),explicit_confirmation:true}}
   :{kind,id:'native-control-'+crypto.randomUUID(),operator:operator.trim(),reason:reason.trim()})
  setFrozen(snapshot);mutation.mutate(snapshot)
 }
 const terminal=['complete','stopped','target_reached'].includes(task.state)
 const closing=task.state==='awaiting_operator'&&task.checkpoint==='native_final_closure_review_required'
 const dirtyInputs=!operator.trim()||!reason.trim()
 return <section aria-label="Native task actions">
  <p><Link to={`/admin/runs/${encodeURIComponent(task.run_id)}/tour/editions?branch=${encodeURIComponent(task.branch_id)}`}>{cs?'Otevřít nativní Tour a ruční Save':'Open native Tour and manual Save'}</Link></p>
  {!terminal&&<>
   <label>{cs?'Operátor řízení':'Control operator'}<input aria-label="Native task control operator" disabled={!!frozen} value={operator} onChange={e=>{setOperator(e.target.value);setConsent(false)}}/></label>
   <label>{cs?'Důvod řízení':'Control reason'}<input aria-label="Native task control reason" disabled={!!frozen} value={reason} onChange={e=>{setReason(e.target.value);setConsent(false)}}/></label>
   <button disabled={dirtyInputs||!!frozen||mutation.isPending||!['queued','active','awaiting_operator','ownership_unverified','pause_requested'].includes(task.state)} onClick={()=>submit('pause')}>{cs?'Bezpečně pozastavit':'Pause safely'}</button>
   <button disabled={dirtyInputs||!!frozen||mutation.isPending} onClick={()=>submit('stop')}>{cs?'Ukončit úlohu':'Stop task'}</button>
  </>}
  {closing&&<>
   <button disabled={reading||mutation.isPending||!!frozen} onClick={()=>{
    const expected=task;setReading(true);setError(null);setApproved(false);setSaved(false);setConsent(false);setReview(null)
    void nativeClosureReview(task.run_id,task.branch_id,task.parent_command_id).then(value=>{
     if(active.current.task_id===expected.task_id&&active.current.revision===expected.revision)setReview(value)
    }).catch(e=>setError(formatApiError(e))).finally(()=>setReading(false))
   }}>{cs?'Zkontrolovat závěrečné uzavření':'Review final closure'}</button>
   {review&&<div>
    <p>{cs?'Skutečně odehrané zápasy':'Actually played matches'}: {review.season_summary.played_match_count} · {cs?'Udělené body':'Awarded points'}: {review.season_summary.awarded_points}</p>
    <p>{cs?'Samostatný Closing Ranking':'Separate Closing Ranking'}: {review.closing_ranking.rows.length} {cs?'hráčů':'players'}</p>
    <table aria-label="Final Closing Ranking"><thead><tr><th>#</th><th>{cs?'Hráč':'Player'}</th><th>{cs?'Body':'Points'}</th></tr></thead><tbody>{review.closing_ranking.rows.map(row=><tr key={row.player_id}><td>{row.rank}</td><td>{row.player_id}</td><td>{row.points}</td></tr>)}</tbody></table>
    <p>{cs?'Žádný další týden se neotevře.':'No following week will open.'}</p>
    <label><input aria-label="Native closure consent" type="checkbox" disabled={!!frozen} checked={consent} onChange={e=>setConsent(e.target.checked)}/>{cs?'Potvrzuji zkontrolované uzavření.':'I confirm the reviewed closure.'}</label>
    {!approved?<button disabled={!consent||dirtyInputs||!!frozen||mutation.isPending} onClick={()=>submit('approve')}>{cs?'Schválit uzavření':'Approve closure'}</button>
     :!saved?<button disabled={!consent||dirtyInputs||!!frozen||mutation.isPending} onClick={()=>submit('save')}>{cs?'Ručně uložit závěrečné uzavření':'Manually Save final closure'}</button>
     :<p role="status">{cs?'Uzavření je uložené. Výslovně pokračujte ve stejné úloze.':'Closure is Saved. Explicitly continue this same task.'}</p>}
   </div>}
  </>}
  {task.state==='awaiting_operator'&&task.checkpoint==='native_season_transition_review_required'&&<>
   <button disabled={reading||mutation.isPending||!!frozen} onClick={()=>{
    const expected=task;setReading(true);setError(null);setApproved(false);setConsent(false);setSeasonReview(null)
    void nativeSeasonReview(task).then(value=>{if(active.current.task_id===expected.task_id&&active.current.revision===expected.revision)setSeasonReview(value)})
     .catch(e=>setError(formatApiError(e))).finally(()=>setReading(false))
   }}>{cs?'Zkontrolovat sezonní přechod úlohy':'Review task Season Transition'}</button>
   {seasonReview&&<div>
    <p>{cs?'Samostatný odcházející Closing Ranking':'Separate outgoing Closing Ranking'}: {seasonReview.outgoing_season_closure.closing_ranking.rows.length} {cs?'hráčů':'players'}</p>
    <p>{cs?'Otevře se':'Will open'} S{seasonReview.preview.impact.target_week.season_index+1} W1</p>
    {!approved?<><label><input aria-label="Native season transition consent" type="checkbox" checked={consent} disabled={!!frozen} onChange={e=>setConsent(e.target.checked)}/>{cs?'Potvrzuji zkontrolovaný Season Transition.':'I confirm the reviewed Season Transition.'}</label>
     <button disabled={!consent||dirtyInputs||!!frozen||mutation.isPending} onClick={()=>submit('season-approve')}>{cs?'Schválit sezonní přechod úlohy':'Approve task Season Transition'}</button></>
     :<p role="status">{cs?'Přechod je schválený. Výslovně pokračujte ve stejné úloze.':'Transition is approved. Explicitly continue this same task.'}</p>}
   </div>}
  </>}
  {frozen&&mutation.isError&&<button disabled={mutation.isPending} onClick={()=>mutation.mutate(frozen)}>{cs?'Zopakovat původní požadavek':'Retry original request'}</button>}
  {(error||mutation.error)&&<p role="alert">{error??formatApiError(mutation.error)}</p>}
 </section>
}

export function NativeTaskSummary({task}:{task:ServerTask}){
 const cs=useLanguage().language==='cs'
 const query=useQuery({queryKey:['native-full-simulation-summary',task.run_id,task.branch_id,task.parent_command_id],queryFn:()=>nativeTaskSummary(task),retry:false})
 return <div>{query.isPending&&<p>{cs?'Načítám uložený souhrn…':'Loading stored summary…'}</p>}
  {query.error&&<p role="alert">{formatApiError(query.error)}</p>}
  {query.data&&<><p>{cs?'Sportovní příkazy úlohy':'Task sporting commands'}: {query.data.persisted_child_command_count}</p>
   <p>{cs?'Potvrzené turnaje odehrané touto úlohou':'Confirmed tournaments played by this task'}: {query.data.completed_tournaments.length}</p>
   <p>Saved Revision: <code>{query.data.terminal_saved_revision_id}</code></p></>}
 </div>
}
