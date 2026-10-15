import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { getBoundaryOptions, setBoundaryTarget } from '../api/fullSimulationBoundaryTargets'
import type { BoundaryRequest, BoundaryTarget } from '../api/fullSimulationBoundaryTargets'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

const copy={
 en:{title:'Event and global slot targets',review:'Review precise targets',refresh:'Refresh canonical choices',choice:'Target boundary',
  before_slot:'Stop BEFORE global Simulation Slot',before_final:'Stop BEFORE this edition’s final slot',after_tournament:'Stop AFTER this edition is officially closed',
  truth:'Only current, authoritative boundaries are selectable. A final requires frozen topology. Official closure requires an adopted tournament source. Save remains manual.',
  none:'No eligible precise boundary in the current week.',operator:'Target operator',reason:'Target audit reason',confirm:'I reviewed the exact edition / global slot and schedule.',
  apply:'Apply precise target',retry:'Retry same target request',cancel:'Cancel retry and review again',accepted:'Precise target applied',
  unavailable:'Unavailable choices',entry:'Entry decision',match:'Match',unknown:'Not planned or not yet frozen',parent:'An earlier weekly review uses a different schedule. Safely stop that parent and review a new operation.',closed:'Edition already closed',passed:'Final slot already started',
  stale:'The server validates the current boundary under its writer lock. If a selection is stale, refresh and review again.'},
 cs:{title:'Událostní cíle a globální sloty',review:'Prověřit přesné cíle',refresh:'Obnovit kanonické možnosti',choice:'Cílová hranice',
  before_slot:'Zastavit PŘED globálním Simulation Slotem',before_final:'Zastavit PŘED slotem finále této edice',after_tournament:'Zastavit PO oficiálním uzavření této edice',
  truth:'Vybrat lze pouze aktuální autoritativní hranice. Finále vyžaduje zmrazenou topologii. Oficiální uzavření vyžaduje přijatý zdroj výsledků turnaje. Save zůstává ruční.',
  none:'V aktuálním týdnu není dostupná přesná cílová hranice.',operator:'Operátor cíle',reason:'Důvod změny cíle',confirm:'Prověřil jsem přesnou edici / globální slot a plán.',
  apply:'Použít přesný cíl',retry:'Zopakovat stejný cílový požadavek',cancel:'Zrušit opakování a znovu prověřit',accepted:'Přesný cíl byl použit',
  unavailable:'Nedostupné možnosti',entry:'Entry rozhodnutí',match:'Zápas',unknown:'Nenaplánováno nebo dosud nezmrazeno',parent:'Dřívější týdenní review používá jiný plán. Bezpečně ukončete tento příkaz a prověřte novou operaci.',closed:'Edice je již uzavřená',passed:'Slot finále již začal',
  stale:'Server ověří aktuální hranici pod zámkem zápisu. Pokud výběr zastaral, obnovte možnosti a znovu je prověřte.'}
} as const
export function BoundaryDescription({target}:{target:BoundaryTarget}){
 const {language}=useLanguage();const t=copy[language]
 return <span>{t[target.kind]}{target.slot_ordinal!==null && <> #{target.slot_ordinal} · {target.slot_kind==='entry'?t.entry:t.match}</>}
  {' · '}S{target.week.season_index} W{target.week.week}{target.edition_id && <> · <code>{target.edition_id}</code></>}</span>
}
export function FullSimulationBoundaryTargets({runId,branchId,parentId,onApplied}:{runId:string;branchId:string;parentId:string;onApplied:()=>void}){
 const {language}=useLanguage();const t=copy[language];const client=useQueryClient()
 const [open,setOpen]=useState(false);const [selection,setSelection]=useState('');const [operator,setOperator]=useState('');const [reason,setReason]=useState('');const [confirmed,setConfirmed]=useState(false)
 const [pending,setPending]=useState<BoundaryRequest|null>(null)
 const query=useQuery({queryKey:['full-simulation-boundary-options',runId,branchId,parentId],queryFn:()=>getBoundaryOptions(runId,branchId,parentId),enabled:open,retry:false})
 const mutation=useMutation({mutationFn:(body:BoundaryRequest)=>setBoundaryTarget(runId,branchId,body),onSuccess:async()=>{
  setPending(null);setConfirmed(false);await client.invalidateQueries({queryKey:['server-simulation-tasks']});onApplied()
 }})
 const target=query.data?.options.find(v=>v.selector_fingerprint===selection)
 return <section aria-label={t.title}>
  <button type="button" onClick={()=>setOpen(!open)}>{t.review}</button>
  {open && <><h5>{t.title}</h5><p>{t.truth}</p><p>{t.stale}</p><code>{parentId}</code>
   <button type="button" disabled={!!pending || query.isFetching} onClick={()=>{setSelection('');setConfirmed(false);void query.refetch()}}>{t.refresh}</button>
   {query.error && <p role="alert">{formatApiError(query.error)}</p>}
   {query.isSuccess && <>
    {!query.data.options.length?<p>{t.none}</p>:<>
     <label>{t.choice}<select aria-label={t.choice} value={selection} disabled={!!pending} onChange={e=>{setSelection(e.target.value);setConfirmed(false)}}>
      <option value="">—</option>{query.data.options.map(v=><option key={v.selector_fingerprint} value={v.selector_fingerprint}>
       {t[v.kind]}{v.slot_ordinal!==null?` #${v.slot_ordinal}`:''}{v.edition_id?` · ${v.edition_id}`:''} · S{v.week.season_index} W{v.week.week}
      </option>)}</select></label>
     {target && <p><BoundaryDescription target={target}/><br/><code>{target.slot_id??target.edition_id}</code><br/><code>{target.schedule_fingerprint}</code></p>}
     <label>{t.operator}<input aria-label={t.operator} disabled={!!pending} value={operator} onChange={e=>setOperator(e.target.value)}/></label>
     <label>{t.reason}<input aria-label={t.reason} disabled={!!pending} value={reason} onChange={e=>setReason(e.target.value)}/></label>
     <label><input type="checkbox" disabled={!!pending} checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>{t.confirm}</label>
     <button type="button" disabled={mutation.isPending || (!pending && (!target || !operator.trim() || !reason.trim() || !confirmed))} onClick={()=>{
      const body=pending??{control_command_id:crypto.randomUUID(),target_command_id:parentId,boundary_target:target!,operator_label:operator.trim(),audit_reason:reason.trim()}
      setPending(body);mutation.mutate(body)
     }}>{pending?t.retry:t.apply}</button>
    </>}
    {query.data.unavailable.length>0 && <details><summary>{t.unavailable}</summary><ul>{query.data.unavailable.map((u,i)=><li key={i}>
     <code>{u.event_id}</code> · {u.kind==='before_final'?t.before_final:u.kind==='after_tournament'?t.after_tournament:t.choice} · {
      u.reason==='parent_week_schedule_review_changed'?t.parent:u.reason==='edition_already_closed'?t.closed:u.reason==='final_slot_already_started'?t.passed:t.unknown} <code>{u.reason}</code>
    </li>)}</ul></details>}
   </>}
   {pending && !mutation.isPending && <button type="button" onClick={()=>{setPending(null);mutation.reset();setSelection('');setConfirmed(false);void query.refetch()}}>{t.cancel}</button>}
   {mutation.error && <p role="alert">{formatApiError(mutation.error)}</p>}
   {mutation.data && <p role="status">{t.accepted}: <BoundaryDescription target={mutation.data.boundary_target}/></p>}
  </>}
 </section>
}
