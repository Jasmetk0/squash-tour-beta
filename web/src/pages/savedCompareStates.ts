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
  if(!runId||!branchId||!Array.isArray(pages)||pages.length===0)return null
  const head=pages[0]?.saved_head_revision_id
  const total=pages[0]?.total_count
  if(typeof head!=='string'||!head||typeof total!=='number'||!Number.isSafeInteger(total)||total<1)return null

  // This endpoint returns ascending sequences inside a page and fetches pages
  // newest first. Each cursor is the oldest sequence of the preceding page.
  // Merely sorting all rows masks malformed, overlapping or stale pagination
  // evidence and could present an incomplete A/B history as verified.
  const entries:SavedRevisionHistoryEntry[]=[]
  let newerPageOldestSequence:number|null=null
  for(let pageIndex=0;pageIndex<pages.length;pageIndex++){
    const page=pages[pageIndex]
    if(!page||page.run_id!==runId||page.branch_id!==branchId||
      page.saved_head_revision_id!==head||page.total_count!==total||
      !Array.isArray(page.saved_revisions)||page.saved_revisions.length===0||
      typeof page.has_more_older!=='boolean')return null

    let previousSequence:number|null=null
    for(const entry of page.saved_revisions){
      if(!entry||typeof entry.revision_id!=='string'||!entry.revision_id||
        typeof entry.revision_branch_id!=='string'||!entry.revision_branch_id||
        !Number.isSafeInteger(entry.sequence)||entry.sequence<1||
        typeof entry.content_hash!=='string'||!entry.content_hash||
        typeof entry.content_hash_algorithm!=='string'||!entry.content_hash_algorithm||
        (previousSequence!==null&&entry.sequence<=previousSequence)||
        (entry.is_branch_head&&entry.revision_id!==head))return null
      previousSequence=entry.sequence
      entries.push(entry)
    }

    const oldest=page.saved_revisions[0].sequence
    const newest=page.saved_revisions[page.saved_revisions.length-1].sequence
    if(newerPageOldestSequence!==null&&newest>=newerPageOldestSequence)return null
    if(pageIndex===0){
      // The selected Branch HEAD must be the latest entry of the first page.
      const latest=page.saved_revisions[page.saved_revisions.length-1]
      if(latest.revision_id!==head||latest.is_branch_head!==true)return null
    }else if(page.saved_revisions.some(entry=>entry.is_branch_head))return null

    if(page.has_more_older){
      if(page.next_before_sequence!==oldest)return null
    }else if(page.next_before_sequence!==null)return null
    // No page may follow an exhausted page.
    if(pageIndex<pages.length-1&&!page.has_more_older)return null
    newerPageOldestSequence=oldest
  }

  if(entries.length>total||
    (pages[pages.length-1].has_more_older?entries.length>=total:entries.length!==total)||
    new Set(entries.map(x=>x.revision_id)).size!==entries.length||
    new Set(entries.map(x=>x.sequence)).size!==entries.length)return null
  // Shared original-source revisions remain valid; only the selected Branch
  // HEAD must match the pagination authority, not every revision's owner.
  return {entries:[...entries].sort((a,b)=>a.sequence-b.sequence),head}
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
    // Server statuses are part of the comparison proof, not a cosmetic label.
    // Reject inconsistent fingerprint presence/equality rather than reporting a
    // forged "unchanged" component or an invented addition/removal.
    const before=c.before_fingerprint,after=c.after_fingerprint
    if((c.status==='added'&&(before!==null||after===null))||
       (c.status==='removed'&&(before===null||after!==null))||
       (c.status==='changed'&&(before===null||after===null||before===after))||
       (c.status==='unchanged'&&(before===null||after===null||before!==after)))return null
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
