import type { FormEvent, ReactNode } from 'react'
import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { cloneWorldPackage, createWorldPackageCountry, deleteWorldPackageCountry, getWorldPackage, getWorldPackageCountries, getWorldPackageCountry, getWorldPackageGeography, getWorldPackageValidation, listWorldPackages, replaceWorldPackageTimezoneAreas, updateWorldPackageCountry, updateWorldPackageCountryPopulation } from '../api/client'
import type { CountryRecord, WorldPackage, WorldPackageClonePayload, WorldPackageCloneResponse, WorldPackageCountryCreatePayload, WorldPackageCountryDetail, WorldPackageCountryPopulationUpdatePayload, WorldPackageCountryUpdatePayload, WorldPackageGeography, WorldPackageValidation } from '../api/types'
import { SectionCard } from '../components/RunScopedUi'
import { useLanguage } from '../i18n/LanguageContext'
import { formatApiError } from '../utils/apiErrors'

function yesNo(value: boolean, yes: string, no: string): string {
  return value ? yes : no
}

function usageLabel(value: number | null, cs = false): string {
  return value === null ? (cs ? 'Využití zatím není sledováno' : 'Usage not tracked yet') : String(value)
}

function shortFingerprint(fingerprint: string): string {
  if (fingerprint.length <= 16) return fingerprint
  return `${fingerprint.slice(0, 8)}…${fingerprint.slice(-8)}`
}

function PackageTable({ packages, cs }: { packages: WorldPackage[], cs: boolean }): JSX.Element {
  if (packages.length === 0) {
    return <p className="status">{cs ? 'Registr zatím nevrátil žádné World Packages.' : 'No World Packages were returned by the registry.'}</p>
  }

  return (
    <div className="table-responsive"><table aria-label="World packages table">
      <thead>
        <tr>
          <th>{cs ? 'Název' : 'Name'}</th>
          <th>World ID</th>
          <th>{cs ? 'Typ' : 'Type'}</th>
          <th>{cs ? 'Stav' : 'Status'}</th>
          <th>{cs ? 'Ověření' : 'Validation'}</th>
          <th>{cs ? 'Režim balíčku' : 'Package mode'}</th>
          <th>{cs ? 'Země' : 'Countries'}</th>
          <th>{cs ? 'Kontinenty' : 'Continents'}</th>
          <th>{cs ? 'Regiony' : 'Regions'}</th>
          <th>{cs ? 'Cestovní regiony' : 'Travel Regions'}</th><th>{cs ? 'Časové oblasti' : 'Timezone Areas'}</th>
          <th>{cs ? 'Použito v Runech' : 'Used by Runs'}</th>
          <th>{cs ? 'Verze' : 'Version'}</th>
          <th>Fingerprint</th>
          <th>{cs ? 'Akce' : 'Actions'}</th>
        </tr>
      </thead>
      <tbody>
        {packages.map((pkg) => (
          <tr key={pkg.world_id}>
            <td>{pkg.name}</td>
            <td><code>{pkg.world_id}</code></td>
            <td>{pkg.type === 'custom' ? (cs ? 'Vlastní' : 'Custom') : (cs ? 'Vestavěný' : 'Built-in')}</td>
            <td>{pkg.status === 'archived' ? (cs ? 'Archivovaný' : 'Archived') : (cs ? 'Aktivní' : 'Active')}</td>
            <td>{pkg.validation_status === 'valid'
              ? (cs ? 'Ověřeno' : 'Valid')
              : (cs ? 'Neověřeno' : 'Unknown')}</td>
            <td>{yesNo(pkg.editable, cs ? 'Upravitelný zdroj' : 'Editable source', cs ? 'Jen pro čtení' : 'Read-only')}</td>
            <td>{pkg.country_count}</td>
            <td>{pkg.continent_count}</td>
            <td>{pkg.region_count}</td>
            <td>{pkg.travel_region_count}</td><td>{pkg.timezone_area_count}</td>
            <td>{usageLabel(pkg.used_by_run_count, cs)}</td>
            <td>{pkg.version}</td>
            <td><code title={pkg.fingerprint}>{shortFingerprint(pkg.fingerprint)}</code></td>
            <td><Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}`}>{cs ? 'Otevřít World Package' : 'Open World Package'}</Link></td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

export function WorldLibraryPage(): JSX.Element {
  const { language } = useLanguage()
  const cs = language === 'cs'
  const packagesQuery = useQuery({ queryKey: ['world-packages'], queryFn: listWorldPackages, retry: false })
  const [search, setSearch] = useState('')
  const [packageType, setPackageType] = useState<'all' | 'built_in' | 'custom'>('all')
  const [packageStatus, setPackageStatus] = useState<'all' | 'active' | 'archived'>('all')
  const [validationStatus, setValidationStatus] = useState<'all' | 'valid' | 'unknown'>('all')
  const [editableOnly, setEditableOnly] = useState(false)
  const [sortBy, setSortBy] = useState<'registry' | 'name' | 'countries'>('registry')
  const packages = packagesQuery.data?.packages ?? []
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const hasFilters = search !== '' || packageType !== 'all' || packageStatus !== 'all' ||
    validationStatus !== 'all' || editableOnly || sortBy !== 'registry'
  const visiblePackages = packages.filter(pkg =>
    (packageType === 'all' || (packageType === 'custom' ? pkg.type === 'custom' : pkg.type === 'official')) &&
    (packageStatus === 'all' || pkg.status === packageStatus) &&
    (validationStatus === 'all' || pkg.validation_status === validationStatus) &&
    (!editableOnly || pkg.editable) &&
    (normalizedSearch === '' || `${pkg.name} ${pkg.world_id}`.toLocaleLowerCase().includes(normalizedSearch))
  )
  if (sortBy !== 'registry') {
    visiblePackages.sort((a, b) => sortBy === 'countries'
      ? b.country_count - a.country_count || a.world_id.localeCompare(b.world_id)
      : a.name.localeCompare(b.name) || a.world_id.localeCompare(b.world_id))
  }
  const resetFilters = () => {
    setSearch('')
    setPackageType('all')
    setPackageStatus('all')
    setValidationStatus('all')
    setEditableOnly(false)
    setSortBy('registry')
  }

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World Packages</h2>
        <p className="subtitle">{cs ? 'Registr dostupných zdrojů světa pro Squash Engine.' : 'Registry of available world sources for Squash Engine.'}</p>
      </div>
      <p>{cs
        ? 'World Packages jsou opakovaně použitelné zdroje světa. Run může vzniknout i prázdný; podporovaný zdroj lze později zkopírovat bez změny originálu.'
        : 'World Packages are reusable world sources. A Run can start empty; a supported source may be copied in later without altering the original.'}
        {' '}{cs ? 'Vlastní zdroje jsou uloženy v ' : 'Custom sources are stored under '}
        <code>config/world_packages/custom/</code>.
      </p>
      <p><Link to="/admin/world">{cs ? 'Zpět na přehled světů' : 'Back to World hub'}</Link></p>

      <SectionCard title={cs ? 'Dostupné World Packages' : 'Available World Packages'}>
        {packagesQuery.isLoading && <p className="status">{cs ? 'Načítám World Packages…' : 'Loading World Packages...'}</p>}
        {packagesQuery.error && <p className="error">{cs ? 'Nepodařilo se načíst World Packages: ' : 'Failed to load World Packages: '}{formatApiError(packagesQuery.error)}</p>}
        {packagesQuery.data && <>
          <div className="form-grid">
            <label>
              {cs ? 'Hledat World Package' : 'Search World Packages'}
              <input type="search" value={search} onChange={event => setSearch(event.target.value)}
                placeholder={cs ? 'Název nebo World ID' : 'Name or World ID'} />
            </label>
            <label>
              {cs ? 'Typ World Package' : 'World Package type'}
              <select value={packageType} onChange={event => setPackageType(event.target.value as typeof packageType)}>
                <option value="all">{cs ? 'Všechny typy' : 'All types'}</option>
                <option value="built_in">{cs ? 'Vestavěné' : 'Built-in'}</option>
                <option value="custom">{cs ? 'Vlastní' : 'Custom'}</option>
              </select>
            </label>
            <label>
              {cs ? 'Stav World Package' : 'World Package status'}
              <select value={packageStatus} onChange={event => setPackageStatus(event.target.value as typeof packageStatus)}>
                <option value="all">{cs ? 'Všechny stavy' : 'All statuses'}</option>
                <option value="active">{cs ? 'Aktivní' : 'Active'}</option>
                <option value="archived">{cs ? 'Archivované' : 'Archived'}</option>
              </select>
            </label>
            <label>
              {cs ? 'Ověření World Package' : 'World Package validation'}
              <select value={validationStatus} onChange={event => setValidationStatus(event.target.value as typeof validationStatus)}>
                <option value="all">{cs ? 'Všechny stavy ověření' : 'All validation states'}</option>
                <option value="valid">{cs ? 'Ověřené' : 'Valid'}</option>
                <option value="unknown">{cs ? 'Neověřené' : 'Unknown'}</option>
              </select>
            </label>
            <label>
              {cs ? 'Seřadit World Packages' : 'Sort World Packages'}
              <select value={sortBy} onChange={event => setSortBy(event.target.value as typeof sortBy)}> 
                <option value="registry">{cs ? 'Pořadí registru' : 'Registry order'}</option>
                <option value="name">{cs ? 'Podle názvu (A–Z)' : 'Name (A–Z)'}</option>
                <option value="countries">{cs ? 'Podle počtu zemí (sestupně)' : 'Country count (descending)'}</option>
              </select>
            </label>
          </div>
          <label><input type="checkbox" checked={editableOnly}
            onChange={event => setEditableOnly(event.target.checked)} />
            {' '}{cs ? 'Pouze upravitelné zdroje' : 'Editable sources only'}
          </label>
          <p className="status">{cs
            ? 'Neověřeno znamená, že registr nepotvrdil výsledek validace; nejde automaticky o chybu.'
            : 'Unknown validation means the registry has not confirmed a result; it does not necessarily indicate an error.'}</p>
          <button type="button" disabled={!hasFilters} onClick={resetFilters}>
            {cs ? 'Vymazat filtry a řazení' : 'Clear filters and sorting'}
          </button>
          <p role="status">{cs
            ? `Zobrazeno ${visiblePackages.length} z ${packages.length} World Packages`
            : `Showing ${visiblePackages.length} of ${packages.length} World Packages`}</p>
          {packages.length > 0 && visiblePackages.length === 0
            ? <p className="status">{cs
              ? 'Žádné World Packages neodpovídají hledání nebo filtrům.'
              : 'No World Packages match your search or filters.'}</p>
            : <PackageTable packages={visiblePackages} cs={cs} />}
        </>}
      </SectionCard>
    </section>
  )
}

function DetailRow({ label, value }: { label: string, value: ReactNode }): JSX.Element {
  return <p><strong>{label}:</strong> {value}</p>
}


function CloneResultCard({ result }: { result: WorldPackageCloneResponse }): JSX.Element {
  return (
    <div className={result.ok && !result.dry_run ? 'status' : result.ok ? 'status' : 'error'} aria-label="Clone result">
      {result.ok && result.dry_run && <p><strong>Preview only:</strong> no files were written.</p>}
      {result.ok && !result.dry_run && <p><strong>Success:</strong> Custom World package created.</p>}
      <DetailRow label="Target path" value={<code>{result.target_path}</code>} />
      <DetailRow label="Source world ID" value={<code>{result.source_world_id}</code>} />
      <DetailRow label="New world ID" value={<code>{result.new_world_id}</code>} />
      <DetailRow label="Dry run" value={String(result.dry_run)} />
      <p><strong>Created files:</strong></p>
      <ul>
        {result.created_files.map((file) => <li key={file}><code>{file}</code></li>)}
      </ul>
      {result.errors.length > 0 && (
        <>
          <p><strong>Clone errors:</strong></p>
          <ul>
            {result.errors.map((error, index) => <li key={`${error.field ?? 'root'}-${index}`}>{error.field ? `${error.field}: ` : ''}{error.message}</li>)}
          </ul>
        </>
      )}
      {result.package && (
        <div aria-label="Created package summary">
          <h4>Created package</h4>
          <DetailRow label="World ID" value={<code>{result.package.world_id}</code>} />
          <DetailRow label="Type" value={result.package.type} />
          <DetailRow label="Source" value={result.package.source} />
          <DetailRow label="Counts" value={`${result.package.country_count} countries, ${result.package.continent_count} continents, ${result.package.region_count} regions, ${result.package.travel_region_count} travel regions`} />
          <DetailRow label="Fingerprint" value={<code title={result.package.fingerprint}>{shortFingerprint(result.package.fingerprint)}</code>} />
        </div>
      )}
      {result.validation && (
        <div aria-label="Clone validation summary">
          <h4>Validation</h4>
          <DetailRow label="Status" value={result.validation.status} />
          <DetailRow label="Errors" value={result.validation.error_count} />
          <DetailRow label="Warnings" value={result.validation.warning_count} />
          <DetailRow label="Info" value={result.validation.info_count} />
        </div>
      )}
      {result.ok && !result.dry_run && <p><Link to={`/admin/world/library/${encodeURIComponent(result.new_world_id)}`}>Open new Custom World detail</Link></p>}
    </div>
  )
}

function CloneBuiltInWorldSection({ source }: { source: WorldPackage }): JSX.Element {
  const queryClient = useQueryClient()
  const [newWorldId, setNewWorldId] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState(`Custom world cloned from ${source.name}.`)
  const [result, setResult] = useState<WorldPackageCloneResponse | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: (payload: WorldPackageClonePayload) => cloneWorldPackage(source.world_id, payload),
    onSuccess: (response) => {
      setResult(response)
      setApiError(null)
      if (response.ok && !response.dry_run) {
        void queryClient.invalidateQueries({ queryKey: ['world-packages'] })
        void queryClient.invalidateQueries({ queryKey: ['world-package', response.new_world_id] })
        void queryClient.invalidateQueries({ queryKey: ['world-package-validation', response.new_world_id] })
      }
    },
    onError: (error) => {
      setResult(null)
      setApiError(formatApiError(error))
    }
  })

  function submitClone(dryRun: boolean): void {
    setApiError(null)
    mutation.mutate({
      new_world_id: newWorldId,
      name,
      description: description.trim() === '' ? null : description,
      dry_run: dryRun
    })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
  }

  return (
    <SectionCard title="Clone Built-in World">
      <p>Create an independent repository-stored Custom World from <strong>{source.name}</strong>. The built-in source and existing Runs are never changed.</p>
      <p className="status">The clone copies the complete package tree, including historical rating evidence and package-owned generation inputs when present.</p>
      <form onSubmit={handleSubmit}>
        <label>
          New World ID
          <input value={newWorldId} onChange={(event) => setNewWorldId(event.target.value)} placeholder="my_custom_world" />
        </label>
        <p className="status">lowercase letters, numbers, underscores only; 3–64 chars; no spaces</p>
        <label>
          Name
          <input value={name} onChange={(event) => setName(event.target.value)} placeholder="My Custom World" />
        </label>
        <label>
          Description
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder={`Custom world cloned from ${source.name}.`} />
        </label>
        <div className="actions">
          <button type="button" disabled={mutation.isPending} onClick={() => submitClone(true)}>Preview clone</button>
          <button type="button" disabled={mutation.isPending} onClick={() => submitClone(false)}>Create Custom World</button>
        </div>
      </form>
      {apiError && <p className="error">Clone request failed: {apiError}</p>}
      {result && !result.ok && <CloneResultCard result={result} />}
      {result && result.ok && <CloneResultCard result={result} />}
    </SectionCard>
  )
}

function ValidationSection({ validation }: { validation: WorldPackageValidation }): JSX.Element {
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState<'all' | 'error' | 'warning' | 'info'>('all')
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const visibleChecks = validation.checks.filter(check =>
    (severity === 'all' || check.severity === severity) &&
    (normalizedSearch === '' ||
      [check.code, check.message, check.path, check.field]
        .some(value => value?.toLocaleLowerCase().includes(normalizedSearch)))
  )
  return (
    <SectionCard title="World Package Validation">
      <DetailRow label="Overall status" value={validation.status} />
      <DetailRow label="Errors" value={validation.error_count} />
      <DetailRow label="Warnings" value={validation.warning_count} />
      <DetailRow label="Info" value={validation.info_count} />
      <div className="form-grid">
        <label>Search validation checks
          <input type="search" value={search} onChange={event => setSearch(event.target.value)}
            placeholder="Code, message, path or field" />
        </label>
        <label>Validation severity
          <select value={severity} onChange={event => setSeverity(event.target.value as typeof severity)}>
            <option value="all">All severities</option>
            <option value="error">Errors</option>
            <option value="warning">Warnings</option>
            <option value="info">Info</option>
          </select>
        </label>
      </div>
      <button type="button" disabled={!search && severity === 'all'}
        onClick={() => { setSearch(''); setSeverity('all') }}>
        Clear validation filters
      </button>
      <p role="status">Showing {visibleChecks.length} of {validation.checks.length} validation checks</p>
      {validation.checks.length === 0
        ? <p className="status">No validation checks were returned for this World Package.</p>
        : visibleChecks.length === 0
          ? <p className="status">No validation checks match your filters.</p>
          : <div className="table-responsive"><table aria-label="World package validation checks">
            <thead>
              <tr>
                <th>Code</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Message</th>
                <th>Path</th>
                <th>Field</th>
              </tr>
            </thead>
            <tbody>
              {visibleChecks.map((check, index) => (
                <tr key={`${check.code}-${check.path ?? 'package'}-${check.field ?? 'root'}-${index}`}>
                  <td><code>{check.code}</code></td>
                  <td>{check.severity}</td>
                  <td>{check.status}</td>
                  <td>{check.message}</td>
                  <td>{check.path ? <code>{check.path}</code> : '—'}</td>
                  <td>{check.field ? <code>{check.field}</code> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table></div>}
    </SectionCard>
  )
}

function GeographySection({ geography, pkg }: { geography: WorldPackageGeography, pkg: WorldPackage }): JSX.Element {
  const queryClient = useQueryClient()
  const [areas, setAreas] = useState(geography.timezone_areas ?? [])
  const mutation = useMutation({ mutationFn: () => replaceWorldPackageTimezoneAreas(pkg.world_id, areas.map((area, position) => ({...area, position})), pkg.fingerprint), onSuccess: async () => { await Promise.all([queryClient.invalidateQueries({queryKey:['world-package-geography',pkg.world_id]}), queryClient.invalidateQueries({queryKey:['world-package',pkg.world_id]}), queryClient.invalidateQueries({queryKey:['world-packages']})]) } })
  const editable = pkg.type === 'custom' && pkg.editable
  return <SectionCard title="Geography">
    <h4>Continents</h4>
    <table><thead><tr><th>Code</th><th>Name</th></tr></thead><tbody>{geography.continents.map((item) => <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td></tr>)}</tbody></table>
    <h4>Regions</h4>
    <table><thead><tr><th>Code</th><th>Name</th><th>Continent</th></tr></thead><tbody>{geography.regions.map((item) => <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td><td>{geography.continents.find((continent) => continent.code === item.continent_code)?.name ?? '—'}</td></tr>)}</tbody></table>
    <h4>Travel Regions</h4>
    <table><thead><tr><th>Code</th><th>Name</th><th>Description</th></tr></thead><tbody>{geography.travel_regions.map((item) => <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td><td>{item.description ?? '—'}</td></tr>)}</tbody></table>
    <h4>Timezone Areas</h4>
    {!geography.timezone_areas_authored && !editable && <p className="status">Unavailable — this package has not yet authored the Timezone Area layer.</p>}
    {(geography.timezone_areas_authored || editable) && <><p>Ordered circular topology; the first and last rows are adjacent. This is independent from Travel Regions.</p><table><thead><tr><th>Position</th><th>Code</th><th>Name</th>{editable && <th>Action</th>}</tr></thead><tbody>{areas.map((area,index)=><tr key={`${area.code}-${index}`}><td>{index}</td><td>{editable?<input aria-label={`Timezone Area code ${index}`} value={area.code} onChange={e=>setAreas(current=>current.map((x,i)=>i===index?{...x,code:e.target.value}:x))}/>:<code>{area.code}</code>}</td><td>{editable?<input aria-label={`Timezone Area name ${index}`} value={area.name} onChange={e=>setAreas(current=>current.map((x,i)=>i===index?{...x,name:e.target.value}:x))}/>:area.name}</td>{editable&&<td><button type="button" disabled={index===0} onClick={()=>setAreas(current=>current.map((item,i)=>i===index-1?current[index]:i===index?current[index-1]:item))}>Move Up</button> <button type="button" disabled={index===areas.length-1} onClick={()=>setAreas(current=>current.map((item,i)=>i===index+1?current[index]:i===index?current[index+1]:item))}>Move Down</button> <button type="button" onClick={()=>setAreas(current=>current.filter((_,i)=>i!==index))}>Remove</button></td>}</tr>)}</tbody></table>{editable&&<p><button type="button" onClick={()=>setAreas(current=>[...current,{code:'',name:'',position:current.length}])}>Add Timezone Area</button> <button type="button" disabled={mutation.isPending} onClick={()=>mutation.mutate()}>Save Timezone Areas</button></p>}{mutation.error&&<p className="error">{formatApiError(mutation.error)}</p>}</>}
  </SectionCard>
}

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function formatPopulationYears(populationByYear: CountryRecord['population_by_year'], cs: boolean): string {
  if (!populationByYear) return '—'
  const years = Object.entries(populationByYear)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([year]) => year)
    .sort((left, right) => Number(left) - Number(right))
  if (years.length === 0) return '—'
  return cs
    ? `${years.length} ${years.length === 1 ? 'rok' : years.length >= 2 && years.length <= 4 ? 'roky' : 'let'}: ${years.join(', ')}`
    : `${years.length} ${years.length === 1 ? 'year' : 'years'}: ${years.join(', ')}`
}

function CountryCell({ value }: { value: ReactNode }): JSX.Element {
  return <td>{value === null || value === undefined || value === '' ? '—' : value}</td>
}

function PackageCountriesTable({ countries, worldId, cs }: { countries: CountryRecord[], worldId: string, cs: boolean }): JSX.Element {
  return (
    <div className="table-responsive"><table aria-label={cs ? 'Země ve World Package' : 'World Package countries table'}>
      <thead>
        <tr>
          <th>{cs ? 'Kód' : 'Code'}</th>
          <th>{cs ? 'Název' : 'Name'}</th>
          <th>Region</th>
          <th>{cs ? 'Populace' : 'Population'}</th>
          <th>{cs ? 'Historie populace' : 'Population coverage'}</th>
          <th>{cs ? 'Rozloha km²' : 'Area km²'}</th>
          <th>{cs ? 'Cestovní region' : 'Travel Region'}</th>
          <th>{cs ? 'Časová oblast' : 'Timezone Area'}</th>
          <th>{cs ? 'Popularita squashe' : 'Squash Popularity'}</th>
          <th>{cs ? 'Dostupnost squashe' : 'Squash Access'}</th>
          <th>{cs ? 'Kvalita rozvoje' : 'Development Quality'}</th>
          <th>{cs ? 'Kvalita soutěží' : 'Competition Quality'}</th>
          <th>{cs ? 'Podpora elity' : 'Elite Support'}</th>
          <th>{cs ? 'Tradice squashe' : 'Squash Tradition'}</th>
          <th>{cs ? 'Akce' : 'Action'}</th>
        </tr>
      </thead>
      <tbody>
        {countries.map((country) => (
          <tr key={country.code}>
            <CountryCell value={<code>{country.code}</code>} />
            <CountryCell value={country.name} />
            <CountryCell value={country.region} />
            <CountryCell value={country.population.toLocaleString()} />
            <CountryCell value={formatPopulationYears(country.population_by_year, cs)} />
            <CountryCell value={formatNumber(country.area_km2)} />
            <CountryCell value={country.travel_region} />
            <CountryCell value={country.timezone_area} />
            <CountryCell value={country.squash_popularity} />
            <CountryCell value={country.squash_access} />
            <CountryCell value={country.development_quality} />
            <CountryCell value={country.competition_quality} />
            <CountryCell value={country.elite_support} />
            <CountryCell value={country.squash_tradition} />
            <td><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(country.code)}`}>{cs ? 'Otevřít' : 'Open'}</Link></td>
          </tr>
        ))}
      </tbody>
    </table></div>
  )
}

const COUNTRY_LIST_PAGE_SIZE = 50

export function WorldPackageCountriesPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const { language } = useLanguage()
  const cs = language === 'cs'
  const countriesQuery = useQuery({
    queryKey: ['world-package-countries', worldId],
    queryFn: () => getWorldPackageCountries(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const data = countriesQuery.data?.world_id === worldId ? countriesQuery.data : null
  const [search, setSearch] = useState('')
  const [region, setRegion] = useState('')
  const [missingTravelRegion, setMissingTravelRegion] = useState(false)
  const [missingTimezoneArea, setMissingTimezoneArea] = useState(false)
  const [sortBy, setSortBy] = useState<'name' | 'code' | 'population'>('name')
  const [page, setPage] = useState(0)
  useEffect(() => {
    setSearch('')
    setRegion('')
    setMissingTravelRegion(false)
    setMissingTimezoneArea(false)
    setSortBy('name')
    setPage(0)
  }, [worldId])
  const sourceCountries = data?.countries ?? []
  const missingTravelCount = sourceCountries.filter(country => !country.travel_region).length
  const missingTimezoneCount = sourceCountries.filter(country => !country.timezone_area).length
  const regions = Array.from(new Set(sourceCountries.map(country => country.region).filter(Boolean)))
    .sort((left, right) => left.localeCompare(right))
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const visibleCountries = sourceCountries
    .filter(country =>
      (region === '' || country.region === region) &&
      (!missingTravelRegion || !country.travel_region) &&
      (!missingTimezoneArea || !country.timezone_area) &&
      `${country.code} ${country.name}`.toLocaleLowerCase().includes(normalizedSearch)
    )
    .sort((left, right) => sortBy === 'code'
      ? left.code.localeCompare(right.code) || left.name.localeCompare(right.name)
      : sortBy === 'population'
        ? right.population - left.population || left.code.localeCompare(right.code)
        : left.name.localeCompare(right.name) || left.code.localeCompare(right.code))
  const pageCount = Math.max(1, Math.ceil(visibleCountries.length / COUNTRY_LIST_PAGE_SIZE))
  const currentPage = Math.min(page, pageCount - 1)
  const pageCountries = visibleCountries.slice(
    currentPage * COUNTRY_LIST_PAGE_SIZE, (currentPage + 1) * COUNTRY_LIST_PAGE_SIZE
  )
  const clearFilters = () => {
    setSearch('')
    setRegion('')
    setMissingTravelRegion(false)
    setMissingTimezoneArea(false)
    setSortBy('name')
    setPage(0)
  }

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>{cs ? 'Země ve World Package' : 'World Package Countries'}</h2>
        <p className="subtitle">{cs
          ? 'Přehled zemí z vybraného World Package.'
          : 'Assembled typed view of the countries in the selected World Package.'}</p>
      </div>
      <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>{cs
        ? 'Zpět na detail World Package' : 'Back to World Package detail'}</Link></p>
      {countriesQuery.isLoading && <p className="status">{cs ? 'Načítám země…' : 'Loading package countries...'}</p>}
      {countriesQuery.error && <p className="error">{cs ? 'Nepodařilo se načíst země: ' : 'Failed to load package countries: '}{formatApiError(countriesQuery.error)}</p>}
      {countriesQuery.isSuccess && !data && <p role="alert" className="error">{cs
        ? 'Odpověď nepatří vybranému World Package.' : 'Response does not belong to the selected World Package.'}</p>}
      {data && (
        <>
          <SectionCard title={cs ? 'Balíček' : 'Package'}>
            <DetailRow label={cs ? 'Název světa' : 'World name'} value={data.world_name} />
            <DetailRow label="World ID" value={<code>{data.world_id}</code>} />
            <DetailRow label={cs ? 'Typ' : 'Type'} value={data.type} />
            <DetailRow label={cs ? 'Zdroj' : 'Source'} value={data.source} />
            <DetailRow label={cs ? 'Počet zemí' : 'Country count'} value={data.country_count} />
            <DetailRow label={cs ? 'Režim balíčku' : 'Package mode'} value={`${data.type === 'custom' ? (cs ? 'Vlastní' : 'Custom') : (cs ? 'Vestavěný' : 'Built-in')} · ${data.read_only ? (cs ? 'Jen pro čtení' : 'Read-only') : (cs ? 'Upravitelný zdroj' : 'Editable source')}`} />
          </SectionCard>
          <SectionCard title={cs ? 'Země v balíčku' : 'Package countries'}>
            <p className="status">{cs
              ? 'Tato stránka zatím nepodporuje hromadné úpravy, import ani export.'
              : 'This inspection screen does not currently provide bulk edit, import, or export actions.'}</p>
            {data.type === 'custom' && data.source === 'custom_config' && !data.read_only && <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/new`}>{cs ? '+ Přidat zemi' : '+ Add country'}</Link></p>}
            <div className="form-grid">
              <label>{cs ? 'Hledat podle názvu nebo kódu země' : 'Search by country name or code'}
                <input type="search" aria-label={cs ? 'Hledat země' : 'Search countries'} value={search}
                  onChange={event => { setSearch(event.target.value); setPage(0) }} />
              </label>
              <label>{cs ? 'Region' : 'Region'}
                <select aria-label={cs ? 'Filtrovat podle regionu' : 'Filter by region'} value={region}
                  onChange={event => { setRegion(event.target.value); setPage(0) }}>
                  <option value="">{cs ? 'Všechny regiony' : 'All regions'}</option>
                  {regions.map(value => <option key={value} value={value}>{value}</option>)}
                </select>
              </label>
              <label>{cs ? 'Řazení zemí' : 'Sort countries'}
                <select value={sortBy} onChange={event => { setSortBy(event.target.value as typeof sortBy); setPage(0) }}>
                  <option value="name">{cs ? 'Název (A–Z)' : 'Name (A–Z)'}</option>
                  <option value="code">{cs ? 'Kód (A–Z)' : 'Code (A–Z)'}</option>
                  <option value="population">{cs ? 'Populace (sestupně)' : 'Population (descending)'}</option>
                </select>
              </label>
            </div>
            <div className="actions">
              <label><input type="checkbox" checked={missingTravelRegion}
                onChange={event => { setMissingTravelRegion(event.target.checked); setPage(0) }} />
                {' '}{cs ? 'Bez cestovního regionu' : 'Unassigned travel region'}
              </label>
              <label><input type="checkbox" checked={missingTimezoneArea}
                onChange={event => { setMissingTimezoneArea(event.target.checked); setPage(0) }} />
                {' '}{cs ? 'Bez časové oblasti' : 'Unassigned timezone area'}
              </label>
            </div>
            <p className="status">{cs
              ? `Nepřiřazený cestovní region: ${missingTravelCount} · Nepřiřazená časová oblast: ${missingTimezoneCount}`
              : `Unassigned travel region: ${missingTravelCount} · Unassigned timezone area: ${missingTimezoneCount}`}
              {' '}{cs ? 'Nepřiřazený údaj nemusí znamenat chybu.' : 'An unassigned value is not necessarily an error.'}</p>
            <button type="button" disabled={!search && !region && !missingTravelRegion && !missingTimezoneArea && sortBy === 'name'} onClick={clearFilters}>
              {cs ? 'Vymazat filtry a řazení' : 'Clear filters and sorting'}
            </button>
            <p role="status">{cs
              ? `Zobrazeno ${visibleCountries.length} z ${sourceCountries.length} zemí`
              : `Showing ${visibleCountries.length} of ${sourceCountries.length} countries`}</p>
            {visibleCountries.length === 0 ? <p className="status">{cs
              ? (sourceCountries.length === 0 ? 'Balíček neobsahuje žádné země.' : 'Žádná země neodpovídá filtrům.')
              : (sourceCountries.length === 0 ? 'This package has no countries.' : 'No countries match your filters.')}</p>
              : <>
                <PackageCountriesTable countries={pageCountries} worldId={worldId} cs={cs} />
                <div className="actions">
                  <button type="button" disabled={currentPage === 0} onClick={() => setPage(value => Math.max(0, value - 1))}>
                    {cs ? '← Předchozí' : '← Previous'}
                  </button>
                  <span>{cs ? 'Strana' : 'Page'} {currentPage + 1} / {pageCount}
                    {' · '}{currentPage * COUNTRY_LIST_PAGE_SIZE + 1}–{Math.min((currentPage + 1) * COUNTRY_LIST_PAGE_SIZE, visibleCountries.length)}
                    {' / '}{visibleCountries.length}</span>
                  <button type="button" disabled={currentPage >= pageCount - 1}
                    onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>
                    {cs ? 'Další →' : 'Next →'}
                  </button>
                </div>
              </>}
          </SectionCard>
        </>
      )}
    </section>
  )
}

export function WorldLibraryDetailPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const packageQuery = useQuery({
    queryKey: ['world-package', worldId],
    queryFn: () => getWorldPackage(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const validationQuery = useQuery({
    queryKey: ['world-package-validation', worldId],
    queryFn: () => getWorldPackageValidation(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId), retry: false })
  const pkg = packageQuery.data

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World Package Details</h2>
        <p className="subtitle">Read-only inspection of a registered World Package.</p>
      </div>
      <p><Link to="/admin/world/library">Back to World Library</Link></p>
      {packageQuery.isLoading && <p className="status">Loading World Package...</p>}
      {packageQuery.error && <p className="error">Failed to load World Package: {formatApiError(packageQuery.error)}</p>}
      {pkg && (
        <>
          <h2>{pkg.name}</h2><p><code>{pkg.world_id}</code></p><p><strong>{pkg.type === 'custom' ? 'Custom' : 'Built-in'} · {pkg.editable ? 'Editable source' : 'Read-only'}</strong></p>
          <nav aria-label="Package sections"><a href="#overview">Overview</a> · <Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}/countries`}>Countries</Link> · <a href="#geography">Geography</a> · <a href="#validation">Validation</a></nav>
          <div id="overview" />
          <SectionCard title="Metadata">
            <DetailRow label="Name" value={pkg.name} />
            <DetailRow label="World ID" value={<code>{pkg.world_id}</code>} />
            <DetailRow label="Description" value={pkg.description} />
            <DetailRow label="Type" value={pkg.type} />
            <DetailRow label="Status" value={pkg.status} />
            <DetailRow label="Source" value={pkg.source} />
            <DetailRow label="Version" value={pkg.version} />
            <DetailRow label="Fingerprint" value={<code>{pkg.fingerprint}</code>} />
          </SectionCard>
          <SectionCard title="Safety">
            <DetailRow label="Editable" value={yesNo(pkg.editable, 'Editable', 'Read-only')} />
            <DetailRow label="Deletable" value={yesNo(pkg.deletable, 'Deletable', 'Not deletable')} />
            <DetailRow label="Archivable" value={yesNo(pkg.archivable, 'Archivable', 'Not archivable')} />
            <p className="status">Built-in World Packages are protected repository inputs. Custom clones are independent editable sources; existing Runs keep their own saved snapshots.</p>
          </SectionCard>
          {pkg.type === 'official' && pkg.source === 'built_in' && <CloneBuiltInWorldSection source={pkg} />}
          <SectionCard title="Contents">
            <DetailRow label="Countries" value={<><span>{pkg.country_count}</span> · <Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}/countries`}>Open package countries</Link></>} />
            <DetailRow label="Continents" value={pkg.continent_count} />
            <DetailRow label="Regions" value={pkg.region_count} />
            <DetailRow label="Travel regions" value={pkg.travel_region_count} />
          </SectionCard>
          <SectionCard title="Usage">
            <DetailRow label="Used by runs" value={usageLabel(pkg.used_by_run_count)} />
            {pkg.used_by_run_count === null && <p className="status">Usage aggregation is not implemented yet.</p>}
          </SectionCard>
          <div id="geography" />
          {geographyQuery.isLoading && <p className="status">Loading geography...</p>}
          {geographyQuery.error && <p className="error">Failed to load geography: {formatApiError(geographyQuery.error)}</p>}
          {geographyQuery.data && <GeographySection geography={geographyQuery.data} pkg={pkg} />}
          <div id="validation" />
          {validationQuery.isLoading && (
            <SectionCard title="World Package Validation">
              <p className="status">Loading World Package validation...</p>
            </SectionCard>
          )}
          {validationQuery.error && (
            <SectionCard title="World Package Validation">
              <p className="error">Failed to load World Package validation: {formatApiError(validationQuery.error)}</p>
            </SectionCard>
          )}
          {validationQuery.data && <ValidationSection validation={validationQuery.data} />}
        </>
      )}
    </section>
  )
}

export function WorldPackageCountryCreatePage(): JSX.Element {
  const { worldId = '' } = useParams(); const navigate = useNavigate(); const queryClient = useQueryClient()
  const packageQuery = useQuery({ queryKey: ['world-package', worldId], queryFn: () => getWorldPackage(worldId), retry: false })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), retry: false })
  const [identity, setIdentity] = useState({ code: '', name: '', notes: '', area: '' })
  const [region, setRegion] = useState(''); const [travelRegion, setTravelRegion] = useState(''); const [timezoneArea, setTimezoneArea] = useState('')
  const [values, setValues] = useState({ squash_popularity: '5.5', squash_access: '5.5', development_quality: '5.5', competition_quality: '5.5', elite_support: '5.5', squash_tradition: '5.5', court_count: '' })
  const [populations, setPopulations] = useState<Array<PopulationRow & { id: number }>>([{ id: 0, year: '2020', population: '' }])
  const [validationError, setValidationError] = useState('')
  const mutation = useMutation({ mutationFn: (payload: WorldPackageCountryCreatePayload) => createWorldPackageCountry(worldId, payload), onSuccess: async response => {
    await Promise.all([queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-packages'] })])
    navigate(`/admin/world/library/${encodeURIComponent(worldId)}/countries/${response.country_detail.country.code}`)
  } })
  const pkg = packageQuery.data; const allowed = pkg?.type === 'custom' && pkg.source === 'custom_config' && pkg.editable
  const setNumber = (key: keyof typeof values, value: string) => setValues(current => ({...current, [key]: value}))
  const sortedPopulations = [...populations].sort((a,b) => Number(a.year) - Number(b.year))
  const submit = (event: FormEvent) => { event.preventDefault(); if (!pkg || !allowed) return
    const years = populations.map(row => row.year); const duplicate = years.find((year, index) => year !== '' && years.indexOf(year) !== index)
    if (duplicate) { setValidationError(`Year ${duplicate} is already authored.`); return }
    if (!years.includes('2020')) { setValidationError('Population year 2020 is required.'); return }
    setValidationError('')
    mutation.mutate({ code: identity.code, name: identity.name, notes: identity.notes || null, area_km2: identity.area ? Number(identity.area) : null, region, travel_region: travelRegion || null, timezone_area: timezoneArea || null,
      rating_scale: 'country_ratings_1_10.v2', squash_popularity: Number(values.squash_popularity), squash_access: Number(values.squash_access), development_quality: Number(values.development_quality), competition_quality: Number(values.competition_quality), elite_support: Number(values.elite_support), squash_tradition: Number(values.squash_tradition), court_count: values.court_count === '' ? null : Number(values.court_count),
      population_by_year: Object.fromEntries(sortedPopulations.map(row => [row.year, Number(row.population)])), expected_package_fingerprint: pkg.fingerprint }) }
  if (packageQuery.isLoading || geographyQuery.isLoading) return <p className="status">Loading country form...</p>
  if (!allowed) return <section className="panel"><p className="error">Countries can only be created in an editable Custom World source.</p></section>
  return <section className="panel"><p><Link to={`/admin/world/library/${worldId}/countries`}>Back to countries</Link></p><h2>Add country</h2><form onSubmit={submit}>
    {(validationError || mutation.error) && <p className="error" role="alert">{validationError || formatApiError(mutation.error)}</p>}
    <fieldset><legend>Identity</legend><label>Code<input required pattern="[A-Z]{3}" maxLength={3} value={identity.code} onChange={e => setIdentity({...identity,code:e.target.value})} /></label><label>Name<input required value={identity.name} onChange={e => setIdentity({...identity,name:e.target.value})} /></label><label>Notes<textarea value={identity.notes} onChange={e => setIdentity({...identity,notes:e.target.value})} /></label><label>Area km²<input type="number" min="1" value={identity.area} onChange={e => setIdentity({...identity,area:e.target.value})} /></label></fieldset>
    <fieldset><legend>Geography</legend><label>Region<select required value={region} onChange={e => setRegion(e.target.value)}><option value="">Select region</option>{geographyQuery.data?.regions.map(item=><option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label><label>Travel Region<select value={travelRegion} onChange={e=>setTravelRegion(e.target.value)}><option value="">None</option>{geographyQuery.data?.travel_regions.map(item=><option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label><label>Timezone Area<select value={timezoneArea} onChange={e=>setTimezoneArea(e.target.value)}><option value="">Not assigned</option>{(geographyQuery.data?.timezone_areas ?? []).map(item=><option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label></fieldset>
    <fieldset><legend>Population</legend>{sortedPopulations.map(row=><div key={row.id}><input aria-label={`Population year ${row.id === 0 ? '2020' : row.id}`} type="number" min="1955" max="2050" required readOnly={row.year==='2020'} value={row.year} onChange={e=>setPopulations(rows=>rows.map(item=>item.id===row.id?{...item,year:e.target.value}:item))}/><input aria-label={`Population value ${row.year || row.id}`} type="number" min="1" required value={row.population} onChange={e=>setPopulations(rows=>rows.map(item=>item.id===row.id?{...item,population:e.target.value}:item))}/>{row.year!=='2020'&&<button type="button" onClick={()=>setPopulations(rows=>rows.filter(item=>item.id!==row.id))}>Remove</button>}</div>)}<button type="button" onClick={()=>setPopulations(rows=>[...rows,{id:Math.max(...rows.map(row=>row.id))+1,year:'',population:''}])}>+ Add authored year</button></fieldset>
    <fieldset><legend>Squash / Country strength</legend>{Object.entries(values).filter(([key]) => key !== 'court_count').map(([key,value])=><label key={key}>{key.split('_').join(' ')}<input type="number" required min={key==='court_count'?0:1} max={10} step={0.1} value={value} onChange={e=>setNumber(key as keyof typeof values,e.target.value)}/></label>)}</fieldset>
    <button type="submit" disabled={mutation.isPending}>{mutation.isPending?'Saving…':'Save country'}</button>
  </form></section>
}

export function WorldPackageCountryDetailPage(): JSX.Element {
  const { worldId = '', countryCode = '' } = useParams()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [editing, setEditing] = useState(false)
  const [populationEditing, setPopulationEditing] = useState(false)
  const [success, setSuccess] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const query = useQuery({ queryKey: ['world-package-country', worldId, countryCode], queryFn: () => getWorldPackageCountry(worldId, countryCode), enabled: Boolean(worldId && countryCode), retry: false })
  const geographyQuery = useQuery({ queryKey: ['world-package-geography', worldId], queryFn: () => getWorldPackageGeography(worldId), enabled: Boolean(worldId), retry: false })
  const mutation = useMutation({
    mutationFn: (payload: WorldPackageCountryUpdatePayload) => updateWorldPackageCountry(worldId, countryCode, payload),
    onSuccess: async (response) => {
      queryClient.setQueryData(['world-package-country', worldId, countryCode], response.country_detail)
      setEditing(false); setSuccess(`Country changes saved. Validation status: ${response.validation.status}.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-packages'] })
      ])
    }
  })
  const populationMutation = useMutation({
    mutationFn: (payload: WorldPackageCountryPopulationUpdatePayload) => updateWorldPackageCountryPopulation(worldId, countryCode, payload),
    onSuccess: async (response) => {
      queryClient.setQueryData(['world-package-country', worldId, countryCode], response.country_detail)
      setPopulationEditing(false); setSuccess(`Population saved. Validation status: ${response.validation.status}.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-country', worldId, countryCode] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-packages'] })
      ])
    }
  })
  const deleteMutation = useMutation({
    mutationFn: () => deleteWorldPackageCountry(worldId, countryCode, data!.package.fingerprint),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-country', worldId, countryCode] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }), queryClient.invalidateQueries({ queryKey: ['world-packages'] })
      ])
      navigate(`/admin/world/library/${encodeURIComponent(worldId)}/countries`)
    }
  })
  const data = query.data
  const canEdit = data?.package.type === 'custom' && data.package.source === 'custom_config' && data.package.editable
  const timeline = Object.entries(data?.country.population_by_year ?? {}).filter(([, value]) => value != null).sort(([a], [b]) => Number(a) - Number(b))
  return <section className="panel">
    <p><Link to="/admin/world/library">World Packages</Link> → <Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>{data?.package.name ?? worldId}</Link> → <Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries`}>Countries</Link>{data ? ` → ${data.country.name}` : ''}</p>
    {query.isLoading && <p className="status">Loading country...</p>}
    {query.error && <p className="error">Failed to load country: {formatApiError(query.error)}</p>}
    {data && <>
      <div className="page-intro"><h2>{data.country.name}</h2><p className="subtitle"><code>{data.country.code}</code></p></div>
      <p><strong>{data.package.name} · {data.package.type === 'custom' ? 'Custom' : 'Built-in'} · {canEdit ? 'Editable source' : 'Read-only'}</strong></p>
      {canEdit && !editing && !populationEditing && <button type="button" onClick={() => { setEditing(true); setSuccess(''); mutation.reset() }}>Edit country</button>}
      {canEdit && !editing && !populationEditing && <button type="button" onClick={() => { setConfirmDelete(true); deleteMutation.reset() }}>Delete country</button>}
      {confirmDelete && <SectionCard title={`Delete ${data.country.code} — ${data.country.name}?`}><p>This removes the Country from this Custom World source.<br />Existing Runs are not changed.</p>{deleteMutation.error && <p className="error" role="alert">{formatApiError(deleteMutation.error)}</p>}<button type="button" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate()}>Delete country</button> <button type="button" disabled={deleteMutation.isPending} onClick={() => setConfirmDelete(false)}>Cancel</button></SectionCard>}
      {success && <p className="status" role="status">{success}</p>}
      {editing && <CountryEditForm detail={data} geography={geographyQuery.data} saving={mutation.isPending} error={mutation.error} onCancel={() => { setEditing(false); mutation.reset() }} onSave={(payload) => mutation.mutate(payload)} />}
      {!editing && <SectionCard title="Overview">
        <DetailRow label="Package" value={data.package.name} /><DetailRow label="Region" value={data.region?.name ?? data.country.region} /><DetailRow label="Travel Region" value={data.travel_region?.name ?? data.country.travel_region ?? '—'} /><DetailRow label="Timezone Area" value={data.timezone_area?.name ?? data.country.timezone_area ?? 'Not assigned'} /><DetailRow label="Area" value={`${formatNumber(data.country.area_km2)} km²`} /><DetailRow label="Current/default population" value={formatNumber(data.country.default_population ?? data.country.population)} />
        {data.country.notes && <DetailRow label="Notes" value={data.country.notes} />}
      </SectionCard>}
      {!populationEditing && <SectionCard title="Population">
        {canEdit && !editing && <button type="button" onClick={() => { setPopulationEditing(true); setSuccess(''); populationMutation.reset() }}>Edit population</button>}
        <DetailRow label="Effective/default population" value={formatNumber(data.country.default_population ?? data.country.population)} /><DetailRow label="Default authored year" value={data.country.default_population_year ?? '—'} /><DetailRow label="Authored population years" value={timeline.length} /><DetailRow label="Earliest authored year" value={timeline[0]?.[0] ?? '—'} /><DetailRow label="Latest authored year" value={timeline[timeline.length - 1]?.[0] ?? '—'} />
        <div style={{maxHeight: '28rem', overflowY: 'auto'}}><table aria-label="Authored population timeline"><thead><tr><th>Year</th><th>Population</th></tr></thead><tbody>{timeline.map(([year, value]) => <tr key={year}><td>{year}{year === '2020' ? ' · Default year' : ''}</td><td>{formatNumber(value)}</td></tr>)}</tbody></table></div>
      </SectionCard>}
      {populationEditing && <PopulationEditForm detail={data} saving={populationMutation.isPending} error={populationMutation.error} onCancel={() => { setPopulationEditing(false); populationMutation.reset() }} onSave={payload => populationMutation.mutate(payload)} />}
      <SectionCard title="Geography"><DetailRow label="Area km²" value={formatNumber(data.country.area_km2)} /><DetailRow label="Region" value={data.region ? `${data.region.name} (${data.region.code})` : data.country.region} /><DetailRow label="Continent" value={data.continent?.name ?? '—'} /><DetailRow label="Travel Region" value={data.travel_region ? `${data.travel_region.name} (${data.travel_region.code})` : data.country.travel_region ?? '—'} /></SectionCard>
      <SectionCard title="Squash / Country strength">
        <DetailRow label="Squash Popularity" value={data.country.squash_popularity} /><DetailRow label="Squash Access" value={data.country.squash_access} /><DetailRow label="Development Quality" value={data.country.development_quality} /><DetailRow label="Competition Quality" value={data.country.competition_quality} /><DetailRow label="Elite Support" value={data.country.elite_support} /><DetailRow label="Squash Tradition" value={data.country.squash_tradition} />
      </SectionCard>
      <details><summary>Technical source</summary><code>{data.source_path}</code></details>
    </>}
  </section>
}

type PopulationRow = { year: string, population: string }
function PopulationEditForm({ detail, saving, error, onCancel, onSave }: { detail: WorldPackageCountryDetail, saving: boolean, error: unknown, onCancel: () => void, onSave: (payload: WorldPackageCountryPopulationUpdatePayload) => void }): JSX.Element {
  const initial = Object.entries(detail.country.population_by_year ?? {}).filter((entry): entry is [string, number] => entry[1] != null).map(([year, population]) => ({ year, population: String(population) }))
  const [rows, setRows] = useState<PopulationRow[]>(initial)
  const [newYear, setNewYear] = useState('')
  const [newPopulation, setNewPopulation] = useState('')
  const [validationError, setValidationError] = useState('')
  const sorted = [...rows].sort((a, b) => Number(a.year) - Number(b.year))
  const add = () => {
    const year = Number(newYear), population = Number(newPopulation)
    if (!Number.isInteger(year) || year < 1955 || year > 2050) return setValidationError('Year must be an integer from 1955 to 2050.')
    if (!Number.isInteger(population) || population <= 0) return setValidationError('Population must be a positive integer.')
    if (rows.some(row => row.year === String(year))) return setValidationError(`Year ${year} is already authored.`)
    setRows(current => [...current, { year: String(year), population: String(population) }]); setNewYear(''); setNewPopulation(''); setValidationError('')
  }
  const submit = (event: FormEvent) => {
    event.preventDefault()
    const invalid = rows.find(row => !Number.isInteger(Number(row.population)) || Number(row.population) <= 0)
    if (invalid) return setValidationError(`Population for ${invalid.year} must be a positive integer.`)
    onSave({ values_by_year: Object.fromEntries(sorted.map(row => [row.year, Number(row.population)])), expected_package_fingerprint: detail.package.fingerprint })
  }
  return <SectionCard title="Population"><form onSubmit={submit}>
    <p><strong>Default year: 2020</strong></p>{(validationError || error != null) && <p className="error" role="alert">{validationError || formatApiError(error)}</p>}
    <table aria-label="Edit authored population timeline"><thead><tr><th>Year</th><th>Population</th><th /></tr></thead><tbody>{sorted.map(row => <tr key={row.year}><td>{row.year}{row.year === '2020' ? ' · Default year' : ''}</td><td><input aria-label={`Population ${row.year}`} type="number" min="1" step="1" required value={row.population} onChange={event => setRows(current => current.map(item => item.year === row.year ? {...item, population: event.target.value} : item))} /></td><td>{row.year !== '2020' && <button type="button" onClick={() => setRows(current => current.filter(item => item.year !== row.year))}>Remove {row.year}</button>}</td></tr>)}</tbody></table>
    <fieldset><legend>Add authored year</legend><label>Year<input aria-label="New population year" type="number" min="1955" max="2050" step="1" value={newYear} onChange={event => setNewYear(event.target.value)} /></label><label>Population<input aria-label="New population value" type="number" min="1" step="1" value={newPopulation} onChange={event => setNewPopulation(event.target.value)} /></label><button type="button" onClick={add}>+ Add authored year</button></fieldset>
    <p><button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save population'}</button> <button type="button" disabled={saving} onClick={onCancel}>Cancel</button></p>
  </form></SectionCard>
}

function CountryEditForm({ detail, geography, saving, error, onCancel, onSave }: { detail: WorldPackageCountryDetail, geography?: WorldPackageGeography, saving: boolean, error: unknown, onCancel: () => void, onSave: (payload: WorldPackageCountryUpdatePayload) => void }): JSX.Element {
  const country = detail.country
  const ratingMaximum = country.rating_scale === "country_ratings_1_10.v2" ? 10 : 5
  const ratingStep = ratingMaximum === 10 ? 0.1 : "any"
  const [name, setName] = useState(country.name)
  const [notes, setNotes] = useState(country.notes ?? '')
  const [area, setArea] = useState(country.area_km2 == null ? '' : String(country.area_km2))
  const [region, setRegion] = useState(country.region)
  const [travelRegion, setTravelRegion] = useState(country.travel_region ?? '')
  const [timezoneArea, setTimezoneArea] = useState(country.timezone_area ?? '')
  const [values, setValues] = useState({ squash_popularity: String(country.squash_popularity), squash_access: String(country.squash_access), development_quality: String(country.development_quality), competition_quality: String(country.competition_quality), elite_support: String(country.elite_support), squash_tradition: String(country.squash_tradition), court_count: country.court_count == null ? '' : String(country.court_count) })
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSave({ rating_scale: country.rating_scale, name, notes: notes || null, area_km2: area ? Number(area) : null, region, travel_region: travelRegion || null, timezone_area: timezoneArea || null,
      squash_popularity: Number(values.squash_popularity), squash_access: Number(values.squash_access), development_quality: Number(values.development_quality), competition_quality: Number(values.competition_quality), elite_support: Number(values.elite_support), squash_tradition: Number(values.squash_tradition), court_count: values.court_count === '' ? null : Number(values.court_count), expected_package_fingerprint: detail.package.fingerprint })
  }
  const numeric = (key: keyof typeof values, label: string, min: number, max?: number, step: number | 'any' = 'any') => <label>{label}<input type="number" required min={min} max={max} step={step} value={values[key]} onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))} /></label>
  return <SectionCard title="Edit country"><form onSubmit={submit}>
    {error != null && <p className="error" role="alert">{formatApiError(error)}</p>}
    <label>Name<input required value={name} onChange={event => setName(event.target.value)} /></label>
    <label>Notes<textarea value={notes} onChange={event => setNotes(event.target.value)} /></label>
    <label>Area km²<input type="number" min="1" value={area} onChange={event => setArea(event.target.value)} /></label>
    <label>Region<select value={region} onChange={event => setRegion(event.target.value)}>{geography?.regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
    <label>Travel Region<select value={travelRegion} onChange={event => setTravelRegion(event.target.value)}><option value="">None</option>{geography?.travel_regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
    <label>Timezone Area<select value={timezoneArea} onChange={event => setTimezoneArea(event.target.value)}><option value="">Not assigned</option>{(geography?.timezone_areas ?? []).map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
    {numeric('squash_popularity', 'Squash Popularity', 1, ratingMaximum, ratingStep)}{numeric('squash_access', 'Squash Access', 1, ratingMaximum, ratingStep)}{numeric('development_quality', 'Development Quality', 1, ratingMaximum, ratingStep)}{numeric('competition_quality', 'Competition Quality', 1, ratingMaximum, ratingStep)}{numeric('elite_support', 'Elite Support', 1, ratingMaximum, ratingStep)}{numeric('squash_tradition', 'Squash Tradition', 1, ratingMaximum, ratingStep)}
    <p>{country.rating_history && <span>Historical ratings require an explicit year and evidence; edit the versioned history through import/API. </span>}<button type="submit" disabled={saving || Boolean(country.rating_history)}>{saving ? 'Saving…' : 'Save changes'}</button> <button type="button" disabled={saving} onClick={onCancel}>Cancel</button></p>
  </form></SectionCard>
}
