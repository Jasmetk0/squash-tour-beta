import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom'
import { getWorldPackage, getWorldPackageCountries, getWorldPackageGeography, getWorldPackageValidation, listWorldPackages } from '../../api/client'
import type { WorldPackageValidationCheck } from '../../api/types'
import { useLanguage } from '../../i18n/LanguageContext'
import { formatApiError } from '../../utils/apiErrors'
import { catalogFromWorlds, catalogPath, inCategory, packageCategories } from './packageCatalog'
import type { CatalogItem, PackageCategory, PackageFilter } from './packageCatalog'

const categories: Record<PackageCategory,{cs:string,en:string}> = {
  world:{cs:'Svět',en:'World'}, countries:{cs:'Země',en:'Countries'},
  category:{cs:'Kategorie',en:'Category'}, series:{cs:'Série',en:'Series'},
  calendar:{cs:'Kalendáře',en:'Calendar'}, setup:{cs:'Nastavení',en:'Setup'},
  players:{cs:'Hráči',en:'Players'}, hybrid:{cs:'Hybridní',en:'Hybrid'}
}
/** Presentation only: unknown future registry values stay byte-for-byte visible. */
function statusText(value: string, cs: boolean): string {
  if (value === 'active') return cs ? 'aktivní' : 'active'
  if (value === 'archived') return cs ? 'archivovaný' : 'archived'
  if (value === 'warnings') return cs ? 'varování' : 'warnings'
  if (value === 'valid') return cs ? 'platné' : 'valid'
  if (value === 'error') return cs ? 'chyba' : 'error'
  if (value === 'warning') return cs ? 'varování' : 'warning'
  if (value === 'info') return cs ? 'informace' : 'info'
  return value
}
function sourceText(value: string, cs: boolean): string {
  if (value === 'built_in') return cs ? 'vestavěný' : 'built-in'
  if (value === 'custom') return cs ? 'vlastní' : 'custom'
  return value
}
/** UI wording only: values, filters, IDs and API data remain numeric/raw. */
function quantity(count: number, cs: boolean, cz: [string,string,string], en: [string,string]): string {
  const label = cs ? (count === 1 ? cz[0] : count >= 2 && count <= 4 ? cz[1] : cz[2])
    : (count === 1 ? en[0] : en[1])
  return `${count} ${label}`
}
const tools: Partial<Record<PackageCategory,string>> = {
  world:'/admin/world/library',countries:'/admin/world/library',
  category:'/admin/tour-seasons/categories',series:'/admin/tour-seasons/tournaments',
  calendar:'/admin/tour-seasons/season-templates',setup:'/admin/tour-seasons'
}
/** Read-only query recovery: never creates, imports or updates package state. */
function RetryRead({ cs, fetching, onRetry, what }: {
  cs: boolean; fetching: boolean; onRetry: () => void; what: 'catalog' | 'detail' | 'countries' | 'geography' | 'validation'
}): JSX.Element {
  const names = {
    catalog: ['seznam balíčků', 'package catalog'],
    detail: ['detail balíčku', 'package details'],
    countries: ['země', 'countries'],
    geography: ['geografii', 'geography'],
    validation: ['kontrolu', 'validation']
  }
  const subject = names[what][cs ? 0 : 1]
  return <button type="button" disabled={fetching} onClick={onRetry}>
    {fetching ? (cs ? 'Opakuji načítání…' : 'Retrying…')
      : (cs ? `Znovu načíst ${subject}` : `Retry ${subject}`)}
  </button>
}

function Inventory() {
  const query = useQuery({ queryKey:['world-packages'], queryFn:listWorldPackages, retry:false })
  const items = useMemo(() => catalogFromWorlds(query.data?.packages ?? []), [query.data])
  return {query,items}
}
function SourceNote({category}:{category?:PackageCategory}):JSX.Element {
  const {language}=useLanguage(), cs=language==='cs'
  return <p className="status">{cs
    ? 'Pouze World Packages mají nyní sjednocený registr přenosných balíčků. Šablony ani závislosti nejsou automaticky balíčky.'
    : 'Only World Packages currently have a unified portable source registry. Templates and dependencies are not automatically packages.'}
    {category && tools[category] && <> · <Link to={tools[category]!}>{cs?'Zdrojové nástroje':'Source tools'} →</Link></>}
  </p>
}
function PackageRow({item}:{item:CatalogItem}): JSX.Element {
  const {language}=useLanguage(), cs=language==='cs'
  return <li className="package-index-row">
    <div><strong><Link to={catalogPath(item)}>{item.name}</Link></strong>
      <p className="status">{item.description}</p>
      <small className="status">{item.key} · {sourceText(item.origin,cs)} · {statusText(item.status,cs)} · {item.version} · {item.editable?(cs?'vlastní':'custom'):(cs?'chráněný':'protected')}</small>
      <div className="package-index-tags">{item.categories.map(cat => <span key={cat}>{categories[cat][language]}</span>)}</div>
    </div>
    <Link to={catalogPath(item)}>{cs?'Detail':'Details'} →</Link>
  </li>
}
export function PackagesHomePage():JSX.Element {
  const {language}=useLanguage(), cs=language==='cs', {query,items}=Inventory()
  return <section className="panel package-index">
    <div className="page-intro"><h2>{cs?'Balíčky':'Packages'}</h2>
      <p className="subtitle">{cs?'Rozcestník zdrojových kategorií bez otevřeného Runu. Aktuální přenosný registr obsahuje pouze World Packages.':'Source-category hub without an active Run. Only World Packages have a portable registry today.'}</p></div>
    <p><Link className="button-link" to="/admin/packages/all">{cs?'Všechny balíčky':'All packages'} →</Link></p>
    {query.isPending && <p role="status">{cs?'Načítám registry…':'Loading registry…'}</p>}
    {query.isError && <><p className="error" role="alert">{cs ? 'Registr balíčků se nepodařilo načíst: ' : 'Package registry failed to load: '}{formatApiError(query.error)}</p><RetryRead cs={cs} what="catalog" fetching={query.isFetching} onRetry={() => { void query.refetch() }} /></>}
    <div className="package-index-categories">{packageCategories.map(cat =>
      <Link key={cat} className="package-index-category" to={'/admin/packages/category/'+cat}>
        <h3>{categories[cat][language]} →</h3>
        <p>{cat==='hybrid'
          ? (cs?'Samostatný hybridní registr není podporován; závislosti z balíčku nedělají hybridní balíček.':'No independent hybrid registry is supported; dependencies do not constitute a hybrid package.')
          : cat==='players'
            ? (cs?'Přenosný obsah hráčských balíčků zatím není definován.':'Portable Player-package payload is not specified yet.')
            : (cs?'Otevřít seznam této kategorie.':'Browse this category.')}</p>
        <small className="status">{(cat==='world'||cat==='countries') && query.isSuccess ? quantity(inCategory(items,cat).length,cs,['registrovaný','registrované','registrovaných'],['registered package','registered packages']) : (cs ? (cat==='world'||cat==='countries' ? (query.isPending ? 'Načítám registr…' : 'Registr není ověřen') : 'Samostatný registr není dostupný') : (cat==='world'||cat==='countries' ? (query.isPending ? 'Loading registry…' : 'Registry unverified') : 'Independent registry unavailable'))}</small>
      </Link>)}</div>
    <SourceNote />
  </section>
}
export function PackagesListPage():JSX.Element {
  const {categoryId=''}=useParams()
  const {pathname}=useLocation()
  const resolvedCategory=pathname==='/admin/packages/all'?'all':categoryId
  const {language}=useLanguage(),cs=language==='cs'
  const {query,items}=Inventory()
  const [search,setSearch]=useState(''),[origin,setOrigin]=useState('any'),[status,setStatus]=useState('any')
  const cat:PackageFilter|null=resolvedCategory==='all'||packageCategories.some(c=>c===resolvedCategory) ? resolvedCategory as PackageFilter : null
  if(!cat) return <section className="panel"><h2>{cs?'Neznámá kategorie':'Unknown category'}</h2><Link to="/admin/packages">{cs ? "Balíčky" : "Packages"}</Link></section>
  const registrySupported = cat === 'all' || cat === 'world' || cat === 'countries'
  const members=inCategory(items,cat)
  const searchTerm=normalizeCatalogSearch(search)
  const shown=members.filter(item=>(origin==='any'||(origin==='custom'?item.editable:!item.editable))
    &&(status==='any'||item.status===status)
    &&[item.key,item.name,item.description].some(s=>normalizeCatalogSearch(s).includes(searchTerm)))
  return <section className="panel package-index">
    <p><Link to="/admin/packages">← {cs?'Kategorie':'Categories'}</Link></p>
    <div className="page-intro"><h2>{cat==='all'?(cs?'Všechny balíčky':'All packages'):categories[cat][language]}</h2>
      <p className="subtitle">{cs?'Jedna identita = jedna položka.':'One identity, one inventory row.'}</p></div>
    <div className="package-index-filters">
      <label>{cs?'Hledání':'Search'}<input type="search" value={search} onChange={e=>setSearch(e.target.value)} /></label>
      <label>{cs?'Typ přístupu':'Access type'}<select aria-label="Package origin" value={origin} onChange={e=>setOrigin(e.target.value)}><option value="any">{cs?'Vše':'All'}</option><option value="custom">{cs?'Vlastní':'Custom'}</option><option value="protected">{cs?'Chráněné':'Protected'}</option></select></label>
      <label>{cs?'Stav':'Status'}<select aria-label="Package status" value={status} onChange={e=>setStatus(e.target.value)}><option value="any">{cs?'Vše':'All'}</option><option value="active">{cs ? "Aktivní" : "Active"}</option><option value="archived">{cs ? "Archivované" : "Archived"}</option></select></label>
    </div>
    {query.isPending && <p role="status">{cs?'Načítám…':'Loading…'}</p>}
    {query.isError && <><p role="alert" className="error">{cs ? 'Registr balíčků se nepodařilo načíst: ' : 'Package registry failed to load: '}{formatApiError(query.error)}</p><RetryRead cs={cs} what="catalog" fetching={query.isFetching} onRetry={() => { void query.refetch() }} /></>}
    {query.isSuccess && <><p className="status">{registrySupported?shown.length+' / '+members.length:(cs?'Samostatný registr této kategorie zatím není dostupný.':'No independent registry for this category yet.')}</p>
      {registrySupported && shown.length ? <ul className="package-index-list">{shown.map(item=><PackageRow key={item.key} item={item}/>)}</ul>
      : <p>{registrySupported ? (members.length === 0 ? (cs ? 'Registr nevrátil žádný balíček v této kategorii.' : 'The registry returned no packages in this category.') : (cs?'Žádný evidovaný balíček neodpovídá filtru.':'No indexed packages match this filter.')) : (cs?'Z této kategorie zatím nemáme ověřený inventář balíčků.':'A verified package inventory for this category is not yet available.')}</p>}
      {registrySupported && members.length>0 && shown.length===0 && (searchTerm || origin!=='any' || status!=='any')
        ? <button type="button" onClick={()=>{setSearch('');setOrigin('any');setStatus('any')}}>{cs?'Vymazat filtry':'Clear filters'}</button> : null}</>}
    {cat!=='all' && <SourceNote category={cat} />}
  </section>
}
/** Accents, case and surrounding whitespace affect only search, never saved country fields. */
function normalizeCatalogSearch(value:string):string {
  return value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim()
}
function resolveCountry(check:WorldPackageValidationCheck,codes:string[]):string|null {
  const raw=[check.path,check.field].filter(Boolean).join('/')
  return codes.find(code => raw.split(/[^A-Za-z0-9]+/).some(part => part.toUpperCase()===code.toUpperCase())) ?? null
}
export function PackageWorldDetailPage():JSX.Element {
  const {worldId=''}=useParams()
  const {language}=useLanguage(),cs=language==='cs'
  const [params,setParams]=useSearchParams(),tab=params.get('tab')||'overview'
  const active=tab==='contents'||tab==='validation'?tab:'overview'
  const [countrySearch,setCountrySearch]=useState('')
  const [severityFilter,setSeverityFilter]=useState('all')
  const q=useQuery({queryKey:['world-package',worldId],queryFn:()=>getWorldPackage(worldId),enabled:Boolean(worldId),retry:false})
  const countriesQuery=useQuery({queryKey:['world-package-countries',worldId],queryFn:()=>getWorldPackageCountries(worldId),enabled:active!=='overview',retry:false})
  const geoQuery=useQuery({queryKey:['world-package-geography',worldId],queryFn:()=>getWorldPackageGeography(worldId),enabled:active==='contents',retry:false})
  const valQuery=useQuery({queryKey:['world-package-validation',worldId],queryFn:()=>getWorldPackageValidation(worldId),enabled:active==='validation',retry:false})
  const pkg=q.data?.world_id===worldId?q.data:null
  const countries=countriesQuery.data?.world_id===worldId?countriesQuery.data.countries:null
  const geo=geoQuery.data?.world_id===worldId?geoQuery.data:null
  const validation=valQuery.data?.world_id===worldId?valQuery.data:null
  const countryTerm=normalizeCatalogSearch(countrySearch)
  const visibleCountries=countries?.filter(c=>normalizeCatalogSearch([c.name,c.code,c.region].join(' ')).includes(countryTerm))??[]
  const visibleChecks=validation?.checks.filter(c=>severityFilter==='all'||c.severity===severityFilter)??[]
  const source='/admin/world/library/'+encodeURIComponent(worldId)
  return <section className="panel package-index">
    <p><Link to="/admin/packages/category/world">← {cs?'World balíčky':'World packages'}</Link></p>
    <div className="page-intro"><p className="eyebrow">WORLD PACKAGE · {worldId}</p><h2>{pkg?.name??worldId}</h2>
      <p className="subtitle">{pkg?.description}</p></div>
    {q.isPending&&<p role="status">{cs?'Načítám zdroj…':'Loading source…'}</p>}
    {q.isError&&<><p className="error" role="alert">{cs ? 'Detail balíčku se nepodařilo načíst: ' : 'Failed to load package details: '}{formatApiError(q.error)}</p><RetryRead cs={cs} what="detail" fetching={q.isFetching} onRetry={() => { void q.refetch() }} /></>}
    {pkg && <>
      <nav className="package-index-tabs" aria-label={cs ? "Záložky balíčku" : "Package tabs"}>{(['overview','contents','validation'] as const).map(k=>
        <button type="button" key={k} aria-current={active===k?'page':undefined} onClick={()=>setParams({tab:k})}>
          {k==='overview'?(cs?'Přehled':'Overview'):k==='contents'?(cs?'Obsah':'Contents'):(cs?'Kontrola':'Validation')}
        </button>)}</nav>
      {active==='overview'&&<article className="package-index-detail">
        <h3>{cs?'Informace a původ':'Metadata and provenance'}</h3>
        <dl><dt>ID</dt><dd>{pkg.world_id}</dd><dt>{cs?'Verze':'Version'}</dt><dd>{pkg.version}</dd>
          <dt>{cs ? "Zdroj" : "Source"}</dt><dd>{sourceText(pkg.source,cs)} · {pkg.type}</dd>
          <dt>{cs ? "Stav" : "Status"}</dt><dd>{statusText(pkg.status,cs)} · {pkg.editable ? (cs ? "upravitelný" : "Editable") : (cs ? "chráněný" : "Protected")}</dd>
          <dt>{cs ? "Otisk" : "Fingerprint"}</dt><dd><code>{pkg.fingerprint}</code></dd>
          <dt>{cs?'Použití':'Usage'}</dt><dd>{pkg.used_by_run_count??(cs?'Nedostupné':'Unavailable')}</dd></dl>
        <h3>{cs?'Skutečně obsažené části':'Actual contents'}</h3>
        <p>{quantity(pkg.country_count,cs,['země','země','zemí'],['country','countries'])} · {quantity(pkg.continent_count,cs,['kontinent','kontinenty','kontinentů'],['continent','continents'])} · {quantity(pkg.region_count,cs,['region','regiony','regionů'],['region','regions'])} · {quantity(pkg.travel_region_count,cs,['cestovní region','cestovní regiony','cestovních regionů'],['travel region','travel regions'])} · {quantity(pkg.timezone_area_count,cs,['časová oblast','časové oblasti','časových oblastí'],['timezone area','timezone areas'])}</p>
        <p><Link to={source}>{pkg.editable?(cs?'Upravit zdroj':'Edit custom source'):(cs?'Vytvořit vlastní kopii':'Create custom copy')} →</Link></p>
        <p><Link to={'/admin/packages/world/'+encodeURIComponent(worldId)+'/apply'}>{cs?'Použít v Runu — vybrat obsah':'Apply to Run — select contents'} →</Link></p>
        <p className="status">{cs?'Selektivní import funguje pro World entity; export tohoto konkrétního zdroje zatím není hotový.':'Selective import supports World entities; source-specific export is not yet available.'}</p>
        <Link to="/admin/runs">{cs?'Vybrat Run':'Choose Run'} →</Link>
      </article>}
      {active==='contents'&&<article className="package-index-detail">
        <h3>{cs?'Země':'Countries'} ({pkg.country_count})</h3>
        {countriesQuery.isPending&&<p role="status">{cs ? "Načítám země…" : "Loading countries…"}</p>}
        {countriesQuery.isError&&<><p role="alert" className="error">{cs ? 'Země se nepodařilo načíst: ' : 'Failed to load countries: '}{formatApiError(countriesQuery.error)}</p><RetryRead cs={cs} what="countries" fetching={countriesQuery.isFetching} onRetry={() => { void countriesQuery.refetch() }} /></>}
        {countries&&<><p role="status" className="status">{cs ? 'Ověřený seznam zemí' : 'Verified country inventory'}: {countries.length}</p><label>{cs?'Hledat zemi, kód nebo region':'Search countries, codes or regions'}<input type="search" value={countrySearch} onChange={e=>setCountrySearch(e.target.value)}/></label>
          {countryTerm&&<p role="status" className="status">{cs ? `Zobrazeno ${visibleCountries.length} z ${countries.length} zemí. Filtr nemění obsah balíčku.` : `Showing ${visibleCountries.length} of ${countries.length} countries. Filtering does not change the package.`}</p>}
          <ul className="package-index-countries">{visibleCountries.map(c=>
            <li key={c.code}><Link to={source+'/countries/'+encodeURIComponent(c.code)}>{c.name} ({c.code})</Link>
              <span className="status">{c.region} · {c.population.toLocaleString(cs ? 'cs-CZ' : 'en-US')}</span></li>)}</ul>
          {countries.length === 0 ? <p role="status">{cs ? "V balíčku nejsou žádné země." : "This package contains no countries."}</p> : visibleCountries.length === 0 ? <p role="status">{cs ? "Žádná země neodpovídá hledání." : "No country matches the search."}</p> : null}</>}
        <h3>{cs?'Geografie':'Geography'}</h3>
        {geoQuery.isPending&&<p role="status">{cs ? "Načítám geografii…" : "Loading geography…"}</p>}
        {geoQuery.isError&&<><p className="error" role="alert">{cs ? 'Geografii se nepodařilo načíst: ' : 'Failed to load geography: '}{formatApiError(geoQuery.error)}</p><RetryRead cs={cs} what="geography" fetching={geoQuery.isFetching} onRetry={() => { void geoQuery.refetch() }} /></>}
        {geo&&<div>{([
          [cs ? 'Kontinenty' : 'Continents',geo.continents.map(x=>x.code+' '+x.name)],
          [cs ? 'Regiony' : 'Regions',geo.regions.map(x=>x.code+' '+x.name)],
          [cs ? 'Cestovní regiony' : 'Travel regions',geo.travel_regions.map(x=>x.code+' '+x.name)],
          [cs ? 'Časové oblasti' : 'Timezone areas',geo.timezone_areas.map(x=>x.code+' '+x.name)]
        ] as [string,string[]][]).map(([name,values])=><details key={name}><summary>{name} ({values.length})</summary>{values.length ? <ul>{values.map(x=><li key={x}>{x}</li>)}</ul> : <p role="status">{cs ? 'V této části nejsou žádné položky.' : 'No entries in this section.'}</p>}</details>)}</div>}
      </article>}
      {active==='validation'&&<article className="package-index-detail">
        <h3>{cs?'Skutečné výsledky kontroly':'Actual validation results'}</h3>
        {valQuery.isPending&&<p role="status">{cs ? "Načítám výsledky kontroly…" : "Loading validation…"}</p>}
        {valQuery.isError&&<><p role="alert" className="error">{cs ? 'Kontrolu se nepodařilo načíst: ' : 'Failed to load validation: '}{formatApiError(valQuery.error)}</p><RetryRead cs={cs} what="validation" fetching={valQuery.isFetching} onRetry={() => { void valQuery.refetch() }} /></>}
        {validation&&<><p className="status">{cs ? "Diagnostické zprávy jsou zobrazeny v původním znění." : "Diagnostic messages are shown verbatim."}</p><p>{statusText(validation.status,cs)} · {quantity(validation.error_count,cs,['chyba','chyby','chyb'],['error','errors'])} · {quantity(validation.warning_count,cs,['varování','varování','varování'],['warning','warnings'])} · {quantity(validation.info_count,cs,['informace','informace','informací'],['info','info'])}</p>
          <label>{cs?'Filtrovat kontroly podle závažnosti':'Filter checks by severity'}<select aria-label="Package validation severity filter" value={severityFilter} onChange={event=>setSeverityFilter(event.target.value)}>
            <option value="all">{cs?'Všechny kontroly':'All checks'}</option>
            <option value="error">{cs?'Chyby':'Errors'}</option>
            <option value="warning">{cs?'Varování':'Warnings'}</option>
            <option value="info">{cs?'Informace':'Information'}</option>
          </select></label>
          <p role="status" className="status">{cs ? `Zobrazeno ${visibleChecks.length} z ${validation.checks.length} kontrol. Souhrn validace se filtrem nemění.` : `Showing ${visibleChecks.length} of ${validation.checks.length} checks. Validation totals remain unchanged.`}</p>
          <ul className="package-index-checks">{visibleChecks.map((check,i)=>{
            const country=resolveCountry(check,countries?.map(c=>c.code)??[])
            return <li key={check.code+':'+i}><strong>{cs ? statusText(check.severity, true).toUpperCase() : check.severity.toUpperCase()} · {check.code}</strong>
              <p>{check.message}</p><small className="status">{check.path}{check.field&&' · '+check.field}</small>
              {country&&<p><Link to={source+'/countries/'+encodeURIComponent(country)}>{cs?'Otevřít dotčenou zemi':'Open affected country'}: {country} →</Link></p>}</li>
          })}</ul>
          {validation.checks.length === 0 ? <p role="status">{cs ? "Kontrola nevrátila žádné jednotlivé záznamy." : "Validation returned no individual checks."}</p> : visibleChecks.length===0 ? <p role="status">{cs ? "Zvolenému filtru neodpovídají žádné záznamy kontroly." : "No validation checks match this filter."}</p> : null}
          {countriesQuery.isError&&<p className="status">{cs?'Odkazy na jednotlivé země nejsou dostupné.':'Country links cannot be verified.'}</p>}
        </>}
      </article>}
    </>}
  </section>
}
