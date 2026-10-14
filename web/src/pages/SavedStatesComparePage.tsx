/** Dedicated read-only Saved Revision Compare A/B (Master v80 §27.22). */
import {useState} from 'react'
import {useInfiniteQuery,useQuery} from '@tanstack/react-query'
import {Link,useParams,useSearchParams} from 'react-router-dom'
import {
  compareSavedRevisions,getSavedRevision,listRunBranches,listSavedRevisionHistory
} from '../api/client'
import type {SavedRevisionHistoryEntry} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {useLanguage} from '../i18n/LanguageContext'
import {historyText} from '../i18n/historyText'
import {projectSavedStateComparison,validateReachableCompareHistory} from './savedCompareStates'
import type {CompareRow} from './savedCompareStates'
import {SavedEditionCompareSection} from './SavedEditionCompareSection'

type Detail={type:'row';id:string}|{type:'state';side:'a'|'b'}|null
const pretty=(v:unknown,language:'en'|'cs')=>v===undefined?historyText('Not provided',language):JSON.stringify(v,null,2)??String(v)

export function SavedStatesComparePage():JSX.Element{
  const {language}=useLanguage()
  const T=(english:string)=>historyText(english,language)
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
      <p className="eyebrow">{T("RUN → HISTORY & BRANCHES → COMPARE")}</p>
      <h2>{T("Compare States A/B · Porovnání uložených stavů")}</h2>
      <p>{T("Read-only comparison of two explicit reachable Saved Revisions. No Restore, Save, simulation, Viewer Branch or Working Draft changes.")}</p>
      <Link to={back}>{T("← Back to History & Branches")}</Link>
    </header>
    <section className="panel" aria-label={T("Compare Saved Revision selection")}>
      <h3>{T("States A → B")}</h3>
      <p className="status">{T('Run:')} <code>{runId}</code> {T('· Both states must be reachable through the same selected Branch. Cross-Branch Compare is not supported by this Saved API. Saved timestamps are not simulation positions.')}</p>
      {branchesQuery.isPending&&<p role="status">{T("Loading Run Branches…")}</p>}
      {branchesQuery.error&&<p role="alert">{formatApiError(branchesQuery.error)}</p>}
      {branchesQuery.isSuccess&&!validBranches&&<p role="alert">
        {T("Branch list has inconsistent Run identities.")}</p>}
      {branchesQuery.isSuccess&&requestedBranch!==null&&!selectedBranch&&
        <p role="alert">{T("Selected Compare Branch does not belong to this Run.")}</p>}
      {validBranches&&branches.length===0&&<p role="status">{T("No saved Run Branch available.")}</p>}
      {validBranches&&selectedBranch&&<div className="saved-compare-selectors">
        <label>{T("Compare Branch")}
          <select aria-label={T("Compare Branch")} value={branchId}
            onChange={event=>setBranch(event.target.value)}>
            {branches.map(b=><option key={b.branch_id} value={b.branch_id}>
              {b.display_name} ({b.branch_id})</option>)}
          </select>
        </label>
        {(['a','b'] as const).map(side=><label key={side}>
          {side==='a'?T("State A · Before"):T("State B · After")}
          <select aria-label={'Compare state '+side.toUpperCase()}
            value={side==='a'?requestedA:requestedB}
            onChange={event=>change(side,event.target.value)}>
            <option value="">{T("Select a reachable Saved Revision")}</option>
            {(history?.entries??[]).map(rev=>
              <option key={rev.revision_id} value={rev.revision_id}>
                #{rev.sequence} · {rev.kind} · {rev.revision_id}
                {rev.is_shared_revision?' · shared ancestor':''}
              </option>)}
          </select>
        </label>)}
      </div>}
      {historyQuery.isPending&&selectedBranch&&<p role="status">{T("Loading reachable Saved Revisions…")}</p>}
      {historyQuery.error&&<p role="alert">{formatApiError(historyQuery.error)}</p>}
      {historyQuery.isSuccess&&selectedBranch&&!history&&<p role="alert">
        {T("Invalid reachable Saved Revision history; Compare disabled.")}</p>}
      {history&&<p className="status">{T('Loaded')} {history.entries.length} {T('reachable revisions.')}
        {' '}{historyQuery.hasNextPage?T("Older pages remain unloaded; Compare only loaded revisions."):
          T("All reachable Saved Revisions loaded.")}
      </p>}
      {historyQuery.hasNextPage&&history&&<button type="button"
        disabled={historyQuery.isFetchingNextPage}
        onClick={()=>historyQuery.fetchNextPage()}>
        {historyQuery.isFetchingNextPage?T("Loading older revisions…"):T("Load older revisions for Compare")}
      </button>}
      {historyQuery.isFetchNextPageError&&<p role="alert">{T("Unable to load older Saved Revisions.")}</p>}
      {history&&(requestedA&&!a||requestedB&&!b)&&<p role="alert">
        {T("Requested state is not in the loaded reachable history.")}
        {' '}{historyQuery.hasNextPage?T("Load older revisions to verify its identity."):
          T("There is no matching reachable Saved Revision.")}
      </p>}
      {history&&requestedA&&requestedA===requestedB&&<p role="alert">
        {T("Select two different Saved Revisions to compare.")}</p>}
      <p className="status">{T('Browsing Branch:')} <code>{branchId||'—'}</code>.
        {T('This is not an Admin Branch activation.')}</p>
    </section>
    {canCompare&&<section className="panel" aria-label={T("Compare Saved Revision results")}>
      <div className="actions">
        <h3>{T("Actual saved differences")}</h3>
        <label>{T("Show")}
          <select aria-label={T("Compare display filter")} value={view}
            onChange={event=>change('filter',event.target.value)}>
            <option value="differences">{T("Differences only · Jen rozdíly")}</option>
            <option value="all">{T("All · Vše")}</option>
          </select>
        </label>
      </div>
      {comparisonQuery.isPending&&<p role="status">{T("Comparing canonical Saved Revisions…")}</p>}
      {comparisonQuery.error&&<p role="alert">{formatApiError(comparisonQuery.error)}</p>}
      {comparisonQuery.isSuccess&&!compared&&<p role="alert">
        {T("Comparison identity/content hashes disagree with the selected states.")}</p>}
      {compared&&<>
        <p className="status">{T("State A:")} <code>{a!.revision_id}</code> →
          {T('State B:')} <code>{b!.revision_id}</code> · {T('exact original source Branches:')}
          {' '}<code>{a!.revision_branch_id}</code> / <code>{b!.revision_branch_id}</code></p>
        <div className="run-world-metrics" aria-label={T("Compare Saved Revision totals")}>
          <div><span>{T("Changed fields/components")}</span><strong>{compared.changed}</strong></div>
          <div><span>{T("Unchanged components")}</span><strong>{compared.unchanged}</strong></div>
          <div><span>{T("Run metadata fields")}</span><strong>{compared.runChanges}</strong></div>
          <div><span>{T("Branch metadata fields")}</span><strong>{compared.branchChanges}</strong></div>
          <div><span>{T("Snapshot components")}</span><strong>{compared.components}</strong></div>
        </div>
        <div className="actions">
          <button type="button" onClick={()=>setDetail({type:'state',side:'a'})}>
            {T("Inspect state A read-only")}</button>
          <button type="button" onClick={()=>setDetail({type:'state',side:'b'})}>
            {T("Inspect state B read-only")}</button>
        </div>
        {rows.length===0?<p role="status">{view==='differences'?
          T("No differences in the supported Saved Revision comparison scope."):
          T("Both Saved Revisions have no exposed comparable fields or components.")}</p>:
          <div className="table-responsive">
            <table aria-label={T("Saved State A B comparison table")} className="saved-compare-table">
              <thead><tr><th>{T("Section")}</th><th>{T("Actual field / component")}</th>
                <th>{T("Status")}</th><th>{T("Evidence")}</th></tr></thead>
              <tbody>{rows.map(row=><tr key={row.id}>
                <td>{row.section==='run'?T("Run metadata"):row.section==='branch'?
                  T("Branch metadata"):T("Saved component")}</td>
                <td><code>{row.key}</code></td>
                <td>{T(row.status)}</td>
                <td><button type="button" onClick={()=>open(row)}
                  aria-label={T('Inspect comparison')+' '+row.id}>{T("Inspect difference")}</button></td>
              </tr>)}</tbody>
            </table>
          </div>}
        <p className="status">{T("Components are compared by canonical Saved fingerprints; no player, tournament, match, ranking or sporting-time difference is invented where field-level evidence is unavailable.")}</p>
      </>}
    </section>}
    {compared&&a&&b&&<SavedEditionCompareSection
      key={[runId,branchId,a.revision_id,b.revision_id].join(':')}
      runId={runId} branchId={branchId} a={a} b={b}/>}
    {detail&&compared&&<aside className="saved-revision-detail-drawer" aria-label={T("Compare read-only detail")}>
      <div className="saved-revision-detail-drawer__heading">
        <strong>{detail.type==='state'?T("Exact Saved Revision state"):
          T("Canonical Saved change evidence")}</strong>
        <button type="button" onClick={close}>{T("Close Compare detail")}</button>
      </div>
      {detail.type==='row'&&selectedRow&&<>
        <h4>{selectedRow.section} · {selectedRow.key}</h4>
        <p>{T('Status:')} <strong>{T(selectedRow.status)}</strong></p>
        <div className="saved-compare-before-after">
          <section><h5>{T("State A · Before")}</h5>
            <pre className="json-block">{pretty(selectedRow.before,language)}</pre></section>
          <section><h5>{T("State B · After")}</h5>
            <pre className="json-block">{pretty(selectedRow.after,language)}</pre></section>
        </div>
        {selectedRow.section==='component'&&<p className="status">
          {T("These are exact component fingerprints, NOT reconstructed player, match or ranking details.")}</p>}
      </>}
      {detail.type==='state'&&<>
        <h4>{T('State')} {detail.side.toUpperCase()} · <code>{stateEntry?.revision_id}</code></h4>
        {stateQuery.isPending&&<p role="status">{T("Loading immutable Saved Revision…")}</p>}
        {stateQuery.error&&<p role="alert">{formatApiError(stateQuery.error)}</p>}
        {stateQuery.isSuccess&&!state&&<p role="alert">
          {T("Read-only Saved Revision identity or hash does not match selected state.")}</p>}
        {state&&<>
          <p>{T('Source Branch:')} <code>{state.revision_branch_id}</code></p>
          <p>{T("Parent:")} <code>{state.parent_revision_id??'Root'}</code></p>
          <p>{T("Saved at:")} {state.created_at??T("Unavailable")}</p>
          <p>{T("Hash:")} <code>{state.content_hash_algorithm}:{state.content_hash}</code></p>
          <h5>{T("Actual Saved change summary")}</h5>
          <pre className="json-block">{pretty(state.change_summary,language)}</pre>
          <h5>{T("Exact Saved payload · read-only")}</h5>
          <pre className="json-block">{pretty(state.payload,language)}</pre>
        </>}
      </>}
    </aside>}
  </main>
}
