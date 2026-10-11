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
const tools: Partial<Record<PackageCategory,string>> = {
  world:'/admin/world/library',countries:'/admin/world/library',
  category:'/admin/tour-seasons/categories',series:'/admin/tour-seasons/tournaments',
  calendar:'/admin/tour-seasons/season-templates',setup:'/admin/tour-seasons'
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
      <small className="status">{item.key} · {item.status} · {item.version} · {item.editable?(cs?'vlastní':'custom'):(cs?'chráněný':'protected')}</small>
      <div className="package-index-tags">{item.categories.map(cat => <span key={cat}>{categories[cat][language]}</span>)}</div>
    </div>
    <Link to={catalogPath(item)}>{cs?'Detail':'Details'} →</Link>
  </li>
}
export function PackagesHomePage():JSX.Element {
  const {language}=useLanguage(), cs=language==='cs', {query,items}=Inventory()
  return <section className="panel package-index">
    <div className="page-intro"><h2>{cs?'Balíčky':'Packages'}</h2>
      <p className="subtitle">{cs?'Rozcestník ověřených zdrojových dat, bez aktivního Runu.':'Verified source content categories, without an active Run.'}</p></div>
    <p><Link className="button-link" to="/admin/packages/all">{cs?'Všechny balíčky':'All packages'} →</Link></p>
    {query.isPending && <p role="status">{cs?'Načítám registry…':'Loading registry…'}</p>}
    {query.isError && <p className="error" role="alert">{formatApiError(query.error)}</p>}
    <div className="package-index-categories">{packageCategories.map(cat =>
      <Link key={cat} className="package-index-category" to={'/admin/packages/category/'+cat}>
        <h3>{categories[cat][language]} →</h3>
        <p>{cat==='hybrid'
          ? (cs?'Jen balíčky s ověřeným vícetypovým obsahem.':'Verified multi-type packages only.')
          : cat==='players'
            ? (cs?'Payload zatím není schválen.':'Payload not yet specified.')
            : (cs?'Otevřít seznam této kategorie.':'Browse this category.')}</p>
        <small className="status">{(cat==='world'||cat==='countries') && query.isSuccess ? inCategory(items,cat).length+(cs?' registrovaných':' registered') : (cs?'Registr zatím není dostupný':'Registry not available')}</small>
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
  if(!cat) return <section className="panel"><h2>{cs?'Neznámá kategorie':'Unknown category'}</h2><Link to="/admin/packages">Packages</Link></section>
  const members=inCategory(items,cat)
  const shown=members.filter(item=>(origin==='any'||(origin==='custom'?item.editable:!item.editable))
    &&(status==='any'||item.status===status)
    &&[item.key,item.name,item.description].some(s=>s.toLowerCase().includes(search.toLowerCase().trim())))
  return <section className="panel package-index">
    <p><Link to="/admin/packages">← {cs?'Kategorie':'Categories'}</Link></p>
    <div className="page-intro"><h2>{cat==='all'?(cs?'Všechny balíčky':'All packages'):categories[cat][language]}</h2>
      <p className="subtitle">{cs?'Jedna identita = jedna položka.':'One identity, one inventory row.'}</p></div>
    <div className="package-index-filters">
      <label>{cs?'Hledání':'Search'}<input type="search" value={search} onChange={e=>setSearch(e.target.value)} /></label>
      <label>{cs?'Původ':'Origin'}<select aria-label="Package origin" value={origin} onChange={e=>setOrigin(e.target.value)}><option value="any">{cs?'Vše':'All'}</option><option value="custom">{cs?'Vlastní':'Custom'}</option><option value="protected">{cs?'Chráněné':'Protected'}</option></select></label>
      <label>{cs?'Stav':'Status'}<select aria-label="Package status" value={status} onChange={e=>setStatus(e.target.value)}><option value="any">{cs?'Vše':'All'}</option><option value="active">Active</option><option value="archived">Archived</option></select></label>
    </div>
    {query.isPending && <p role="status">{cs?'Načítám…':'Loading…'}</p>}
    {query.isError && <p role="alert" className="error">{formatApiError(query.error)}</p>}
    {query.isSuccess && <><p className="status">{cat==='all'||cat==='world'||cat==='countries'?shown.length+' / '+members.length:(cs?'Samostatný registr této kategorie zatím není dostupný.':'No independent registry for this category yet.')}</p>
      {shown.length ? <ul className="package-index-list">{shown.map(item=><PackageRow key={item.key} item={item}/>)}</ul>
      : <p>{cat==='all'||cat==='world'||cat==='countries' ? (cs?'Žádný evidovaný balíček neodpovídá filtru.':'No indexed packages match this filter.') : (cs?'Z této kategorie zatím nemáme ověřený inventář balíčků.':'A verified package inventory for this category is not yet available.')}</p>}</>}
    {cat!=='all' && <SourceNote category={cat} />}
  </section>
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
  const q=useQuery({queryKey:['world-package',worldId],queryFn:()=>getWorldPackage(worldId),enabled:Boolean(worldId),retry:false})
  const countriesQuery=useQuery({queryKey:['world-package-countries',worldId],queryFn:()=>getWorldPackageCountries(worldId),enabled:active!=='overview',retry:false})
  const geoQuery=useQuery({queryKey:['world-package-geography',worldId],queryFn:()=>getWorldPackageGeography(worldId),enabled:active==='contents',retry:false})
  const valQuery=useQuery({queryKey:['world-package-validation',worldId],queryFn:()=>getWorldPackageValidation(worldId),enabled:active==='validation',retry:false})
  const pkg=q.data?.world_id===worldId?q.data:null
  const countries=countriesQuery.data?.world_id===worldId?countriesQuery.data.countries:null
  const geo=geoQuery.data?.world_id===worldId?geoQuery.data:null
  const validation=valQuery.data?.world_id===worldId?valQuery.data:null
  const source='/admin/world/library/'+encodeURIComponent(worldId)
  return <section className="panel package-index">
    <p><Link to="/admin/packages/category/world">← {cs?'World balíčky':'World packages'}</Link></p>
    <div className="page-intro"><p className="eyebrow">WORLD PACKAGE · {worldId}</p><h2>{pkg?.name??worldId}</h2>
      <p className="subtitle">{pkg?.description}</p></div>
    {q.isPending&&<p role="status">{cs?'Načítám zdroj…':'Loading source…'}</p>}
    {q.isError&&<p className="error" role="alert">{formatApiError(q.error)}</p>}
    {pkg && <>
      <nav className="package-index-tabs" aria-label="Package tabs">{(['overview','contents','validation'] as const).map(k=>
        <button type="button" key={k} aria-current={active===k?'page':undefined} onClick={()=>setParams({tab:k})}>
          {k==='overview'?(cs?'Přehled':'Overview'):k==='contents'?(cs?'Obsah':'Contents'):(cs?'Kontrola':'Validation')}
        </button>)}</nav>
      {active==='overview'&&<article className="package-index-detail">
        <h3>{cs?'Informace a původ':'Metadata and provenance'}</h3>
        <dl><dt>ID</dt><dd>{pkg.world_id}</dd><dt>{cs?'Verze':'Version'}</dt><dd>{pkg.version}</dd>
          <dt>{cs?'Zdroj':'Source'}</dt><dd>{pkg.source} · {pkg.type}</dd>
          <dt>Status</dt><dd>{pkg.status} · {pkg.editable?'Editable':'Protected'}</dd>
          <dt>Fingerprint</dt><dd><code>{pkg.fingerprint}</code></dd>
          <dt>{cs?'Použití':'Usage'}</dt><dd>{pkg.used_by_run_count??(cs?'Nedostupné':'Unavailable')}</dd></dl>
        <h3>{cs?'Skutečně obsažené části':'Actual contents'}</h3>
        <p>{pkg.country_count} countries · {pkg.continent_count} continents · {pkg.region_count} regions · {pkg.travel_region_count} travel regions · {pkg.timezone_area_count} timezone areas</p>
        <p><Link to={source}>{pkg.editable?(cs?'Upravit zdroj':'Edit custom source'):(cs?'Vytvořit vlastní kopii':'Create custom copy')} →</Link></p>
        <p><Link to={'/admin/packages/world/'+encodeURIComponent(worldId)+'/apply'}>{cs?'Použít v Runu — vybrat obsah':'Apply to Run — select contents'} →</Link></p>
        <p className="status">{cs?'Selektivní import funguje pro World entity; export tohoto konkrétního zdroje zatím není hotový.':'Selective import supports World entities; source-specific export is not yet available.'}</p>
        <Link to="/admin/runs">{cs?'Vybrat Run':'Choose Run'} →</Link>
      </article>}
      {active==='contents'&&<article className="package-index-detail">
        <h3>{cs?'Země':'Countries'} ({pkg.country_count})</h3>
        {countriesQuery.isPending&&<p role="status">Loading countries…</p>}
        {countriesQuery.isError&&<p role="alert" className="error">{formatApiError(countriesQuery.error)}</p>}
        {countries&&<><label>{cs?'Hledat zemi':'Search countries'}<input type="search" value={countrySearch} onChange={e=>setCountrySearch(e.target.value)}/></label>
          <ul className="package-index-countries">{countries.filter(c=>(c.name+' '+c.code).toLowerCase().includes(countrySearch.toLowerCase())).map(c=>
            <li key={c.code}><Link to={source+'/countries/'+encodeURIComponent(c.code)}>{c.name} ({c.code})</Link>
              <span className="status">{c.region} · {c.population.toLocaleString()}</span></li>)}</ul></>}
        <h3>{cs?'Geografie':'Geography'}</h3>
        {geoQuery.isPending&&<p role="status">Loading geography…</p>}
        {geoQuery.isError&&<p className="error" role="alert">{formatApiError(geoQuery.error)}</p>}
        {geo&&<div>{([
          ['Continents',geo.continents.map(x=>x.code+' '+x.name)],
          ['Regions',geo.regions.map(x=>x.code+' '+x.name)],
          ['Travel regions',geo.travel_regions.map(x=>x.code+' '+x.name)],
          ['Timezone areas',geo.timezone_areas.map(x=>x.code+' '+x.name)]
        ] as [string,string[]][]).map(([name,values])=><details key={name}><summary>{name} ({values.length})</summary><ul>{values.map(x=><li key={x}>{x}</li>)}</ul></details>)}</div>}
      </article>}
      {active==='validation'&&<article className="package-index-detail">
        <h3>{cs?'Skutečné výsledky kontroly':'Actual validation results'}</h3>
        {valQuery.isPending&&<p role="status">Loading validation…</p>}
        {valQuery.isError&&<p role="alert" className="error">{formatApiError(valQuery.error)}</p>}
        {validation&&<><p>{validation.status} · {validation.error_count} errors · {validation.warning_count} warnings · {validation.info_count} info</p>
          <ul className="package-index-checks">{validation.checks.map((check,i)=>{
            const country=resolveCountry(check,countries?.map(c=>c.code)??[])
            return <li key={check.code+':'+i}><strong>{check.severity.toUpperCase()} · {check.code}</strong>
              <p>{check.message}</p><small className="status">{check.path}{check.field&&' · '+check.field}</small>
              {country&&<p><Link to={source+'/countries/'+encodeURIComponent(country)}>{cs?'Otevřít dotčenou zemi':'Open affected country'}: {country} →</Link></p>}</li>
          })}</ul>
          {countriesQuery.isError&&<p className="status">{cs?'Odkazy na jednotlivé země nejsou dostupné.':'Country links cannot be verified.'}</p>}
        </>}
      </article>}
    </>}
  </section>
}
