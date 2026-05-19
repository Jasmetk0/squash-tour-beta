import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getTalentClassSummary, listCountries } from '../api/client'

const TALENT_PREVIEW_DEFAULT_YEAR_START = 2030
const TALENT_PREVIEW_DEFAULT_YEARS = 10
const TALENT_PREVIEW_DEFAULT_SEED = 123

function formatNumber(value: number | null | undefined): string {
  if (value == null) return '—'
  return value.toLocaleString('en-US')
}

function formatDecimal(value: number | null | undefined): string {
  if (value == null) return '—'
  return value.toFixed(2)
}

function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

export function CountryDetailPage(): JSX.Element {
  const { countryCode = '' } = useParams()
  const normalizedCode = countryCode.toUpperCase()

  const countriesQuery = useQuery({ queryKey: ['countries-list'], queryFn: listCountries, retry: false })

  const country = countriesQuery.data?.countries.find((item) => item.code.toUpperCase() === normalizedCode)

  const talentSummaryQuery = useQuery({
    queryKey: ['talent-class-summary', TALENT_PREVIEW_DEFAULT_YEAR_START, TALENT_PREVIEW_DEFAULT_YEARS, TALENT_PREVIEW_DEFAULT_SEED],
    queryFn: () =>
      getTalentClassSummary({
        year_start: TALENT_PREVIEW_DEFAULT_YEAR_START,
        years: TALENT_PREVIEW_DEFAULT_YEARS,
        seed: TALENT_PREVIEW_DEFAULT_SEED
      }),
    retry: false,
    enabled: Boolean(country)
  })

  const talentCountry = talentSummaryQuery.data?.countries.find((item) => item.country_code.toUpperCase() === normalizedCode)

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
        <h2>
          {country.name} ({country.code})
        </h2>
        <p className="subtitle">Country profile and authored model inputs for the FAX squash simulation engine.</p>
      </div>

      <div className="dashboard-actions-row">
        <Link className="button-secondary" to="/admin/world/countries">Back to Countries list</Link>
        <Link className="button-link" to="/admin/world/talent-preview">Open Talent Preview</Link>
        <Link className="button-link" to="/admin/world/countries">Edit in Countries list/editor</Link>
      </div>
      <p className="status">Current editing is handled in the Countries list drawer editor.</p>

      <article className="panel nested-panel">
        <h3>Identity</h3>
        <div className="dashboard-grid">
          <article className="metric-card"><span>Code</span><strong>{country.code}</strong></article>
          <article className="metric-card"><span>Name</span><strong>{country.name}</strong></article>
          <article className="metric-card"><span>Region</span><strong>{country.region}</strong></article>
          <article className="metric-card"><span>Travel region</span><strong>{country.travel_region ?? country.region}</strong></article>
          <article className="metric-card"><span>Flag asset</span><strong>{country.flag_asset || '—'}</strong></article>
        </div>
      </article>

      <article className="panel nested-panel">
        <h3>Scale / Resources</h3>
        <div className="dashboard-grid">
          <article className="metric-card"><span>Population</span><strong>{formatNumber(country.population)}</strong></article>
          <article className="metric-card"><span>Wealth support</span><strong>{formatDecimal(country.wealth_support)}</strong></article>
          <article className="metric-card"><span>Court count</span><strong>{formatNumber(country.court_count)}</strong></article>
        </div>
      </article>

      <article className="panel nested-panel">
        <h3>Squash Model Inputs</h3>
        <div className="dashboard-grid">
          <article className="metric-card"><span>Squash popularity</span><strong>{formatDecimal(country.squash_popularity)}</strong></article>
          <article className="metric-card"><span>Squash tradition</span><strong>{formatDecimal(country.squash_tradition)}</strong></article>
          <article className="metric-card"><span>System quality</span><strong>{formatDecimal(country.system_quality)}</strong></article>
          <article className="metric-card"><span>Competition density</span><strong>{formatDecimal(country.competition_density ?? 3)}</strong></article>
          <article className="metric-card"><span>Federation quality</span><strong>{formatDecimal(country.federation_quality ?? country.system_quality)}</strong></article>
        </div>
      </article>

      <article className="panel nested-panel">
        <h3>Style DNA</h3>
        {Object.entries(country.style_dna ?? {}).length > 0 ? (
          <table>
            <thead>
              <tr>
                <th>Trait</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(country.style_dna).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="status">No style DNA values configured.</p>
        )}
      </article>

      <article className="panel nested-panel">
        <h3>Notes</h3>
        <p>{country.notes?.trim() ? country.notes : 'No notes.'}</p>
      </article>

      <article className="panel nested-panel">
        <h3>Talent Preview</h3>
        {talentSummaryQuery.isLoading ? <p className="status">Loading country talent forecast…</p> : null}
        {talentSummaryQuery.isError ? <p className="error">Country talent forecast unavailable.</p> : null}
        {talentCountry ? (
          <>
            <div className="dashboard-grid">
              <article className="metric-card"><span>Elite Talents</span><strong>{talentCountry.total_elite_talents}</strong></article>
              <article className="metric-card"><span>Tour Talents</span><strong>{talentCountry.total_tour_talents}</strong></article>
              <article className="metric-card"><span>Pro Depth</span><strong>{talentCountry.total_pro_depth}</strong></article>
              <article className="metric-card"><span>Avg Elite / year</span><strong>{formatDecimal(talentCountry.average_elite_talents_per_year)}</strong></article>
              <article className="metric-card"><span>Avg Tour / year</span><strong>{formatDecimal(talentCountry.average_tour_talents_per_year)}</strong></article>
              <article className="metric-card"><span>Avg Pro Depth / year</span><strong>{formatDecimal(talentCountry.average_pro_depth_per_year)}</strong></article>
              <article className="metric-card"><span>Top-band rate</span><strong>{formatPercent(talentCountry.average_top_band_rate)}</strong></article>
            </div>
            <p className="status">Aggregate mapping currently uses existing technical bands: Elite = elite/special/generational, Tour = strong, Pro Depth = solid. Final potential-tier mapping will replace this later.</p>
          </>
        ) : null}
        {talentSummaryQuery.data && !talentCountry ? (
          <p className="status">No forecast row found for this country in the current Talent Preview summary.</p>
        ) : null}
        <p>
          <Link to="/admin/world/talent-preview">Open full Talent Preview</Link>
        </p>
      </article>

      <article className="panel nested-panel">
        <h3>Development Curves</h3>
        <p className="status">Planned / Future</p>
        <p>Planned: editable season-by-season tables will be added later for authored country progression inputs.</p>
      </article>

      <article className="panel nested-panel">
        <h3>Generated Output from Master Run</h3>
        <p className="status">Planned / Future</p>
        <p>Run-derived country output summaries will appear here once backend country summary endpoints exist.</p>
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

      <article className="panel nested-panel">
        <details>
          <summary>Advanced raw payload</summary>
          <pre>{JSON.stringify(country, null, 2)}</pre>
        </details>
      </article>
    </section>
  )
}
