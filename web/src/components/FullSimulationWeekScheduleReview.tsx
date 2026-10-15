import {useState} from 'react'
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query'
import {approveNextWeekExtension,getNextWeekExtensionInspection} from '../api/fullSimulationWeekReview'
import type {WeekExtensionApprovalRequest} from '../api/fullSimulationWeekReview'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'

export function FullSimulationWeekScheduleReview({
 runId,branchId,taskId,taskRevision
}:{runId:string;branchId:string;taskId:string;taskRevision:number}){
 const {language}=useLanguage()
 const queryClient=useQueryClient()
 const [operator,setOperator]=useState('')
 const [reason,setReason]=useState('')
 const [consent,setConsent]=useState(false)
 const [frozenRequest,setFrozenRequest]=useState<WeekExtensionApprovalRequest|null>(null)
 const result=useQuery({
   queryKey:['next-week-extension-inspection',runId,branchId],
   queryFn:()=>getNextWeekExtensionInspection(runId,branchId),
   retry:false,refetchOnWindowFocus:false,
 })
 const mutation=useMutation({
   mutationFn:(body:WeekExtensionApprovalRequest)=>approveNextWeekExtension(runId,branchId,body),
   onSuccess:async()=>{
     await queryClient.invalidateQueries({queryKey:['server-simulation-tasks']})
     await queryClient.invalidateQueries({queryKey:['next-week-extension-inspection',runId,branchId]})
   }
 })
 const t=language==='cs'
 ?{title:'Kontrola změněného týdenního rozpisu',readonly:'Prohlídka nic nemění. K rozšíření je nutné samostatné výslovné schválení.',loading:'Kontroluji zmrazené rozpisy…',
    empty:'Pro aktuální týden nebyl nalezen čekající příkaz Next Week.',proof:'Původní rozpis beze změn, nové sloty navazují',
    unchanged:'Rozpis beze změny',blocked:'Nelze bezpečně prokázat návaznost',newSlots:'Nové knockout sloty',
    operator:'Schvalující operátor',reason:'Důvod schválení',consent:'Potvrzuji, že stávající výsledky zůstanou neměnné a schvaluji pouze uvedené nové sloty.',
    approve:'Výslovně schválit rozšíření týdne',retry:'Opakovat stejný požadavek',cancel:'Zrušit požadavek',
    approved:'Rozpis schválen. Pokračování serverové úlohy vyžaduje další samostatné potvrzení.'}
 :{title:'Changed week schedule inspection',readonly:'Inspection changes nothing. Append-only extension requires separate explicit approval.',loading:'Inspecting frozen schedules…',
    empty:'No pending Next Week command was found for the current week.',proof:'Original schedule unchanged; new slots append',
    unchanged:'Schedule unchanged',blocked:'Append-only extension not proven',newSlots:'New knockout slots',
    operator:'Approving operator',reason:'Approval reason',consent:'I confirm that committed results remain immutable and approve only the listed new slots.',
    approve:'Explicitly approve week extension',retry:'Retry same request',cancel:'Cancel request',
    approved:'Schedule approved. Resuming the server task requires another separate confirmation.'}
 return <section aria-label={t.title}>
  <p>{t.readonly}</p>
  {result.isPending&&<p role="status">{t.loading}</p>}
  {result.error&&<p role="alert">{formatApiError(result.error)}</p>}
  {result.data?.length===0&&<p>{t.empty}</p>}
  {result.data?.map(item=><div key={item.command_id}>
   <p><code>{item.command_id}</code> · <strong>{item.status==='append_only_proven'?t.proof:item.status==='unchanged'?t.unchanged:t.blocked}</strong></p>
   {item.status==='append_only_proven'&&<>
    <p>{t.newSlots}: {item.new_slots.map(s=>s.ordinal).join(', ')}</p>
    <p><code>{item.current_schedule_fingerprint}</code></p>
    <label>{t.operator}<input value={operator} onChange={e=>setOperator(e.target.value)} disabled={!!frozenRequest}/></label>
    <label>{t.reason}<input value={reason} onChange={e=>setReason(e.target.value)} disabled={!!frozenRequest}/></label>
    <label><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} disabled={!!frozenRequest}/>{t.consent}</label>
    <button type="button" disabled={mutation.isPending||(!frozenRequest&&(!operator.trim()||!reason.trim()||!consent))}
      onClick={()=>{
       if(!item.current_schedule_fingerprint)return
       const body=frozenRequest??{
         control_command_id:crypto.randomUUID(),task_id:taskId,
         target_week_command_id:item.command_id,expected_task_revision:taskRevision,
         expected_receipt_fingerprint:item.receipt_fingerprint,
         expected_current_schedule_fingerprint:item.current_schedule_fingerprint,
         operator_label:operator.trim(),audit_reason:reason.trim(),
         confirm_committed_work_is_immutable:true as const
       }
       setFrozenRequest(body)
       mutation.mutate(body)
      }}>{frozenRequest?t.retry:t.approve}</button>
    {frozenRequest&&!mutation.isPending&&!mutation.isSuccess&&<button type="button" onClick={()=>{
      setFrozenRequest(null);mutation.reset();void result.refetch()
    }}>{t.cancel}</button>}
   </>}
   {item.status==='blocked'&&<p><code>{item.reason}</code></p>}
  </div>)}
  {mutation.error&&<p role="alert">{formatApiError(mutation.error)}</p>}
  {mutation.isSuccess&&<p role="status">{t.approved}</p>}
 </section>
}
