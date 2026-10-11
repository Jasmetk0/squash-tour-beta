import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { listRunPlayers } from '../../../api/client'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSectionCard } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { viewerPlayersPath, viewerTopSearchPath } from '../../../viewer/viewerRoutes'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { selectViewerComparisonPlayers } from './viewerComparisonDisplay'
import { buildSelectedH2HPath, ViewerComparisonPlayerCard, ViewerComparisonSummary, ViewerSamplePlayersList } from './viewerComparisonRender'

export function ViewerMatchPredictorPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const [searchParams] = useSearchParams()
  const playersQuery = useQuery({
    queryKey: ['viewer-match-predictor-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Match Predictor" description="Read-only Match Predictor destination used by H2H and Predictions navigation.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []
  const selectedPlayers = selectViewerComparisonPlayers(players, searchParams)
  const { playerA, playerB, hasPlayerParams, hasMissingRequestedPlayer } = selectedPlayers
  const h2hPath = buildSelectedH2HPath(selectedPlayers)

  return (
    <ViewerShellPage title="Match Predictor" description="Read-only Match Predictor using existing active-run player data only.">
      <ViewerLandingGrid>
        <ViewerSectionCard title="Match Predictor" kicker="Active Viewer run" variant="hero">
          {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
          {playersQuery.isError ? <ViewerEmptyState>Player metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
          <ViewerMetadataList
            ariaLabel="Match Predictor active run summary"
            items={[
              { label: 'Active run ID', value: activeRunId },
              { label: 'Total player count', value: playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—' },
              { label: 'Returned player count', value: playersQuery.isLoading ? 'Loading…' : players.length }
            ]}
          />
          {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        </ViewerSectionCard>
        <ViewerSectionCard title="Predictor Inputs" kicker="Read-only player fields">
          {!playersQuery.isLoading && !playersQuery.isError && hasMissingRequestedPlayer ? <ViewerEmptyState>Player data is not available for this run yet.</ViewerEmptyState> : null}
          {!playersQuery.isLoading && !playersQuery.isError && !hasPlayerParams ? (
            <>
              <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
              <ViewerSamplePlayersList players={players} label="Sample active run players for future predictor inputs" runId={activeRunId} />
            </>
          ) : null}
          {!playersQuery.isLoading && !playersQuery.isError && playerA && playerB ? <p className="status">Matched players are shown from active-run player data only.</p> : null}
        </ViewerSectionCard>
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player A" player={playerA} />
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player B" player={playerB} />
        <ViewerComparisonSummary playerA={playerA} playerB={playerB} title="Input Comparison" />
        <ViewerSectionCard title="Links" kicker="Read-only navigation">
          <ViewerActiveRunLinks
            links={[
              { label: 'Open active run players', to: viewerPlayersPath(activeRunId) },
              { label: 'Open Viewer search', to: viewerTopSearchPath() },
              { label: 'Open H2H comparison', to: h2hPath }
            ]}
          />
        </ViewerSectionCard>
        <ViewerSectionCard title="Deferred Predictor Outputs" kicker="No prediction read model">
          <ul className="viewer-home-list" aria-label="Deferred Predictor Outputs">
            <li>This preview is not connected for this data shape yet.</li>
            <li>No prediction is shown until a real prediction read model exists.</li>
            <li>No odds are shown until a real odds read model exists.</li>
          </ul>
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}
