/** ATP 1990–2026 date reference, NOT executable tennis/squash Calendar. */
import type { ATPReferencePreview, ATPReferenceConfirm } from './atpReferencePackages'
export type { ATPReferencePreview, ATPReferenceConfirm }
export const ATP_CALENDAR_REFERENCE_SETUP_ID = 'atp_tour_1990_2026_calendar_reference_setup'
export const ATP_CALENDAR_REFERENCE_CHILD_IDS = [
  'atp_tour_1990_2026_category',
  'atp_tour_1990_2026_series',
  'atp_tour_1990_2026_calendar'
] as const

export type ATPCalendarReferenceCatalog = {
  package_id:string
  package_type:'Setup'
  source_version:number
  source_fingerprint:string
  reference_span:{from:number;to:number}
  dated_years:number[]
  undated_years:number[]
  provisional_years:number[]
  usage:'source_reference_only_no_playable_calendar'
  children:{
    package_id:string
    package_type:'Category'|'Series'|'Calendar'
    source_version:number
    source_fingerprint:string
    entity_count:number
  }[]
}

const record=(v:unknown):v is Record<string,unknown> =>
  Boolean(v&&typeof v==='object'&&!Array.isArray(v))
const fingerprint=(v:unknown):v is string =>
  typeof v==='string' && /^[0-9a-f]{64}$/.test(v)
const uniqueSortedYears=(v:unknown,first:number,last:number):v is number[] =>
  Array.isArray(v) && v.length===last-first+1 &&
  v.every((year,i)=>year===first+i)

export function validATPCalendarCatalog(v:unknown):v is ATPCalendarReferenceCatalog {
  if(!record(v)||v.package_id!==ATP_CALENDAR_REFERENCE_SETUP_ID||
    v.package_type!=='Setup'||v.source_version!==1||
    !fingerprint(v.source_fingerprint)||v.usage!=='source_reference_only_no_playable_calendar'||
    !record(v.reference_span)||v.reference_span.from!==1990||v.reference_span.to!==2026||
    !uniqueSortedYears(v.dated_years,2025,2026)||
    !uniqueSortedYears(v.undated_years,1990,2024)||
    !uniqueSortedYears(v.provisional_years,2026,2026)||
    !Array.isArray(v.children)||v.children.length!==3)return false
  return v.children.every((item:unknown,i:number)=>{
    if(!record(item))return false
    const count=[11,164,150]
    return item.package_id===ATP_CALENDAR_REFERENCE_CHILD_IDS[i] &&
      item.package_type===['Category','Series','Calendar'][i] &&
      item.source_version===1 && fingerprint(item.source_fingerprint) &&
      item.entity_count===count[i]
  })
}

/** No user-controlled or stale source identity may enable mutation. */
export function reviewedATPCalendarReference(
  catalog:ATPCalendarReferenceCatalog,preview:ATPReferencePreview,
  runId:string,branchId:string
):boolean {
  if(!validATPCalendarCatalog(catalog)||!record(preview))return false
  const doc=preview.document_identity
  return record(doc)&&preview.run_id===runId&&preview.branch_id===branchId&&
    typeof preview.saved_head_revision_id==='string'&&!!preview.saved_head_revision_id&&
    Number.isSafeInteger(preview.draft_version)&&preview.draft_version>=0&&
    (preview.current_state_fingerprint===null||fingerprint(preview.current_state_fingerprint))&&
    fingerprint(preview.preview_fingerprint)&&
    doc.package_type==='Setup'&&doc.package_id===catalog.package_id&&
    doc.source_version===catalog.source_version&&
    doc.source_fingerprint===catalog.source_fingerprint&&
    ['additions','unchanged','updates','not_included','unresolved',
     'automatically_resolvable','invalid','conflicts'].every(k=>
        Array.isArray(preview[k as keyof ATPReferencePreview])&&
        (preview[k as keyof ATPReferencePreview] as unknown[]).every(x=>typeof x==='string'))
}
