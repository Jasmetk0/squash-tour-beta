import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'

import { listRunPlayers } from '../../../api/client'
import { ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSectionCard } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { selectViewerComparisonPlayers, selectedComparisonPlayers } from './viewerComparisonDisplay'
import { ViewerComparisonPlayerCard, ViewerComparisonSummary, ViewerPlayerComparisonLinks, ViewerSamplePlayersList } from './viewerComparisonRender'

type ViewerComparisonRouteKind = 'h2h' | 'compare'

function ViewerPlayerComparisonContent({ routeKind }: { routeKind: ViewerComparisonRouteKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const [searchParams] = useSearchParams()
  const playersQuery = useQuery({
    queryKey: ['viewer-player-comparison-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Player Comparison" description="Read-only player comparison using the active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []
  const selectedPlayers = selectViewerComparisonPlayers(players, searchParams)
  const { playerA, playerB, hasPlayerParams, hasMissingRequestedPlayer } = selectedPlayers

  return (
    <ViewerShellPage
      title="Player Comparison"
      description={routeKind === 'h2h' ? 'Read-only H2H comparison using existing active-run player fields only.' : 'Read-only player comparison using existing active-run player fields only.'}
    >
      <ViewerLandingGrid>
        <ViewerSectionCard title="Player Comparison" kicker="Active Viewer run" variant="hero">
          {playersQuery.isLoading ? <p className="status">Loading active run player metadata…</p> : null}
          {playersQuery.isError ? <ViewerEmptyState>Player metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
          <ViewerMetadataList
            items={[
              { label: 'Active run ID', value: activeRunId },
              { label: 'Total player count', value: playersQuery.isLoading ? 'Loading…' : playersQuery.data?.total ?? '—' },
              { label: 'Returned player count', value: playersQuery.isLoading ? 'Loading…' : players.length }
            ]}
          />
          {!playersQuery.isLoading && !playersQuery.isError && players.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
          {!playersQuery.isLoading && !playersQuery.isError && hasMissingRequestedPlayer ? <ViewerEmptyState>Player data is not available for this run yet.</ViewerEmptyState> : null}
          {!playersQuery.isLoading && !playersQuery.isError && !hasPlayerParams ? (
            <>
              <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
              <ViewerSamplePlayersList players={players} label="Sample active run players for comparison links" runId={activeRunId} />
            </>
          ) : null}
        </ViewerSectionCard>
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player A" player={playerA} />
        <ViewerComparisonPlayerCard activeRunId={activeRunId} title="Player B" player={playerB} />
        <ViewerComparisonSummary playerA={playerA} playerB={playerB} />
        <ViewerPlayerComparisonLinks activeRunId={activeRunId} players={selectedComparisonPlayers(selectedPlayers)} />
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}

export function ViewerPlayerComparisonPage(): JSX.Element {
  return <ViewerPlayerComparisonContent routeKind="compare" />
}

export function ViewerPlayerComparePage(): JSX.Element {
  return <ViewerPlayerComparisonPage />
}

export function ViewerH2HPage(): JSX.Element {
  return <ViewerPlayerComparisonContent routeKind="h2h" />
}
