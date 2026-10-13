/** Run → World reads only the selected Branch's Run-owned package copy.
 * A historical checkpoint is not silently substituted with current Run data.
 */
import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getRunPackageState, getSavedRevision, listSavedRevisionHistory } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { projectRunWorld, worldRatingKeys } from './runWorldReadModel'
import { historicalRunWorldSnapshot } from './runWorldSavedRevision'
import { projectRunWorldCountryHistory } from './runWorldCountryHistory'
import type { RunWorldCountryHistory } from './runWorldCountryHistory'
import { RunWorldCountryHistoryPanel } from './RunWorldCountryHistoryPanel'
import { RunWorldCountrySavedPlayers } from './RunWorldCountrySavedPlayers'
import { RunWorldCountryTournaments } from './RunWorldCountryTournaments'
import { RunWorldCountryRecords } from './RunWorldCountryRecords'
import { projectCountryTournaments } from './runWorldCountryTournaments'
import type { CountryTournaments } from './runWorldCountryTournaments'
import type { RunWorldCountry, RunWorldOverview, WorldPopulation } from './runWorldReadModel'

const startYear=2000
function formatCount(n:number,language:string):string {
  return new Intl.NumberFormat(language==='cs'?'cs-CZ':'en-US').format(n)
}
function populationLabel(p:WorldPopulation,cs:boolean):string {
  if(p.value==null) return cs?'Chybí':'Missing'
  if(p.kind==='exact') return cs?'Přímý údaj':'Exact'
  if(p.kind==='nearest') return (cs?'Nejbližší doložený rok: ':'Nearest year: ')+p.sourceYear
  if(p.kind==='default') return cs?'Výchozí údaj (2020)':'Default (2020)'
  return cs?'Starší údaj bez roku':'Legacy value (year unknown)'
}
function queryYear(params:URLSearchParams):number {
  const raw=params.get('year')
  const year=raw==null?startYear:Number(raw)
  return raw!==null && !/^[0-9]{4}$/.test(raw) || !Number.isSafeInteger(year) || year<1955 || year>2050
    ? startYear : year
}
function countryUrl(runId:string,code:string,params:URLSearchParams):string {
  return '/admin/runs/'+encodeURIComponent(runId)+'/world/countries/'+encodeURIComponent(code)+
    '?'+params.toString()
}
function TabLink({active,to,label}:{active:boolean;to:string;label:string}):JSX.Element {
  return <Link aria-current={active?'page':undefined} to={to}>{label}</Link>
}
function CountryDetail({runId,branchId,savedHead,historicalRevisionId,country,world,params,cs,language,selectedWorldYear,history,historyError,tournaments,tournamentsError,tournamentsPending,tournamentSourceRevision,presentSeason,presentWeek}:{
  runId:string;branchId:string;savedHead:string|null;historicalRevisionId:string|null;country:RunWorldCountry;world:RunWorldOverview;
  params:URLSearchParams;cs:boolean;language:string;selectedWorldYear:number
  history:RunWorldCountryHistory|null;historyError:string|null
  tournaments:CountryTournaments|null;tournamentsError:string|null;tournamentsPending:boolean
  tournamentSourceRevision:string|null;presentSeason:number|null;presentWeek:number|null
}):JSX.Element {
  const available=['overview','population','ratings','players','records','tournaments']
  const labels=cs?['Přehled','Populace','Atributy země','Hráči a talenty','Rekordy','Turnaje']:
    ['Overview','Population','Country Attributes','Players & Talent','Records','Tournaments']
  const raw=params.get('tab')
  const active=available.includes(raw??'')?raw!:'overview'
  const linked=(tab:string)=>{
    const next=new URLSearchParams(params)
    next.set('tab',tab)
    return countryUrl(runId,country.code,next)
  }
  const yearLink=(year:number)=>{
    const next=new URLSearchParams(params)
    next.set('year',String(year))
    return countryUrl(runId,country.code,next)
  }
  const returnParams=new URLSearchParams(params)
  returnParams.delete('tab')
  return <section aria-label="Run World country detail">
    <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/world?'+returnParams.toString()}>
      ← {cs?'Zpět na seznam zemí':'Back to countries'}
    </Link>
    <div className="page-intro"><p className="eyebrow">{world.worldName} · {params.get('year')||startYear}</p>
      <h3>{country.name} <small>({country.code})</small></h3>
    </div>
    <nav className="run-world-tabs" aria-label="Country detail sections">
      {available.map((tab,i)=><TabLink key={tab} active={active===tab} to={linked(tab)} label={labels[i]}/>)}
    </nav>
    {active==='overview' && <div className="run-world-detail-grid">
      <section className="section-subtle"><h4>{cs?'Základní údaje':'Country facts'}</h4>
        <dl><dt>Region</dt><dd>{country.region??'—'}</dd>
          <dt>Travel Region</dt><dd>{country.travelRegion??'—'}</dd>
          <dt>Timezone Area</dt><dd>{country.timezoneArea??'—'}</dd>
          <dt>{cs?'Plocha':'Area'}</dt><dd>{country.areaKm2==null?'—':formatCount(country.areaKm2,language)+' km²'}</dd>
          <dt>{cs?'Zdroj':'Source'}</dt><dd>{country.manual?(cs?'Ruční Runový záznam':'Manual Run entity'):(cs?'Kopie balíčku v Runu':'Run-owned package copy')}</dd>
        </dl>
      </section>
      <section className="section-subtle"><h4>{cs?'Populace a ratingy':'Population and ratings'}</h4>
        <p>{country.population.value==null?'—':formatCount(country.population.value,language)}
          {' '}<small>({populationLabel(country.population,cs)})</small></p>
        <p>{cs?'Škála ratingů':'Rating scale'}: 1–{country.ratingScale}</p>
        <p>{cs?'Dostupné detaily jsou v záložkách Populace a Atributy země.':'See Population and Country Attributes for available data and provenance.'}</p>
      </section>
    </div>}
    {(active==='population'||active==='ratings')&&history&&
      <RunWorldCountryHistoryPanel
        key={country.code} country={country} history={history}
        tab={active} cs={cs} language={language} yearLink={yearLink}
      />}
    {(active==='population'||active==='ratings')&&!history&&
      <p role="alert">{historyError??(cs?'Historické podklady této země nejsou dostupné.':'Country history source is unavailable.')}</p>}
    {active==='players'&&(historicalRevisionId
      ? <section className="section-subtle" aria-label="Historical country roster unavailable">
          <h4>{cs?'Historický soupis hráčů':'Historical player roster'}</h4>
          <p role="status">{cs
            ? 'Tato stránka zobrazuje historický World ze Saved Revision '+historicalRevisionId+
              '. Autoritativní historický soupis hráčů této revize zde zatím není připojen. Současní hráči se nikdy nepoužijí jako náhrada.'
            : 'This page shows the World stored in Saved Revision '+historicalRevisionId+
              '. An authoritative player roster for that revision is not yet connected. Current saved players are never substituted.'}</p>
        </section>
      : <RunWorldCountrySavedPlayers
          key={runId+':'+branchId+':'+(savedHead??'none')+':'+country.code}
          runId={runId} branchId={branchId} savedHead={savedHead}
          countryCode={country.code} selectedWorldYear={selectedWorldYear}
          language={language==='cs'?'cs':'en'}
        />)}
    {active==='tournaments'&&<RunWorldCountryTournaments
      runId={runId} branchId={branchId} countryCode={country.code}
      sourceRevision={tournamentSourceRevision} historical={historicalRevisionId!==null}
      currentSeason={presentSeason} currentWeek={presentWeek}
      model={tournaments} loading={tournamentsPending} error={tournamentsError} cs={cs} countryParams={params}/>}
    {active==='records'&&<RunWorldCountryRecords
      runId={runId} branchId={branchId} countryCode={country.code}
      savedRevisionId={historicalRevisionId??savedHead}
      historical={historicalRevisionId!==null} cs={cs}/>}

  </section>
}
export function RunWorldPage():JSX.Element {
  const {runId='',countryCode}=useParams()
  const {language}=useLanguage()
  const cs=language==='cs'
  const {selectedBranch,isLoading:branchLoading,error:branchError}=useAdminBranch()
  const time=useAdminTime()
  const [params,setParams]=useSearchParams()
  const year=queryYear(params)
  const search=params.get('q')??''
  const branchId=selectedBranch?.run_id===runId?selectedBranch.branch_id:null
  // The data year is NOT a simulation checkpoint and a selected Saved Revision
  // is NOT the mutable current Saved HEAD. Keep all three contexts separate.
  const selectedRevisionId=params.get('revision')?.trim()??''
  const historicalRevision=selectedRevisionId.length>0
  const allowed=Boolean(runId&&branchId&&time.mode==='present'&&!time.isLoading&&!time.error&&!branchLoading&&!branchError)
  const q=useQuery({
    queryKey:['run-world-current-packages',runId,branchId],
    queryFn:()=>getRunPackageState(runId,branchId!),
    enabled:allowed&&!historicalRevision,
    retry:false
  })
  const historyList=useQuery({
    queryKey:['run-world-reachable-saved-revisions',runId,branchId,selectedBranch?.saved_head_revision_id],
    queryFn:()=>listSavedRevisionHistory(runId,branchId!,{limit:200}),
    enabled:allowed,
    retry:false
  })
  const historyListMatches=Boolean(historyList.data&&historyList.data.run_id===runId&&
    historyList.data.branch_id===branchId&&
    historyList.data.saved_head_revision_id===selectedBranch?.saved_head_revision_id)
  const revision=useQuery({
    queryKey:['run-world-exact-saved-revision',runId,branchId,selectedRevisionId],
    queryFn:()=>getSavedRevision(runId,branchId!,selectedRevisionId),
    enabled:allowed&&historicalRevision,
    retry:false
  })
  const savedSource=useMemo(()=>{
    if(!allowed||!historicalRevision||!revision.data||!branchId)
      return {source:null,error:null}
    try {return {source:historicalRunWorldSnapshot(revision.data,runId,branchId,selectedRevisionId),error:null}}
    catch(error){return {source:null,error:formatApiError(error)}}
  },[allowed,historicalRevision,revision.data,runId,branchId,selectedRevisionId])
  // The present World can include unsaved edits. Calendar reads are always from
  // immutable Saved HEAD (or the explicitly selected historical Saved Revision).
  const tournamentTab=Boolean(countryCode&&params.get('tab')==='tournaments')
  const tournamentSourceRevision=historicalRevision?selectedRevisionId:
    (selectedBranch?.saved_head_revision_id??'')
  const calendarRevision=useQuery({
    queryKey:['run-world-saved-calendar',runId,branchId,tournamentSourceRevision],
    queryFn:()=>getSavedRevision(runId,branchId!,tournamentSourceRevision),
    enabled:allowed&&tournamentTab&&!historicalRevision&&Boolean(tournamentSourceRevision),
    retry:false
  })
  const calendarSource=useMemo(()=>{
    if(!allowed||!tournamentTab||!branchId)return {read:null,error:null}
    if(historicalRevision)return {read:savedSource.source,error:savedSource.error}
    if(!calendarRevision.data||!tournamentSourceRevision)return {read:null,error:null}
    try{return {read:historicalRunWorldSnapshot(calendarRevision.data,runId,branchId,tournamentSourceRevision),error:null}}
    catch(error){return {read:null,error:formatApiError(error)}}
  },[allowed,tournamentTab,branchId,historicalRevision,savedSource.source,savedSource.error,
    calendarRevision.data,tournamentSourceRevision,runId])
  const tournamentProjection=useMemo(()=>{
    if(!allowed||!tournamentTab||!countryCode||!calendarSource.read?.response)
      return {model:null,error:null}
    try{return {model:projectCountryTournaments(calendarSource.read.response,runId,
      calendarSource.read.revisionBranchId,countryCode),error:null}}
    catch(error){return {model:null,error:formatApiError(error)}}
  },[allowed,tournamentTab,countryCode,calendarSource.read,runId])
  const tournamentsPending=Boolean(allowed&&tournamentTab&&tournamentSourceRevision&&
    (historicalRevision?revision.isPending:calendarRevision.isPending))
  const tournamentsError=calendarSource.error||tournamentProjection.error||
    (!tournamentSourceRevision?(cs?'Žádná uložená revize.':'No Saved Revision is available.'):
      calendarRevision.error&&!historicalRevision?formatApiError(calendarRevision.error):null)
  const readState=historicalRevision?savedSource.source?.response:q.data
  const sourceBranchId=historicalRevision?savedSource.source?.revisionBranchId:branchId
  const readEnabled=Boolean(allowed&&readState&&sourceBranchId)
  const projection=useMemo(()=>{
    if(!readEnabled||!readState||!sourceBranchId)return {world:null,error:null}
    try {return {world:projectRunWorld(readState,runId,sourceBranchId,year),error:null}}
    catch(error){return {world:null,error:formatApiError(error)}}
  },[readEnabled,readState,runId,sourceBranchId,year])
  const historyProjection=useMemo(()=>{
    if(!readEnabled||!readState||!sourceBranchId||!countryCode)return {history:null,error:null}
    try {return {history:projectRunWorldCountryHistory(readState,runId,sourceBranchId,countryCode,year),error:null}}
    catch(error){return {history:null,error:formatApiError(error)}}
  },[readEnabled,readState,runId,sourceBranchId,countryCode,year])
  const world=projection.world
  const visible=world?.countries.filter(c=>[c.code,c.name,c.region??''].some(v=>
    v.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase())))??[]
  const country=world?.countries.find(c=>c.code===countryCode)
  function changeParam(key:string,value:string):void {
    const next=new URLSearchParams(params)
    if(value)next.set(key,value);else next.delete(key)
    setParams(next,{replace:true})
  }
  return <section className="panel run-world-page">
    <div className="page-intro">
      <p className="eyebrow">PRODUCT RUN · WORLD</p>
      <h2>{cs?'Svět Runu':'Run World'}</h2>
      <p className="subtitle">{cs
        ? 'Čti současný Run World nebo přesně vybranou uloženou revizi. Datový rok, čas simulace a Saved Revision jsou oddělené.'
        : 'Read the current Run-owned World or an exact reachable Saved Revision. Reads never write; data year, simulation time and Saved Revision are separate.'}</p>
    </div>
    {branchError&&<p role="alert">{branchError}</p>}
    {time.error&&<p role="alert">{time.error}</p>}
    {time.mode!=='present'&&<p role="alert">{cs
      ? 'Historický simulační checkpoint '+(time.viewCheckpointId??'—')+' zatím nemá ověřené propojení na konkrétní Saved Revision World. Žádná dnešní ani jiná uložená data se nenahrazují.'
      : 'Simulation checkpoint '+(time.viewCheckpointId??'—')+' has no verified mapping to an exact Saved Revision World snapshot. No present or unrelated revision is substituted.'}</p>}
    {!branchLoading&&!branchId&&<p role="alert">{cs?'Vyber platnou branch tohoto Runu.':'Select a valid Branch of this Run.'}</p>}
    {allowed&&<div className="section-subtle" aria-label="Run World saved revision selector">
      <label>{cs?'Zdroj World snapshotu (Saved Revision)':'World snapshot source (Saved Revision)'}
        <select aria-label="World Saved Revision" value={selectedRevisionId}
          onChange={e=>changeParam('revision',e.target.value)}>
          <option value="">{cs?'Současný stav Runu (může obsahovat neuložené změny)':'Current Run state (may include unsaved changes)'}</option>
          {historyListMatches&&[...historyList.data!.saved_revisions].reverse().map(item=>
            <option key={item.revision_id} value={item.revision_id}>
              #{item.sequence} · {item.revision_id} {item.is_shared_revision?'· shared':''}
            </option>)}
          {historicalRevision&&(!historyListMatches||!historyList.data!.saved_revisions.some(x=>x.revision_id===selectedRevisionId))&&
            <option value={selectedRevisionId}>{cs?'Požadovaná revize':'Requested revision'}: {selectedRevisionId}</option>}
        </select>
      </label>
      <p className="status">{cs?'Čas simulace':'Simulation time'}: {cs?'současnost':'present'}
        {' · '}{cs?'Rok dat':'Data year'}: {year}
        {' · '}{cs?'Uložená revize':'Saved Revision'}: {historicalRevision?selectedRevisionId:(cs?'živý stav':'live state')}
      </p>
      {historyListMatches&&historyList.data!.has_more_older&&<p className="status">{cs
        ? 'Nabídka obsahuje nejnovějších 200 revizí. Starší dostupnou revizi lze otevřít přímým parametrem revision.'
        : 'Selector shows the newest 200 revisions. Older reachable revisions can be opened by an exact revision URL parameter.'}</p>}
      {historyList.isSuccess&&!historyListMatches&&<p role="alert">{cs
        ? 'Historie revizí nesouhlasí s vybraným Runem, branchí nebo Saved HEAD.'
        : 'Revision list does not match selected Run, Branch or Saved HEAD.'}</p>}
    </div>}
    {allowed&&!historicalRevision&&q.isPending&&<p role="status">{cs?'Načítám současný World snapshot…':'Loading current World snapshot…'}</p>}
    {allowed&&historicalRevision&&revision.isPending&&<p role="status">{cs?'Načítám vybranou historickou revizi…':'Loading exact Saved Revision…'}</p>}
    {allowed&&!historicalRevision&&q.error&&<p role="alert">{formatApiError(q.error)}</p>}
    {allowed&&historicalRevision&&revision.error&&<p role="alert">{cs
      ? 'Vybraná revize není v historii této branche dostupná: ':'Requested revision is unavailable or unreachable from this Branch: '}{formatApiError(revision.error)}</p>}
    {savedSource.error&&<p role="alert">{savedSource.error}</p>}
    {projection.error&&<p role="alert">{projection.error}</p>}
    {allowed&&historicalRevision&&savedSource.source&&!savedSource.source.response&&<p role="alert">{cs
      ? 'Vybraná Saved Revision neobsahuje uloženou komponentu Run World. Současný World se nepoužije.'
      : 'The selected Saved Revision has no saved Run World component. Current World is not substituted.'}</p>}
    {allowed&&!historicalRevision&&q.isSuccess&&!world&&!projection.error&&<section className="section-subtle">
      <h3>{cs?'World zatím není přiřazen':'No World assigned yet'}</h3>
      <p>{cs?'Tato branch neobsahuje uložené země světového balíčku. Nejde o svět s nulovou populací.':'This Branch has no Run-owned World countries yet; this is not a zero-population world.'}</p>
      <Link to="/admin/packages">{cs?'Otevřít balíčky':'Open Packages'} →</Link>
    </section>}
    {allowed&&historicalRevision&&savedSource.source?.response&&!world&&!projection.error&&<p role="alert">{cs
      ? 'Tato uložená revize nemá kompletní World Package. Neukazuje se žádná současná náhrada.'
      : 'This Saved Revision has no complete World Package. No current fallback is displayed.'}</p>}
    {world&&<div>
      <div className="run-world-overview-header">
        <div><strong>{world.worldName}</strong> <code>{world.worldId}</code>
          <p className="status">{cs?'Zdrojový balíček':'Source Package'}: {world.sourceLabel} · v{world.sourceVersion} · {cs?'Ruční Runové country záznamy':'Manual Run country entities'}: {world.manualCountryCount}</p>
          <p className="status">{cs?'Branch':'Branch'}: {selectedBranch?.display_name??branchId} · {cs?'Otisk Run snapshotu':'Run snapshot fingerprint'}: <code>{world.stateFingerprint.slice(0,14)}…</code></p>
          {historicalRevision&&<p className="status">Saved Revision: <code>{selectedRevisionId}</code> · {cs?'Původní branch':'Origin Branch'}: <code>{savedSource.source?.revisionBranchId??'—'}</code>{savedSource.source?.isShared?' · shared ancestor':''}</p>}</div>
        <label>{cs?'Rok dat':'Data year'}
          <select aria-label="World data year" value={year} onChange={e=>changeParam('year',e.target.value)}>
            {Array.from({length:96},(_,i)=>1955+i).map(y=><option key={y} value={y}>{y}</option>)}
          </select>
        </label>
      </div>
      {countryCode ? (country?<CountryDetail runId={runId} branchId={branchId!}
          savedHead={historicalRevision?null:selectedBranch?.saved_head_revision_id??null}
          historicalRevisionId={historicalRevision?selectedRevisionId:null}
          country={country} world={world} params={params} cs={cs} language={language}
          selectedWorldYear={year}
          history={historyProjection.history} historyError={historyProjection.error}
          tournaments={tournamentProjection.model} tournamentsError={tournamentsError}
          tournamentsPending={tournamentsPending} tournamentSourceRevision={tournamentSourceRevision||null}
          presentSeason={time.presentSeason} presentWeek={time.presentWeek}/>
        :<p role="alert">{cs?'Země v tomto Run World neexistuje.':'Country does not exist in this Run World.'} <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/world'}>{cs?'Zpět':'Back'}</Link></p>)
        :<>
        <div className="run-world-metrics" aria-label="World summary metrics">
          <div><span>{cs?'Zemí':'Countries'}</span><strong>{world.countries.length}</strong></div>
          <div><span>{cs?'Světová populace':'World population'}</span>
            <strong>{world.populationComplete?formatCount(world.exactPopulation,language):(cs?'Neúplná':'Incomplete')}</strong>
            {!world.populationComplete&&<small>{cs?'Součet dostupných hodnot (včetně odhadů): ':'Available values including estimates: '}
              {formatCount(world.knownPopulation,language)} · {world.estimatedPopulationCount} {cs?'zemí bez přesného údaje':'countries without exact year data'}</small>}
          </div>
          <div><span>{cs?'Země s neúplnými údaji':'Countries with incomplete data'}</span><strong>{world.missingCountryCount}</strong>
            <small>{cs?'Informační údaj, nikoliv blokující validace':'Informational only; not an operation blocker'}</small></div>
        </div>
        <div className="run-world-country-toolbar">
          <label>{cs?'Hledat zemi':'Search countries'}
            <input type="search" aria-label="Search Run World countries" value={search}
              onChange={e=>changeParam('q',e.target.value)} placeholder={cs?'Kód, název nebo region':'Code, name or region'}/>
          </label>
          <p>{visible.length} / {world.countries.length}</p>
        </div>
        <div className="table-responsive"><table aria-label="Run World countries">
          <thead><tr><th>{cs?'Země':'Country'}</th><th>Region</th>
            <th>{cs?'Populace':'Population'}</th><th>{cs?'Původ populace':'Population evidence'}</th>
            <th>{cs?'Ratingy':'Ratings'}</th><th>{cs?'Data':'Data'}</th></tr></thead>
          <tbody>{visible.map(c=><tr key={c.code}>
            <td><Link to={countryUrl(runId,c.code,params)}>{c.name} ({c.code})</Link></td>
            <td>{c.region??'—'}</td>
            <td>{c.population.value==null?'—':formatCount(c.population.value,language)}</td>
            <td>{populationLabel(c.population,cs)}</td>
            <td>{worldRatingKeys.filter(key=>c.ratings[key].value!=null).length}/6 (1–{c.ratingScale})</td>
            <td>{c.incomplete?(cs?'Neúplné':'Incomplete'):(cs?'Úplné':'Complete')}</td>
          </tr>)}</tbody></table></div>
        {visible.length===0&&<p role="status">{cs?'Filtru neodpovídá žádná země.':'No countries match the filter.'}</p>}
        <p className="status">{cs
          ? 'Nepřesné populační hodnoty a starší ratingy jsou označené. Talent Preview a historické výpočty jsou oddělené nástroje.'
          : 'Estimated populations and legacy ratings are labeled. Talent Preview and historical calculations remain separate workflows.'}</p>
        <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/players/generate'}>
          {cs?'Generovat hráče':'Generate players'} →
        </Link>
      </>}
    </div>}
  </section>
}
