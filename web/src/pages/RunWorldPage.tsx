/** Run → World reads only the selected Branch's Run-owned package copy.
 * A historical checkpoint is not silently substituted with current Run data.
 */
import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { getRunPackageState } from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'
import { projectRunWorld, worldRatingKeys } from './runWorldReadModel'
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
function CountryDetail({runId,country,world,params,cs,language}:{
  runId:string;country:RunWorldCountry;world:RunWorldOverview;
  params:URLSearchParams;cs:boolean;language:string
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
    {active==='population'&&<section className="section-subtle">
      <h4>{cs?'Populace pro zvolený rok':'Population for selected year'}</h4>
      <p>{country.population.value==null?'—':formatCount(country.population.value,language)}</p>
      <p role="status">{populationLabel(country.population,cs)}.
        {country.population.kind!=='exact'&&' '+(cs?'Jde o fallback/odhad, nikoli potvrzenou populaci zvoleného roku.':'This is fallback/estimated data, not verified population for the selected year.')}</p>
      <p>{cs?'Editace historické populace a grafy budou navazující implementace; zobrazení nic nezapisuje.':'Historical population editing and charts are separate follow-up work. This view never writes.'}</p>
    </section>}
    {active==='ratings'&&<section className="section-subtle">
      <h4>{cs?'Šest ratingů země':'Six country ratings'}</h4>
      <p>{cs?'Použitá škála':'Scale'}: 1–{country.ratingScale}. {cs?'Zdroj roku a metoda jsou vypsány u každé hodnoty.':'Source year and method appear beside each value.'}</p>
      <div className="table-responsive"><table><thead><tr>
        <th>{cs?'Atribut':'Attribute'}</th><th>{cs?'Hodnota':'Value'}</th><th>{cs?'Zdroj':'Source'}</th>
      </tr></thead><tbody>{worldRatingKeys.map(key=><tr key={key}>
        <td>{key.replace(/_/g,' ')}</td><td>{country.ratings[key].value??'—'}</td>
        <td>{country.ratings[key].provenance}{country.ratings[key].sourceYear==null?'':' · '+country.ratings[key].sourceYear}</td>
      </tr>)}</tbody></table></div>
    </section>}
    {active==='players'&&<section className="section-subtle">
      <h4>{cs?'Hráči a talenty':'Players & Talent'}</h4>
      <p>{cs?'V tomto řezu není připojený časově věrný seznam hráčů země; očekávání není skutečný intake.':'A historically scoped country roster is not yet connected here; expected intake is not an actual roster.'}</p>
      <Link to={'/admin/runs/'+encodeURIComponent(runId)+'/players'}>{cs?'Otevřít hráče Runu':'Open Run players'} →</Link>
    </section>}
    {(active==='records'||active==='tournaments')&&<section className="section-subtle">
      <h4>{labels[available.indexOf(active)]}</h4>
      <p role="status">{cs?'Pro tento Run, branch a rok ještě není připojený autoritativní historický read-model. Žádné výsledky ani rekordy se nedopočítávají z aktuálních dat.':'No authoritative historical read model is connected for this Run, Branch and year. Results and records are never invented from current data.'}</p>
    </section>}
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
  const allowed=Boolean(runId&&branchId&&time.mode==='present'&&!time.isLoading&&!time.error&&!branchLoading&&!branchError)
  const q=useQuery({
    queryKey:['run-world-current-packages',runId,branchId],
    queryFn:()=>getRunPackageState(runId,branchId!),
    enabled:allowed,
    retry:false
  })
  const projection=useMemo(()=>{
    if(!q.data||!branchId)return {world:null,error:null}
    try {return {world:projectRunWorld(q.data,runId,branchId,year),error:null}}
    catch(error){return {world:null,error:formatApiError(error)}}
  },[q.data,runId,branchId,year])
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
        ? 'Jediným zdrojem je kopie World Package v právě vybrané branchi. Náhled nic nezapisuje.'
        : 'This view uses only the World Package copy stored in the selected Branch. All reads are non-mutating.'}</p>
    </div>
    {branchError&&<p role="alert">{branchError}</p>}
    {time.error&&<p role="alert">{time.error}</p>}
    {time.mode!=='present'&&<p role="alert">{cs
      ? 'Vybrán historický checkpoint. Aktuální World snapshot se nesmí vydávat za historická data. Přejdi na současný čas.'
      : 'Historical checkpoint selected. Current World data must not impersonate historical facts. Select the present time.'}</p>}
    {!branchLoading&&!branchId&&<p role="alert">{cs?'Vyber platnou branch tohoto Runu.':'Select a valid Branch of this Run.'}</p>}
    {allowed&&q.isPending&&<p role="status">{cs?'Načítám World snapshot…':'Loading Run World snapshot…'}</p>}
    {q.error&&<p role="alert">{formatApiError(q.error)}</p>}
    {projection.error&&<p role="alert">{projection.error}</p>}
    {allowed&&q.isSuccess&&!world&&!projection.error&&<section className="section-subtle">
      <h3>{cs?'World zatím není přiřazen':'No World assigned yet'}</h3>
      <p>{cs?'Tato branch neobsahuje uložené země světového balíčku. Nejde o svět s nulovou populací.':'This Branch has no Run-owned World countries yet; this is not a zero-population world.'}</p>
      <Link to="/admin/packages">{cs?'Otevřít balíčky':'Open Packages'} →</Link>
    </section>}
    {world&&<div>
      <div className="run-world-overview-header">
        <div><strong>{world.worldName}</strong> <code>{world.worldId}</code>
          <p className="status">{cs?'Zdrojový balíček':'Source Package'}: {world.sourceLabel} · v{world.sourceVersion} · {cs?'Ruční Runové country záznamy':'Manual Run country entities'}: {world.manualCountryCount}</p>
          <p className="status">{cs?'Branch':'Branch'}: {selectedBranch?.display_name??branchId} · {cs?'Otisk Run snapshotu':'Run snapshot fingerprint'}: <code>{world.stateFingerprint.slice(0,14)}…</code></p></div>
        <label>{cs?'Rok dat':'Data year'}
          <select aria-label="World data year" value={year} onChange={e=>changeParam('year',e.target.value)}>
            {Array.from({length:96},(_,i)=>1955+i).map(y=><option key={y} value={y}>{y}</option>)}
          </select>
        </label>
      </div>
      {countryCode ? (country?<CountryDetail runId={runId} country={country} world={world} params={params} cs={cs} language={language}/>
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
