import {useMemo,useState} from 'react'
import type {TourView} from '../api/calendarTour'
import {
  deriveNativeTourOperatorQueue,
  type NativeTourOperatorStage,
} from '../pages/nativeTourOperatorQueue'
import {useLanguage} from '../i18n/LanguageContext'

const copy={
  cs:{
    title:'Fronta operátora Tour',description:'Rychlý přehled existujících Editions podle skutečného stavu této Branch. Jen pro čtení: není to kontrola způsobilosti, potvrzení Save ani povolení spustit zápas.',
    source:'Zdroj',draft:'Working Draft: uvedené kroky mohou obsahovat neuložené změny. Před zápasy a publikováním prověřte skutečný Saved stav.',
    saved:'Zobrazený Tour stav je uložený. Další operace stále vyžadují běžný náhled, potvrzení a případný ruční Save.',
    all:'Celkem',current:'Tento týden',future:'Budoucí',past:'Minulé',
    incomplete:'Bez potvrzeného výsledku',search:'Hledat Edition',searchHint:'Název nebo přesné ID Edition',
    period:'Zobrazené Editions',everything:'Všechny Editions',
    needsReview:'Zatím bez potvrzení výsledku',reviewed:'Výsledky potvrzené',
    empty:'Žádná Edition neodpovídá filtru.',noEditions:'V této Tour zatím není žádná Edition.',
    next:'Popsaná etapa',schedule:'Plán',applications:'Přihlášky',field:'Schválený field',matches:'Zápasy',results:'Výsledky',
    jump:'Přejít k ovládání Edition',prev:'Předchozí',nextPage:'Další',page:'Strana',
    invalid:'Frontu nelze odvodit z aktuálního ověřeného Tour zdroje:',
    stages:{
      applications:'Zkontrolovat přihlášky',field:'Zkontrolovat schválení field',
      draw:'Zkontrolovat los',group_tie:'Vyřešit nerozhodnutou skupinu',
      play:'Zkontrolovat zápasy a případný Saved los',
      results:'Zkontrolovat výsledky',reviewed:'Výsledky potvrzené v zobrazeném stavu'
    }
  },
  en:{
    title:'Tour operator queue',description:'Quick index of real Editions in this Branch and their currently observed stage. Read-only: not eligibility validation, a Save confirmation or permission to execute matches.',
    source:'Source',draft:'Working Draft: observed stages may include unsaved changes. Verify actual Saved authority before matches and publication.',
    saved:'Displayed Tour state is Saved. Further actions still require ordinary preview, consent and any mandatory manual Save.',
    all:'Total',current:'This week',future:'Future',past:'Past',
    incomplete:'Results not confirmed',search:'Search Edition',searchHint:'Edition name or exact ID',
    period:'Show Editions',everything:'All Editions',
    needsReview:'Results not yet confirmed',reviewed:'Results confirmed',
    empty:'No Edition matches these filters.',noEditions:'No Editions are present in this Tour yet.',
    next:'Observed stage',schedule:'Scheduled',applications:'Applications',field:'Approved field',matches:'Matches',results:'Results',
    jump:'Go to Edition controls',prev:'Previous',nextPage:'Next',page:'Page',
    invalid:'Cannot derive the operator queue from the current verified Tour source:',
    stages:{
      applications:'Review applications',field:'Review field approval',
      draw:'Review draw',group_tie:'Resolve undecided group tie',
      play:'Review matches and Signed draw before play',
      results:'Review results',reviewed:'Results confirmed in displayed state'
    }
  }
} as const

type QueueFilter='all'|'current'|'future'|'past'|'unfinished'|'reviewed'
const PAGE_SIZE=12
const complete=(stage:NativeTourOperatorStage)=>stage==='reviewed'

export function NativeTourOperatorQueue({
  view,runId,branchId,
}:{
  view:TourView;runId:string;branchId:string
}):JSX.Element{
  const {language}=useLanguage()
  const t=copy[language]
  const [search,setSearch]=useState('')
  const [filter,setFilter]=useState<QueueFilter>('all')
  const [page,setPage]=useState(0)
  const result=useMemo(()=>{
    try {return {queue:deriveNativeTourOperatorQueue(view,runId,branchId),error:null}}
    catch(e){return {queue:null,error:e instanceof Error?e.message:'Invalid native Tour evidence'}}
  },[view,runId,branchId])
  const queue=result.queue
  const normalized=search.trim().toLocaleLowerCase()
  const matches=queue?.items.filter(item=>{
    const found=(item.name+' '+item.editionId).toLocaleLowerCase().includes(normalized)
    if(!found)return false
    if(filter==='all')return true
    if(filter==='unfinished')return !complete(item.stage)
    if(filter==='reviewed')return complete(item.stage)
    return item.period===filter
  })??[]
  const totalPages=Math.max(1,Math.ceil(matches.length/PAGE_SIZE))
  const actualPage=Math.min(page,totalPages-1)
  const visible=matches.slice(actualPage*PAGE_SIZE,(actualPage+1)*PAGE_SIZE)
  const changeFilter=(next:QueueFilter)=>{setFilter(next);setPage(0)}
  const changeSearch=(next:string)=>{setSearch(next);setPage(0)}
  return <section aria-label={t.title} className="panel">
    <h3>{t.title}</h3>
    <p className="status">{t.description}</p>
    {result.error&&<p role="alert">{t.invalid} {result.error}</p>}
    {queue&&<>
      <p className="status">{t.source}: <code>{queue.source.savedHead.slice(0,12)}</code>
        {' · '}{t.all}: {queue.items.length}
        {' · '}{t.current}: {queue.items.filter(i=>i.period==='current').length}
        {' · '}{t.future}: {queue.items.filter(i=>i.period==='future').length}
        {' · '}{t.past}: {queue.items.filter(i=>i.period==='past').length}
        {' · '}{t.incomplete}: {queue.items.filter(i=>!complete(i.stage)).length}</p>
      <p className="status">{queue.source.workingDraft?t.draft:t.saved}</p>
      {queue.items.length>0&&<>
        <label>{t.search}<input aria-label={t.search} type="search" value={search}
          onChange={e=>changeSearch(e.target.value)} placeholder={t.searchHint}/></label>
        {' '}
        <label>{t.period}<select aria-label={t.period} value={filter}
          onChange={e=>changeFilter(e.target.value as QueueFilter)}>
          <option value="all">{t.everything}</option>
          <option value="current">{t.current}</option>
          <option value="future">{t.future}</option>
          <option value="past">{t.past}</option>
          <option value="unfinished">{t.needsReview}</option>
          <option value="reviewed">{t.reviewed}</option>
        </select></label>
        <p className="status">{matches.length} / {queue.items.length}</p>
        {visible.length===0?<p role="status">{t.empty}</p>:<ol>
          {visible.map(item=><li key={item.editionId}>
            <strong>{item.name}</strong> · <code>{item.editionId}</code>
            <p>{t.schedule}: S{item.seasonIndex+1}/W{item.week}
              {' · '}{t.next}: {t.stages[item.stage]}</p>
            <p>{t.applications}: {item.applications}
              {' · '}{t.field}: {item.mainField}
              {' · '}{t.matches}: {item.matches}
              {' · '}{t.results}: {item.results}</p>
            <a href={'#native-tour-edition-'+item.sourceIndex}>{t.jump}</a>
          </li>)}
        </ol>}
        {totalPages>1&&<div>
          <button type="button" onClick={()=>setPage(n=>Math.max(0,n-1))}
            disabled={actualPage===0}>{t.prev}</button>
          {' '}{t.page} {actualPage+1} / {totalPages}{' '}
          <button type="button" onClick={()=>setPage(n=>Math.min(totalPages-1,n+1))}
            disabled={actualPage===totalPages-1}>{t.nextPage}</button>
        </div>}
      </>}
      {queue.items.length===0&&<p role="status">{t.noEditions}</p>}
    </>}
  </section>
}
