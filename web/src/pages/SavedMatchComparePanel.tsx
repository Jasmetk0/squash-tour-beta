/** On-demand, read-only match-result evidence for one existing A/B Saved Edition.
 * This never queries current Working Draft, mutable HEAD or inferred match IDs. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {getSavedTourEdition} from '../api/client'
import type {SavedTourEvent} from '../api/savedTour'
import type {SavedRevisionHistoryEntry} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {comparePublishedSavedMatches} from './savedMatchCompare'
import type {PublishedMatchStatus} from './savedMatchCompare'

type Props={
  runId:string;branchId:string;seasonIndex:number;eventId:string
  a:SavedRevisionHistoryEntry;b:SavedRevisionHistoryEntry
  calendarA:SavedTourEvent;calendarB:SavedTourEvent
}
const statuses:PublishedMatchStatus[]=['added','removed','changed','unchanged']
const pretty=(v:unknown)=>v===null?'Not published':JSON.stringify(v,null,2)
export function SavedMatchComparePanel({
  runId,branchId,seasonIndex,eventId,a,b,calendarA,calendarB
}:Props):JSX.Element{
  const [filter,setFilter]=useState<'differences'|'all'>('differences')
  const [inspected,setInspected]=useState<string|null>(null)
  const queryA=useQuery({
    queryKey:['compare-exact-saved-match-edition',runId,branchId,a.revision_id,seasonIndex,eventId],
    queryFn:()=>getSavedTourEdition(runId,branchId,a.revision_id,seasonIndex,eventId),
    retry:false
  })
  const queryB=useQuery({
    queryKey:['compare-exact-saved-match-edition',runId,branchId,b.revision_id,seasonIndex,eventId],
    queryFn:()=>getSavedTourEdition(runId,branchId,b.revision_id,seasonIndex,eventId),
    retry:false
  })
  const compared=queryA.data&&queryB.data?comparePublishedSavedMatches(
    runId,branchId,seasonIndex,eventId,a,b,calendarA,calendarB,queryA.data,queryB.data
  ):null
  const rows=compared?.rows.filter(r=>filter==='all'||r.status!=='unchanged')??[]
  const selected=compared?.rows.find(r=>r.matchId===inspected)
  return <section className="section-subtle" aria-label="Compare exact published Saved matches">
    <h5>Published match results · skutečné výsledky A/B</h5>
    <p className="status">Only the canonical published Match IDs and recorded winner,
      loser, scoreline, round and bracket position from these two immutable Saved
      Editions. Missing publication is not proof of an unplayed or removed match.</p>
    {(queryA.isPending||queryB.isPending)&&<p role="status">Reading exact Saved match evidence…</p>}
    {queryA.error&&<p role="alert">State A match source: {formatApiError(queryA.error)}</p>}
    {queryB.error&&<p role="alert">State B match source: {formatApiError(queryB.error)}</p>}
    {queryA.isSuccess&&queryB.isSuccess&&!compared&&<p role="alert">
      Saved match comparison rejected: Revision, original owner, Edition or
      published Match IDs differ from the selected immutable evidence.</p>}
    {compared?.availability==='unpublished'&&<p role="status">
      At least one selected Saved Edition has no published Tournament Result.
      Individual match differences cannot be established from the available published evidence.</p>}
    {compared?.availability==='published'&&<>
      <p className="status">Published evidence A: <code>{a.revision_id}</code>
        {' '}({a.revision_branch_id}) → B: <code>{b.revision_id}</code>
        {' '}({b.revision_branch_id}). Match identity is exact Match ID,
        not inferred from opponents or bracket slots.</p>
      <div className="run-world-metrics" aria-label="Compare published Saved match totals">
        {statuses.map(s=><div key={s}><span>{s}</span><strong>{compared.counts[s]}</strong></div>)}
      </div>
      <label>Match comparison display{' '}
        <select aria-label="Compare published match display filter" value={filter}
          onChange={e=>{setFilter(e.target.value as 'differences'|'all');setInspected(null)}}>
          <option value="differences">Differences only · Jen rozdíly</option>
          <option value="all">All · Vše</option>
        </select>
      </label>
      {!rows.length?<p role="status">{filter==='differences'?
        'No changes in the published canonical match records.':
        'Neither Saved publication contains a canonical match record.'}</p>:
      <div className="table-responsive">
        <table aria-label="Compared published Saved matches">
          <thead><tr><th>Match ID</th><th>Status</th><th>Winner A → B</th>
            <th>Score A → B</th><th>Changed exact fields</th><th>Evidence</th></tr></thead>
          <tbody>{rows.map(r=><tr key={r.matchId}>
            <td><code>{r.matchId}</code></td><td>{r.status}</td>
            <td>{r.a?.winner_player_id??'—'} → {r.b?.winner_player_id??'—'}</td>
            <td>{r.a?.scoreline??'—'} → {r.b?.scoreline??'—'}</td>
            <td>{r.changedFields.join(', ')||'—'}</td>
            <td><button type="button" onClick={()=>setInspected(r.matchId)}
              aria-label={'Inspect published match '+r.matchId}>Inspect A/B</button></td>
          </tr>)}</tbody>
        </table>
      </div>}
      {selected&&<div className="section-subtle" aria-label="Exact published match A B detail">
        <div className="actions"><h5>Saved Match ID · <code>{selected.matchId}</code></h5>
          <button type="button" onClick={()=>setInspected(null)}>Close match evidence</button></div>
        <p>Status: <strong>{selected.status}</strong>;
          exact changed fields: {selected.changedFields.join(', ')||'Whole published match record'}</p>
        <div className="saved-compare-before-after">
          <section><h5>State A · original published match</h5>
            <pre className="json-block">{pretty(selected.a)}</pre></section>
          <section><h5>State B · original published match</h5>
            <pre className="json-block">{pretty(selected.b)}</pre></section>
        </div>
      </div>}
    </>}
  </section>
}
