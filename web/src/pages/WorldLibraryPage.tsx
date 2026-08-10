import type { FormEvent, ReactNode } from 'react'
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { cloneOfficialWorldPackage, getWorldPackage, getWorldPackageCountries, getWorldPackageValidation, listWorldPackages } from '../api/client'
import type { CountryRecord, WorldPackage, WorldPackageCloneResponse, WorldPackageValidation } from '../api/types'
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
          <th>Source</th>
          <th>Editable</th>
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
            <td>{pkg.type}</td>
            <td>{pkg.status}</td>
            <td>{pkg.source}</td>
            <td>{yesNo(pkg.editable, 'Editable', 'Read-only')}</td>
            <td>{pkg.country_count}</td>
            <td>{pkg.continent_count}</td>
            <td>{pkg.region_count}</td>
            <td>{pkg.travel_region_count}</td>
            <td>{usageLabel(pkg.used_by_run_count)}</td>
            <td>{pkg.version}</td>
            <td><code title={pkg.fingerprint}>{shortFingerprint(pkg.fingerprint)}</code></td>
            <td><Link to={`/admin/world/library/${encodeURIComponent(pkg.world_id)}`}>View details</Link></td>
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

function PackageCountriesTable({ countries }: { countries: CountryRecord[] }): JSX.Element {
  return (
    <table>
      <thead>
        <tr>
          <th>Code</th><th>Name</th><th>Region</th><th>Area km²</th><th>Population</th><th>Default population year</th><th>Default population</th><th>Population years</th><th>Wealth</th><th>Popularity</th><th>Tradition</th><th>System</th><th>Competition</th><th>Federation</th><th>Courts</th><th>Travel region</th>
        </tr>
      </thead>
      <tbody>
        {countries.map((country) => (
          <tr key={country.code}>
            <CountryCell value={<code>{country.code}</code>} />
            <CountryCell value={country.name} />
            <CountryCell value={country.region} />
            <CountryCell value={formatNumber(country.area_km2)} />
            <CountryCell value={country.population.toLocaleString()} />
            <CountryCell value={country.default_population_year} />
            <CountryCell value={formatNumber(country.default_population)} />
            <CountryCell value={formatPopulationYears(country.population_by_year)} />
            <CountryCell value={country.wealth_support} />
            <CountryCell value={country.squash_popularity} />
            <CountryCell value={country.squash_tradition} />
            <CountryCell value={country.system_quality} />
            <CountryCell value={country.competition_density} />
            <CountryCell value={country.federation_quality} />
            <CountryCell value={country.court_count} />
            <CountryCell value={country.travel_region} />
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
            <DetailRow label="Source package mode" value={data.read_only ? 'Read-only' : 'Editable'} />
          </SectionCard>
          <SectionCard title="Package countries">
            <p className="status">This inspection screen does not currently provide create, edit, delete, import, or export actions, regardless of source package editability.</p>
            <PackageCountriesTable countries={data.countries} />
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
