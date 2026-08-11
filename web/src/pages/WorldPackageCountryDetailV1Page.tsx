import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import type { CountryV1Record, WorldPackageCountryV1Detail } from '../api/countryV1'
import { getWorldPackageCountryV1 } from '../api/countryV1Client'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function DetailRow({ label, value }: { label: string, value: string | number }): JSX.Element {
  return <p><strong>{label}:</strong> {value}</p>
}

export function CountryV1StrengthSection({ country }: { country: CountryV1Record }): JSX.Element {
  return (
    <SectionCard title="Squash / Country strength">
      <DetailRow label="Squash Popularity" value={country.squash_popularity} />
      <DetailRow label="Squash Access" value={country.squash_access} />
      <DetailRow label="Development Quality" value={country.development_quality} />
      <DetailRow label="Competition Quality" value={country.competition_quality} />
      <DetailRow label="Elite Support" value={country.elite_support} />
      <DetailRow label="Squash Tradition" value={country.squash_tradition} />
      <DetailRow label="Court Count" value={formatNumber(country.court_count)} />
    </SectionCard>
  )
}

export function CountryV1ReadOnlyDetail({ detail }: { detail: WorldPackageCountryV1Detail }): JSX.Element {
  const timeline = Object.entries(detail.country.population_by_year ?? {})
    .filter((entry): entry is [string, number] => entry[1] != null)
    .sort(([left], [right]) => Number(left) - Number(right))

  return (
    <>
      <div className="page-intro">
        <h2>{detail.country.name}</h2>
        <p className="subtitle"><code>{detail.country.code}</code></p>
      </div>

      <p>
        <strong>
          {detail.package.name} · {detail.package.type === 'custom' ? 'Custom' : 'Built-in'} · {detail.package.editable ? 'Editable source' : 'Read-only'}
        </strong>
      </p>

      <SectionCard title="Overview">
        <DetailRow label="Package" value={detail.package.name} />
        <DetailRow label="Region" value={detail.region?.name ?? detail.country.region} />
        <DetailRow label="Continent" value={detail.continent?.name ?? '—'} />
        <DetailRow label="Travel Region" value={detail.travel_region?.name ?? detail.country.travel_region ?? '—'} />
        <DetailRow label="Area km²" value={formatNumber(detail.country.area_km2)} />
        <DetailRow
          label="Current/default population"
          value={formatNumber(detail.country.default_population ?? detail.country.population)}
        />
        {detail.country.notes && <DetailRow label="Notes" value={detail.country.notes} />}
      </SectionCard>

      <CountryV1StrengthSection country={detail.country} />

      <SectionCard title="Population timeline">
        {timeline.length === 0 ? (
          <p>No authored population timeline values.</p>
        ) : (
          <div style={{ maxHeight: '28rem', overflowY: 'auto' }}>
            <table aria-label="Authored population timeline">
              <thead><tr><th>Year</th><th>Population</th></tr></thead>
              <tbody>
                {timeline.map(([year, value]) => (
                  <tr key={year}>
                    <td>{year}{year === '2020' ? ' · Default year' : ''}</td>
                    <td>{formatNumber(value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </SectionCard>

      <details>
        <summary>Technical source</summary>
        <code>{detail.source_path}</code>
      </details>
    </>
  )
}

export function WorldPackageCountryDetailV1Page(): JSX.Element {
  const { worldId = '', countryCode = '' } = useParams()
  const query = useQuery({
    queryKey: ['world-package-country', worldId, countryCode],
    queryFn: () => getWorldPackageCountryV1(worldId, countryCode),
    enabled: Boolean(worldId && countryCode),
    retry: false,
  })

  const detail = query.data

  return (
    <section className="panel">
      <p>
        <Link to="/admin/world/library">World Packages</Link>
        {' → '}
        <Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>{detail?.package.name ?? worldId}</Link>
        {' → '}
        <Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries`}>Countries</Link>
        {detail ? ` → ${detail.country.name}` : ''}
      </p>

      {query.isLoading && <p className="status">Loading country...</p>}
      {query.error && <p className="error">Failed to load country: {formatApiError(query.error)}</p>}
      {detail && <CountryV1ReadOnlyDetail detail={detail} />}
    </section>
  )
}
