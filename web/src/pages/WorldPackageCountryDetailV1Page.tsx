import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getWorldPackageGeography } from '../api/client'
import type {
  CountryV1Record,
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1UpdatePayload,
} from '../api/countryV1'
import { getWorldPackageCountryV1, updateWorldPackageCountryV1 } from '../api/countryV1Client'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { CountryV1EditForm } from './WorldPackageCountryEditV1Form'

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
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [success, setSuccess] = useState('')

  const query = useQuery({
    queryKey: ['world-package-country', worldId, countryCode],
    queryFn: () => getWorldPackageCountryV1(worldId, countryCode),
    enabled: Boolean(worldId && countryCode),
    retry: false,
  })

  const detail = query.data
  const canEdit = detail?.package.type === 'custom'
    && detail.package.source === 'custom_config'
    && detail.package.editable

  const geographyQuery = useQuery({
    queryKey: ['world-package-geography', worldId],
    queryFn: () => getWorldPackageGeography(worldId),
    enabled: Boolean(worldId && canEdit),
    retry: false,
  })

  const updateMutation = useMutation({
    mutationFn: (payload: WorldPackageCountryV1UpdatePayload) =>
      updateWorldPackageCountryV1(worldId, countryCode, payload),
    onSuccess: async (response) => {
      queryClient.setQueryData(
        ['world-package-country', worldId, countryCode],
        response.country_detail,
      )
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }),
        queryClient.invalidateQueries({ queryKey: ['world-packages'] }),
      ])
      setEditing(false)
      setSuccess('Country saved.')
    },
  })

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

      {detail && !editing && (
        <>
          {canEdit && (
            <p>
              <button
                type="button"
                onClick={() => {
                  setEditing(true)
                  setSuccess('')
                  updateMutation.reset()
                }}
              >
                Edit country
              </button>
            </p>
          )}
          {success && <p className="status" role="status">{success}</p>}
          <CountryV1ReadOnlyDetail detail={detail} />
        </>
      )}

      {detail && editing && (
        <>
          <div className="page-intro">
            <h2>{detail.country.name}</h2>
            <p className="subtitle"><code>{detail.country.code}</code></p>
          </div>
          {geographyQuery.error && (
            <p className="error">Failed to load geography: {formatApiError(geographyQuery.error)}</p>
          )}
          <CountryV1EditForm
            detail={detail}
            geography={geographyQuery.data}
            saving={updateMutation.isPending}
            error={updateMutation.error}
            onCancel={() => {
              setEditing(false)
              updateMutation.reset()
            }}
            onSave={(payload) => updateMutation.mutate(payload)}
          />
        </>
      )}
    </section>
  )
}
