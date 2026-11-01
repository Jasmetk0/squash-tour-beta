/** Cross-Run component evidence, never Restore/Save or an Admin Branch activation. */
import {useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {Link,useSearchParams} from 'react-router-dom'
import {listRunContainers} from '../api/client'
import {compareCrossSavedRevisions} from '../api/crossSavedCompare'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import {SavedCrossRunSource,useCrossSource,type CrossSelection} from './SavedCrossRunSource'
import {projectCrossSavedStateComparison} from './crossSavedCompare'
import type {CompareRow} from './savedCompareStates'
const selection=(p:URLSearchParams,side:string):CrossSelection=>({run:p.get('run_'+side)??'',
  branch:p.get('branch_'+side)??'',revision:p.get('rev_'+side)??''})
const same=(a:CrossSelection,b:CrossSelection)=>a.run===b.run&&a.branch===b.branch&&a.revision===b.revision
export function SavedCrossRunComparePage(){
  const [params]=useSearchParams()
  // Back/forward/source links restore both selectors together. Locale/filter
  // changes do not reset unsent choices or launch another comparison.
  const key=JSON.stringify([selection(params,'a'),selection(params,'b')])
  return <CrossRunCompare key={key}/>
}
function CrossRunCompare(){
  const {language}=useLanguage(),cs=language==='cs'
  const T=(en:string,cz:string)=>cs?cz:en
  const [params,setParams]=useSearchParams()
  const requestedA=selection(params,'a'),requestedB=selection(params,'b')
  const [a,setA]=useState(requestedA),[b,setB]=useState(requestedB)
  const [detail,setDetail]=useState<string|null>(null)
  const runs=useQuery({queryKey:['canonical-run-containers'],queryFn:listRunContainers,retry:false,
    refetchOnWindowFocus:false,refetchOnReconnect:false})
  const rawRuns=runs.data?.run_containers
  const entries=Array.isArray(rawRuns)?rawRuns:[]
  const validRuns=runs.isSuccess&&!runs.isFetching&&Array.isArray(rawRuns)&&
    entries.every(r=>r&&typeof r.run_id==='string'&&r.run_id)&&new Set(entries.map(r=>r.run_id)).size===entries.length
  const left=useCrossSource(a,entries,validRuns),right=useCrossSource(b,entries,validRuns)
  const applied=same(a,requestedA)&&same(b,requestedB)
  const ready=Boolean(left.source&&right.source)
  const query=useQuery({queryKey:['cross-saved-compare',requestedA,requestedB,left.source?.head,right.source?.head],
    queryFn:()=>compareCrossSavedRevisions(a.run,a.branch,a.revision,b.run,b.branch,b.revision),
    enabled:applied&&ready,retry:false,refetchOnWindowFocus:false,refetchOnReconnect:false})
  const compared=applied&&ready&&!query.isFetching&&left.source&&right.source?
    projectCrossSavedStateComparison(query.data,left.source,right.source):null
  const all=params.get('filter')==='all'
  const rows=compared?.rows.filter(r=>all||r.status!=='unchanged')??[]
  const selected=compared?.rows.find(r=>r.id===detail)
  const apply=()=>setParams({run_a:a.run,branch_a:a.branch,rev_a:a.revision,
    run_b:b.run,branch_b:b.branch,rev_b:b.revision,filter:all?'all':'differences'})
  const section=(value:CompareRow['section'])=>value==='run'?T('Run metadata','Metadata Runu'):
    value==='branch'?T('Branch metadata','Metadata větve'):T('Saved component','Uložená komponenta')
  const status=(row:CompareRow)=>cs?({added:'přidáno',removed:'odebráno',changed:'změněno',unchanged:'beze změny'}[row.status]):row.status
  return <main className="saved-compare-page">
    <header className="page-intro"><h2>{T('Cross-Run Saved Comparison','Porovnání uložených stavů mezi Runy')}</h2>
      <p>{T('Read-only Admin comparison. No Save, Restore, simulation or active Branch changes.',
        'Porovnání v Adminu pouze pro čtení. Nemění Save, obnovu, simulaci ani aktivní větev.')}</p>
      <Link to="/admin/runs">{T('Back to Runs','Zpět na Runy')}</Link></header>
    {runs.isFetching&&<p role="status">{T('Loading Runs…','Načítám Runy…')}</p>}
    {runs.error&&<p role="alert">{formatApiError(runs.error)}</p>}
    {runs.isSuccess&&!runs.isFetching&&!validRuns&&<p role="alert">{T('Invalid Run inventory.','Neplatný seznam Runů.')}</p>}
    <div className="saved-compare-before-after">
      <SavedCrossRunSource side="A" selection={a} onChange={setA} runs={entries} validRuns={validRuns} state={left} cs={cs}/>
      <SavedCrossRunSource side="B" selection={b} onChange={setB} runs={entries} validRuns={validRuns} state={right} cs={cs}/>
    </div>
    <div className="actions"><button type="button" disabled={(!left.validRun&&!right.validRun)||query.isFetching}
      onClick={()=>{if(left.validRun)left.branches.refetch();if(right.validRun)right.branches.refetch();if(left.validBranch)left.history.refetch();if(right.validBranch)right.history.refetch()}}>
      {T('Refresh sources','Znovu načíst zdroje')}</button><button type="button" onClick={()=>{setA(b);setB(a);setDetail(null)}}>
      {T('Swap A/B','Prohodit A/B')}</button>
      <button type="button" disabled={!ready||query.isFetching} onClick={apply}>{T('Compare','Porovnat')}</button></div>
    {!applied&&<p role="status">{T('Selections changed. Press Compare to read this pair.','Výběr se změnil. Pro načtení této dvojice stiskni Porovnat.')}</p>}
    {applied&&ready&&query.isFetching&&<p role="status">{T('Loading comparison…','Načítám porovnání…')}</p>}
    {applied&&ready&&query.error&&<p role="alert">{formatApiError(query.error)}{' '}
      <button type="button" onClick={()=>query.refetch()}>{T('Retry comparison','Zopakovat porovnání')}</button></p>}
    {applied&&ready&&query.isSuccess&&!query.isFetching&&!compared&&<p role="alert">{T(
      'Comparison does not match the selected Saved identities. Reload sources before retrying.',
      'Porovnání neodpovídá vybraným uloženým zdrojům. Před dalším pokusem znovu načti zdroje.')}</p>}
    {compared&&<section className="panel" aria-label={T('Cross-Run comparison results','Výsledky porovnání Runů')}>
      <h3>{T('Changes overview','Přehled změn')}</h3>
      <p>{T('Changed fields/components','Změněná pole/komponenty')}: {compared.changed} · {T('Unchanged components','Nezměněné komponenty')}: {compared.unchanged}</p>
      <p className="status">{T('Stored metadata and canonical component fingerprints only. This is not a completed player, tournament or ranking field comparison. Similar names never pair identities across Runs.',
        'Pouze uložená metadata a kanonické otisky komponent. Nejde o dokončené detailní porovnání hráčů, turnajů nebo rankingů. Podobná jména nespojují identity mezi Runy.')}</p>
      <label>{T('Show','Zobrazit')} <select aria-label={T('Cross-Run display filter','Filtr porovnání Runů')} value={all?'all':'differences'}
        onChange={e=>setParams(p=>{const next=new URLSearchParams(p);next.set('filter',e.target.value);return next})}>
        <option value="differences">{T('Differences only','Jen rozdíly')}</option><option value="all">{T('All','Vše')}</option></select></label>
      {rows.length?<div className="table-responsive"><table className="saved-compare-table" aria-label={T('Cross-Run comparison table','Tabulka porovnání Runů')}>
        <thead><tr><th>{T('Section','Sekce')}</th><th>{T('Key','Klíč')}</th><th>{T('Status','Stav')}</th><th>{T('Evidence','Podklad')}</th></tr></thead>
        <tbody>{rows.map(row=><tr key={row.id}><td>{section(row.section)}</td><td><code>{row.key}</code></td><td>{status(row)}</td><td>
          <button type="button" onClick={()=>setDetail(row.id)} aria-label={T('Inspect','Prohlédnout')+' '+row.id}>{T('Inspect difference','Prohlédnout rozdíl')}</button>
        </td></tr>)}</tbody></table></div>:<p role="status">{T('No differences in this supported scope.','V podporovaném rozsahu nejsou rozdíly.')}</p>}
    </section>}
    {selected&&<aside className="panel" aria-label={T('Cross-Run difference detail','Detail rozdílu mezi Runy')}>
      <h3>{section(selected.section)} · {selected.key}</h3><button type="button" onClick={()=>setDetail(null)}>{T('Close detail','Zavřít detail')}</button>
      <div className="saved-compare-before-after"><section><h4>A</h4><pre className="json-block">{selected.before===undefined?T('Missing','Chybí'):JSON.stringify(selected.before,null,2)}</pre></section>
        <section><h4>B</h4><pre className="json-block">{selected.after===undefined?T('Missing','Chybí'):JSON.stringify(selected.after,null,2)}</pre></section></div>
      <p>{T('Missing is distinct from stored null; zero, false and empty strings keep their JSON types.',
        'Chybějící hodnota se odlišuje od uloženého null; nula, false a prázdný řetězec zachovávají své typy.')}</p>
    </aside>}
  </main>
}
