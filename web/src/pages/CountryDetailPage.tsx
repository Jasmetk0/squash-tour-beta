import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { listCountries } from '../api/client'

function formatNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  return value.toLocaleString('en-US')
}

export function CountryDetailPage(): JSX.Element {
  const { countryCode = '' } = useParams()
  const normalizedCode = countryCode.toUpperCase()

  const countriesQuery = useQuery({ queryKey: ['countries-list'], queryFn: listCountries, retry: false })

  const country = countriesQuery.data?.countries.find((item) => item.code.toUpperCase() === normalizedCode)

  if (countriesQuery.isLoading) {
    return (
      <section className="panel">
        <h2>Country Detail</h2>
        <p className="status">Loading country profile…</p>
      </section>
    )
  }

  if (countriesQuery.isError) {
    return (
      <section className="panel">
        <h2>Country Detail</h2>
        <p className="error">Could not load countries dataset.</p>
        <p>
          Return to the <Link to="/admin/world/countries">Countries list</Link>.
        </p>
      </section>
    )
  }

  if (!country) {
    return (
      <section className="panel">
        <h2>Country not found</h2>
        <p className="status">No country exists for code {normalizedCode || countryCode}.</p>
        <p>
          Back to <Link to="/admin/world/countries">Countries list</Link>.
        </p>
      </section>
    )
  }

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>{country.name}</h2>
        <p className="subtitle">Country profile for {country.code}. This shell will be the long-term home for deeper country workflows.</p>
      </div>

      <div className="dashboard-actions-row">
        <Link className="button-secondary" to="/admin/world/countries">Back to Countries list</Link>
        <Link className="button-link" to="/admin/world/talent-preview">Open Talent Preview</Link>
      </div>

      <article className="panel nested-panel">
        <h3>Overview</h3>
        <div className="dashboard-grid">
          <article className="metric-card"><span>Code</span><strong>{country.code}</strong></article>
          <article className="metric-card"><span>Name</span><strong>{country.name}</strong></article>
          <article className="metric-card"><span>Region</span><strong>{country.region}</strong></article>
          <article className="metric-card"><span>Travel region</span><strong>{country.travel_region ?? country.region}</strong></article>
          <article className="metric-card"><span>Population</span><strong>{formatNumber(country.population)}</strong></article>
          <article className="metric-card"><span>Wealth support</span><strong>{country.wealth_support}</strong></article>
          <article className="metric-card"><span>Squash popularity</span><strong>{country.squash_popularity}</strong></article>
          <article className="metric-card"><span>Squash tradition</span><strong>{country.squash_tradition}</strong></article>
          <article className="metric-card"><span>System quality</span><strong>{country.system_quality}</strong></article>
          <article className="metric-card"><span>Competition density</span><strong>{country.competition_density ?? 3}</strong></article>
          <article className="metric-card"><span>Federation quality</span><strong>{country.federation_quality ?? country.system_quality}</strong></article>
          <article className="metric-card"><span>Court count</span><strong>{formatNumber(country.court_count)}</strong></article>
        </div>
      </article>

      <article className="panel nested-panel">
        <h3>Inputs</h3>
        <p className="status">Current authored country inputs from the Countries dataset.</p>
        <pre>{JSON.stringify(country, null, 2)}</pre>
        <p>
          Edit authored values from the <Link to="/admin/world/countries">Countries list drawer editor</Link>.
        </p>
      </article>

      <article className="panel nested-panel">
        <h3>Development Curves</h3>
        <p className="status">Planned / Future</p>
        <p>Planned: editable season-by-season tables (no drag editor initially) for popularity, tradition, system quality, competition density, federation quality, court count, and talent multiplier.</p>
      </article>

      <article className="panel nested-panel">
        <h3>Talent Preview</h3>
        <p className="status">Current + Planned</p>
        <p>Use Talent Preview to review expected Elite Talents, Tour Talents, and Pro Depth by country before generation.</p>
      </article>

      <article className="panel nested-panel">
        <h3>Generated Output from Master Run</h3>
        <p className="status">Planned / Future</p>
        <p>Planned: generated output will default to Master Run once run-derived country summaries are implemented.</p>
        <p>This section will keep authored inputs and generated outcomes visibly separate.</p>
      </article>

      <article className="panel nested-panel">
        <h3>Top Players</h3>
        <p className="status">Planned / Future</p>
      </article>

      <article className="panel nested-panel">
        <h3>History</h3>
        <p className="status">Planned / Future</p>
      </article>

      <article className="panel nested-panel">
        <h3>Titles / Results</h3>
        <p className="status">Planned / Future</p>
      </article>
    </section>
  )
}
