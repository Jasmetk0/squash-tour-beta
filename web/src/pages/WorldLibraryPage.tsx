import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getWorldPackage, listWorldPackages } from '../api/client'
import type { WorldPackage } from '../api/types'
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
          <th>Manual Overrides</th>
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
            <td>{pkg.manual_override_count}</td>
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
        <h2>World Library</h2>
        <p className="subtitle">Read-only registry of foundational world input bundles available to the engine.</p>
      </div>
      <p>
        World Packages are foundational world input bundles. A run will eventually be created from one selected World Package.
        Official FAX World is built in and read-only. Custom Worlds are not implemented yet. This page currently exposes the
        canonical config as Official FAX World.
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

export function WorldLibraryDetailPage(): JSX.Element {
  const { worldId = '' } = useParams()
  const packageQuery = useQuery({
    queryKey: ['world-package', worldId],
    queryFn: () => getWorldPackage(worldId),
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
            <p className="status">Official FAX World is built into repository config and is read-only in this phase.</p>
          </SectionCard>
          <SectionCard title="Contents">
            <DetailRow label="Countries" value={pkg.country_count} />
            <DetailRow label="Manual overrides" value={pkg.manual_override_count} />
            <DetailRow label="Continents" value={pkg.continent_count} />
            <DetailRow label="Regions" value={pkg.region_count} />
            <DetailRow label="Travel regions" value={pkg.travel_region_count} />
          </SectionCard>
          <SectionCard title="Storage">
            {pkg.storage.world_metadata_path && <DetailRow label="World metadata path" value={<code>{pkg.storage.world_metadata_path}</code>} />}
            <DetailRow label="Countries path" value={<code>{pkg.storage.countries_path}</code>} />
            {pkg.storage.continents_path && <DetailRow label="Continents path" value={<code>{pkg.storage.continents_path}</code>} />}
            {pkg.storage.regions_path && <DetailRow label="Regions path" value={<code>{pkg.storage.regions_path}</code>} />}
            {pkg.storage.travel_regions_path && <DetailRow label="Travel regions path" value={<code>{pkg.storage.travel_regions_path}</code>} />}
            <DetailRow label="Manual player overrides path" value={<code>{pkg.storage.manual_player_overrides_path}</code>} />
          </SectionCard>
          <SectionCard title="Usage">
            <DetailRow label="Used by runs" value={usageLabel(pkg.used_by_run_count)} />
            {pkg.used_by_run_count === null && <p className="status">Usage aggregation is not implemented yet.</p>}
          </SectionCard>
          <SectionCard title="Read-only links">
            <p><Link to="/admin/world/countries">Open Countries Editor</Link> — this still edits the current canonical countries dataset, not package-scoped countries yet.</p>
            <p><Link to="/admin/world/package">Open Legacy World Package Import/Export</Link> — this is legacy canonical import/export, not multi-world package management yet.</p>
          </SectionCard>
        </>
      )}
    </section>
  )
}
