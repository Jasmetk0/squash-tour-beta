/** Focused future prospect cohort API; intentionally separate from legacy simulation client. */

export type NativeFutureCohortRequest = {
  schema_version: 'native_calendar_cohort_request.v1'
  world_package_id: string
  season_index: number
  base_annual_intake_target: number
  country_code: string | null
}

export type NativeFutureCohortPreview = {
  schema_version: 'native_calendar_cohort_preview.v1'
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  review_fingerprint: string
  previous_run_prospect_source_fingerprint: string | null
  record_content_fingerprint: string
  prepared_profile_count: number
  first_prepared_prospects: { prospect_id: string; country_code: string; season_week: number }[]
  season_label: string
  materialization_supported: boolean
  materialization_blocker: string | null
  request: NativeFutureCohortRequest
  preview_only: true
}

const base=import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
const url=(run:string,branch:string)=>
  `${base}/admin/players/runs/${encodeURIComponent(run)}/branches/${encodeURIComponent(branch)}/intake/native-calendar`

async function post<T>(path:string,body:unknown):Promise<T>{
  const response=await fetch(path,{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify(body),
  })
  if(!response.ok)throw new Error(await response.text()||'Native prospect request failed')
  return await response.json() as T
}

export async function previewFutureNativeProspects(
  run: string, branch: string, requestBody: NativeFutureCohortRequest,
): Promise<NativeFutureCohortPreview> {
  const result=await post<NativeFutureCohortPreview>(url(run,branch)+'/preview',requestBody)
  if(result.run_id!==run||result.branch_id!==branch||result.schema_version!=='native_calendar_cohort_preview.v1'
    ||!result.preview_only||!/^([0-9a-f]{64})$/.test(result.review_fingerprint))
    throw Error('Native future cohort preview source is not authoritative')
  return result
}

export async function materializeFutureNativeProspects(
  run: string, branch: string, review: NativeFutureCohortPreview,
  label: string, reason: string,
): Promise<{run_id:string;branch_id:string;created_count:number;requires_manual_source_save:boolean}> {
  const result=await post<{run_id:string;branch_id:string;created_count:number;requires_manual_source_save:boolean}>(
    url(run,branch)+'/materialize',{
      request:review.request,expected_saved_head:review.saved_head_revision_id,
      expected_review_fingerprint:review.review_fingerprint,explicit_confirmation:true,
      audit_label:label,audit_reason:reason,
    },
  )
  if(result.run_id!==run||result.branch_id!==branch||!result.requires_manual_source_save)
    throw Error('Native future cohort materialization scope is invalid')
  return result
}
