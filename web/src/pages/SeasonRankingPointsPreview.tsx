import { useQuery } from '@tanstack/react-query'

import { getAdminPointBreakdown, getAdminRankingSnapshot, getAdminRankingTable } from '../api/client'
import { DetailFieldGrid } from '../components/DetailUi'
import { formatApiError } from '../utils/apiErrors'
import { safeToCompactSeasonLabel } from '../utils/seasonLabels'

type Props = { seasonLabelRaw: string | null }

export function SeasonRankingPointsPreview({ seasonLabelRaw }: Props): JSX.Element {
  const compactLabel = seasonLabelRaw ? safeToCompactSeasonLabel(seasonLabelRaw) : null

  const rankingQuery = useQuery({
    queryKey: ['season-detail-ranking-preview', compactLabel],
    queryFn: () => getAdminRankingTable(compactLabel ?? '', { limit: 10 }),
    enabled: Boolean(compactLabel),
    retry: false
  })
  const snapshotQuery = useQuery({
    queryKey: ['season-detail-ranking-snapshot-preview', compactLabel, 1],
    queryFn: () => getAdminRankingSnapshot(compactLabel ?? '', 1),
    enabled: Boolean(compactLabel),
    retry: false
  })
  const pointBreakdownQuery = useQuery({
    queryKey: ['season-detail-point-breakdown-preview', compactLabel],
    queryFn: () => getAdminPointBreakdown(compactLabel ?? '', { limit: 10, applied_only: true, include_zero_point_awards: false }),
    enabled: Boolean(compactLabel),
    retry: false
  })

  if (!compactLabel) {
    return <p className="status">Ranking &amp; points preview unavailable for invalid season label.</p>
  }

  return (
    <>
      <h3>Ranking &amp; points preview</h3>

      <h4>Ranking table (Top 10)</h4>
      {rankingQuery.isLoading ? <p className="status">Loading ranking table preview…</p> : null}
      {rankingQuery.error ? <p className="error">Ranking table preview unavailable: {formatApiError(rankingQuery.error)}</p> : null}
      {rankingQuery.data ? (
        <>
          <DetailFieldGrid fields={[
            { label: 'Player count', value: rankingQuery.data.summary.player_count },
            { label: 'Ranked player count', value: rankingQuery.data.summary.ranked_player_count },
            { label: 'Zero point players', value: rankingQuery.data.summary.zero_point_players },
            { label: 'Countries represented', value: rankingQuery.data.summary.countries_represented },
            { label: 'Leader player id', value: rankingQuery.data.summary.leader_player_id ?? '—' },
            { label: 'Leader points', value: rankingQuery.data.summary.leader_points ?? '—' }
          ]} />
          {rankingQuery.data.rows.length > 0 ? (
            <table>
              <thead>
                <tr>
                  <th>Rank</th><th>Player</th><th>Country</th><th>Points</th><th>Movement / status</th><th>Source</th>
                </tr>
              </thead>
              <tbody>
                {rankingQuery.data.rows.slice(0, 10).map((row) => (
                  <tr key={row.player_id}>
                    <td>{row.rank}</td>
                    <td>{row.player_name} ({row.player_id})</td>
                    <td>{row.country_code}</td>
                    <td>{row.table_points}</td>
                    <td>{row.movement ?? '—'}</td>
                    <td>{row.source_generation ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="status">No ranking rows available.</p>}
        </>
      ) : null}

      <h4>Ranking snapshot W1</h4>
      {snapshotQuery.isLoading ? <p className="status">Loading ranking snapshot W1 preview…</p> : null}
      {snapshotQuery.error ? <p className="status">Ranking snapshot W1 unavailable.</p> : null}
      {snapshotQuery.data ? (
        snapshotQuery.data.summary ? <DetailFieldGrid fields={[
          { label: 'Season week', value: snapshotQuery.data.metadata?.season_week ?? snapshotQuery.data.summary.ranking.season_week ?? '—' },
          { label: 'Snapshot exists', value: String(snapshotQuery.data.snapshot_exists) },
          { label: 'Persisted', value: snapshotQuery.data.metadata ? String(snapshotQuery.data.metadata.persisted) : '—' },
          { label: 'Ranking row count', value: snapshotQuery.data.summary.ranking.player_count },
          { label: 'Warnings', value: snapshotQuery.data.validation_warnings.length },
          { label: 'Errors', value: snapshotQuery.data.validation_errors.length }
        ]} /> : <p className="status">Ranking snapshot W1 unavailable.</p>
      ) : null}

      <h4>Point breakdown (Top 10, applied only, non-zero)</h4>
      {pointBreakdownQuery.isLoading ? <p className="status">Loading point breakdown preview…</p> : null}
      {pointBreakdownQuery.error ? <p className="error">Point breakdown preview unavailable: {formatApiError(pointBreakdownQuery.error)}</p> : null}
      {pointBreakdownQuery.data ? (
        <>
          <DetailFieldGrid fields={[
            { label: 'Summary rows', value: pointBreakdownQuery.data.summary_rows.length },
            { label: 'Applied only', value: String(pointBreakdownQuery.data.metadata.applied_only) },
            { label: 'Include zero-point awards', value: String(pointBreakdownQuery.data.metadata.filters.include_zero_point_awards) },
            { label: 'Table type', value: pointBreakdownQuery.data.metadata.table_type },
            { label: 'Warnings', value: pointBreakdownQuery.data.validation_warnings.length },
            { label: 'Errors', value: pointBreakdownQuery.data.validation_errors.length }
          ]} />
          {pointBreakdownQuery.data.summary_rows.length > 0 ? (
            <table>
              <thead><tr><th>Player</th><th>Event / Source</th><th>Points</th><th>Reason / Round / Category</th></tr></thead>
              <tbody>
                {pointBreakdownQuery.data.summary_rows.slice(0, 10).map((row) => (
                  <tr key={row.player_id}>
                    <td>{row.player_name} ({row.player_id})</td>
                    <td>{row.top_result_event_id ?? '—'} / {pointBreakdownQuery.data.metadata.source}</td>
                    <td>{row.ranking_points}</td>
                    <td>{row.top_result_stage ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <p className="status">No point breakdown rows available.</p>}
        </>
      ) : null}
    </>
  )
}
