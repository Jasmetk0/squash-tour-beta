import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getRunPlayerCareerHistory,
  getRunPlayerCareerPerformance,
  getRunPlayerTournamentResults
} from '../api/client'
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

  const tournamentResultsQuery = useQuery({
    queryKey: ['player-career-results', runId, playerId],
    queryFn: () => getRunPlayerTournamentResults(runId, playerId),
    enabled: Boolean(runId && playerId)
  })

  // This legacy diagnostic combines three independent requests. Even a cached or
  // incorrectly scoped server response must not be presented as another player.
  const correctIdentity = (data: { requested_run_id: string; player_id: string }) =>
    data.requested_run_id === runId && data.player_id === playerId
  const career = query.data && correctIdentity(query.data) ? query.data : null
  const performance = performanceQuery.data && correctIdentity(performanceQuery.data) ? performanceQuery.data : null
  const results = tournamentResultsQuery.data && correctIdentity(tournamentResultsQuery.data)
    ? tournamentResultsQuery.data : null
  const careerMismatch = Boolean(query.data && !career)
  const performanceMismatch = Boolean(performanceQuery.data && !performance)
  const resultsMismatch = Boolean(tournamentResultsQuery.data && !results)
  const first = career?.entries[0]
  const latest = career && career.entries.length > 0 ? career.entries[career.entries.length - 1] : null
  const overallDelta = first && latest ? latest.overall - first.overall : null

  return (
    <section className="panel">
      <PageIntro title="Player Career History" subtitle="Longitudinal player snapshots across linked run lineage." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Player', value: playerId || 'unknown' },
          { label: 'Entries', value: career?.entries.length ?? '—' }
        ]}
      />

      <SectionCard title="Career header">
        {query.isLoading ? <p className="status">Loading career history…</p> : null}
        {query.error ? <p className="error">Failed to load career history: {String(query.error)}</p> : null}
        {careerMismatch ? <p role="alert">Career history does not match the requested Run and player identity.</p> : null}
        {career ? (
          <>
            <p>
              <strong>{career.player_name ?? 'Unknown player'}</strong> ({career.player_id}) • {career.country_code ?? '—'}
            </p>
            <p>
              Origin source: {latest?.origin_source_type ?? '—'} | Origin band: {latest?.origin_quality_band ?? '—'} | Origin season:{' '}
              {latest?.origin_season ?? '—'} | Origin override: {latest?.origin_override_id ?? '—'}
            </p>
            <p>
              <Link to={`/runs/${encodeURIComponent(runId)}/players`}>← Back to players explorer</Link>
            </p>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Trend summary">
        {career ? (
          <p>
            Seasons tracked: {career.entries.length} | Overall delta: {overallDelta === null ? '—' : overallDelta >= 0 ? `+${overallDelta}` : overallDelta}
          </p>
        ) : (
          <p className="status">{careerMismatch ? 'Career trend unavailable because the response identity does not match.' : 'Load career history to view trend summary.'}</p>
        )}
      </SectionCard>

      <SectionCard title="Career timeline">
        {career ? (
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
              {career.entries.map((entry) => (
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
        {performanceMismatch ? <p role="alert">Season performance does not match the requested Run and player identity.</p> : null}
        {performance ? (
          performance.entries.length > 0 ? (
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
                {performance.entries.map((entry) => (
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

      <SectionCard title="Tournament results timeline">
        {tournamentResultsQuery.isLoading ? <p className="status">Loading tournament results timeline…</p> : null}
        {tournamentResultsQuery.error ? (
          <p className="error">Failed to load tournament results timeline: {String(tournamentResultsQuery.error)}</p>
        ) : null}
        {resultsMismatch ? <p role="alert">Tournament results do not match the requested Run and player identity.</p> : null}
        {results ? (
          results.entries.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Season</th>
                  <th>Week</th>
                  <th>Run</th>
                  <th>Event</th>
                  <th>Category</th>
                  <th>Finish</th>
                  <th>Wins</th>
                  <th>Losses</th>
                  <th>Points</th>
                </tr>
              </thead>
              <tbody>
                {results.entries.map((entry) => (
                  <tr key={`result-${entry.run_id}-${entry.event_id}-${entry.event_sequence}`}>
                    <td>{entry.season}</td>
                    <td>{displayMetric(entry.week)}</td>
                    <td>{entry.run_id}</td>
                    <td>{entry.event_name ?? entry.event_id}</td>
                    <td>{entry.event_category ?? '—'}</td>
                    <td>{entry.finish ?? '—'}{entry.is_title ? ' 🏆' : ''}</td>
                    <td>{entry.wins}</td>
                    <td>{entry.losses}</td>
                    <td>{displayMetric(entry.ranking_points_awarded)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="status">No tournament results are available for this player yet.</p>
          )
        ) : null}
      </SectionCard>
    </section>
  )
}
