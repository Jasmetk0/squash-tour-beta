/** Dedicated read-only Saved Revision Compare A/B (Master v80 §27.22). */
import {useState} from 'react'
import {useInfiniteQuery,useQuery} from '@tanstack/react-query'
import {Link,useParams,useSearchParams} from 'react-router-dom'
import {
  compareSavedRevisions,getSavedRevision,listRunBranches,listSavedRevisionHistory
} from '../api/client'
import type {SavedRevisionHistoryEntry} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {projectSavedStateComparison,validateReachableCompareHistory} from './savedCompareStates'
import type {CompareRow} from './savedCompareStates'

type Detail={type:'row';id:string}|{type:'state';side:'a'|'b'}|null
const pretty=(v:unknown)=>v===undefined?'Not provided':JSON.stringify(v,null,2)??String(v)

export function SavedStatesComparePage():JSX.Element{
  const {runId=''}=useParams()
  const [params,setParams]=useSearchParams()
  const [detail,setDetail]=useState<Detail>(null)
  const requestedBranch=params.get('branch')
  const requestedA=params.get('a')??''
  const requestedB=params.get('b')??''
  const view=params.get('filter')==='all'?'all':'differences'
  const branchesQuery=useQuery({
    queryKey:['run-branches',runId],queryFn:()=>listRunBranches(runId),
    enabled:Boolean(runId),retry:false,
  })
  const branches=branchesQuery.data?.run_branches??[]
  const validBranches=branches.every(b=>b.run_id===runId&&b.branch_id)&&
    new Set(branches.map(b=>b.branch_id)).size===branches.length
  const branchId=requestedBranch===null?branches[0]?.branch_id??'':
    branches.some(b=>b.branch_id===requestedBranch)?requestedBranch:''
  const selectedBranch=branches.find(b=>b.branch_id===branchId)
  const historyQuery=useInfiniteQuery({
    queryKey:['saved-revision-history',runId,branchId],
    queryFn:({pageParam})=>listSavedRevisionHistory(runId,branchId,{
      limit:50,...(pageParam===undefined?{}:{beforeSequence:pageParam})
    }),
    initialPageParam:undefined as number|undefined,
    getNextPageParam:last=>last.has_more_older?last.next_before_sequence??undefined:undefined,
    enabled:Boolean(branchId&&validBranches),retry:false
  })
  const history=historyQuery.data&&validBranches?
    validateReachableCompareHistory(runId,branchId,historyQuery.data.pages):null
  const a=history?.entries.find(x=>x.revision_id===requestedA)
  const b=history?.entries.find(x=>x.revision_id===requestedB)
  const canCompare=Boolean(a&&b&&a.revision_id!==b.revision_id)
  const comparisonQuery=useQuery({
    queryKey:['saved-states-compare',runId,branchId,requestedA,requestedB],
    queryFn:()=>compareSavedRevisions(runId,branchId,requestedA,requestedB),
    enabled:canCompare,retry:false
  })
  const compared=canCompare&&comparisonQuery.data&&history&&a&&b?
    projectSavedStateComparison(comparisonQuery.data,runId,branchId,a,b,history.head):null
  const rows=compared?.rows.filter(r=>view==='all'||r.status!=='unchanged')??[]
  const selectedRow=detail?.type==='row'?compared?.rows.find(x=>x.id===detail.id):null
  const stateEntry:SavedRevisionHistoryEntry|undefined=detail?.type==='state'?
    detail.side==='a'?a:b:undefined
  const stateQuery=useQuery({
    queryKey:['compare-readonly-state',runId,branchId,stateEntry?.revision_id],
    queryFn:()=>getSavedRevision(runId,branchId,stateEntry!.revision_id),
    enabled:Boolean(stateEntry&&canCompare&&compared),retry:false
  })
  const state=stateEntry&&stateQuery.data&&
    stateQuery.data.run_id===runId&&stateQuery.data.branch_id===branchId&&
    stateQuery.data.revision_id===stateEntry.revision_id&&
    stateQuery.data.content_hash===stateEntry.content_hash&&
    stateQuery.data.revision_branch_id===stateEntry.revision_branch_id?stateQuery.data:null
  const change=(key:string,value:string)=>{
    const next=new URLSearchParams(params)
    if(value)next.set(key,value);else next.delete(key)
    setDetail(null)
    setParams(next,{replace:true})
  }
  const setBranch=(value:string)=>{
    const next=new URLSearchParams(params)
    next.set('branch',value);next.delete('a');next.delete('b')
    setDetail(null);setParams(next,{replace:true})
  }
  const open=(r:CompareRow)=>setDetail({type:'row',id:r.id})
  const close=()=>setDetail(null)
  const back='/admin/runs/'+encodeURIComponent(runId)+'/branches'
  return <main className="saved-compare-page">
    <header className="page-intro">
      <p className="eyebrow">RUN → HISTORY & BRANCHES → COMPARE</p>
      <h2>Compare States A/B · Porovnání uložených stavů</h2>
      <p>Read-only comparison of two explicit reachable Saved Revisions.
        No Restore, Save, simulation, Viewer Branch or Working Draft changes.</p>
      <Link to={back}>← Back to History & Branches</Link>
    </header>
    <section className="panel" aria-label="Compare Saved Revision selection">
      <h3>States A → B</h3>
      <p className="status">Run: <code>{runId}</code> · Both states must be reachable through
        the same selected Branch. Cross-Branch Compare is not supported by this Saved API.
        Saved timestamps are not simulation positions.</p>
      {branchesQuery.isPending&&<p role="status">Loading Run Branches…</p>}
      {branchesQuery.error&&<p role="alert">{formatApiError(branchesQuery.error)}</p>}
      {branchesQuery.isSuccess&&!validBranches&&<p role="alert">
        Branch list has inconsistent Run identities.</p>}
      {branchesQuery.isSuccess&&requestedBranch!==null&&!selectedBranch&&
        <p role="alert">Selected Compare Branch does not belong to this Run.</p>}
      {validBranches&&branches.length===0&&<p role="status">No saved Run Branch available.</p>}
      {validBranches&&selectedBranch&&<div className="saved-compare-selectors">
        <label>Compare Branch
          <select aria-label="Compare Branch" value={branchId}
            onChange={event=>setBranch(event.target.value)}>
            {branches.map(b=><option key={b.branch_id} value={b.branch_id}>
              {b.display_name} ({b.branch_id})</option>)}
          </select>
        </label>
        {(['a','b'] as const).map(side=><label key={side}>
          {side==='a'?'State A · Before':'State B · After'}
          <select aria-label={'Compare state '+side.toUpperCase()}
            value={side==='a'?requestedA:requestedB}
            onChange={event=>change(side,event.target.value)}>
            <option value="">Select a reachable Saved Revision</option>
            {(history?.entries??[]).map(rev=>
              <option key={rev.revision_id} value={rev.revision_id}>
                #{rev.sequence} · {rev.kind} · {rev.revision_id}
                {rev.is_shared_revision?' · shared ancestor':''}
              </option>)}
          </select>
        </label>)}
      </div>}
      {historyQuery.isPending&&selectedBranch&&<p role="status">Loading reachable Saved Revisions…</p>}
      {historyQuery.error&&<p role="alert">{formatApiError(historyQuery.error)}</p>}
      {historyQuery.isSuccess&&selectedBranch&&!history&&<p role="alert">
        Invalid reachable Saved Revision history; Compare disabled.</p>}
      {history&&<p className="status">Loaded {history.entries.length} reachable revisions.
        {' '}{historyQuery.hasNextPage?'Older pages remain unloaded; Compare only loaded revisions.':
          'All reachable Saved Revisions loaded.'}
      </p>}
      {historyQuery.hasNextPage&&history&&<button type="button"
        disabled={historyQuery.isFetchingNextPage}
        onClick={()=>historyQuery.fetchNextPage()}>
        {historyQuery.isFetchingNextPage?'Loading older revisions…':'Load older revisions for Compare'}
      </button>}
      {historyQuery.isFetchNextPageError&&<p role="alert">Unable to load older Saved Revisions.</p>}
      {history&&(requestedA&&!a||requestedB&&!b)&&<p role="alert">
        Requested state is not in the loaded reachable history.
        {' '}{historyQuery.hasNextPage?'Load older revisions to verify its identity.':
          'There is no matching reachable Saved Revision.'}
      </p>}
      {history&&requestedA&&requestedA===requestedB&&<p role="alert">
        Select two different Saved Revisions to compare.</p>}
      <p className="status">Browsing Branch: <code>{branchId||'—'}</code>.
        This is not an Admin Branch activation.</p>
    </section>
    {canCompare&&<section className="panel" aria-label="Compare Saved Revision results">
      <div className="actions">
        <h3>Actual saved differences</h3>
        <label>Show
          <select aria-label="Compare display filter" value={view}
            onChange={event=>change('filter',event.target.value)}>
            <option value="differences">Differences only · Jen rozdíly</option>
            <option value="all">All · Vše</option>
          </select>
        </label>
      </div>
      {comparisonQuery.isPending&&<p role="status">Comparing canonical Saved Revisions…</p>}
      {comparisonQuery.error&&<p role="alert">{formatApiError(comparisonQuery.error)}</p>}
      {comparisonQuery.isSuccess&&!compared&&<p role="alert">
        Comparison identity/content hashes disagree with the selected states.</p>}
      {compared&&<>
        <p className="status">State A: <code>{a!.revision_id}</code> →
          State B: <code>{b!.revision_id}</code> · exact original source Branches:
          {' '}<code>{a!.revision_branch_id}</code> / <code>{b!.revision_branch_id}</code></p>
        <div className="run-world-metrics" aria-label="Compare Saved Revision totals">
          <div><span>Changed fields/components</span><strong>{compared.changed}</strong></div>
          <div><span>Unchanged components</span><strong>{compared.unchanged}</strong></div>
          <div><span>Run metadata fields</span><strong>{compared.runChanges}</strong></div>
          <div><span>Branch metadata fields</span><strong>{compared.branchChanges}</strong></div>
          <div><span>Snapshot components</span><strong>{compared.components}</strong></div>
        </div>
        <div className="actions">
          <button type="button" onClick={()=>setDetail({type:'state',side:'a'})}>
            Inspect state A read-only</button>
          <button type="button" onClick={()=>setDetail({type:'state',side:'b'})}>
            Inspect state B read-only</button>
        </div>
        {rows.length===0?<p role="status">{view==='differences'?
          'No differences in the supported Saved Revision comparison scope.':
          'Both Saved Revisions have no exposed comparable fields or components.'}</p>:
          <div className="table-responsive">
            <table aria-label="Saved State A B comparison table" className="saved-compare-table">
              <thead><tr><th>Section</th><th>Actual field / component</th>
                <th>Status</th><th>Evidence</th></tr></thead>
              <tbody>{rows.map(row=><tr key={row.id}>
                <td>{row.section==='run'?'Run metadata':row.section==='branch'?
                  'Branch metadata':'Saved component'}</td>
                <td><code>{row.key}</code></td>
                <td>{row.status}</td>
                <td><button type="button" onClick={()=>open(row)}
                  aria-label={'Inspect comparison '+row.id}>Inspect difference</button></td>
              </tr>)}</tbody>
            </table>
          </div>}
        <p className="status">Components are compared by canonical Saved fingerprints;
          no player, tournament, match, ranking or sporting-time difference is invented
          where field-level evidence is unavailable.</p>
      </>}
    </section>}
    {detail&&compared&&<aside className="saved-revision-detail-drawer" aria-label="Compare read-only detail">
      <div className="saved-revision-detail-drawer__heading">
        <strong>{detail.type==='state'?'Exact Saved Revision state':
          'Canonical Saved change evidence'}</strong>
        <button type="button" onClick={close}>Close Compare detail</button>
      </div>
      {detail.type==='row'&&selectedRow&&<>
        <h4>{selectedRow.section} · {selectedRow.key}</h4>
        <p>Status: <strong>{selectedRow.status}</strong></p>
        <div className="saved-compare-before-after">
          <section><h5>State A · Before</h5>
            <pre className="json-block">{pretty(selectedRow.before)}</pre></section>
          <section><h5>State B · After</h5>
            <pre className="json-block">{pretty(selectedRow.after)}</pre></section>
        </div>
        {selectedRow.section==='component'&&<p className="status">
          These are exact component fingerprints, NOT reconstructed player,
          match or ranking details.</p>}
      </>}
      {detail.type==='state'&&<>
        <h4>State {detail.side.toUpperCase()} · <code>{stateEntry?.revision_id}</code></h4>
        {stateQuery.isPending&&<p role="status">Loading immutable Saved Revision…</p>}
        {stateQuery.error&&<p role="alert">{formatApiError(stateQuery.error)}</p>}
        {stateQuery.isSuccess&&!state&&<p role="alert">
          Read-only Saved Revision identity or hash does not match selected state.</p>}
        {state&&<>
          <p>Source Branch: <code>{state.revision_branch_id}</code></p>
          <p>Parent: <code>{state.parent_revision_id??'Root'}</code></p>
          <p>Saved at: {state.created_at??'Unavailable'}</p>
          <p>Hash: <code>{state.content_hash_algorithm}:{state.content_hash}</code></p>
          <h5>Actual Saved change summary</h5>
          <pre className="json-block">{pretty(state.change_summary)}</pre>
          <h5>Exact Saved payload · read-only</h5>
          <pre className="json-block">{pretty(state.payload)}</pre>
        </>}
      </>}
    </aside>}
  </main>
}
