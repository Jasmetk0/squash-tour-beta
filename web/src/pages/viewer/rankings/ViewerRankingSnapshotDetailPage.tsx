import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getViewerOfficialRankingHistoryDetail } from '../../../api/client'
import { RunScopedHeader, SectionCard } from '../../../components/RunScopedUi'
import { formatApiError } from '../../../utils/apiErrors'
import { RankingPreviewTable } from '../../../viewer/RankingPreviewTable'
import { useViewerProductRunRouteContext } from '../../../viewer/ViewerProductRunRouteContext'
import { viewerRankingsPath } from '../../../viewer/viewerRoutes'

export function ViewerRankingSnapshotDetailPage(): JSX.Element {
  const { snapshotSequence = '' } = useParams()
  const { productRunId } = useViewerProductRunRouteContext()
  const weekOrdinal = /^\d+$/.test(snapshotSequence) ? Number.parseInt(snapshotSequence, 10) : Number.NaN
  const query = useQuery({
    queryKey: ['viewer-official-ranking-history-detail', productRunId, weekOrdinal],
    queryFn: () => getViewerOfficialRankingHistoryDetail(productRunId, weekOrdinal),
    enabled: Number.isInteger(weekOrdinal) && weekOrdinal >= 0,
    retry: false
  })

  const ranking = query.data
  const rows = (ranking?.rows ?? []).map((row) => ({
    rank: row.rank,
    playerId: row.player_id,
    playerName: null,
    country: null,
    points: row.points,
    tournamentsCounted: null,
    movement: null,
    previousRank: null
  }))

  return (
    <section className="panel">
      <RunScopedHeader
        title="MSA Rankings"
        runId={productRunId}
        subtitle="Historical Official Ranking publication from the selected Viewer Branch."
      />
      <p><Link to={viewerRankingsPath(productRunId)}>Back to ranking history</Link></p>
      {!Number.isInteger(weekOrdinal) || weekOrdinal < 0 ? <p className="error">Invalid ranking publication identity.</p> : null}
      {query.isLoading ? <p className="status">Loading Official Ranking publication…</p> : null}
      {query.isError ? <p className="error">Failed to load Official Ranking publication: {formatApiError(query.error)}</p> : null}
      {ranking ? (
        <SectionCard title={`Season ${2000 + ranking.season_index} · Week ${ranking.week}`}>
          <p className="status">
            Policy <strong>{ranking.policy_id}</strong> · Best {ranking.best_n} · {ranking.row_count} ranked players
          </p>
          <RankingPreviewTable rows={rows} ariaLabel="Historical Official Ranking table" runId={productRunId} />
        </SectionCard>
      ) : null}
    </section>
  )
}
