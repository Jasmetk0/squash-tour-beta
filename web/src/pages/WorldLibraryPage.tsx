import type { FormEvent, ReactNode } from 'react'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { cloneOfficialWorldPackage, getWorldPackage, getWorldPackageCountries, getWorldPackageCountry, getWorldPackageGeography, getWorldPackageValidation, listWorldPackages, updateWorldPackageCountry, updateWorldPackageCountryPopulation } from '../api/client'
import type { CountryRecord, WorldPackage, WorldPackageCloneResponse, WorldPackageCountryDetail, WorldPackageCountryPopulationUpdatePayload, WorldPackageCountryUpdatePayload, WorldPackageGeography, WorldPackageValidation } from '../api/types'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function yesNo(value: boolean, yes: string, no: string): string {
  return value ? yes : no
}

function usageLabel(value: number | null): string {
  return value === null ? 'Usage not tracked yet' : String(value)
}

function shortFingerprint(fingerprint: string): string {
  if (fingerprint.length <= 16) return fingerprint
  return `${fingerprint.slice(0, 8)}…${fingerprint.slice(-8)}`
}

function PackageTable({ packages }: { packages: WorldPackage[] }): JSX.Element {
  if (packages.length === 0) {
    return <p className="status">No World Packages were returned by the registry. This read-only library has nothing to display yet.</p>
  }

  return (
    <table aria-label="World packages table">
      <thead>
        <tr>
          <th>Name</th>
          <th>World ID</th>
          <th>Type</th>
          <th>Status</th>
          <th>Package mode</th>
          <th>Countries</th>
          <th>Continents</th>
          <th>Regions</th>
          <th>Travel Regions</th>
          <th>Used by Runs</th>
          <th>Version</th>
          <th>Fingerprint</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {packages.map((pkg) => (
          <tr key={pkg.world_id}>
            <td>{pkg.name}</td>
            <td><code>{pkg.world_id}</code></td>
            <td>{pkg.type === 'custom' ? 'Custom' : 'Built-in'}</td>
            <td>{pkg.status}</td>
            <td>{yesNo(pkg.editable, 'Editable source', 'Read-only')}</td>
            <td>{pkg.country_count}</td>
            <td>{pkg.continent_count}</td>
            <td>{pkg.region_count}</td>
            <td>{pkg.travel_region_count}</td>
            <td>{usageLabel(pkg.used_by_run_count)}</td>
            <td>{pkg.version}</td>
            <td><code title={pkg.fingerprint}>{shortFingerprint(pkg.fingerprint)}</code></td>
            <td><Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}`}>Open World Package</Link></td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function WorldLibraryPage(): JSX.Element {
  const packagesQuery = useQuery({ queryKey: ['world-packages'], queryFn: listWorldPackages, retry: false })

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World Packages</h2>
        <p className="subtitle">Registry of foundational World Packages available to the engine.</p>
      </div>
      <p>
        World Packages are foundational world input bundles. A run will eventually be created from one selected World Package.
        Official FAX World is built in and read-only. Custom World Packages live under <code>config/world_packages/custom/</code> and use the same canonical package-scoped storage contract.
      </p>
      <p><Link to="/admin/world">Back to World hub</Link></p>

      <SectionCard title="Available World Packages">
        {packagesQuery.isLoading && <p className="status">Loading World Packages...</p>}
        {packagesQuery.error && <p className="error">Failed to load World Packages: {formatApiError(packagesQuery.error)}</p>}
        {packagesQuery.data && <PackageTable packages={packagesQuery.data.packages} />}
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

function CloneOfficialWorldSection(): JSX.Element {
  const queryClient = useQueryClient()
  const [newWorldId, setNewWorldId] = useState('')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('Custom world cloned from Official FAX World.')
  const [result, setResult] = useState<WorldPackageCloneResponse | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)
  const mutation = useMutation({
    mutationFn: cloneOfficialWorldPackage,
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
    <SectionCard title="Clone Official World">
      <p>Create a repository-stored Custom World by cloning the current built-in Official FAX World package. This does not edit Official FAX World and does not affect existing runs.</p>
      <p className="status">Clone creates a new Custom World Package only. Editing, deleting, and archiving Custom World Packages are not implemented yet.</p>
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
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Custom world cloned from Official FAX World." />
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
  return (
    <SectionCard title="World Package Validation">
      <DetailRow label="Overall status" value={validation.status} />
      <DetailRow label="Errors" value={validation.error_count} />
      <DetailRow label="Warnings" value={validation.warning_count} />
      <DetailRow label="Info" value={validation.info_count} />
      <table aria-label="World package validation checks">
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
          {validation.checks.map((check) => (
            <tr key={`${check.code}-${check.path ?? 'package'}-${check.field ?? 'root'}`}>
              <td><code>{check.code}</code></td>
              <td>{check.severity}</td>
              <td>{check.status}</td>
              <td>{check.message}</td>
              <td>{check.path ? <code>{check.path}</code> : '—'}</td>
              <td>{check.field ? <code>{check.field}</code> : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </SectionCard>
  )
}

function GeographySection({ geography }: { geography: WorldPackageGeography }): JSX.Element {
  return <SectionCard title="Geography">
    <h4>Continents</h4>
    <table><thead><tr><th>Code</th><th>Name</th></tr></thead><tbody>{geography.continents.map((item) => <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td></tr>)}</tbody></table>
    <h4>Regions</h4>
    <table><thead><tr><th>Code</th><th>Name</th><th>Continent</th></tr></thead><tbody>{geography.regions.map((item) => <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td><td>{geography.continents.find((continent) => continent.code === item.continent_code)?.name ?? '—'}</td></tr>)}</tbody></table>
    <h4>Travel Regions</h4>
    <table><thead><tr><th>Code</th><th>Name</th><th>Description</th></tr></thead><tbody>{geography.travel_regions.map((item) => <tr key={item.code}><td><code>{item.code}</code></td><td>{item.name}</td><td>{item.description ?? '—'}</td></tr>)}</tbody></table>
  </SectionCard>
}


function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function formatPopulationYears(populationByYear: CountryRecord['population_by_year']): string {
  if (!populationByYear) return '—'
  const years = Object.entries(populationByYear)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([year]) => year)
    .sort((left, right) => Number(left) - Number(right))
  if (years.length === 0) return '—'
  return `${years.length} ${years.length === 1 ? 'year' : 'years'}: ${years.join(', ')}`
}

function CountryCell({ value }: { value: ReactNode }): JSX.Element {
  return <td>{value === null || value === undefined || value === '' ? '—' : value}</td>
}

function PackageCountriesTable({ countries, worldId }: { countries: CountryRecord[], worldId: string }): JSX.Element {
  return (
    <table>
      <thead>
        <tr>
          <th>Code</th><th>Name</th><th>Region</th><th>Population</th><th>Population coverage</th><th>Area km²</th><th>Travel Region</th><th>Squash Popularity</th><th>System Quality</th><th>Federation Quality</th><th>Courts</th><th>Action</th>
        </tr>
      </thead>
      <tbody>
        {countries.map((country) => (
          <tr key={country.code}>
            <CountryCell value={<code>{country.code}</code>} />
            <CountryCell value={country.name} />
            <CountryCell value={country.region} />
            <CountryCell value={country.population.toLocaleString()} />
            <CountryCell value={formatPopulationYears(country.population_by_year)} />
            <CountryCell value={formatNumber(country.area_km2)} />
            <CountryCell value={country.travel_region} />
            <CountryCell value={country.squash_popularity} />
            <CountryCell value={country.system_quality} />
            <CountryCell value={country.federation_quality} />
            <CountryCell value={country.court_count} />
            <td><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(country.code)}`}>Open</Link></td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function WorldPackageCountriesPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const countriesQuery = useQuery({
    queryKey: ['world-package-countries', worldId],
    queryFn: () => getWorldPackageCountries(worldId),
    enabled: Boolean(worldId),
    retry: false
  })
  const data = countriesQuery.data
  const [search, setSearch] = useState('')
  const visibleCountries = (data?.countries ?? [])
    .filter((country) => `${country.code} ${country.name}`.toLowerCase().includes(search.trim().toLowerCase()))
    .sort((left, right) => left.name.localeCompare(right.name) || left.code.localeCompare(right.code))

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>World Package Countries</h2>
        <p className="subtitle">Assembled typed view of the countries in the selected World Package.</p>
      </div>
      <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>Back to World Package detail</Link></p>
      {countriesQuery.isLoading && <p className="status">Loading package countries...</p>}
      {countriesQuery.error && <p className="error">Failed to load package countries: {formatApiError(countriesQuery.error)}</p>}
      {data && (
        <>
          <SectionCard title="Package">
            <DetailRow label="World name" value={data.world_name} />
            <DetailRow label="World ID" value={<code>{data.world_id}</code>} />
            <DetailRow label="Type" value={data.type} />
            <DetailRow label="Source" value={data.source} />
            <DetailRow label="Country count" value={data.country_count} />
            <DetailRow label="Package mode" value={`${data.type === 'custom' ? 'Custom' : 'Built-in'} · ${data.read_only ? 'Read-only' : 'Editable source'}`} />
          </SectionCard>
          <SectionCard title="Package countries">
            <p className="status">This inspection screen does not currently provide create, edit, delete, import, or export actions, regardless of source package editability.</p>
            <label>Search by country name or code<input aria-label="Search countries" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
            <p>{visibleCountries.length} {visibleCountries.length === 1 ? 'country' : 'countries'}</p>
            <PackageCountriesTable countries={visibleCountries} worldId={worldId} />
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
            <p className="status">Official FAX World is built into repository config and is read-only. Custom World mutation actions are not implemented yet; safety fields are metadata only.</p>
          </SectionCard>
          {pkg.world_id === 'official_fax_world' && pkg.type === 'official' && <CloneOfficialWorldSection />}
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
          {geographyQuery.data && <GeographySection geography={geographyQuery.data} />}
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

export function WorldPackageCountryDetailPage(): JSX.Element {
  const { worldId = '', countryCode = '' } = useParams()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [populationEditing, setPopulationEditing] = useState(false)
  const [success, setSuccess] = useState('')
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
  const data = query.data
  const canEdit = data?.package.type === 'custom' && data.package.source === 'custom_config' && data.package.editable
  const timeline = Object.entries(data?.country.population_by_year ?? {}).filter(([, value]) => value != null).sort(([a], [b]) => Number(a) - Number(b))
  const style = Object.entries(data?.country.style_dna ?? {})
  return <section className="panel">
    <p><Link to="/admin/world/library">World Packages</Link> → <Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>{data?.package.name ?? worldId}</Link> → <Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries`}>Countries</Link>{data ? ` → ${data.country.name}` : ''}</p>
    {query.isLoading && <p className="status">Loading country...</p>}
    {query.error && <p className="error">Failed to load country: {formatApiError(query.error)}</p>}
    {data && <>
      <div className="page-intro"><h2>{data.country.name}</h2><p className="subtitle"><code>{data.country.code}</code></p></div>
      <p><strong>{data.package.name} · {data.package.type === 'custom' ? 'Custom' : 'Built-in'} · {canEdit ? 'Editable source' : 'Read-only'}</strong></p>
      {canEdit && !editing && !populationEditing && <button type="button" onClick={() => { setEditing(true); setSuccess(''); mutation.reset() }}>Edit country</button>}
      {success && <p className="status" role="status">{success}</p>}
      {editing && <CountryEditForm detail={data} geography={geographyQuery.data} saving={mutation.isPending} error={mutation.error} onCancel={() => { setEditing(false); mutation.reset() }} onSave={(payload) => mutation.mutate(payload)} />}
      {!editing && <SectionCard title="Overview">
        <DetailRow label="Package" value={data.package.name} /><DetailRow label="Region" value={data.region?.name ?? data.country.region} /><DetailRow label="Travel Region" value={data.travel_region?.name ?? data.country.travel_region ?? '—'} /><DetailRow label="Area" value={`${formatNumber(data.country.area_km2)} km²`} /><DetailRow label="Current/default population" value={formatNumber(data.country.default_population ?? data.country.population)} />
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
        <DetailRow label="Wealth Support" value={data.country.wealth_support} /><DetailRow label="Squash Popularity" value={data.country.squash_popularity} /><DetailRow label="Squash Tradition" value={data.country.squash_tradition} /><DetailRow label="System Quality" value={data.country.system_quality} /><DetailRow label="Competition Density" value={data.country.competition_density ?? '—'} /><DetailRow label="Federation Quality" value={data.country.federation_quality ?? '—'} /><DetailRow label="Court Count" value={formatNumber(data.country.court_count)} />
        <h4>Style DNA</h4>{style.length === 0 ? <p>No Style DNA values authored.</p> : <dl>{style.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>}
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

type StyleRow = { id: number, key: string, value: string }
function CountryEditForm({ detail, geography, saving, error, onCancel, onSave }: { detail: WorldPackageCountryDetail, geography?: WorldPackageGeography, saving: boolean, error: unknown, onCancel: () => void, onSave: (payload: WorldPackageCountryUpdatePayload) => void }): JSX.Element {
  const country = detail.country
  const [name, setName] = useState(country.name)
  const [notes, setNotes] = useState(country.notes ?? '')
  const [area, setArea] = useState(country.area_km2 == null ? '' : String(country.area_km2))
  const [region, setRegion] = useState(country.region)
  const [travelRegion, setTravelRegion] = useState(country.travel_region ?? '')
  const [values, setValues] = useState({ wealth_support: String(country.wealth_support), squash_popularity: String(country.squash_popularity), squash_tradition: String(country.squash_tradition), system_quality: String(country.system_quality), competition_density: String(country.competition_density), federation_quality: String(country.federation_quality), court_count: country.court_count == null ? '' : String(country.court_count) })
  const [styleRows, setStyleRows] = useState<StyleRow[]>(Object.entries(country.style_dna ?? {}).map(([key, value], id) => ({ id, key, value: String(value) })))
  const submit = (event: FormEvent) => {
    event.preventDefault()
    onSave({ name, notes: notes || null, area_km2: area ? Number(area) : null, region, travel_region: travelRegion || null,
      wealth_support: Number(values.wealth_support), squash_popularity: Number(values.squash_popularity), squash_tradition: Number(values.squash_tradition), system_quality: Number(values.system_quality), competition_density: Number(values.competition_density), federation_quality: Number(values.federation_quality), court_count: values.court_count === '' ? null : Number(values.court_count),
      style_dna: Object.fromEntries(styleRows.filter(row => row.key.trim()).map(row => [row.key.trim(), Number(row.value)])), expected_package_fingerprint: detail.package.fingerprint })
  }
  const numeric = (key: keyof typeof values, label: string, min: number, max?: number, step = 1) => <label>{label}<input type="number" required min={min} max={max} step={step} value={values[key]} onChange={event => setValues(current => ({ ...current, [key]: event.target.value }))} /></label>
  return <SectionCard title="Edit country"><form onSubmit={submit}>
    {error != null && <p className="error" role="alert">{formatApiError(error)}</p>}
    <label>Name<input required value={name} onChange={event => setName(event.target.value)} /></label>
    <label>Notes<textarea value={notes} onChange={event => setNotes(event.target.value)} /></label>
    <label>Area km²<input type="number" min="1" value={area} onChange={event => setArea(event.target.value)} /></label>
    <label>Region<select value={region} onChange={event => setRegion(event.target.value)}>{geography?.regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
    <label>Travel Region<select value={travelRegion} onChange={event => setTravelRegion(event.target.value)}><option value="">None</option>{geography?.travel_regions.map(item => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label>
    {numeric('wealth_support', 'Wealth Support', 1, 5)}{numeric('squash_popularity', 'Squash Popularity', 1, 5)}{numeric('squash_tradition', 'Squash Tradition', 1, 5)}{numeric('system_quality', 'System Quality', 1, 5)}{numeric('competition_density', 'Competition Density', 1, 5, 0.1)}{numeric('federation_quality', 'Federation Quality', 1, 5, 0.1)}{numeric('court_count', 'Court Count', 0)}
    <fieldset><legend>Style DNA</legend>{styleRows.map((row, index) => <div key={row.id}><input aria-label={`Style DNA key ${index + 1}`} value={row.key} onChange={event => setStyleRows(rows => rows.map(item => item.id === row.id ? { ...item, key: event.target.value } : item))} /><input aria-label={`Style DNA value ${index + 1}`} type="number" step="any" value={row.value} onChange={event => setStyleRows(rows => rows.map(item => item.id === row.id ? { ...item, value: event.target.value } : item))} /><button type="button" onClick={() => setStyleRows(rows => rows.filter(item => item.id !== row.id))}>Remove</button></div>)}<button type="button" onClick={() => setStyleRows(rows => [...rows, { id: Math.max(-1, ...rows.map(row => row.id)) + 1, key: '', value: '0' }])}>Add Style DNA entry</button></fieldset>
    <p><button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button> <button type="button" disabled={saving} onClick={onCancel}>Cancel</button></p>
  </form></SectionCard>
}
