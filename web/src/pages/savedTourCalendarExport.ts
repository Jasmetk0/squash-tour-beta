/** Read-only export of one already validated immutable Saved Tour calendar. */
import {validSavedTourCalendar,type SavedTourCalendar,type SavedTourEvent} from '../api/savedTour'
import {filterSavedTourEvents,type SavedCalendarDiscoveryFilters} from './savedTourCalendarDiscovery'

export type SavedTourExportScope='season'|'filtered'
export type SavedTourExportFormat='json'|'csv'

export type SavedTourExportContext={
  runId:string;branchId:string;revisionId:string;seasonIndex:number
  scope:SavedTourExportScope
  filters:SavedCalendarDiscoveryFilters
  focusedWeek:number|null
}

export type SavedTourExportRow={
  event_id:string
  event_name:string
  season:string
  season_week:number
  tour_level:string|null
  category:string
  ranking_status:string
  template_id:string
  host_country:string
  host_city:string|null
  region:string
  main_draw_size:number
  qualification_draw_size:number
  seeds_count:number
  qualifier_spots:number
  wild_cards:number
  byes:number
  result_published:boolean
  champion_player_id:string|null
  finalist_player_id:string|null
}

export type SavedTourExportEvidence={
  schema_version:'saved_tour_calendar_export.v1'
  evidence:'read_only_saved_revision_calendar'
  source:{
    run_id:string;branch_id:string;revision_branch_id:string;saved_revision_id:string
    season_index:number;season:string;week_count:number;calendar_status:'empty'|'ready'
    total_saved_editions:number
  }
  selection:{
    scope:SavedTourExportScope
    focused_week:number|null
    filters:SavedCalendarDiscoveryFilters|null
  }
  exported_edition_count:number
  published_final_count:number
  editions:SavedTourExportRow[]
}

const toRow=(e:SavedTourEvent):SavedTourExportRow=>({
  event_id:e.event_id,event_name:e.event_name,season:e.season,season_week:e.season_week,
  tour_level:e.tour_level,category:e.category,ranking_status:e.ranking_status,
  template_id:e.template_id,host_country:e.host_country,host_city:e.host_city,
  region:e.region,main_draw_size:e.main_draw_size,
  qualification_draw_size:e.qualification_draw_size,seeds_count:e.seeds_count,
  qualifier_spots:e.qualifier_spots,wild_cards:e.wild_cards,byes:e.byes,
  result_published:e.result_published,
  champion_player_id:e.result_published?e.champion_player_id:null,
  finalist_player_id:e.result_published?e.finalist_player_id:null,
})

const normalizedFilters=(filters:SavedCalendarDiscoveryFilters):SavedCalendarDiscoveryFilters=>({
  tour:filters.tour,category:filters.category,country:filters.country,
  search:filters.search,publication:filters.publication,
  playerId:filters.playerId,playerOutcome:filters.playerOutcome,
})

/**
 * Do not derive an export from a stale query or a guessed "current HEAD".
 * All rows are selected from the complete, exact validated Saved source.
 * Unknown/incomplete publication flags never become synthetic finals.
 */
export function buildSavedTourCalendarExport(
  model:SavedTourCalendar,context:SavedTourExportContext,
):SavedTourExportEvidence{
  if(!context||!['season','filtered'].includes(context.scope)
    ||!validSavedTourCalendar(model,context.runId,context.branchId,context.revisionId,context.seasonIndex))
    throw Error('Saved Tour export source scope is invalid')
  if(context.scope==='filtered'
    &&context.focusedWeek!==null
    &&(!Number.isSafeInteger(context.focusedWeek)||context.focusedWeek<1
      ||context.focusedWeek>model.week_count))
    throw Error('Saved Tour export focused week is invalid')
  const f=context.filters
  if(!f||typeof f!=='object'
    ||['tour','category','country','search','playerId'].some(k=>typeof f[k as keyof SavedCalendarDiscoveryFilters]!=='string')
    ||!['all','published','not-published'].includes(f.publication)
    ||!['any','champion','finalist'].includes(f.playerOutcome))
    throw Error('Saved Tour export filters are invalid')
  const rows=context.scope==='season'
    ?model.editions
    :filterSavedTourEvents(model.editions,f).filter(e=>
      context.focusedWeek===null||e.season_week===context.focusedWeek)
  const exported=rows.map(toRow)
  return {
    schema_version:'saved_tour_calendar_export.v1',
    evidence:'read_only_saved_revision_calendar',
    source:{
      run_id:model.run_id,branch_id:model.branch_id,
      revision_branch_id:model.revision_branch_id,
      saved_revision_id:model.saved_revision_id,
      season_index:model.season_index,season:model.season,
      week_count:model.week_count,calendar_status:model.calendar_status,
      total_saved_editions:model.edition_count,
    },
    selection:{
      scope:context.scope,focused_week:context.scope==='filtered'?context.focusedWeek:null,
      filters:context.scope==='filtered'?normalizedFilters(f):null,
    },
    exported_edition_count:exported.length,
    published_final_count:exported.filter(e=>e.result_published).length,
    editions:exported,
  }
}

const csvColumns=[
  'run_id','branch_id','revision_branch_id','saved_revision_id','season_index',
  'event_id','event_name','season','season_week','tour_level','category',
  'ranking_status','template_id','host_country','host_city','region','main_draw_size',
  'qualification_draw_size','seeds_count','qualifier_spots','wild_cards','byes',
  'result_published','champion_player_id','finalist_player_id',
] as const

/**
 * RFC4180 quoting plus spreadsheet formula injection protection. Export a
 * standalone table: source IDs are repeated for EACH record, no hidden header
 * comment or implicit "active" scope. CSV with zero rows is prohibited because
 * a header alone cannot identify its Saved Revision.
 */
export function savedTourCalendarCsv(evidence:SavedTourExportEvidence):string{
  if(!evidence.editions.length)throw Error('Cannot export an empty Saved Tour CSV without source rows')
  const quote=(value:string|number|boolean|null):string=>{
    const raw=value===null?'':String(value)
    const safe=/^[\s\u0000-\u001f]*[=+\-@]/u.test(raw)||/^[\t\r\n]/u.test(raw)
      ?"'"+raw:raw
    return '"'+safe.replace(/"/g,'""')+'"'
  }
  const lines=[csvColumns.map(quote).join(',')]
  for(const e of evidence.editions){
    const row={
      run_id:evidence.source.run_id,
      branch_id:evidence.source.branch_id,
      revision_branch_id:evidence.source.revision_branch_id,
      saved_revision_id:evidence.source.saved_revision_id,
      season_index:evidence.source.season_index,
      ...e,
    }
    lines.push(csvColumns.map(column=>quote(row[column])).join(','))
  }
  return '\uFEFF'+lines.join('\r\n')+'\r\n'
}

const filePart=(raw:string)=>raw.replace(/[^a-z0-9_-]+/gi,'_').slice(0,42)||'source'

export function serializeSavedTourCalendarExport(
  evidence:SavedTourExportEvidence,format:SavedTourExportFormat,
):{filename:string;content:string;mime:string}{
  if(format!=='json'&&format!=='csv')throw Error('Unsupported Saved Tour export format')
  if(evidence.schema_version!=='saved_tour_calendar_export.v1'
    ||evidence.evidence!=='read_only_saved_revision_calendar')
    throw Error('Invalid Saved Tour export evidence')
  const scope=evidence.selection.scope
  const filename='squash-saved-tour-S'+(evidence.source.season_index+1)
    +'-'+filePart(evidence.source.branch_id)
    +'-'+filePart(evidence.source.saved_revision_id)
    +'-'+scope+'.'+format
  return format==='json'
    ?{filename,content:JSON.stringify(evidence,null,2)+'\n',mime:'application/json;charset=utf-8'}
    :{filename,content:savedTourCalendarCsv(evidence),mime:'text/csv;charset=utf-8'}
}
