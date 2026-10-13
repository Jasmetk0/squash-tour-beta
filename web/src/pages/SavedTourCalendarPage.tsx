import {useQuery} from '@tanstack/react-query'
import {useMemo} from 'react'
import {Link,useParams,useSearchParams} from 'react-router-dom'
import {getSavedTourCalendar} from '../api/client'
import {validSavedTourCalendar} from '../api/savedTour'
import type {SavedTourEvent} from '../api/savedTour'
import {useAdminBranch} from '../admin/AdminBranchContext'
import {useAdminTime} from '../admin/AdminTimeContext'
import {useLanguage} from '../i18n/LanguageContext'
import {formatApiError} from '../utils/apiErrors'
import {calendarSeasonIndex} from './runWorldCountryTournaments'

const choices=Array.from({length:50},(_,i)=>i)
export function SavedTourCalendarPage():JSX.Element{
  const {runId=''}=useParams()
  const [params,setParams]=useSearchParams()
  const {selectedBranch,isLoading:branchLoading,error:branchError}=useAdminBranch()
  const time=useAdminTime(),{language}=useLanguage(),cs=language==='cs'
  const branch=selectedBranch?.run_id===runId?selectedBranch.branch_id:null
  const requestedBranch=params.get('branch')
  const requestedRevision=params.get('revision')
  const revision=requestedRevision===null?selectedBranch?.saved_head_revision_id??null:requestedRevision
  const raw=params.get('season')
  const season=raw===null?calendarSeasonIndex(time.presentSeason):/^(0|[1-9]\d*)$/.test(raw)?Number(raw):null
  const seasonIndex=season===null?0:season
  const seasonValid=seasonIndex>=0&&seasonIndex<50&&(raw===null||season!==null)
  const scopeValid=Boolean(runId&&branch&&revision&&revision.trim()===revision&&
    (!requestedBranch||requestedBranch===branch)&&seasonValid&&!branchError&&
    !branchLoading&&!time.isLoading&&!time.error&&time.mode==='present')
  const query=useQuery({
    queryKey:['saved-tour-calendar',runId,branch,revision,seasonIndex],
    queryFn:()=>getSavedTourCalendar(runId,branch!,revision!,seasonIndex),
    enabled:scopeValid,retry:false
  })
  const model=scopeValid&&query.data&&validSavedTourCalendar(query.data,runId,branch!,revision!,seasonIndex)
    ?query.data:null
  const invalid=Boolean(scopeValid&&query.data&&!model)
  const view=params.get('view')==='list'?'list':'weeks'
  const filters={tour:params.get('tour')??'',category:params.get('category')??'',
    country:params.get('country')??''}
  const editions=useMemo(()=>model?.editions??[],[model])
  const options=(field:'tour_level'|'category'|'host_country')=>[...new Set(editions.map(e=>e[field]).filter((v):v is string=>Boolean(v)))].sort()
  const shown=editions.filter(e=>(!filters.tour||e.tour_level===filters.tour)
    &&(!filters.category||e.category===filters.category)
    &&(!filters.country||e.host_country===filters.country))
  const set=(key:string,value:string)=>{
    const copy=new URLSearchParams(params)
    if(value)copy.set(key,value);else copy.delete(key)
    // Pin a new navigation to the exact immutable source it displayed.
    if(branch)copy.set('branch',branch)
    if(revision)copy.set('revision',revision)
    setParams(copy)
  }
  const editionHref=(e:SavedTourEvent)=>{
    const copy=new URLSearchParams(params)
    copy.set('branch',branch!);copy.set('revision',revision!);copy.set('season',String(seasonIndex))
    return '/admin/runs/'+encodeURIComponent(runId)+'/tour/calendar/'+encodeURIComponent(e.event_id)+'?'+copy.toString()
  }
  const name=(e:SavedTourEvent)=><Link to={editionHref(e)}>{e.event_name||e.event_id}</Link>
  const label=String(2000+seasonIndex)+'/'+String(2001+seasonIndex)
  const issue=branchError||time.error||
    (time.mode==='checkpoint'?(cs?'Checkpoint nemá ověřenou vazbu na Saved Revision.':'Checkpoint is not mapped to a Saved Revision.'):
    (!seasonValid?(cs?'Neplatná sezona.':'Invalid season.'):
    requestedBranch&&branch&&requestedBranch!==branch?(cs?'Nesouhlasí vybraná Branch.':'Selected Branch does not match the link.'):
    requestedRevision!==null&&!revision?(cs?'Chybí ID revize.':'Revision ID is missing.'):null))
  return <section className="panel">
    <div className="page-intro"><p className="eyebrow">RUN → TOUR → CALENDAR</p>
      <h2>{cs?'Uložený sezonní kalendář':'Saved season calendar'}</h2>
      <p>{cs?'Jen neměnná Saved Revision; neuložené plány ani checkpointy nepoužíváme.':
        'Immutable Saved Revision only; no live draft or guessed checkpoint mapping.'}</p>
    </div>
    <p className="status">Run: <code>{runId}</code> · Branch: <code>{branch??'—'}</code>
      {' · '}Saved Revision: <code>{revision??'—'}</code>{requestedRevision===null?' · HEAD':''}</p>
    <div className="grid">
      <label>{cs?'Sezona':'Season'} <select aria-label="Saved Tour season" value={seasonIndex}
        onChange={e=>set('season',e.target.value)}>
        {choices.map(n=><option key={n} value={n}>{2000+n}/{2001+n}</option>)}</select></label>
      <label>{cs?'Pohled':'View'} <select aria-label="Saved Tour view" value={view}
        onChange={e=>set('view',e.target.value)}>
        <option value="weeks">{cs?'61 týdnů':'61 weeks'}</option>
        <option value="list">{cs?'Seznam':'List'}</option>
      </select></label>
      <label>Tour <select aria-label="Saved Tour filter Tour" value={filters.tour}
        onChange={e=>set('tour',e.target.value)}>
        <option value="">{cs?'Všechny':'All'}</option>
        {options('tour_level').map(v=><option key={v} value={v}>{v}</option>)}</select></label>
      <label>{cs?'Kategorie':'Category'} <select aria-label="Saved Tour filter category" value={filters.category}
        onChange={e=>set('category',e.target.value)}>
        <option value="">{cs?'Všechny':'All'}</option>
        {options('category').map(v=><option key={v} value={v}>{v}</option>)}</select></label>
      <label>{cs?'Země':'Country'} <select aria-label="Saved Tour filter country" value={filters.country}
        onChange={e=>set('country',e.target.value)}>
        <option value="">{cs?'Všechny':'All'}</option>
        {options('host_country').map(v=><option key={v} value={v}>{v}</option>)}</select></label>
    </div>
    {issue&&<p role="alert">{issue}</p>}
    {!issue&&!scopeValid&&!branchLoading&&!time.isLoading&&<p role="alert">{cs?
      'Uložená Branch nebo revize není dostupná.':'Saved Branch or revision is unavailable.'}</p>}
    {query.isPending&&scopeValid&&<p role="status">{cs?'Načítám Saved Calendar…':'Loading Saved Calendar…'}</p>}
    {query.error&&<p role="alert">{formatApiError(query.error)}</p>}
    {invalid&&<p role="alert">{cs?'Odpověď kalendáře neodpovídá vybrané Run/Branch/revizi/sezoně.':
      'Calendar response does not match the selected Run/Branch/revision/season.'}</p>}
    {model&&<>
      <p className="status">{label} · {model.edition_count} {cs?'uložených edic':'saved editions'}
        {' · '}{shown.length} {cs?'po filtrování':'after filtering'}
        {' · '}{cs?'Zdrojová Branch':'Source Branch'}: <code>{model.revision_branch_id}</code></p>
      {model.calendar_status==='empty'&&<p role="status">{cs?'Tato revize nemá uložený Calendar Package.':
        'This revision has no saved Calendar Package.'}</p>}
      {model.calendar_status==='ready'&&shown.length===0&&<p role="status">{cs?
        'V této sezoně nejsou turnaje odpovídající filtrům.':'No saved editions match the filters in this season.'}</p>}
      {view==='weeks'?<div className="saved-tour-week-grid" aria-label="Saved Tour 61 season weeks">
        {Array.from({length:61},(_,i)=>{
          const week=i+1,events=shown.filter(e=>e.season_week===week)
          return <section key={week} className="section-subtle">
            <h4>{cs?'Týden':'Week'} {week}</h4>
            {events.map(e=><p key={e.event_id}>{name(e)} <small>· {e.category} · {e.host_country}
              {e.result_published?' · '+(cs?'publikovaný výsledek':'published result'):''}</small></p>)}
            {events.length===0&&<small>—</small>}
          </section>
        })}</div>:<div className="table-responsive"><table aria-label="Saved Tour edition list">
          <thead><tr><th>{cs?'Týden':'Week'}</th><th>{cs?'Edice':'Edition'}</th>
            <th>Tour</th><th>{cs?'Kategorie':'Category'}</th><th>{cs?'Země':'Country'}</th>
            <th>{cs?'Výsledek':'Result'}</th></tr></thead>
          <tbody>{shown.map(e=><tr key={e.event_id}>
            <td>{e.season_week}</td><td>{name(e)}</td><td>{e.tour_level??'—'}</td>
            <td>{e.category}</td><td>{e.host_country}</td>
            <td>{e.result_published?(cs?'Publikován':'Published'):'—'}</td>
          </tr>)}</tbody></table></div>}
      <p className="status">{cs?
        'Plánované budoucí edice nejsou důkazem uskutečněného turnaje.':'A saved future plan does not prove a tournament was played.'}</p>
    </>}
  </section>
}
