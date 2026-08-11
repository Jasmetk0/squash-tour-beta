import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { getWorldPackageGeography } from '../api/client'
import type {
  CountryV1Record,
  WorldPackageCountryV1Detail,
  WorldPackageCountryV1PopulationUpdatePayload,
  WorldPackageCountryV1UpdatePayload,
} from '../api/countryV1'
import {
  deleteWorldPackageCountryV1,
  getWorldPackageCountryV1,
  updateWorldPackageCountryPopulationV1,
  updateWorldPackageCountryV1,
} from '../api/countryV1Client'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { CountryV1DeleteConfirmation } from './WorldPackageCountryDeleteV1Confirmation'
import { CountryV1EditForm } from './WorldPackageCountryEditV1Form'
import { CountryV1PopulationEditForm } from './WorldPackageCountryPopulationV1Form'

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
      <p>No Style DNA values authored. Country V1 does not author national play-style DNA.</p>
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
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [populationEditing, setPopulationEditing] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
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

  async function refreshRelatedCountryQueries(): Promise<void> {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['world-package-countries', worldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-package', worldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-package-validation', worldId] }),
      queryClient.invalidateQueries({ queryKey: ['world-packages'] }),
    ])
  }

  const updateMutation = useMutation({
    mutationFn: (payload: WorldPackageCountryV1UpdatePayload) =>
      updateWorldPackageCountryV1(worldId, countryCode, payload),
    onSuccess: async (response) => {
      queryClient.setQueryData(['world-package-country', worldId, countryCode], response.country_detail)
      await refreshRelatedCountryQueries()
      setEditing(false)
      setSuccess(`Country changes saved. Validation status: ${response.validation.status}.`)
    },
  })

  const populationMutation = useMutation({
    mutationFn: (payload: WorldPackageCountryV1PopulationUpdatePayload) =>
      updateWorldPackageCountryPopulationV1(worldId, countryCode, payload),
    onSuccess: async (response) => {
      queryClient.setQueryData(['world-package-country', worldId, countryCode], response.country_detail)
      await refreshRelatedCountryQueries()
      setPopulationEditing(false)
      setSuccess(`Population saved. Validation status: ${response.validation.status}.`)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => {
      if (!detail) throw new Error('Country detail is not loaded')
      return deleteWorldPackageCountryV1(worldId, countryCode, detail.package.fingerprint)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['world-package-country', worldId, countryCode] }),
        refreshRelatedCountryQueries(),
      ])
      navigate(`/admin/world/library/${encodeURIComponent(worldId)}/countries`)
    },
  })

  const showingReadOnly = detail && !editing && !populationEditing

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

      {showingReadOnly && (
        <>
          {canEdit && (
            <p>
              <button
                type="button"
                onClick={() => {
                  setEditing(true)
                  setConfirmDelete(false)
                  setSuccess('')
                  updateMutation.reset()
                }}
              >
                Edit country
              </button>{' '}
              <button
                type="button"
                onClick={() => {
                  setPopulationEditing(true)
                  setConfirmDelete(false)
                  setSuccess('')
                  populationMutation.reset()
                }}
              >
                Edit population
              </button>{' '}
              <button
                type="button"
                onClick={() => {
                  setConfirmDelete(true)
                  setSuccess('')
                  deleteMutation.reset()
                }}
              >
                Delete country
              </button>
            </p>
          )}
          {confirmDelete && (
            <CountryV1DeleteConfirmation
              code={detail.country.code}
              name={detail.country.name}
              saving={deleteMutation.isPending}
              error={deleteMutation.error}
              onConfirm={() => deleteMutation.mutate()}
              onCancel={() => {
                setConfirmDelete(false)
                deleteMutation.reset()
              }}
            />
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

      {detail && populationEditing && (
        <>
          <div className="page-intro">
            <h2>{detail.country.name}</h2>
            <p className="subtitle"><code>{detail.country.code}</code></p>
          </div>
          <CountryV1PopulationEditForm
            detail={detail}
            saving={populationMutation.isPending}
            error={populationMutation.error}
            onCancel={() => {
              setPopulationEditing(false)
              populationMutation.reset()
            }}
            onSave={(payload) => populationMutation.mutate(payload)}
          />
        </>
      )}
    </section>
  )
}
