/** Cross-source identity proof; no current state substitutes for either Saved source. */
import type {SavedRevisionHistoryEntry} from '../api/types'
import type {CrossSavedRevisionComparison} from '../api/crossSavedCompare'
import {projectSavedComparisonRows} from './savedCompareStates'
export type CrossSource={runId:string;branchId:string;head:string;revision:SavedRevisionHistoryEntry}
const record=(v:unknown):v is Record<string,unknown>=>!!v&&typeof v==='object'&&!Array.isArray(v)
const fields=['revision_id','revision_branch_id','sequence','parent_revision_id','kind',
  'payload_schema_version','content_hash_algorithm','content_hash','created_at','is_shared_revision','is_branch_head'] as const
export function projectCrossSavedStateComparison(value:unknown,a:CrossSource,b:CrossSource){
  if(!record(value))return null
  const matches=(v:unknown,s:CrossSource)=>{
    if(!record(v)||v.run_id!==s.runId||v.branch_id!==s.branchId||
      v.saved_head_revision_id!==s.head||!record(v.revision))return false
    const r=v.revision
    return fields.every(k=>r[k]===s.revision[k])
  }
  if(!matches(value.from_source,a)||!matches(value.to_source,b))return null
  const data=value as CrossSavedRevisionComparison
  const result=projectSavedComparisonRows(data)
  if(!result)return null
  for(const map of [data.run_changes,data.branch_changes]){
    for(const change of Object.values(map)){
      if(typeof change.before_present!=='boolean'||typeof change.after_present!=='boolean'||
        (!change.before_present&&change.before!==null)||(!change.after_present&&change.after!==null))return null
    }
  }
  return {...result,rows:result.rows.map(row=>{
    if(row.section==='component')return row
    const change=(row.section==='run'?data.run_changes:data.branch_changes)[row.key]
    return {...row,before:change.before_present?row.before:undefined,after:change.after_present?row.after:undefined}
  })}
}
