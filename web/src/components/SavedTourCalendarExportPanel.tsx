import {useMemo,useState} from 'react'
import type {SavedTourCalendar} from '../api/savedTour'
import type {SavedCalendarDiscoveryFilters} from '../pages/savedTourCalendarDiscovery'
import {useLanguage} from '../i18n/LanguageContext'
import {
  buildSavedTourCalendarExport,serializeSavedTourCalendarExport,
  type SavedTourExportFormat,type SavedTourExportScope,
} from '../pages/savedTourCalendarExport'

const messages={
  cs:{
    title:'Export přesné uložené sezony',
    explanation:'Pouze ověřená Saved Revision této Branch; žádné neuložené změny, domyšlené zápasy ani vypočtené výsledky.',
    selection:'Rozsah exportu',
    season:'Celá uložená sezona',
    filtered:'Aktuální filtry a vybraný týden',
    json:'Stáhnout JSON včetně zdroje a filtrů',
    csv:'Stáhnout CSV pro tabulku',
    count:'Edice v exportu',published:'Publikovaná finále',
    empty:'CSV není možné pro prázdný výběr – neobsahovalo by identitu Saved Revision. JSON zachovává úplný původ i pro prázdnou sezonu.',
    caveat:'Naplánovaná Edition není důkazem odehrání. Publikovaná finále jsou pouze ta, která doložil Saved zdroj.',
    error:'Export nebylo možné bezpečně vytvořit:',
  },
  en:{
    title:'Export exact Saved season',
    explanation:'Only the verified Saved Revision of this Branch; never unsaved changes, inferred matches or synthetic results.',
    selection:'Export scope',
    season:'Whole Saved season',
    filtered:'Current filters and focused week',
    json:'Download JSON with source and filters',
    csv:'Download CSV for spreadsheets',
    count:'Editions in export',published:'Published finals',
    empty:'CSV is unavailable for an empty selection because it could not identify its Saved Revision. JSON retains complete provenance even for an empty season.',
    caveat:'A planned Edition does not prove it was played. Published finals are only those attested by the Saved source.',
    error:'Cannot safely prepare the export:',
  },
} as const

function downloadFile(filename:string,content:string,mime:string):void{
  const url=URL.createObjectURL(new Blob([content],{type:mime}))
  const anchor=document.createElement('a')
  anchor.href=url
  anchor.download=filename
  try{
    document.body.append(anchor)
    anchor.click()
  }finally{
    anchor.remove()
    URL.revokeObjectURL(url)
  }
}

export function SavedTourCalendarExportPanel({
  model,runId,branchId,revisionId,seasonIndex,filters,focusedWeek,
}:{
  model:SavedTourCalendar
  runId:string;branchId:string;revisionId:string;seasonIndex:number
  filters:SavedCalendarDiscoveryFilters;focusedWeek:number|null
}):JSX.Element{
  const {language}=useLanguage(),t=messages[language]
  const [scope,setScope]=useState<SavedTourExportScope>('season')
  const [error,setError]=useState<string|null>(null)
  // No server calls; changing the selected HEAD or filters immediately
  // recalculates from the validated parent read and never uses old evidence.
  const prepared=useMemo(()=>{
    try{
      return {data:buildSavedTourCalendarExport(model,{
        runId,branchId,revisionId,seasonIndex,filters,focusedWeek,scope,
      }),error:null}
    }catch(e){
      return {data:null,error:e instanceof Error?e.message:'Invalid export evidence'}
    }
  },[model,runId,branchId,revisionId,seasonIndex,filters,focusedWeek,scope])
  const issue=prepared.error??error
  const exportFile=(format:SavedTourExportFormat)=>{
    setError(null)
    try{
      // Refresh the identity check at the exact user gesture, not merely at
      // render time; failed/foreign source never starts a download.
      const evidence=buildSavedTourCalendarExport(model,{
        runId,branchId,revisionId,seasonIndex,filters,focusedWeek,scope,
      })
      const file=serializeSavedTourCalendarExport(evidence,format)
      downloadFile(file.filename,file.content,file.mime)
    }catch(e){
      setError(e instanceof Error?e.message:'Unable to export the Saved season')
    }
  }
  return <section aria-label={t.title} className="section-subtle">
    <h3>{t.title}</h3>
    <p>{t.explanation}</p>
    <label>{t.selection} <select aria-label={t.selection} value={scope}
      onChange={e=>{setScope(e.target.value as SavedTourExportScope);setError(null)}}>
      <option value="season">{t.season}</option>
      <option value="filtered">{t.filtered}</option>
    </select></label>
    {prepared.data&&<p className="status">{t.count}: {prepared.data.exported_edition_count}
      {' · '}{t.published}: {prepared.data.published_final_count}
      {' · '}Saved Revision: <code>{prepared.data.source.saved_revision_id}</code></p>}
    {issue&&<p role="alert">{t.error} {issue}</p>}
    <div className="actions">
      <button type="button" disabled={!prepared.data} onClick={()=>exportFile('json')}>{t.json}</button>
      <button type="button" disabled={!prepared.data?.exported_edition_count}
        onClick={()=>exportFile('csv')}>{t.csv}</button>
    </div>
    {prepared.data?.exported_edition_count===0&&<p role="status">{t.empty}</p>}
    <p className="status">{t.caveat}</p>
  </section>
}
