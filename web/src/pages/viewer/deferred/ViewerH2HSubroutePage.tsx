import { useQuery } from '@tanstack/react-query'

import { listRunPlayers } from '../../../api/client'
import {
  ViewerActiveRunCard,
  ViewerActiveRunLinks,
  ViewerEmptyState,
  ViewerLandingGrid,
  ViewerMetadataList,
  ViewerSectionCard,
} from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerPlayersPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTopH2HPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'
import { ViewerSamplePlayersList } from '../explore/viewerComparisonRender'
import {
  type ViewerH2HSubrouteKind,
  viewerH2HSubrouteContent,
} from './viewerDeferredConfigs'
import {
  commonDeferredSourceMetadataItems,
} from './ViewerDeferredSourceMetadataRender'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerH2HSubroutePage({
  kind,
}: {
  kind: ViewerH2HSubrouteKind
}): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const legacySimulationRunId = useActiveViewerRunId()
  const content = viewerH2HSubrouteContent[kind]

  const {
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    productRunId,
    kind,
    scope: 'h2h',
  })

  const playersQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-legacy-players', kind, legacySimulationRunId],
    queryFn: () => listRunPlayers(legacySimulationRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(legacySimulationRunId),
    retry: false,
  })

  if (!productRunId) {
    return (
      <ViewerShellPage
        title={content.title}
        description="Read-only H2H Explorer that defers analytics until authoritative match history exists."
      >
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const samplePlayers = playersQuery.data?.players ?? []
  const playerTotal = playersQuery.data?.total
  const isLoading = isLoadingMetadata || playersQuery.isLoading
  const hasError = hasMetadataError || playersQuery.isError
  const hasAnyData = hasAnySourceMetadata || samplePlayers.length > 0

  return (
    <ViewerShellPage
      title={content.title}
      description="Read-only H2H Explorer using canonical Saved-Revision sporting metadata while player browsing remains on the current legacy player source."
    >
      <ViewerLandingGrid>
        <ViewerActiveRunCard
          ariaLabel={content.title + ' canonical source metadata'}
          kicker="Selected Product Run"
          title={content.title + ' source metadata'}
        >
          {isLoading ? (
            <p className="status">Loading canonical and player source metadata…</p>
          ) : null}
          {hasError ? (
            <ViewerEmptyState>Some H2H source metadata is temporarily unavailable.</ViewerEmptyState>
          ) : null}

          <ViewerMetadataList
            ariaLabel={content.title + ' source metadata values'}
            items={[
              ...commonDeferredSourceMetadataItems({
                productRunId,
                metadata,
                isLoading: isLoadingMetadata,
              }),
              {
                label: 'Player source',
                value: legacySimulationRunId
                  ? 'Legacy SimulationRun player registry'
                  : 'Unavailable',
              },
              {
                label: 'Total player count',
                value: playersQuery.isLoading ? 'Loading…' : (playerTotal ?? '—'),
              },
              {
                label: 'Returned/sample player count',
                value: playersQuery.isLoading ? 'Loading…' : samplePlayers.length,
              },
            ]}
          />

          {!isLoading && !hasError && !hasAnyData ? (
            <ViewerEmptyState>No canonical source data or player sample is available for this Product Run yet.</ViewerEmptyState>
          ) : null}

          {!legacySimulationRunId ? (
            <ViewerEmptyState>
              Canonical sporting metadata is available, but the legacy player source is not mapped for this selection.
            </ViewerEmptyState>
          ) : null}

          <ViewerSamplePlayersList
            players={samplePlayers}
            label={content.title + ' sample players'}
            runId={productRunId}
          />
        </ViewerActiveRunCard>

        <ViewerSectionCard
          title="Deferred H2H outputs"
          kicker="No authoritative match read model"
        >
          <ViewerEmptyState>
            This preview is not connected for this data shape yet.
          </ViewerEmptyState>
          <p className="status">{content.note}</p>
        </ViewerSectionCard>

        <ViewerSectionCard title="Source links" kicker="Read-only navigation">
          <ViewerActiveRunLinks
            links={[
              { label: 'Open H2H comparison', to: viewerTopH2HPath() },
              {
                label: 'Open active run players',
                to: viewerPlayersPath(productRunId),
              },
              {
                label: 'Open active run tournaments',
                to: viewerTournamentsPath(productRunId),
              },
              {
                label: 'Open active run rankings',
                to: viewerRankingsPath(productRunId),
              },
              {
                label: 'Open active run race',
                to: viewerRacePath(productRunId),
              },
              { label: 'Open run browser', to: viewerRunsPath() },
            ]}
          />
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}
