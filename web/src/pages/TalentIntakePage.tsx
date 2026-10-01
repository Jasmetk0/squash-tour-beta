import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, getRunWeeklyIntakeCohortSeasonPreview, materializeRunProspects } from '../api/client'

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

  const materializeMutation = useMutation({
    mutationFn: () =>
      materializeRunProspects(runId, {
        base_annual_intake_target: baseAnnualTarget,
        season_growth_rate: seasonGrowthRate,
        overwrite: false
      })
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
        <h3>Next workflow boundary</h3>
        <p>
          Concrete generation can later compare this frozen cohort allocation with the Expected vs Generated talent output already shown in{' '}
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
