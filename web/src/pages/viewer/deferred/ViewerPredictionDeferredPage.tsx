import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { commonDeferredSourceMetadataItems } from './ViewerDeferredSourceMetadata'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'
import { buildPredictionDeferredSourceLinks } from './viewerDeferredLinks'
import {
  type ViewerPredictionDeferredKind,
  viewerPredictionDeferredConfigs,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerPredictionDeferredPage({
  kind,
}: {
  kind: ViewerPredictionDeferredKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerPredictionDeferredConfigs[kind]
  const {
    statusQuery,
    eventsQuery,
    rankingSnapshotsQuery,
    raceSnapshotsQuery,
    finalsQuery,
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    activeRunId,
    kind,
    scope: 'prediction',
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only predictions destination requiring an active Viewer run."
      >
        <ViewerEmptyState>
          No data is available for this run yet.
        </ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only predictions page using existing active-run metadata only."
    >
      <ViewerDeferredSourceCard
        title={config.title}
        subtitle={
          <>
            Outputs remain deferred. This page only shows safe source
            availability from the active Viewer run.
          </>
        }
        isLoadingMetadata={isLoadingMetadata}
        hasMetadataError={hasMetadataError}
        hasAnySourceMetadata={hasAnySourceMetadata}
        metadataItems={commonDeferredSourceMetadataItems({
          activeRunId,
          metadata,
          eventsLoading: eventsQuery.isLoading,
          rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
          raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
          finalsLoading: finalsQuery.isLoading,
        })}
        deferredCopy={config.deferredCopy}
        sourceLinks={buildPredictionDeferredSourceLinks(activeRunId)}
        sourceLinksAriaLabel={`${config.title} links`}
      />
    </ViewerShellPage>
  )
}
