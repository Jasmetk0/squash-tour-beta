import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRunTalentPlan, listGeneratedPlayersProvenance } from '../api/client'
import { CurrentContextStrip, EmptyState, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

export function WorldGenerationPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [countryCode, setCountryCode] = useState('')
  const [qualityBand, setQualityBand] = useState('')

  const planQuery = useQuery({
    queryKey: ['run-talent-plan', runId],
    queryFn: () => getRunTalentPlan(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const playersQuery = useQuery({
    queryKey: ['generated-player-provenance', runId, countryCode, qualityBand],
    queryFn: () =>
      listGeneratedPlayersProvenance(runId, {
        country_code: countryCode || undefined,
        quality_band: qualityBand || undefined,
        limit: 300
      }),
    enabled: Boolean(runId),
    retry: false
  })

  const qualityBandOptions = useMemo(() => {
    const allBands = new Set<string>()
    for (const country of planQuery.data?.countries ?? []) {
      for (const key of Object.keys(country.actual_band_counts)) {
        allBands.add(key)
      }
    }
    return Array.from(allBands).sort()
  }, [planQuery.data])

  return (
    <section className="panel">
      <RunScopedHeader
        title="World generation diagnostics"
        runId={runId}
        subtitle="Persisted annual talent plan and generated-player provenance for this run."
      />
      <p>
        <Link to={`/runs/${runId}/diagnostics`}>Back to diagnostics</Link>
      </p>
      <CurrentContextStrip
        items={[
          { label: 'Season', value: planQuery.data?.season ?? '—' },
          { label: 'Seed', value: planQuery.data?.seed ?? '—' },
          { label: 'Total talents', value: planQuery.data?.total_talents ?? '—' }
        ]}
      />

      <SectionCard title="Run talent plan summary">
        {planQuery.isLoading && <p className="status">Loading run talent plan...</p>}
        {planQuery.error && <p className="error">Failed to load run talent plan: {formatApiError(planQuery.error)}</p>}
        {planQuery.data && (
          <>
            <p className="status">
              Dataset status: {planQuery.data.dataset_status ?? 'n/a'} · Config version: {planQuery.data.config_version ?? 'n/a'}
            </p>
            <table aria-label="Run talent country allocations table">
              <thead>
                <tr>
                  <th>Country</th>
                  <th>Planned</th>
                  <th>Actual bands</th>
                </tr>
              </thead>
              <tbody>
                {planQuery.data.countries.map((country) => (
                  <tr key={country.country_code}>
                    <td>{country.country_code}</td>
                    <td>{country.planned_count}</td>
                    <td>
                      {Object.entries(country.actual_band_counts)
                        .map(([band, count]) => `${band}: ${count}`)
                        .join(', ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </SectionCard>

      <SectionCard title="Generated players provenance">
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.75rem' }}>
          <label>
            Country
            <input
              aria-label="Filter by country"
              value={countryCode}
              onChange={(event) => setCountryCode(event.target.value.toUpperCase())}
              placeholder="e.g. EGY"
              maxLength={3}
            />
          </label>
          <label>
            Quality band
            <select aria-label="Filter by quality band" value={qualityBand} onChange={(event) => setQualityBand(event.target.value)}>
              <option value="">All</option>
              {qualityBandOptions.map((band) => (
                <option key={band} value={band}>
                  {band}
                </option>
              ))}
            </select>
          </label>
        </div>
        {playersQuery.isLoading && <p className="status">Loading generated players provenance...</p>}
        {playersQuery.error && <p className="error">Failed to load generated players provenance: {formatApiError(playersQuery.error)}</p>}
        {playersQuery.data && playersQuery.data.players.length === 0 && <EmptyState message="No persisted generated-player provenance found." />}
        {playersQuery.data && playersQuery.data.players.length > 0 && (
          <table aria-label="Generated players provenance table">
            <thead>
              <tr>
                <th>Player ID</th>
                <th>Country</th>
                <th>Band</th>
                <th>Sequence</th>
                <th>Talent seed</th>
                <th>Top band</th>
              </tr>
            </thead>
            <tbody>
              {playersQuery.data.players.map((player) => (
                <tr key={player.player_id}>
                  <td>{player.player_id}</td>
                  <td>{player.country_code}</td>
                  <td>{player.quality_band}</td>
                  <td>{player.talent_sequence}</td>
                  <td>{player.talent_seed_value}</td>
                  <td>{player.is_top_band ? 'Yes' : 'No'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
    </section>
  )
}
