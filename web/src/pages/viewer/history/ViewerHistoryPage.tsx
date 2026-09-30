import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerFinalsRace, getViewerTournamentHistory, listViewerOfficialRankingHistory } from '../../../api/client'
import { ViewerEmptyState, ViewerMetadataList } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerFinalsPath, viewerHistoryPath, viewerRankingsPath, viewerTournamentsPath } from '../../../viewer/viewerRoutes'

export function ViewerHistoryPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const enabled = Boolean(productRunId)

  const tournamentsQuery = useQuery({
    queryKey: ['viewer-top-history-tournaments', productRunId],
    queryFn: () => getViewerTournamentHistory(productRunId ?? ''),
    enabled,
    retry: false
  })
  const rankingsQuery = useQuery({
    queryKey: ['viewer-top-history-rankings', productRunId],
    queryFn: () => listViewerOfficialRankingHistory(productRunId ?? ''),
    enabled,
    retry: false
  })
  const raceQuery = useQuery({
    queryKey: ['viewer-top-history-finals-race', productRunId],
    queryFn: () => getViewerFinalsRace(productRunId ?? ''),
    enabled,
    retry: false
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title="History" description="Canonical Saved-Revision history for the selected Viewer Product Run.">
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const completedTournaments = (tournamentsQuery.data?.tournaments ?? []).filter((event) => event.result_published)
  const rankingPublications = rankingsQuery.data?.publications ?? []
  const racePublications = raceQuery.data?.publications ?? []
  const loading = tournamentsQuery.isLoading || rankingsQuery.isLoading || raceQuery.isLoading
  const unavailable = tournamentsQuery.isError || rankingsQuery.isError || raceQuery.isError
  const viewerBranch =
    tournamentsQuery.data?.viewer_branch_id ??
    rankingsQuery.data?.viewer_branch_id ??
    raceQuery.data?.viewer_branch_id ??
    '—'

  return (
    <ViewerShellPage title="History" description="Canonical Saved-Revision sporting publication history for the selected Viewer Product Run.">
      <article className="viewer-active-run-card" aria-label="Canonical history summary">
        <span className="eyebrow">Selected Product Run</span>
        <h3>{productRunId}</h3>
        {loading ? <p className="status">Loading canonical history…</p> : null}
        {unavailable ? <ViewerEmptyState>Canonical history is temporarily unavailable.</ViewerEmptyState> : null}
        {!unavailable ? (
          <ViewerMetadataList
            ariaLabel="Canonical history summary fields"
            items={[
              { label: 'Product Run', value: productRunId },
              { label: 'Viewer Branch', value: viewerBranch },
              { label: 'Completed tournaments', value: completedTournaments.length },
              { label: 'Official Ranking publications', value: rankingPublications.length },
              { label: 'Finals Race publications', value: racePublications.length }
            ]}
          />
        ) : null}
        {!loading && !unavailable && completedTournaments.length === 0 && rankingPublications.length === 0 && racePublications.length === 0 ? (
          <ViewerEmptyState>No canonical sporting publications are available for this run yet.</ViewerEmptyState>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerHistoryPath(productRunId)}>Open full run history</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(productRunId)}>Tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(productRunId)}>Rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsPath(productRunId)}>World Tour Finals</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
