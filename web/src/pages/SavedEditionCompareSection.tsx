/** True tournament Edition diff; uses the SAME reachable Saved Revision A/B
 * scope as Compare, but never infers entities from opaque component hashes. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useSearchParams} from 'react-router-dom'
import {getSavedTourCalendar} from '../api/client'
import type {SavedRevisionHistoryEntry} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {compareSavedSeasonEditions} from './savedEditionCompare'
import type {SavedEditionDiff,SavedEditionDiffStatus} from './savedEditionCompare'
import {SavedMatchComparePanel} from './SavedMatchComparePanel'

type Props={runId:string;branchId:string;a:SavedRevisionHistoryEntry;b:SavedRevisionHistoryEntry}
const statuses:SavedEditionDiffStatus[]=['added','removed','changed','unchanged']
const show=(v:unknown)=>v===null?'null':JSON.stringify(v,null,2)??'Not provided'

export function SavedEditionCompareSection({runId,branchId,a,b}:Props):JSX.Element{
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
    r.changedFields.join(', '):r.status==='unchanged'?'None':'Whole Edition'
  return <section className="panel" aria-label="Compare saved season Editions">
    <h3>Saved Tournament Editions · skutečné změny turnajů</h3>
    <p className="status">Read-only comparison of the full canonical Saved Calendar
      for one explicit sporting season; each side uses its own immutable A/B Revision
      and original owner Branch. This is not a historical match or ranking comparison.</p>
    <div className="actions">
      <label>Sporting season{' '}
        <select aria-label="Compare Edition season"
          value={validSeason?seasonIndex:''}
          onChange={e=>set('editionSeason',e.target.value)}>
          {!validSeason&&<option value="">Invalid season</option>}
          {Array.from({length:50},(_,i)=><option key={i} value={i}>
            {2000+i}/{2001+i}</option>)}
        </select></label>
      <label>Show Editions{' '}
        <select aria-label="Compare Edition display filter" value={view}
          onChange={e=>set('editionFilter',e.target.value)}>
          <option value="differences">Differences only · Jen rozdíly</option>
          <option value="all">All · Vše</option>
        </select></label>
    </div>
    {!validSeason&&<p role="alert">Invalid Saved Edition sporting season. Select a valid season.</p>}
    {validSeason&&(qA.isPending||qB.isPending)&&<p role="status">
      Reading exact {label} Saved Calendars A/B…</p>}
    {qA.error&&<p role="alert">State A: {formatApiError(qA.error)}</p>}
    {qB.error&&<p role="alert">State B: {formatApiError(qB.error)}</p>}
    {validSeason&&qA.isSuccess&&qB.isSuccess&&!compared&&<p role="alert">
      Saved Edition identity, source Branch or calendar evidence is inconsistent.
      No tournament differences will be inferred.</p>}
    {compared&&<>
      <p className="status">Season {label} · Selected Branch <code>{branchId}</code>
        {' · '}State A <code>{a.revision_id}</code> (source{' '}
        <code>{compared.branchOwners.a}</code>) → State B <code>{b.revision_id}</code>
        {' '}(source <code>{compared.branchOwners.b}</code>)
        {' · '}A: {qA.data!.calendar_status} / {qA.data!.edition_count} saved Editions
        {' · '}B: {qB.data!.calendar_status} / {qB.data!.edition_count} saved Editions</p>
      <div className="run-world-metrics" aria-label="Compare saved Edition totals">
        {statuses.map(s=><div key={s}><span>{s}</span><strong>{compared.counts[s]}</strong></div>)}
      </div>
      {rows.length===0?<p role="status">
        {view==='differences'?'No changed canonical Editions in this season.':
          'No Saved Editions exist in either selected revision for this season.'}</p>:
        <div className="table-responsive">
          <table aria-label="Compared Saved Edition changes">
            <thead><tr><th>Event ID / Name</th><th>Season week</th>
              <th>Status</th><th>Exact changed fields</th><th>Source evidence</th></tr></thead>
            <tbody>{rows.map(r=><tr key={r.eventId}>
              <td><strong>{r.name}</strong> <code>{r.eventId}</code></td>
              <td>{r.a?.season_week??'—'} → {r.b?.season_week??'—'}</td>
              <td>{r.status}</td>
              <td>{diff(r)}</td>
              <td><button type="button" onClick={()=>setDetail(r.eventId)}
                aria-label={'Inspect Saved Edition '+r.eventId}>Inspect A/B</button></td>
            </tr>)}</tbody>
          </table>
        </div>}
      <p className="status">Only actual saved Edition fields are compared by Event ID.
        No plans, fake tournament results, inferred head changes or cross-Branch activations.</p>
    </>}
    {selected&&<aside className="saved-revision-detail-drawer" aria-label="Saved Edition A B detail">
      <div className="saved-revision-detail-drawer__heading">
        <strong>Exact Saved Edition · read-only</strong>
        <button type="button" onClick={()=>setDetail(null)}>Close Edition comparison</button>
      </div>
      <h4>{selected.name} · <code>{selected.eventId}</code></h4>
      <p>Status: <strong>{selected.status}</strong> · Changed:
        {' '}{diff(selected)} · Season {label}</p>
      <p>State A: <code>{a.revision_id}</code> (original <code>{a.revision_branch_id}</code>)
        {' '}→ State B: <code>{b.revision_id}</code>
        {' '}(original <code>{b.revision_branch_id}</code>)</p>
      <div className="saved-compare-before-after">
        <section><h5>A · Before · actual Saved Edition</h5>
          <pre className="json-block">{show(selected.a)}</pre></section>
        <section><h5>B · After · actual Saved Edition</h5>
          <pre className="json-block">{show(selected.b)}</pre></section>
      </div>
      {selected.a&&selected.b&&<SavedMatchComparePanel
        key={[a.revision_id,b.revision_id,seasonIndex,selected.eventId].join(':')}
        runId={runId} branchId={branchId} seasonIndex={seasonIndex}
        eventId={selected.eventId} a={a} b={b}
        calendarA={selected.a} calendarB={selected.b}/>}
      {(!selected.a||!selected.b)&&<p className="status">
        This Edition exists in only one selected Saved Revision.
        There is no second published Edition to compare match results against.</p>}
    </aside>}
  </section>
}
