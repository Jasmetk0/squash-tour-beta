import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {approveNextWeekExtension,getNextWeekExtensionInspection} from '../api/fullSimulationWeekReview'
import type {WeekExtensionApprovalRequest,WeekExtensionCandidate} from '../api/fullSimulationWeekReview'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

type ApprovalScope={runId:string;branchId:string;taskId:string;taskRevision:number}
type FrozenApproval={runId:string;branchId:string;taskId:string;body:WeekExtensionApprovalRequest}

// The React key is an authorization boundary: any change unmounts the consent form.
// Returning to previously seen evidence mounts a NEW, unchecked form.
export function weekExtensionConsentEvidence(scope:ApprovalScope,item:WeekExtensionCandidate):string{
 return JSON.stringify([
  scope.runId,scope.branchId,scope.taskId,scope.taskRevision,
  item.command_id,item.week?.season_index,item.week?.week,item.status,
  item.old_schedule_fingerprint,item.original_slot_count,
  item.receipt_fingerprint,item.current_schedule_fingerprint,
  item.new_slots.map(s=>[s.ordinal,s.group_id,s.event_id,s.round_number])
 ])
}

function ApprovalForm({
 scope,item,disabled,onApprove
}:{scope:ApprovalScope;item:WeekExtensionCandidate;disabled:boolean;onApprove:(body:WeekExtensionApprovalRequest)=>void}){
 const {language}=useLanguage()
 const [operator,setOperator]=useState('')
 const [reason,setReason]=useState('')
 const [consent,setConsent]=useState(false)
 const cs=language==='cs'
 return <>
  <p>{cs?'Nové knockout sloty':'New knockout slots'}: {item.new_slots.map(s=>s.ordinal).join(', ')}</p>
  <p><code>{item.current_schedule_fingerprint}</code></p>
  <label>{cs?'Schvalující operátor':'Approving operator'}<input value={operator} onChange={e=>setOperator(e.target.value)} disabled={disabled}/></label>
  <label>{cs?'Důvod schválení':'Approval reason'}<input value={reason} onChange={e=>setReason(e.target.value)} disabled={disabled}/></label>
  <label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} disabled={disabled}/>{cs
   ?'Potvrzuji, že stávající výsledky zůstanou neměnné a schvaluji pouze uvedené nové sloty.'
   :'I confirm that committed results remain immutable and approve only the listed new slots.'}</label>
  <button type="button" disabled={disabled||!operator.trim()||!reason.trim()||!consent||!item.current_schedule_fingerprint}
   onClick={()=>{
    // The exact displayed candidate and task revision are captured in ONE immutable request.
    if(!consent||!item.current_schedule_fingerprint||!operator.trim()||!reason.trim())return
    onApprove({
     control_command_id:crypto.randomUUID(),task_id:scope.taskId,
     target_week_command_id:item.command_id,expected_task_revision:scope.taskRevision,
     expected_receipt_fingerprint:item.receipt_fingerprint,
     expected_current_schedule_fingerprint:item.current_schedule_fingerprint,
     operator_label:operator.trim(),audit_reason:reason.trim(),
     confirm_committed_work_is_immutable:true
    })
   }}>{cs?'Výslovně schválit rozšíření týdne':'Explicitly approve week extension'}</button>
 </>
}

// Scope changes remount the entire inspector; a failed request cannot leak to another task.
export function FullSimulationWeekScheduleReview(scope:ApprovalScope){
 return <WeekScheduleReviewContent key={JSON.stringify([scope.runId,scope.branchId,scope.taskId])} {...scope}/>
}

function WeekScheduleReviewContent(scope:ApprovalScope){
 const {runId,branchId,taskId}=scope
 const {language}=useLanguage()
 const queryClient=useQueryClient()
 const [frozenRequest,setFrozenRequest]=useState<FrozenApproval|null>(null)
 // Cancellation ends this consent session, even when refreshed proof is identical.
 const [consentGeneration,setConsentGeneration]=useState(0)
 const result=useQuery({
  queryKey:['next-week-extension-inspection',runId,branchId],
  queryFn:()=>getNextWeekExtensionInspection(runId,branchId),
  retry:false,refetchOnWindowFocus:false,
 })
 const mutation=useMutation({
  mutationFn:(request:FrozenApproval)=>approveNextWeekExtension(request.runId,request.branchId,request.body),
  onSuccess:async(_response,request)=>{
   await queryClient.invalidateQueries({queryKey:['server-simulation-tasks']})
   await queryClient.invalidateQueries({queryKey:['next-week-extension-inspection',request.runId,request.branchId]})
  }
 })
 const cs=language==='cs'
 const title=cs?'Kontrola změněného týdenního rozpisu':'Changed week schedule inspection'
 const disabled=mutation.isPending||mutation.isSuccess||!!frozenRequest
 return <section aria-label={title}>
  <p>{cs?'Prohlídka nic nemění. K rozšíření je nutné samostatné výslovné schválení.':'Inspection changes nothing. Append-only extension requires separate explicit approval.'}</p>
  {result.isPending&&<p role="status">{cs?'Kontroluji zmrazené rozpisy…':'Inspecting frozen schedules…'}</p>}
  {result.error&&<p role="alert">{formatApiError(result.error)}</p>}
  {result.data?.length===0&&<p>{cs?'Pro aktuální týden nebyl nalezen čekající příkaz Next Week.':'No pending Next Week command was found for the current week.'}</p>}
  {result.data?.map(item=><div key={item.command_id}>
   <p><code>{item.command_id}</code> · <strong>{item.status==='append_only_proven'
     ?(cs?'Původní rozpis beze změn, nové sloty navazují':'Original schedule unchanged; new slots append')
     :item.status==='unchanged'?(cs?'Rozpis beze změny':'Schedule unchanged')
     :(cs?'Nelze bezpečně prokázat návaznost':'Append-only extension not proven')}</strong></p>
   {item.status==='append_only_proven'&&<ApprovalForm
    key={JSON.stringify([consentGeneration,weekExtensionConsentEvidence(scope,item)])}
    scope={scope} item={item} disabled={disabled}
    onApprove={body=>{
     if(disabled)return
     const request={runId,branchId,taskId,body}
     setFrozenRequest(request)
     mutation.mutate(request)
    }}/>}
   {item.status==='blocked'&&<p><code>{item.reason}</code></p>}
  </div>)}
  {frozenRequest&&mutation.isError&&<>
   <p>{cs
    ?'Původní požadavek je zmrazený. Opakování použije stejný příkaz, revizi a fingerprinty, i když se mezitím změnil rozpis.'
    :'The original request is frozen. Retry uses the same command, revision and fingerprints even if the schedule has changed.'}</p>
   <button type="button" onClick={()=>mutation.mutate(frozenRequest)}>
    {cs?'Opakovat stejný požadavek':'Retry same request'}
   </button>
   <button type="button" onClick={()=>{
    // A new command requires new operator input, reason and checked consent.
    setConsentGeneration(generation=>generation+1)
    setFrozenRequest(null);mutation.reset();void result.refetch()
   }}>{cs?'Zrušit požadavek':'Cancel request'}</button>
  </>}
  {mutation.error&&<p role="alert">{formatApiError(mutation.error)}</p>}
  {mutation.isSuccess&&<p role="status">{cs
   ?'Rozpis schválen. Pokračování serverové úlohy vyžaduje další samostatné potvrzení.'
   :'Schedule approved. Resuming the server task requires another separate confirmation.'}</p>}
 </section>
}
