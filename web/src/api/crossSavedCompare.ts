/** Isolated read-only client: no simulation/Save/Restore command dispatch. */
import {ApiError} from './client'
import type {SavedRevisionHistoryEntry,SavedRevisionComponentComparison} from './types'
export type CrossSavedRevisionComparisonSource={
  run_id:string;branch_id:string;saved_head_revision_id:string;revision:SavedRevisionHistoryEntry
}
export type CrossSavedRevisionComparison={
  from_source:CrossSavedRevisionComparisonSource;to_source:CrossSavedRevisionComparisonSource
  run_changes:Record<string,{before:unknown;after:unknown;before_present:boolean;after_present:boolean}>
  branch_changes:Record<string,{before:unknown;after:unknown;before_present:boolean;after_present:boolean}>
  components:SavedRevisionComponentComparison[]
}
const API_BASE=import.meta.env.VITE_API_BASE_URL??'http://127.0.0.1:8000'
export async function compareCrossSavedRevisions(
  runAId:string,branchAId:string,revisionAId:string,runBId:string,branchBId:string,revisionBId:string
):Promise<CrossSavedRevisionComparison>{
  const query=new URLSearchParams({run_a_id:runAId,branch_a_id:branchAId,revision_a_id:revisionAId,
    run_b_id:runBId,branch_b_id:branchBId,revision_b_id:revisionBId})
  const response=await fetch(API_BASE+'/admin/cross-run-compare?'+query.toString(),{method:'GET',headers:{Accept:'application/json'}})
  if(!response.ok)throw new ApiError(await response.text()||'Saved comparison request failed',response.status)
  return response.json() as Promise<CrossSavedRevisionComparison>
}
