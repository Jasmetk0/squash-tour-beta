/** Independent Run/Branch/reachable Saved selector. All operations are GETs. */
import {useInfiniteQuery,useQuery} from '@tanstack/react-query'
import {listRunBranches,listSavedRevisionHistory} from '../api/client'
import type {RunContainer} from '../api/types'
import {formatApiError} from '../utils/apiErrors'
import {validateReachableCompareHistory} from './savedCompareStates'
import type {CrossSource} from './crossSavedCompare'
export type CrossSelection={run:string;branch:string;revision:string}
export function useCrossSource(selection:CrossSelection,runs:RunContainer[],validRuns:boolean){
  const {run,branch,revision}=selection
  const validRun=validRuns&&runs.some(r=>r.run_id===run)
  const branches=useQuery({queryKey:['cross-compare-branches',run],queryFn:()=>listRunBranches(run),
    enabled:validRun,retry:false,refetchOnWindowFocus:false,refetchOnReconnect:false})
  const raw=branches.data?.run_branches
  const entries=Array.isArray(raw)?raw:[]
  const validBranches=branches.isSuccess&&!branches.isFetching&&Array.isArray(raw)&&entries.every(b=>b&&b.run_id===run&&typeof b.branch_id==='string'&&b.branch_id)&&
    new Set(entries.map(b=>b.branch_id)).size===entries.length
  const validBranch=validRun&&validBranches&&entries.some(b=>b.branch_id===branch)
  const history=useInfiniteQuery({queryKey:['cross-compare-history',run,branch],
    queryFn:({pageParam})=>listSavedRevisionHistory(run,branch,{limit:50,
      ...(pageParam===undefined?{}:{beforeSequence:pageParam})}),initialPageParam:undefined as number|undefined,
    getNextPageParam:last=>last.has_more_older?last.next_before_sequence??undefined:undefined,
    enabled:validBranch,retry:false,refetchOnWindowFocus:false,refetchOnReconnect:false})
  const verified=validBranch&&history.data&&!history.isFetching?
    validateReachableCompareHistory(run,branch,history.data.pages):null
  const selected=verified?.entries.find(r=>r.revision_id===revision)
  const source:CrossSource|null=selected&&verified?{runId:run,branchId:branch,head:verified.head,revision:selected}:null
  return {branches,entries,validRun,validBranches,validBranch,history,verified,source}
}
export function SavedCrossRunSource({side,selection,onChange,runs,validRuns,state,cs}:{
  side:'A'|'B';selection:CrossSelection;onChange:(next:CrossSelection)=>void;
  runs:RunContainer[];validRuns:boolean;state:ReturnType<typeof useCrossSource>;cs:boolean
}){
  const T=(en:string,cz:string)=>cs?cz:en
  return <fieldset className="panel"><legend>{T('Source','Zdroj')} {side}</legend>
    <label>{side} Run <select aria-label={side+' Run'} value={selection.run} disabled={!validRuns}
      onChange={e=>onChange({run:e.target.value,branch:'',revision:''})}>
      <option value="">{T('Select Run','Vyber Run')}</option>
      {(validRuns?runs:[]).map(r=><option key={r.run_id} value={r.run_id}>{r.display_name||r.run_id}</option>)}
    </select></label>
    <label>{T('Branch','Větev')} <select aria-label={side+' '+T('Branch','Větev')}
      value={selection.branch} disabled={!state.validRun||!state.validBranches}
      onChange={e=>onChange({...selection,branch:e.target.value,revision:''})}>
      <option value="">{T('Select Branch','Vyber větev')}</option>
      {(state.validBranches?state.entries:[]).map(b=><option key={b.branch_id} value={b.branch_id}>{b.display_name} · {b.branch_id}</option>)}
    </select></label>
    <label>{T('Saved Revision','Uložená revize')} <select aria-label={side+' '+T('Saved Revision','Uložená revize')}
      value={selection.revision} disabled={!state.verified}
      onChange={e=>onChange({...selection,revision:e.target.value})}>
      <option value="">{T('Select reachable revision','Vyber dostupnou revizi')}</option>
      {(state.verified?.entries??[]).map(r=><option key={r.revision_id} value={r.revision_id}>
        #{r.sequence} · {r.kind} · {r.revision_id}</option>)}
    </select></label>
    {state.branches.isFetching||state.history.isFetching?<p role="status">{T('Checking saved sources…','Ověřuji uložené zdroje…')}</p>:null}
    {state.branches.error&&<p role="alert">{formatApiError(state.branches.error)}</p>}
    {state.history.error&&<p role="alert">{formatApiError(state.history.error)}</p>}
    {state.branches.isSuccess&&!state.branches.isFetching&&!state.validBranches&&<p role="alert">{T('Branch list identities are inconsistent.','Identity v seznamu větví nesouhlasí.')}</p>}
    {selection.run&&!state.validRun&&validRuns&&<p role="alert">{T('Run is unavailable.','Run není dostupný.')}</p>}
    {selection.branch&&state.validBranches&&!state.validBranch&&<p role="alert">{T('Branch does not belong to this Run.','Větev nepatří do tohoto Runu.')}</p>}
    {state.history.isSuccess&&!state.history.isFetching&&!state.verified&&<p role="alert">{T('Saved history identity is inconsistent.','Identita uložené historie nesouhlasí.')}</p>}
    {selection.revision&&state.verified&&!state.source&&<p role="alert">{T('Revision is not in loaded reachable history.','Revize není v načtené dostupné historii.')}</p>}
    {state.verified&&state.history.hasNextPage&&<button type="button" disabled={state.history.isFetching}
      onClick={()=>state.history.fetchNextPage()}>{T('Load older revisions','Načíst starší revize')}</button>}
    {state.source&&<p className="status">Run: <code>{selection.run}</code> · {T('Browsing Branch','Prohlížená větev')}: <code>{selection.branch}</code><br/>
      {T('Original source Branch','Původní zdrojová větev')}: <code>{state.source.revision.revision_branch_id}</code><br/>
      Saved HEAD: <code>{state.source.head}</code><br/>
      {T('Saved at','Uloženo')}: {state.source.revision.created_at??'—'}<br/>
      {T('Saved timestamp is not simulation time.','Čas uložení není čas simulace.')}</p>}
  </fieldset>
}
