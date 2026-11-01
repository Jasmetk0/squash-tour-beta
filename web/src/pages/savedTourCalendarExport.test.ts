import {describe,expect,it} from 'vitest'
import type {SavedTourCalendar,SavedTourEvent} from '../api/savedTour'
import {
  buildSavedTourCalendarExport,serializeSavedTourCalendarExport,savedTourCalendarCsv,
  type SavedTourExportContext,
} from './savedTourCalendarExport'

const event=(id:string,week:number,partial:Partial<SavedTourEvent>={}):SavedTourEvent=>({
  event_id:id,event_name:'Cup '+id,season:'2002/2003',season_week:week,
  template_id:'template',category:'GOLD',tour_level:'WORLD',host_country:'CZE',
  host_city:'Brno',region:'EUROPE',main_draw_size:16,
  qualification_draw_size:8,seeds_count:4,qualifier_spots:4,wild_cards:2,byes:0,
  ranking_status:'ranked',result_published:false,
  champion_player_id:null,finalist_player_id:null,...partial,
})
const source=(editions:SavedTourEvent[]=[
  event('A',5,{result_published:true,champion_player_id:'p1',finalist_player_id:'p2'}),
  event('B',5,{host_country:'EGY'}),
  event('C',10,{host_country:'CZE'})
]):SavedTourCalendar=>({
  schema_version:'run_saved_tour_calendar.v1',source:'reachable_saved_revision',
  run_id:'run-a',branch_id:'branch-a',revision_branch_id:'ancestor-branch',
  saved_revision_id:'rev-old',season_index:2,season:'2002/2003',
  week_count:61,calendar_status:'ready',edition_count:editions.length,editions,
})
const filters={
  tour:'',category:'',country:'',search:'',publication:'all' as const,
  playerId:'',playerOutcome:'any' as const,
}
const ctx=(parts:Partial<SavedTourExportContext>={}):SavedTourExportContext=>({
  runId:'run-a',branchId:'branch-a',revisionId:'rev-old',seasonIndex:2,
  scope:'season',filters,focusedWeek:null,...parts,
})

describe('immutable Saved Tour calendar export proof',()=>{
  it('exports all exactly saved Editions and source identities without inventing match results',()=>{
    const original=source(),snapshot=JSON.stringify(original)
    const result=buildSavedTourCalendarExport(original,ctx())
    expect(result.schema_version).toBe('saved_tour_calendar_export.v1')
    expect(result.evidence).toBe('read_only_saved_revision_calendar')
    expect(result.source).toEqual({
      run_id:'run-a',branch_id:'branch-a',
      revision_branch_id:'ancestor-branch',saved_revision_id:'rev-old',
      season_index:2,season:'2002/2003',week_count:61,
      calendar_status:'ready',total_saved_editions:3,
    })
    expect(result.exported_edition_count).toBe(3)
    expect(result.published_final_count).toBe(1)
    expect(result.editions.map(e=>e.event_id)).toEqual(['A','B','C'])
    expect(result.editions.find(e=>e.event_id==='B')?.champion_player_id).toBeNull()
    expect(result.selection.filters).toBeNull()
    expect(result.selection.focused_week).toBeNull()
    expect(JSON.stringify(original)).toBe(snapshot)
  })
  it('matches the current country, result-publication and focused-week filters',()=>{
    const result=buildSavedTourCalendarExport(source(),ctx({
      scope:'filtered',focusedWeek:5,
      filters:{...filters,country:'CZE',publication:'published'},
    }))
    expect(result.editions.map(e=>e.event_id)).toEqual(['A'])
    expect(result.exported_edition_count).toBe(1)
    expect(result.published_final_count).toBe(1)
    expect(result.selection).toEqual({
      scope:'filtered',focused_week:5,
      filters:{...filters,country:'CZE',publication:'published'},
    })
  })
  it('ignores filters for full-season export and never calls another read',()=>{
    const result=buildSavedTourCalendarExport(source(),ctx({
      scope:'season',focusedWeek:5,
      filters:{...filters,country:'EGY',search:'never-exists'},
    }))
    expect(result.exported_edition_count).toBe(3)
    expect(result.selection.filters).toBeNull()
    expect(result.selection.focused_week).toBeNull()
  })
  it('rejects foreign Run/Branch/Revision, stale season, tampered counts and invalid week',()=>{
    const model=source()
    for(const context of [
      ctx({runId:'other'}),ctx({branchId:'other'}),
      ctx({revisionId:'new-head'}),ctx({seasonIndex:3}),
      ctx({scope:'filtered',focusedWeek:62}),
      ctx({scope:'filtered',focusedWeek:-1}),
      ctx({scope:'filtered',focusedWeek:1.4}),
    ])expect(()=>buildSavedTourCalendarExport(model,context)).toThrow()
    expect(()=>buildSavedTourCalendarExport({...model,edition_count:100},ctx())).toThrow()
    expect(()=>buildSavedTourCalendarExport({...model,saved_revision_id:'forged'},ctx())).toThrow()
    expect(()=>buildSavedTourCalendarExport(source([
      event('a',3),event('a',5),
    ]),ctx())).toThrow()
  })
  it('does not certify an unplayed Edition or invent a published champion',()=>{
    const unpublished=event('not-played',9,{
      result_published:false,champion_player_id:null,finalist_player_id:null
    })
    const results=buildSavedTourCalendarExport(source([unpublished]),ctx())
    expect(results.published_final_count).toBe(0)
    expect(results.editions).toMatchObject([{
      event_id:'not-played',result_published:false,
      champion_player_id:null,finalist_player_id:null
    }])
  })
  it('binds each CSV data row to immutable source and escapes RFC4180 content',()=>{
    const malicious=event('=2+2',1,{
      event_name:'=SUM(1,2), "hello"\nnext',
      result_published:true,champion_player_id:'-HYPERLINK("url")',
      finalist_player_id:'+formula',host_country:'CZE'
    })
    const result=buildSavedTourCalendarExport(source([malicious]),ctx())
    const csv=savedTourCalendarCsv(result)
    expect(csv.startsWith('\uFEFF"run_id","branch_id"')).toBe(true)
    expect(csv).toContain('"run-a","branch-a","ancestor-branch","rev-old","2"')
    expect(csv).toContain('"\'=2+2"')
    expect(csv).toContain('"\'=SUM(1,2), ""hello""\nnext"')
    expect(csv).toContain('"\'-HYPERLINK(""url"")"')
    expect(csv).toContain('"\'+formula"')
    expect(csv.endsWith('\r\n')).toBe(true)
    expect(csv.split('\r\n').filter(Boolean)).toHaveLength(2)
  })
  it('preserves empty Saved season as a metadata-only JSON but refuses identity-free CSV',()=>{
    const empty=source([])
    empty.calendar_status='empty'
    const result=buildSavedTourCalendarExport(empty,ctx())
    expect(result.editions).toEqual([])
    expect(result.exported_edition_count).toBe(0)
    const file=serializeSavedTourCalendarExport(result,'json')
    expect(file.mime).toBe('application/json;charset=utf-8')
    expect(JSON.parse(file.content).source.saved_revision_id).toBe('rev-old')
    expect(()=>serializeSavedTourCalendarExport(result,'csv')).toThrow(/empty/)
  })
  it('safe filenames have no path escape even for unusual valid Branch/Revision IDs',()=>{
    const original=source()
    original.branch_id='../some weird branch'
    original.saved_revision_id='../../an-old-revision'
    const result=buildSavedTourCalendarExport(original,ctx({
      branchId:original.branch_id,revisionId:original.saved_revision_id,
    }))
    const csv=serializeSavedTourCalendarExport(result,'csv')
    expect(csv.filename).toMatch(/^squash-saved-tour-S3-[a-zA-Z0-9_-]+-[a-zA-Z0-9_-]+-season\.csv$/)
    expect(csv.filename).not.toContain('../')
    const json=serializeSavedTourCalendarExport(result,'json')
    expect(JSON.parse(json.content).source.saved_revision_id).toBe('../../an-old-revision')
  })
})
