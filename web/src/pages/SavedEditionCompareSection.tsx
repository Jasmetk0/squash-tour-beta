/** True tournament Edition diff; uses the SAME reachable Saved Revision A/B
 * scope as Compare, but never infers entities from opaque component hashes. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useSearchParams} from 'react-router-dom'
import {getSavedTourCalendar} from '../api/client'
import type {SavedRevisionHistoryEntry} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {useLanguage} from '../i18n/LanguageContext'
import {historyText} from '../i18n/historyText'
import {compareSavedSeasonEditions} from './savedEditionCompare'
import type {SavedEditionDiff,SavedEditionDiffStatus} from './savedEditionCompare'
import {SavedMatchComparePanel} from './SavedMatchComparePanel'

type Props={runId:string;branchId:string;a:SavedRevisionHistoryEntry;b:SavedRevisionHistoryEntry}
const statuses:SavedEditionDiffStatus[]=['added','removed','changed','unchanged']
const show=(v:unknown,language:'en'|'cs')=>v===null?'null':JSON.stringify(v,null,2)??historyText('Not provided',language)

export function SavedEditionCompareSection({runId,branchId,a,b}:Props):JSX.Element{
  const {language}=useLanguage()
  const T=(english:string)=>historyText(english,language)
  const [params,setParams]=useSearchParams()
  const [detail,setDetail]=useState<string|null>(null)
  const raw=params.get('editionSeason')
  const seasonIndex=raw===null?0:/^(0|[1-9]\d*)$/.test(raw)?Number(raw):NaN
  const validSeason=Number.isInteger(seasonIndex)&&seasonIndex>=0&&seasonIndex<50
  const view=params.get('editionFilter')==='all'?'all':'differences'
  const qA=useQuery({
    queryKey:['compare-canonical-editions',runId,branchId,a.revision_id,seasonIndex],
    queryFn:()=>getSavedTourCalendar(runId,branchId,a.revision_id,seasonIndex),
    enabled:validSeason,retry:false
  })
  const qB=useQuery({
    queryKey:['compare-canonical-editions',runId,branchId,b.revision_id,seasonIndex],
    queryFn:()=>getSavedTourCalendar(runId,branchId,b.revision_id,seasonIndex),
    enabled:validSeason,retry:false
  })
  const compared=validSeason&&qA.data&&qB.data?
    compareSavedSeasonEditions(runId,branchId,seasonIndex,a,b,qA.data,qB.data):null
  const rows=compared?.rows.filter(r=>view==='all'||r.status!=='unchanged')??[]
  const selected=detail?compared?.rows.find(x=>x.eventId===detail):undefined
  const set=(key:string,value:string)=>{
    const next=new URLSearchParams(params)
    next.set(key,value)
    setParams(next,{replace:true});setDetail(null)
  }
  const label=2000+seasonIndex+'/'+String(2001+seasonIndex)
  const diff=(r:SavedEditionDiff)=>r.changedFields.length?
    r.changedFields.join(', '):r.status==='unchanged'?T('None'):T('Whole Edition')
  return <section className="panel" aria-label={T("Compare saved season Editions")}>
    <h3>{T("Saved Tournament Editions · skutečné změny turnajů")}</h3>
    <p className="status">{T("Read-only comparison of the full canonical Saved Calendar for one explicit sporting season; each side uses its own immutable A/B Revision and original owner Branch. This is not a historical match or ranking comparison.")}</p>
    <div className="actions">
      <label>{T("Sporting season")}{' '}
        <select aria-label={T("Compare Edition season")}
          value={validSeason?seasonIndex:''}
          onChange={e=>set('editionSeason',e.target.value)}>
          {!validSeason&&<option value="">{T("Invalid season")}</option>}
          {Array.from({length:50},(_,i)=><option key={i} value={i}>
            {2000+i}/{2001+i}</option>)}
        </select></label>
      <label>{T("Show Editions")}{' '}
        <select aria-label={T("Compare Edition display filter")} value={view}
          onChange={e=>set('editionFilter',e.target.value)}>
          <option value="differences">{T("Differences only · Jen rozdíly")}</option>
          <option value="all">{T("All · Vše")}</option>
        </select></label>
    </div>
    {!validSeason&&<p role="alert">{T("Invalid Saved Edition sporting season. Select a valid season.")}</p>}
    {validSeason&&(qA.isPending||qB.isPending)&&<p role="status">
      {T("Reading exact")} {label} {T("Saved Calendars A/B…")}</p>}
    {qA.error&&<p role="alert">{T("State A:")} {formatApiError(qA.error)}</p>}
    {qB.error&&<p role="alert">{T("State B:")} {formatApiError(qB.error)}</p>}
    {validSeason&&qA.isSuccess&&qB.isSuccess&&!compared&&<p role="alert">
      {T("Saved Edition identity, source Branch or calendar evidence is inconsistent. No tournament differences will be inferred.")}</p>}
    {compared&&<>
      <p className="status">{T("Season")} {label} · {T('Selected Branch')} <code>{branchId}</code>
        {' · '}State A <code>{a.revision_id}</code> ({T('source')}{' '}
        <code>{compared.branchOwners.a}</code>) → {T('State')} B <code>{b.revision_id}</code>
        {' '}(source <code>{compared.branchOwners.b}</code>)
        {' · '}A: {qA.data!.calendar_status} / {qA.data!.edition_count} {T("saved Editions")}
        {' · '}B: {qB.data!.calendar_status} / {qB.data!.edition_count} {T("saved Editions")}</p>
      <div className="run-world-metrics" aria-label={T("Compare saved Edition totals")}>
        {statuses.map(s=><div key={s}><span>{T(s)}</span><strong>{compared.counts[s]}</strong></div>)}
      </div>
      {rows.length===0?<p role="status">
        {view==='differences'?T("No changed canonical Editions in this season."):
          T("No Saved Editions exist in either selected revision for this season.")}</p>:
        <div className="table-responsive">
          <table aria-label={T("Compared Saved Edition changes")}>
            <thead><tr><th>{T("Event ID / Name")}</th><th>{T("Season week")}</th>
              <th>{T("Status")}</th><th>{T("Exact changed fields")}</th><th>{T("Source evidence")}</th></tr></thead>
            <tbody>{rows.map(r=><tr key={r.eventId}>
              <td><strong>{r.name}</strong> <code>{r.eventId}</code></td>
              <td>{r.a?.season_week??'—'} → {r.b?.season_week??'—'}</td>
              <td>{T(r.status)}</td>
              <td>{diff(r)}</td>
              <td><button type="button" onClick={()=>setDetail(r.eventId)}
                aria-label={T('Inspect Saved Edition')+' '+r.eventId}>{T("Inspect A/B")}</button></td>
            </tr>)}</tbody>
          </table>
        </div>}
      <p className="status">{T("Only actual saved Edition fields are compared by Event ID. No plans, fake tournament results, inferred head changes or cross-Branch activations.")}</p>
    </>}
    {selected&&<aside className="saved-revision-detail-drawer" aria-label={T("Saved Edition A B detail")}>
      <div className="saved-revision-detail-drawer__heading">
        <strong>{T("Exact Saved Edition · read-only")}</strong>
        <button type="button" onClick={()=>setDetail(null)}>{T("Close Edition comparison")}</button>
      </div>
      <h4>{selected.name} · <code>{selected.eventId}</code></h4>
      <p>{T('Status:')} <strong>{T(selected.status)}</strong> · {T('Changed:')}
        {' '}{diff(selected)} · Season {label}</p>
      <p>{T("State A:")} <code>{a.revision_id}</code> ({T('original')} <code>{a.revision_branch_id}</code>)
        {' '}→ State B: <code>{b.revision_id}</code>
        {' '}({T('original')} <code>{b.revision_branch_id}</code>)</p>
      <div className="saved-compare-before-after">
        <section><h5>{T("A · Before · actual Saved Edition")}</h5>
          <pre className="json-block">{show(selected.a,language)}</pre></section>
        <section><h5>{T("B · After · actual Saved Edition")}</h5>
          <pre className="json-block">{show(selected.b,language)}</pre></section>
      </div>
      {selected.a&&selected.b&&<SavedMatchComparePanel
        key={[a.revision_id,b.revision_id,seasonIndex,selected.eventId].join(':')}
        runId={runId} branchId={branchId} seasonIndex={seasonIndex}
        eventId={selected.eventId} a={a} b={b}
        calendarA={selected.a} calendarB={selected.b}/>}
      {(!selected.a||!selected.b)&&<p className="status">
        {T("This Edition exists in only one selected Saved Revision. There is no second published Edition to compare match results against.")}</p>}
    </aside>}
  </section>
}
