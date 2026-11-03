/** Read-only ATP 1990–2026 source manifest and bounded Run Apply review. */
export const ATP_REFERENCE_SETUP_ID = 'atp_tour_1990_2026_reference_setup'
export const ATP_REFERENCE_CHILD_IDS = [
  'atp_tour_1990_2026_category',
  'atp_tour_1990_2026_series'
] as const

export type ATPReferenceChild = {
  package_id: string
  package_type: 'Category' | 'Series'
  source_version: number
  source_fingerprint: string
  entity_count: number
}
export type ATPReferenceCatalog = {
  package_id: string
  package_type: 'Setup'
  source_version: number
  source_fingerprint: string
  reference_span: { from: number; to: number }
  provisional_years: number[]
  usage: string
  children: ATPReferenceChild[]
}
export type ATPReferencePreview = {
  run_id: string
  branch_id: string
  saved_head_revision_id: string
  draft_version: number
  current_state_fingerprint: string | null
  preview_fingerprint: string
  document_identity: {
    package_type: 'Setup'
    package_id: string
    source_version: number
    source_fingerprint: string
  }
  additions: string[]
  unchanged: string[]
  updates: string[]
  not_included: string[]
  unresolved: string[]
  automatically_resolvable: string[]
  invalid: string[]
  conflicts: string[]
}
export type ATPReferenceConfirm = {
  command_id: string
  expected_head_revision_id: string
  expected_draft_version: number
  expected_state_fingerprint: string | null
  expected_preview_fingerprint: string
  conflict_resolutions: Record<string,'keep_run'|'use_source'>
}
const fingerprint = (x:unknown):x is string =>
  typeof x === 'string' && /^[0-9a-f]{64}$/.test(x)
const record = (x:unknown):x is Record<string,unknown> =>
  Boolean(x && typeof x==='object' && !Array.isArray(x))
const strings = (x:unknown):x is string[] =>
  Array.isArray(x) && x.every(y=>typeof y==='string')

/** Fail closed when response identity or its child sources are inconsistent. */
export function validATPCatalog(input:unknown):input is ATPReferenceCatalog {
  if(!record(input)||input.package_id!==ATP_REFERENCE_SETUP_ID||
     input.package_type!=='Setup'||input.source_version!==1||
     !fingerprint(input.source_fingerprint)||input.usage!=='source_reference_only_no_playable_calendar'||
     !record(input.reference_span)||input.reference_span.from!==1990||
     input.reference_span.to!==2026||!Array.isArray(input.provisional_years)||
     input.provisional_years.length!==1||input.provisional_years[0]!==2026||
     !Array.isArray(input.children)||input.children.length!==2)return false
  return input.children.every((item,i)=>{
    const child=record(item)?item:{}
    return child.package_id===ATP_REFERENCE_CHILD_IDS[i] &&
      child.package_type===(i===0?'Category':'Series') &&
      child.source_version===1 && fingerprint(child.source_fingerprint) &&
      typeof child.entity_count==='number' && Number.isSafeInteger(child.entity_count) &&
      child.entity_count>0
  })
}

/** Only exact, fresh, server-sourced Run/Branch previews can enable confirm. */
export function reviewedATPReference(
  catalog:ATPReferenceCatalog, preview:ATPReferencePreview,
  runId:string, branchId:string
):boolean {
  if(!validATPCatalog(catalog) || !record(preview))return false
  const doc=preview.document_identity
  return record(doc) && preview.run_id===runId && preview.branch_id===branchId &&
    Boolean(preview.saved_head_revision_id) &&
    Number.isSafeInteger(preview.draft_version) && preview.draft_version>=0 &&
    (preview.current_state_fingerprint===null||fingerprint(preview.current_state_fingerprint)) &&
    fingerprint(preview.preview_fingerprint) &&
    doc.package_type==='Setup' && doc.package_id===catalog.package_id &&
    doc.source_version===catalog.source_version &&
    doc.source_fingerprint===catalog.source_fingerprint &&
    ['additions','unchanged','updates','not_included','unresolved',
     'automatically_resolvable','invalid','conflicts'].every(key =>
       strings(preview[key as keyof ATPReferencePreview]))
}
