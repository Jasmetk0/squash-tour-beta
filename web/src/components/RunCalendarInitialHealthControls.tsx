import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {useEffect,useRef,useState} from 'react'
import {confirmCalendarInitialHealth,getCalendarInitialHealth,reviewCalendarInitialHealth,savePlayerHealthRevision} from '../api/client'
import {validateInitialHealthReview,validateInitialHealthView,validateInitialHealthSave,type InitialHealthRequest,type InitialHealthReview} from '../api/calendarInitialHealth'
import type {RunCalendarMetadata} from '../api/runCalendarCreation'
import {formatApiError} from '../utils/apiErrors'
import {acknowledgeSavedRunForm} from './RunNavigationSafeguard'

export function RunCalendarInitialHealthControls({runId,branchId,head,clock,population,playerIds,locale}: {
  runId:string;branchId:string;head:string;clock:RunCalendarMetadata;population:string;playerIds:string[];locale:'cs'|'en'
}):JSX.Element {
  const cs=locale==='cs',client=useQueryClient()
  const [review,setReview]=useState<InitialHealthReview|null>(null),[approved,setApproved]=useState(false)
  const [saveApproved,setSaveApproved]=useState(false),[error,setError]=useState('')
  const view=useQuery({queryKey:['calendar-initial-health',runId,branchId,head,population],retry:false,
    queryFn:async()=>validateInitialHealthView(await getCalendarInitialHealth(runId,branchId),runId,branchId,head,population,clock,playerIds)})
  const data=view.data
  const signature=JSON.stringify([runId,branchId,head,population,clock,playerIds,data?.draft_version,data?.health_fingerprint])
  const current=useRef(signature);current.current=signature
  useEffect(()=>{setReview(null);setApproved(false);setSaveApproved(false);setError('')},[signature])
  async function refresh(){
    await Promise.all(['calendar-initial-health','calendar-population-save','package-working-draft','admin-run-branches','run-branches']
      .map(key=>client.invalidateQueries({queryKey:[key,runId]})))
  }
  const reviewing=useMutation({retry:false,mutationFn:async()=>{
    if(!data||data.state||data.draft_status!=='clean')throw Error('Initial health requires a clean saved population')
    const request:InitialHealthRequest={command_id:'initial-health-'+crypto.randomUUID(),expected_saved_head:head,
      expected_draft_version:data.draft_version,expected_population_fingerprint:population,
      initialization_policy:'fresh_without_history.v1',audit_label:'Admin',audit_reason:'Reviewed fresh initial health baseline without invented history'}
    return {signature,value:validateInitialHealthReview(await reviewCalendarInitialHealth(runId,branchId,request),request,runId,branchId,clock,playerIds)}
  },onSuccess:r=>{if(current.current===r.signature){setReview(r.value);setApproved(false);setError('')}},
  onError:e=>{setError(formatApiError(e));setApproved(false)}})
  const confirming=useMutation({retry:false,mutationFn:async(frozen:InitialHealthReview)=>{
    const installed=validateInitialHealthView(await confirmCalendarInitialHealth(runId,branchId,frozen.request,frozen.health_fingerprint),runId,branchId,head,population,clock,playerIds)
    if(installed.health_fingerprint!==frozen.health_fingerprint)throw Error('Confirmed health differs from review')
  },onSuccess:async()=>{setReview(null);setApproved(false);setError('');await refresh()},
  onError:async e=>{setApproved(false);setError(formatApiError(e));await refresh()}})
  const saving=useMutation({retry:false,mutationFn:async()=>{
    if(!data?.health_component_fingerprint||data.saved||data.draft_status!=='dirty')throw Error('Health Save proof changed')
    return validateInitialHealthSave(await savePlayerHealthRevision(runId,branchId,{
      expected_draft_version:data.draft_version,expected_player_health_fingerprint:data.health_component_fingerprint}),runId,branchId,data.health_component_fingerprint)
  },onSuccess:async()=>{acknowledgeSavedRunForm(runId,branchId);setSaveApproved(false);setError('');await refresh()},
  onError:async e=>{setSaveApproved(false);setError(formatApiError(e));await refresh()}})
  const busy=Boolean(view.error)||view.isFetching||reviewing.isPending||confirming.isPending||saving.isPending
  const reviewCurrent=review&&data&&!data.state&&data.draft_status==='clean'
    &&review.request.expected_draft_version===data.draft_version&&review.request.expected_saved_head===head
  return <section data-run-navigation-readonly aria-label={cs?'Počáteční zdravotní stav':'Initial health'}>
    <h3>{cs?'Počáteční zdravotní stav':'Initial health'}</h3>
    <p>{cs?'Výslovně zvolený základ bez zranění, nemocí a zdravotní historie. Nejde o odhad realistického rozložení zdraví. Zdravotní záznamy lze upravit na profilu hráče v záložce Zdraví. Posouvání času se doplní později.':
      'An explicitly chosen baseline without injuries, illnesses or health history. This is not an estimate of realistic health distribution. Edit health records in the player profile Health tab. Time progression will follow later.'}</p>
    {(error||view.error)&&<p role="alert">{error||formatApiError(view.error)}</p>}
    {data&&!data.state&&<button disabled={busy||data.draft_status!=='clean'} onClick={()=>{setReview(null);setApproved(false);reviewing.mutate()}}>
      {cs?'Zkontrolovat zdravotní základ':'Review initial health'}</button>}
    {reviewCurrent&&<>
      <p>{cs?'Hráči bez zdravotních záznamů':'Players without health records'}: {playerIds.length}</p>
      <label><input type="checkbox" aria-label={cs?'Potvrdit zdravotní základ':'Confirm initial health'} checked={approved} onChange={e=>setApproved(e.target.checked)}/>
        {cs?'Chci vytvořit tento zdravotní základ.':'Create this initial health baseline.'}</label>
      <button disabled={!approved||busy} onClick={()=>review&&confirming.mutate(review)}>{cs?'Vytvořit zdravotní základ':'Create initial health'}</button>
    </>}
    {data?.state?.schema_version==='player_health_calendar_state.v2' ? <p role="status">{cs?'Zdravotní základ byl rozšířen o potvrzené zdravotní záznamy. Otevři zdraví hráče.':'Health baseline has reviewed health records. Open player Health.'}</p> : data?.state&&(data.saved?<p role="status">{cs?'Zdravotní základ je uložený.':'Initial health is saved.'}</p>:<>
      <p role="status">{cs?'Zdravotní základ čeká na ruční uložení.':'Initial health is waiting for an explicit Save.'}</p>
      <label><input type="checkbox" aria-label={cs?'Potvrdit uložení zdraví':'Confirm health Save'} checked={saveApproved} onChange={e=>setSaveApproved(e.target.checked)}/>
        {cs?'Uložit zdravotní základ do nové revize.':'Save initial health in a new revision.'}</label>
      <button disabled={!saveApproved||busy||data.draft_status!=='dirty'} onClick={()=>saving.mutate()}>{cs?'Uložit zdravotní základ':'Save initial health'}</button>
    </>)}
  </section>
}
