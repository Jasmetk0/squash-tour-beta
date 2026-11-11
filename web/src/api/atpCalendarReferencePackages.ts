/** ATP 1990–2026 date reference, NOT executable tennis/squash Calendar. */
import type { ATPReferencePreview, ATPReferenceConfirm } from './atpReferencePackages'
export type { ATPReferencePreview, ATPReferenceConfirm }
export const ATP_CALENDAR_REFERENCE_SETUP_ID = 'atp_tour_1990_2026_calendar_reference_setup'
export const ATP_CALENDAR_REFERENCE_CHILD_IDS = [
  'atp_tour_1990_2026_category',
  'atp_tour_1990_2026_series',
  'atp_tour_1990_2026_calendar',
  'atp_squash_sporting_profiles'
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
  usage:'source_reference_only_no_playable_calendar'|'saved_reference_calendar_with_explicit_squash_sporting_profiles'
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
const canonicalYearPartition=(dated:unknown,undated:unknown):boolean => {
  if(!Array.isArray(dated)||!Array.isArray(undated)||dated.length<1)return false
  const ascending=(years:unknown[]):boolean=>years.every((year,i)=>
    typeof year==='number'&&Number.isSafeInteger(year)&&year>=1990&&year<=2026&&
    (i===0||(typeof years[i-1]==='number'&&year>Number(years[i-1]))))
  const combined=[...dated,...undated].sort((a,b)=>a-b)
  return ascending(dated)&&ascending(undated)&&combined.length===37&&
    combined.every((year,i)=>year===1990+i)&&dated.includes(2026)
}

export function validATPCalendarCatalog(v:unknown):v is ATPCalendarReferenceCatalog {
  if(!record(v)||v.package_id!==ATP_CALENDAR_REFERENCE_SETUP_ID||
    v.package_type!=='Setup'||(v.source_version!==1&&v.source_version!==2)||
    !fingerprint(v.source_fingerprint)||v.usage!==(v.source_version===1?'source_reference_only_no_playable_calendar':'saved_reference_calendar_with_explicit_squash_sporting_profiles')||
    !record(v.reference_span)||v.reference_span.from!==1990||v.reference_span.to!==2026||
    !canonicalYearPartition(v.dated_years,v.undated_years)||
    !Array.isArray(v.provisional_years)||v.provisional_years.length!==1||
    v.provisional_years[0]!==2026||
    !Array.isArray(v.children)||v.children.length!==(v.source_version===1?3:4))return false
  return v.children.every((item:unknown,i:number)=>{
    if(!record(item))return false
    const validCount=i<2 ? item.entity_count===[11,164][i] :
      typeof item.entity_count==='number' &&
      Number.isSafeInteger(item.entity_count) &&
      item.entity_count>=(i===3?1:37) && item.entity_count<=10000
    return item.package_id===ATP_CALENDAR_REFERENCE_CHILD_IDS[i] &&
      item.package_type===['Category','Series','Calendar','Category'][i] &&
      (i===3?typeof item.source_version==='number'&&Number.isSafeInteger(item.source_version)&&item.source_version>=1:item.source_version===1) && fingerprint(item.source_fingerprint) &&
      validCount
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

export type ATPCalendarReferenceYearView = {
  year:number
  package_id:'atp_tour_1990_2026_calendar'
  source_fingerprint:string
  read_only:true
  run_mutated:false
  coverage:{
    atp_season_year:number
    roster_series_count:number
    dated_series_count:number
    undated_series_ids:string[]
    known_not_held_series_ids:string[]
    date_coverage_state:string
    year_source_status:string
    year_source_url:string|null
  }
  events:{
    series_id:string
    category_id:string
    start_date:string
    end_date:string
    start_year_week:{iso_year:number;iso_week:number}
    end_year_week:{iso_year:number;iso_week:number}
    iso_weeks_occupied:{iso_year:number;iso_week:number}[]
    source_url:string
    year_source_state:string
  }[]
}

const positiveInt=(v:unknown):v is number =>
  typeof v==='number' && Number.isSafeInteger(v) && v>=0
const dateString=(v:unknown):v is string =>
  typeof v==='string' && /^\d{4}-\d{2}-\d{2}$/.test(v)
const isoYearWeek=(v:unknown):boolean =>
  record(v)&&positiveInt(v.iso_year)&&positiveInt(v.iso_week)&&
  v.iso_week>=1&&v.iso_week<=53

/** Match the server's exact Calendar child fingerprint before rendering. */
export function validATPCalendarYearView(
  value:unknown,expectedYear:number,calendarFingerprint:string
):value is ATPCalendarReferenceYearView {
  if(!record(value)||value.year!==expectedYear||
     value.package_id!=='atp_tour_1990_2026_calendar'||
     !fingerprint(value.source_fingerprint)||
     value.source_fingerprint!==calendarFingerprint||
     value.read_only!==true||value.run_mutated!==false||
     !record(value.coverage)||!Array.isArray(value.events))return false
  const cov=value.coverage
  if(cov.atp_season_year!==expectedYear||!positiveInt(cov.roster_series_count)||
     !positiveInt(cov.dated_series_count)||
     !Array.isArray(cov.undated_series_ids)||
     !Array.isArray(cov.known_not_held_series_ids)||
     typeof cov.date_coverage_state!=='string'||
     typeof cov.year_source_status!=='string'||
     !(cov.year_source_url===null||typeof cov.year_source_url==='string')||
     value.events.length!==cov.dated_series_count)return false
  const seen=new Set<string>()
  return value.events.every((entry:unknown)=>{
    if(!record(entry)||typeof entry.series_id!=='string'||!entry.series_id||
       seen.has(entry.series_id)||typeof entry.category_id!=='string'||
       !dateString(entry.start_date)||!dateString(entry.end_date)||
       entry.start_date>entry.end_date||
       !isoYearWeek(entry.start_year_week)||!isoYearWeek(entry.end_year_week)||
       !Array.isArray(entry.iso_weeks_occupied)||
       entry.iso_weeks_occupied.length<1||
       !entry.iso_weeks_occupied.every(isoYearWeek)||
       typeof entry.source_url!=='string'||
       !entry.source_url.startsWith('https://www.atptour.com/')&&
       !entry.source_url.startsWith('https://www.nextgenatpfinals.com/')||
       typeof entry.year_source_state!=='string')return false
    seen.add(entry.series_id)
    return true
  })
}

type ATPYearWeek = {calendar_year:number;year_week:number}
type ATPRunWeek = ATPYearWeek & {season_index:number;season_week:number}
type ATPWeekSource = {
  source_identity:string
  source_start_date:string
  source_end_date:string
  review_flags:string[]
}

export type SavedATPRunWeekPreview = {
  events:(ATPWeekSource & {
    run_weeks:ATPRunWeek[]
    source_finish_run_week:ATPRunWeek
  })[]
  outside_horizon:(ATPWeekSource & {outside_year_weeks:ATPYearWeek[]})[]
  source_tour_bindings:{
    selected_occurrences:Record<string,{series_name:string;historical_category_label:string}>
  }
}

const earthWeek=(v:unknown):v is number=>positiveInt(v)&&v>=1&&v<=52
const yearWeek=(v:unknown):v is ATPYearWeek=>
  record(v)&&positiveInt(v.calendar_year)&&earthWeek(v.year_week)
const runWeek=(v:unknown):v is ATPRunWeek=>
  record(v)&&positiveInt(v.season_index)&&earthWeek(v.season_week)&&yearWeek(v)

export function validSavedATPRunWeekPreview(
  v:unknown,runId:string,branchId:string,revisionId:string,year:number
):v is SavedATPRunWeekPreview {
  if(!record(v)||v.schema_version!=='atp_earth_run_week_preview.v1'||
    v.run_id!==runId||v.branch_id!==branchId||v.saved_head_revision_id!==revisionId||
    v.saved_run_calendar_verified!==true||v.uses_saved_run_package_snapshot!==true||
    v.saved_package_source_verified!==true||v.no_sporting_install!==true||v.run_mutated!==false||
    !record(v.calendar)||v.calendar.weeks_per_year!==52||
    !Array.isArray(v.selected_atp_years)||v.selected_atp_years.length!==1||
    v.selected_atp_years[0]!==year||
    !Array.isArray(v.events)||!Array.isArray(v.outside_horizon)||
    !record(v.source_tour_bindings)||v.source_tour_bindings.verified_occurrences!==2407||
    !record(v.source_tour_bindings.selected_occurrences))return false
  const selected=v.source_tour_bindings.selected_occurrences
  const identities=new Set<string>()
  function verifiedSource(row:unknown):row is Record<string,unknown> {
    if(!record(row)||typeof row.source_identity!=='string'||
      !row.source_identity.startsWith(`atp_${year}_`)||identities.has(row.source_identity)||
      !dateString(row.source_start_date)||!dateString(row.source_end_date)||
      row.source_start_date>row.source_end_date||
      !Array.isArray(row.review_flags)||!row.review_flags.every(flag=>typeof flag==='string'))
      return false
    const binding=selected[row.source_identity]
    if(!record(binding)||typeof binding.series_name!=='string'||
      typeof binding.historical_category_label!=='string')return false
    identities.add(row.source_identity)
    return true
  }
  return v.events.every(row=>verifiedSource(row)&&
      Array.isArray(row.run_weeks)&&row.run_weeks.length>=1&&row.run_weeks.length<=3&&
      row.run_weeks.every(runWeek)&&runWeek(row.source_finish_run_week))&&
    v.outside_horizon.every(row=>verifiedSource(row)&&
      Array.isArray(row.outside_year_weeks)&&row.outside_year_weeks.length>=1&&
      row.outside_year_weeks.every(yearWeek))&&identities.size===Object.keys(selected).length
}
