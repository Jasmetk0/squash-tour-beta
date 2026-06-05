import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { commonDeferredSourceMetadataItems } from './ViewerDeferredSourceMetadataRender'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'
import { buildStatsDeferredSourceLinks } from './viewerDeferredLinks'
import {
  type ViewerStatsDeferredKind,
  viewerStatsDeferredConfigs,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerStatsDeferredPage({
  kind,
}: {
  kind: ViewerStatsDeferredKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerStatsDeferredConfigs[kind]
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
    scope: 'stats',
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only stats and records destination requiring an active Viewer run."
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
      description="Conservative read-only stats and records page using existing active-run metadata only."
    >
      <ViewerDeferredSourceCard
        title={config.title}
        subtitle={
          <>
            No records or statistics are calculated here yet. This page only
            shows safe source availability from the active Viewer run.
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
        sourceLinks={buildStatsDeferredSourceLinks(activeRunId)}
        sourceLinksAriaLabel={`${config.title} links`}
      />
    </ViewerShellPage>
  )
}
