import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, getRunProspectTalentSummary, getRunWeeklyIntakeCohortSeasonPreview, listRunProspects, materializeRunProspects } from '../api/client'

export function TalentIntakePage(): JSX.Element {
  const params = useParams()
  const [runIdInput, setRunIdInput] = useState(params.runId ?? '')
  const [baseAnnualTarget, setBaseAnnualTarget] = useState(200)
  const [seasonGrowthRate, setSeasonGrowthRate] = useState(0.015)
  const [countryFilter, setCountryFilter] = useState('')
  const [reviewConfirmed, setReviewConfirmed] = useState(false)

  const runId = (params.runId ?? runIdInput).trim()
  const previewQuery = useQuery({
    queryKey: ['run-weekly-intake-cohort-season-preview', runId, baseAnnualTarget, seasonGrowthRate],
    queryFn: () =>
      getRunWeeklyIntakeCohortSeasonPreview(runId, {
        base_annual_intake_target: baseAnnualTarget,
        season_growth_rate: seasonGrowthRate
      }),
    enabled: runId.length > 0,
    retry: false
  })

  const prospectsQuery = useQuery({
    queryKey: ['run-prospects', runId, previewQuery.data?.season_start_year],
    queryFn: () =>
      listRunProspects(runId, {
        season_start_year: previewQuery.data?.season_start_year,
        limit: 500,
        offset: 0
      }),
    enabled: runId.length > 0 && previewQuery.data !== undefined,
    retry: false
  })

  const talentSummaryQuery = useQuery({
    queryKey: ['run-prospect-talent-summary', runId, previewQuery.data?.season_start_year],
    queryFn: () => getRunProspectTalentSummary(runId, previewQuery.data?.season_start_year),
    enabled: runId.length > 0 && previewQuery.data !== undefined,
    retry: false
  })

  const materializeMutation = useMutation({
    mutationFn: () =>
      materializeRunProspects(runId, {
        base_annual_intake_target: baseAnnualTarget,
        season_growth_rate: seasonGrowthRate,
        overwrite: false
      }),
    onSuccess: () => {
      void prospectsQuery.refetch()
      void talentSummaryQuery.refetch()
    }
  })

  const filteredCountries = useMemo(() => {
    const needle = countryFilter.trim().toLowerCase()
    const rows = previewQuery.data?.country_totals ?? []
    return [...rows]
      .filter(
        (row) =>
          !needle ||
          row.country_code.toLowerCase().includes(needle) ||
          (row.country_name ?? '').toLowerCase().includes(needle)
      )
      .sort((a, b) => b.allocated_count - a.allocated_count || a.country_code.localeCompare(b.country_code))
  }, [countryFilter, previewQuery.data?.country_totals])

  return (
    <section className="panel">
      <div className="page-intro">
        <h2>Talent Intake</h2>
        <p className="subtitle">
          Read-only preview of the season&apos;s complete 15-year-old cohort before any concrete players are materialized.
        </p>
      </div>

      <p>
        The cohort contains players whose 15th birthday falls inside the selected Run season. Weekly timing and country allocation are deterministic
        planning data only; this page does not create or persist players.
      </p>

      <section className="panel nested-panel">
        <h3>Season preview</h3>
        <div className="grid">
          {!params.runId ? (
            <label>
              Run ID
              <input value={runIdInput} onChange={(event) => setRunIdInput(event.target.value)} placeholder="Run ID" />
            </label>
          ) : null}
          <label>
            Base annual intake
            <input
              type="number"
              min={0}
              value={baseAnnualTarget}
              onChange={(event) => {
                setBaseAnnualTarget(Math.max(0, Number(event.target.value)))
                setReviewConfirmed(false)
                materializeMutation.reset()
              }}
            />
          </label>
          <label>
            Season growth rate
            <input
              type="number"
              min={0}
              max={0.1}
              step={0.001}
              value={seasonGrowthRate}
              onChange={(event) => {
                setSeasonGrowthRate(Math.min(0.1, Math.max(0, Number(event.target.value))))
                setReviewConfirmed(false)
                materializeMutation.reset()
              }}
            />
          </label>
        </div>

        {!runId ? <p className="status">Enter a Run ID to load its locked world and current season intake preview.</p> : null}
        {previewQuery.isLoading ? <p className="status">Loading season intake preview…</p> : null}
        {previewQuery.isError ? <p className="error">Preview unavailable: {formatApiError(previewQuery.error)}</p> : null}

        {previewQuery.data ? (
          <>
            <div className="summary-grid">
              <p><strong>Run:</strong> {previewQuery.data.run_id}</p>
              <p><strong>World:</strong> {previewQuery.data.world_name ?? previewQuery.data.world_id}</p>
              <p><strong>Season:</strong> {previewQuery.data.season}</p>
              <p><strong>Annual target:</strong> {previewQuery.data.annual_target}</p>
              <p><strong>Weekly total:</strong> {previewQuery.data.total_weekly_target}</p>
              <p><strong>Variation:</strong> {previewQuery.data.season_variation_multiplier.toFixed(4)}</p>
            </div>

            <h4>Country totals</h4>
            <label>
              Country filter
              <input
                value={countryFilter}
                onChange={(event) => setCountryFilter(event.target.value)}
                placeholder="Code or name"
              />
            </label>
            <table aria-label="Talent intake country totals">
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Players turning 15</th>
                  <th>Share of cohort</th>
                </tr>
              </thead>
              <tbody>
                {filteredCountries.map((row) => (
                  <tr key={row.country_code}>
                    <td>{row.country_name ?? row.country_code} ({row.country_code})</td>
                    <td>{row.allocated_count}</td>
                    <td>{formatPercent(previewQuery.data ? row.allocated_count / Math.max(1, previewQuery.data.total_weekly_target) : 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <h4>Weekly intake timing</h4>
            <table aria-label="Talent intake weekly schedule">
              <thead>
                <tr>
                  <th>Season week</th>
                  <th>Calendar week</th>
                  <th>Birth cohort</th>
                  <th>Target</th>
                  <th>Allocated</th>
                </tr>
              </thead>
              <tbody>
                {previewQuery.data.weeks.map((week) => (
                  <tr key={week.season_week}>
                    <td>{week.season_week}</td>
                    <td>{week.calendar_year} / {week.year_week}</td>
                    <td>{week.birth_year} / {week.birth_year_week}</td>
                    <td>{week.target_intake_count}</td>
                    <td>{week.total_allocated}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="status">
              Generated player quality and potential are materialized only after confirmation. This preview defines the exact cohort scope that will be used.
            </p>

            <section className="panel nested-panel">
              <h4>Review → Confirm materialization</h4>
              <p>
                Review Run <strong>{previewQuery.data.run_id}</strong>, season <strong>{previewQuery.data.season}</strong>,
                annual target <strong>{previewQuery.data.annual_target}</strong> and total cohort <strong>{previewQuery.data.total_weekly_target}</strong>.
              </p>
              <label>
                <input
                  type="checkbox"
                  checked={reviewConfirmed}
                  onChange={(event) => setReviewConfirmed(event.target.checked)}
                />{' '}
                I reviewed this cohort preview and want to materialize these 15-year-old prospects.
              </label>
              <div>
                <button
                  type="button"
                  disabled={!reviewConfirmed || materializeMutation.isPending}
                  onClick={() => materializeMutation.mutate()}
                >
                  {materializeMutation.isPending ? 'Materializing…' : 'Confirm materialization'}
                </button>
              </div>
              <p className="status">
                Safety: confirmation uses <code>overwrite: false</code>. Existing conflicting cohort records are not silently replaced.
              </p>
              {materializeMutation.isError ? (
                <p className="error">Materialization failed: {formatApiError(materializeMutation.error)}</p>
              ) : null}
              {materializeMutation.data ? (
                <div aria-label="Talent intake materialization result">
                  <p><strong>{materializeMutation.data.message}</strong></p>
                  <p>
                    Created {materializeMutation.data.created_count}; existing {materializeMutation.data.existing_count};
                    persisted in scope {materializeMutation.data.total_persisted_for_scope}.
                  </p>
                  <p>
                    Requested {materializeMutation.data.requested_prospect_count}; conflicts {materializeMutation.data.conflict_count};
                    already materialized: {materializeMutation.data.already_materialized ? 'yes' : 'no'}.
                  </p>
                </div>
              ) : null}
            </section>
          </>
        ) : null}
      </section>

      <section className="panel nested-panel">
        <h3>Expected vs Generated talent quality</h3>
        <p>
          Expected values use the shared provisional rarity policy against the exact persisted 15-year-old cohort size. Generated values are derived
          deterministically from each persisted prospect seed.
        </p>
        {talentSummaryQuery.isLoading ? <p className="status">Loading talent quality summary…</p> : null}
        {talentSummaryQuery.isError ? <p className="error">Talent summary unavailable: {formatApiError(talentSummaryQuery.error)}</p> : null}
        {talentSummaryQuery.data ? (
          <>
            <p>
              Materialized cohort: <strong>{talentSummaryQuery.data.total_materialized}</strong> prospects. Policy:{' '}
              <code>{talentSummaryQuery.data.quality_policy_id}</code>.
            </p>
            <table aria-label="Talent intake expected generated global quality">
              <thead>
                <tr>
                  <th>Quality band</th>
                  <th>Weight</th>
                  <th>Expected</th>
                  <th>Generated</th>
                  <th>Δ</th>
                </tr>
              </thead>
              <tbody>
                {QUALITY_BANDS.map((band) => {
                  const expected = talentSummaryQuery.data.expected_band_counts[band] ?? 0
                  const generated = talentSummaryQuery.data.generated_band_counts[band] ?? 0
                  return (
                    <tr key={band}>
                      <td>{formatQualityBand(band)}</td>
                      <td>{formatPercent(talentSummaryQuery.data.quality_weights[band] ?? 0)}</td>
                      <td>{expected.toFixed(2)}</td>
                      <td>{generated}</td>
                      <td>{formatDelta(generated - expected)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {talentSummaryQuery.data.countries.length > 0 ? (
              <>
                <h4>Country quality comparison</h4>
                <table aria-label="Talent intake expected generated country quality">
                  <thead>
                    <tr>
                      <th>Country</th>
                      <th>Cohort</th>
                      <th>Solid E → G</th>
                      <th>Strong E → G</th>
                      <th>Elite E → G</th>
                      <th>Special E → G</th>
                      <th>Generational E → G</th>
                    </tr>
                  </thead>
                  <tbody>
                    {talentSummaryQuery.data.countries.map((country) => (
                      <tr key={country.country_code}>
                        <td>{country.country_name ?? country.country_code} ({country.country_code})</td>
                        <td>{country.materialized_count}</td>
                        {QUALITY_BANDS.map((band) => (
                          <td key={band}>
                            {formatExpectedGenerated(
                              country.expected_band_counts[band] ?? 0,
                              country.generated_band_counts[band] ?? 0
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            ) : (
              <p className="status">Materialize the cohort to populate Expected vs Generated quality output.</p>
            )}
            <p className="status">
              Quality band rarity and potential OVR are intentionally separate authorities in this slice. No OVR threshold is used to manufacture a band.
            </p>
          </>
        ) : null}
      </section>

      <section className="panel nested-panel">
        <h3>Materialized cohort inspection</h3>
        <p>
          These are the prospect records currently persisted for the selected Run season. This is concrete generated output, not a forecast.
        </p>
        {prospectsQuery.isLoading ? <p className="status">Loading materialized prospects…</p> : null}
        {prospectsQuery.isError ? <p className="error">Prospects unavailable: {formatApiError(prospectsQuery.error)}</p> : null}
        {prospectsQuery.data ? (
          <>
            <p>
              Persisted prospects: <strong>{prospectsQuery.data.total}</strong>.
              {prospectsQuery.data.total > prospectsQuery.data.prospects.length
                ? ` Showing first ${prospectsQuery.data.prospects.length}.`
                : ''}
            </p>
            {prospectsQuery.data.prospects.length > 0 ? (
              <table aria-label="Materialized talent intake prospects">
                <thead>
                  <tr>
                    <th>Prospect</th>
                    <th>Country</th>
                    <th>Season week</th>
                    <th>Quality band</th>
                    <th>Potential OVR</th>
                    <th>Development</th>
                  </tr>
                </thead>
                <tbody>
                  {prospectsQuery.data.prospects.map((prospect) => (
                    <tr key={prospect.prospect_id}>
                      <td>{prospect.display_name}</td>
                      <td>{prospect.country_name ?? prospect.country_code} ({prospect.country_code})</td>
                      <td>{prospect.season_week}</td>
                      <td>{formatQualityBand(prospect.quality_band)}</td>
                      <td>{readPotentialOvr(prospect.potential_json) ?? '—'}</td>
                      <td>{readDevelopmentTiming(prospect.development_json) ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="status">No 15-year-old prospects have been materialized for this season yet.</p>
            )}
            <p className="status">
              Potential OVR currently comes from the provisional prospect sporting-profile policy. Quality band comes independently from the shared
              rarity policy and persisted prospect seed.
            </p>
          </>
        ) : null}
      </section>

      <section className="panel nested-panel">
        <h3>Next workflow boundary</h3>
        <p>
          Talent Intake now exposes its own Expected vs Generated quality distribution. The world-level calibration view remains available in{' '}
          <Link to="/admin/world/talent-preview">Talent Preview</Link>.
        </p>
        <p>
          Current persisted player tooling remains available in <Link to="/admin/players/database">Player Database</Link>.
        </p>
      </section>
    </section>
  )
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

function formatApiError(error: unknown): string {
  if (error instanceof ApiError) return `${error.status} ${error.message}`
  return String(error)
}


function readPotentialOvr(value: Record<string, unknown>): number | null {
  const potential = value.potential_ovr
  return typeof potential === 'number' && Number.isFinite(potential) ? potential : null
}

function readDevelopmentTiming(value: Record<string, unknown>): string | null {
  const timing = value.development_timing
  return typeof timing === 'string' && timing.length > 0 ? timing : null
}


const QUALITY_BANDS = [
  'solid_prospect',
  'strong_prospect',
  'elite_prospect',
  'special_prospect',
  'generational_talent'
] as const

function formatQualityBand(value: string): string {
  return value
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter: string) => letter.toUpperCase())
}

function formatDelta(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}`
}

function formatExpectedGenerated(expected: number, generated: number): string {
  return `${expected.toFixed(2)} → ${generated} (${formatDelta(generated - expected)})`
}
