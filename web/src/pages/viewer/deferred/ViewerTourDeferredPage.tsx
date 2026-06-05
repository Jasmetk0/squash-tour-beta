import { Link } from 'react-router-dom'

import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerPlannedEventPath } from '../../../viewer/viewerRoutes'
import { selectNextOrderedEvent } from '../tour/viewerTourDisplay'
import {
  renderFinalsSourceValue,
  renderLatestPersistedEventSourceValue,
  renderLatestRaceSnapshotSourceValue,
  renderLatestRankingSnapshotSourceValue,
  renderLoadingValue,
} from './ViewerDeferredSourceMetadata'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'
import { buildTourDeferredSourceLinks } from './viewerDeferredLinks'
import {
  type ViewerTourDeferredKind,
  viewerTourDeferredConfigs,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerTourDeferredPage({
  kind,
}: {
  kind: ViewerTourDeferredKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerTourDeferredConfigs[kind]
  const {
    runQuery,
    eventsQuery,
    rankingSnapshotsQuery,
    raceSnapshotsQuery,
    finalsQuery,
    metadata,
    orderedEventCount,
    season,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    activeRunId,
    kind,
    scope: 'tour',
    includeRun: true,
    eventCountMode: 'status-progress',
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only Tour destination requiring an active Viewer run."
      >
        <ViewerEmptyState>
          No data is available for this run yet.
        </ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const nextScheduledEvent = selectNextOrderedEvent(runQuery.data)

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only Tour page using existing active-run metadata only."
    >
      <ViewerDeferredSourceCard
        title={config.title}
        subtitle={
          <>
            No real read model exists yet. This page only shows safe source
            availability from the active Viewer run.
          </>
        }
        isLoadingMetadata={isLoadingMetadata}
        hasMetadataError={hasMetadataError}
        hasAnySourceMetadata={hasAnySourceMetadata}
        metadataItems={[
          { label: 'Active run ID', value: activeRunId },
          {
            label: 'Season',
            value: renderLoadingValue(runQuery.isLoading, season),
          },
          {
            label: 'Completed/persisted event count',
            value: renderLoadingValue(eventsQuery.isLoading, metadata.eventCount),
          },
          {
            label: 'Ordered calendar event count',
            value: renderLoadingValue(runQuery.isLoading, orderedEventCount),
          },
          {
            label: 'Ranking snapshot count',
            value: renderLoadingValue(
              rankingSnapshotsQuery.isLoading,
              metadata.rankingSnapshotCount,
            ),
          },
          {
            label: 'Race snapshot count',
            value: renderLoadingValue(
              raceSnapshotsQuery.isLoading,
              metadata.raceSnapshotCount,
            ),
          },
          {
            label: 'Finals availability',
            value: renderFinalsSourceValue(
              activeRunId,
              metadata.finalsAvailability,
              finalsQuery.isLoading,
            ),
          },
          {
            label: 'Next scheduled event',
            value: nextScheduledEvent ? (
              <Link
                to={viewerPlannedEventPath(
                  activeRunId,
                  nextScheduledEvent.event_id,
                )}
              >
                {nextScheduledEvent.event_id}
              </Link>
            ) : (
              '—'
            ),
          },
          {
            label: 'Latest persisted event',
            value: renderLatestPersistedEventSourceValue(
              activeRunId,
              metadata.latestPersistedEvent,
            ),
          },
          {
            label: 'Latest ranking snapshot',
            value: renderLatestRankingSnapshotSourceValue(
              activeRunId,
              metadata.latestRankingSnapshot,
            ),
          },
          {
            label: 'Latest race snapshot',
            value: renderLatestRaceSnapshotSourceValue(
              activeRunId,
              metadata.latestRaceSnapshot,
            ),
          },
        ]}
        deferredCopy={config.deferredCopy}
        sourceLinks={buildTourDeferredSourceLinks(activeRunId)}
        sourceLinksAriaLabel={`${config.title} source links`}
      />
    </ViewerShellPage>
  )
}
