import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRunPlayerCareerHistory, getRunPlayerCareerPerformance } from '../api/client'
import { CurrentContextStrip, PageIntro, SectionCard } from '../components/RunScopedUi'

function displayMetric(value: number | null | undefined): string | number {
  return value ?? '—'
}

export function PlayerCareerPage(): JSX.Element {
  const { runId = '', playerId = '' } = useParams()

  const query = useQuery({
    queryKey: ['player-career-history', runId, playerId],
    queryFn: () => getRunPlayerCareerHistory(runId, playerId),
    enabled: Boolean(runId && playerId)
  })

  const performanceQuery = useQuery({
    queryKey: ['player-career-performance', runId, playerId],
    queryFn: () => getRunPlayerCareerPerformance(runId, playerId),
    enabled: Boolean(runId && playerId)
  })

  const first = query.data?.entries[0]
  const latest = query.data && query.data.entries.length > 0 ? query.data.entries[query.data.entries.length - 1] : null
  const overallDelta = first && latest ? latest.overall - first.overall : null

  return (
    <section className="panel">
      <PageIntro title="Player Career History" subtitle="Longitudinal player snapshots across linked run lineage." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Player', value: playerId || 'unknown' },
          { label: 'Entries', value: query.data?.entries.length ?? '—' }
        ]}
      />

      <SectionCard title="Career header">
        {query.isLoading ? <p className="status">Loading career history…</p> : null}
        {query.error ? <p className="error">Failed to load career history: {String(query.error)}</p> : null}
        {query.data ? (
          <>
            <p>
              <strong>{query.data.player_name ?? 'Unknown player'}</strong> ({query.data.player_id}) • {query.data.country_code ?? '—'}
            </p>
            <p>
              Origin source: {latest?.origin_source_type ?? '—'} | Origin band: {latest?.origin_quality_band ?? '—'} | Origin season:{' '}
              {latest?.origin_season ?? '—'} | Origin override: {latest?.origin_override_id ?? '—'}
            </p>
            <p>
              <Link to={`/runs/${runId}/players`}>← Back to players explorer</Link>
            </p>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Trend summary">
        {query.data ? (
          <p>
            Seasons tracked: {query.data.entries.length} | Overall delta: {overallDelta === null ? '—' : overallDelta >= 0 ? `+${overallDelta}` : overallDelta}
          </p>
        ) : (
          <p className="status">Load career history to view trend summary.</p>
        )}
      </SectionCard>

      <SectionCard title="Career timeline">
        {query.data ? (
          <table>
            <thead>
              <tr>
                <th>Season</th>
                <th>Run</th>
                <th>Age</th>
                <th>Overall</th>
                <th>Technique</th>
                <th>Movement</th>
                <th>Physical</th>
                <th>Mental</th>
                <th>Source</th>
                <th>Band</th>
              </tr>
            </thead>
            <tbody>
              {query.data.entries.map((entry) => (
                <tr key={`${entry.run_id}-${entry.season}`}>
                  <td>{entry.season}</td>
                  <td>{entry.run_id}</td>
                  <td>{entry.age}</td>
                  <td>{entry.overall}</td>
                  <td>{entry.technique}</td>
                  <td>{entry.movement}</td>
                  <td>{entry.physical}</td>
                  <td>{entry.mental}</td>
                  <td>{entry.source_type ?? '—'}</td>
                  <td>{entry.quality_band ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
      </SectionCard>

      <SectionCard title="Season performance">
        {performanceQuery.isLoading ? <p className="status">Loading season performance…</p> : null}
        {performanceQuery.error ? <p className="error">Failed to load season performance: {String(performanceQuery.error)}</p> : null}
        {performanceQuery.data ? (
          performanceQuery.data.entries.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Run</th>
                  <th>Ranking</th>
                  <th>Race</th>
                  <th>Tournaments</th>
                  <th>Titles</th>
                  <th>Finals</th>
                  <th>SF</th>
                  <th>QF</th>
                  <th>Wins</th>
                  <th>Losses</th>
                </tr>
              </thead>
              <tbody>
                {performanceQuery.data.entries.map((entry) => (
                  <tr key={`performance-${entry.run_id}-${entry.season}`}>
                    <td>{entry.season}</td>
                    <td>{entry.run_id}</td>
                    <td>{displayMetric(entry.ranking_position)}</td>
                    <td>{displayMetric(entry.race_position)}</td>
                    <td>{entry.tournaments_played}</td>
                    <td>{entry.titles}</td>
                    <td>{entry.finals}</td>
                    <td>{entry.semifinals}</td>
                    <td>{entry.quarterfinals}</td>
                    <td>{entry.wins}</td>
                    <td>{entry.losses}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No season performance entries are available for this player yet.</p>
          )
        ) : null}
      </SectionCard>
    </section>
  )
}
