/** Exact Saved Revision A/B comparison presentation. This NEVER reconstructs
 * players, matches or rankings from opaque component hashes. */
import type {
  SavedRevisionHistoryEntry,SavedRevisionComparison,SavedRevisionHistoryPageResponse
} from '../api/types'

export type CompareRow={
  id:string;section:'run'|'branch'|'component';key:string
  status:'added'|'removed'|'changed'|'unchanged'
  before:unknown;after:unknown
}
export type CompareResult={
  rows:CompareRow[];changed:number;unchanged:number
  runChanges:number;branchChanges:number;components:number
}
export function validateReachableCompareHistory(
  runId:string,branchId:string,pages:SavedRevisionHistoryPageResponse[]
):{entries:SavedRevisionHistoryEntry[];head:string}|null{
  if(!runId||!branchId||!pages.length)return null
  const head=pages[0].saved_head_revision_id
  const total=pages[0].total_count
  if(!head||!Number.isSafeInteger(total)||total<0||
    pages.some(p=>p.run_id!==runId||p.branch_id!==branchId||
      p.saved_head_revision_id!==head||p.total_count!==total||
      !Array.isArray(p.saved_revisions)))return null
  const entries=pages.flatMap(p=>p.saved_revisions)
  if(entries.length>total)return null
  if(new Set(entries.map(x=>x.revision_id)).size!==entries.length||
     new Set(entries.map(x=>x.sequence)).size!==entries.length ||
     entries.some(x=>!x.revision_id||!x.revision_branch_id||
       !Number.isSafeInteger(x.sequence)||x.sequence<1||
       !x.content_hash||!x.content_hash_algorithm||
       (x.is_branch_head&&x.revision_id!==head)))return null
  // The read model promises ascending global sequence; pages may be requested newest first.
  const ascending=[...entries].sort((a,b)=>a.sequence-b.sequence)
  return {entries:ascending,head}
}
export function projectSavedStateComparison(
  data:SavedRevisionComparison,runId:string,branchId:string,
  a:SavedRevisionHistoryEntry,b:SavedRevisionHistoryEntry,
  knownHead:string
):CompareResult|null{
  if(data.run_id!==runId||data.branch_id!==branchId||
    data.saved_head_revision_id!==knownHead||
    !a.revision_id||!b.revision_id||a.revision_id===b.revision_id)return null
  const same=(x:SavedRevisionHistoryEntry,y:SavedRevisionHistoryEntry)=>
    x.revision_id===y.revision_id&&x.sequence===y.sequence&&
    x.content_hash===y.content_hash&&x.content_hash_algorithm===y.content_hash_algorithm&&
    x.revision_branch_id===y.revision_branch_id&&
    x.parent_revision_id===y.parent_revision_id
  if(!same(data.from_revision,a)||!same(data.to_revision,b))return null
  const validMap=(map:unknown):map is Record<string,{before:unknown;after:unknown}>=>
    !!map&&typeof map==='object'&&!Array.isArray(map)&&
    Object.values(map).every(x=>!!x&&typeof x==='object'&&!Array.isArray(x)&&
      'before' in x&&'after' in x)
  if(!validMap(data.run_changes)||!validMap(data.branch_changes)||
    !Array.isArray(data.components))return null
  const rows:CompareRow[]=[]
  for(const [section,map] of [
    ['run',data.run_changes],['branch',data.branch_changes]
  ] as const){
    for(const key of Object.keys(map).sort()){
      if(!key)return null
      rows.push({id:section+':'+key,section,key,status:'changed',
        before:map[key].before,after:map[key].after})
    }
  }
  const ids=new Set<string>()
  for(const c of data.components){
    if(!c||!c.component_key||ids.has(c.component_key)||
      !['added','removed','changed','unchanged'].includes(c.status)||
      (c.before_fingerprint!==null&&typeof c.before_fingerprint!=='string')||
      (c.after_fingerprint!==null&&typeof c.after_fingerprint!=='string'))
      return null
    // Do not infer component payloads from fingerprints.
    ids.add(c.component_key)
    rows.push({id:'component:'+c.component_key,section:'component',
      key:c.component_key,status:c.status,
      before:c.before_fingerprint,after:c.after_fingerprint})
  }
  const changed=rows.filter(row=>row.status!=='unchanged').length
  return {rows,changed,unchanged:rows.length-changed,
    runChanges:Object.keys(data.run_changes).length,
    branchChanges:Object.keys(data.branch_changes).length,
    components:data.components.length}
}
