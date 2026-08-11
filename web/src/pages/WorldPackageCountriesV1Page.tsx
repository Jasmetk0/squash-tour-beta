import { useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getWorldPackageCountriesV1 } from '../api/countryV1Client'
import type { CountryV1Record } from '../api/countryV1'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toLocaleString()
}

function formatPopulationYears(populationByYear: CountryV1Record['population_by_year']): string {
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

export function CountryV1Table({ countries, worldId }: { countries: CountryV1Record[], worldId: string }): JSX.Element {
  return (
    <table aria-label="World package Country V1 table">
      <thead>
        <tr>
          <th>Code</th>
          <th>Name</th>
          <th>Region</th>
          <th>Population</th>
          <th>Population coverage</th>
          <th>Area km²</th>
          <th>Travel Region</th>
          <th>Squash Popularity</th>
          <th>Squash Access</th>
          <th>Development Quality</th>
          <th>Competition Quality</th>
          <th>Elite Support</th>
          <th>Squash Tradition</th>
          <th>Courts</th>
          <th>Action</th>
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
            <CountryCell value={country.squash_access} />
            <CountryCell value={country.development_quality} />
            <CountryCell value={country.competition_quality} />
            <CountryCell value={country.elite_support} />
            <CountryCell value={country.squash_tradition} />
            <CountryCell value={country.court_count} />
            <td>
              <Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/${encodeURIComponent(country.code)}`}>
                Open
              </Link>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function WorldPackageCountriesV1Page(): JSX.Element {
  const { worldId = '' } = useParams()
  const [search, setSearch] = useState('')
  const countriesQuery = useQuery({
    queryKey: ['world-package-countries', worldId],
    queryFn: () => getWorldPackageCountriesV1(worldId),
    enabled: Boolean(worldId),
    retry: false,
  })

  const data = countriesQuery.data
  const normalizedSearch = search.trim().toLowerCase()
  const visibleCountries = (data?.countries ?? [])
    .filter((country) => `${country.code} ${country.name}`.toLowerCase().includes(normalizedSearch))
    .sort((left, right) => left.name.localeCompare(right.name) || left.code.localeCompare(right.code))

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Countries</h2>
        <p className="subtitle">Country V1 data for this World Package.</p>
      </div>
      <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}`}>Back to World Package</Link></p>

      {countriesQuery.isLoading && <p className="status">Loading countries...</p>}
      {countriesQuery.error && <p className="error">Failed to load countries: {formatApiError(countriesQuery.error)}</p>}

      {data && (
        <>
          <SectionCard title="Country dataset">
            <p><strong>World:</strong> {data.world_name} (<code>{data.world_id}</code>)</p>
            <p><strong>Country count:</strong> {data.country_count}</p>
            <p><strong>Package mode:</strong> {data.type === 'custom' ? 'Custom' : 'Built-in'} · {data.read_only ? 'Read-only' : 'Editable source'}</p>
          </SectionCard>

          <SectionCard title="Package countries">
            {data.type === 'custom' && data.source === 'custom_config' && !data.read_only && (
              <p><Link to={`/admin/world/library/${encodeURIComponent(worldId)}/countries/new`}>+ Add country</Link></p>
            )}
            <label>
              Search by country name or code
              <input
                aria-label="Search countries"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </label>
            <p>{visibleCountries.length} {visibleCountries.length === 1 ? 'country' : 'countries'}</p>
            <CountryV1Table countries={visibleCountries} worldId={worldId} />
          </SectionCard>
        </>
      )}
    </section>
  )
}
