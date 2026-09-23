import { useQuery } from '@tanstack/react-query'

import { getViewerOfficialRanking } from '../../../api/client'
import { ViewerActiveRunCard, ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { formatApiError } from '../../../utils/apiErrors'
import { RankingPreviewTable } from '../../../viewer/RankingPreviewTable'
import { findViewerTopLevelHubLink } from '../../../viewer/viewerHubLinks'
import { viewerRankingsPath } from '../../../viewer/viewerRoutes'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'

const VIEWER_RANKINGS_HUB_LINK = findViewerTopLevelHubLink('MSA Rankings')

export function ViewerRankingsPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const rankingQuery = useQuery({
    queryKey: ['viewer-current-official-ranking', productRunId],
    queryFn: () => getViewerOfficialRanking(productRunId as string),
    enabled: Boolean(productRunId),
    retry: false
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title={VIEWER_RANKINGS_HUB_LINK.label} description={VIEWER_RANKINGS_HUB_LINK.description ?? ''}>
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const ranking = rankingQuery.data
  const previewRows = (ranking?.rows ?? []).slice(0, 10).map((row) => ({
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
    <ViewerShellPage title={VIEWER_RANKINGS_HUB_LINK.label} description={VIEWER_RANKINGS_HUB_LINK.description ?? ''}>
      <ViewerActiveRunCard ariaLabel="MSA Rankings current Official Ranking" title="Current Official Ranking">
        {rankingQuery.isLoading ? <p className="status">Loading published Official Ranking…</p> : null}
        {rankingQuery.isError ? (
          <ViewerEmptyState>Published Official Ranking is unavailable: {formatApiError(rankingQuery.error)}</ViewerEmptyState>
        ) : null}
        {ranking ? (
          <>
            <ViewerMetadataList
              items={[
                { label: 'Product Run ID', value: ranking.product_run_id },
                { label: 'Viewer Branch ID', value: ranking.viewer_branch_id },
                { label: 'Season', value: ranking.season_index + 2000 },
                { label: 'Week', value: ranking.week },
                { label: 'Ranking players', value: ranking.row_count },
                { label: 'Best N', value: ranking.best_n }
              ]}
            />
            {previewRows.length ? (
              <div>
                <h4>Top 10 Official Ranking</h4>
                <RankingPreviewTable rows={previewRows} ariaLabel="Current Top 10 Official Ranking table" runId={productRunId} />
              </div>
            ) : <ViewerEmptyState>The published Official Ranking contains no players.</ViewerEmptyState>}
            <ViewerActiveRunLinks links={[{ label: 'Open active run rankings', to: viewerRankingsPath(productRunId) }]} />
          </>
        ) : null}
      </ViewerActiveRunCard>
    </ViewerShellPage>
  )
}
