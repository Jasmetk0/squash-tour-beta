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
import { buildRankingDeferredSourceLinks } from './viewerDeferredLinks'
import { hasAnyDeferredSourceMetadata } from './viewerDeferredSourceMetadata'
import {
  viewerRankingDeferredConfigs,
  type ViewerRankingDeferredKind,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerRankingDeferredPage({
  kind,
}: {
  kind: ViewerRankingDeferredKind
}): JSX.Element {
  const config = viewerRankingDeferredConfigs[kind]
  const activeRunId = useActiveViewerRunId()
  const {
    runQuery,
    statusQuery,
    eventsQuery,
    rankingSnapshotsQuery,
    raceSnapshotsQuery,
    finalsQuery,
    metadata,
    isLoadingMetadata,
    hasMetadataError,
  } = useViewerDeferredSourceQueries({
    activeRunId,
    kind,
    scope: 'ranking',
    includeRun: true,
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only rankings destination requiring an active Viewer run."
      >
        <ViewerEmptyState>
          No data is available for this run yet.
        </ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const orderedEventCount =
    runQuery.data?.season_state.ordered_events.length ??
    statusQuery.data?.progress.total_events ??
    runQuery.data?.run.total_events ??
    null
  const season =
    statusQuery.data?.season ??
    runQuery.data?.season_state.season ??
    runQuery.data?.run.season ??
    finalsQuery.data?.season ??
    null
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(
    metadata,
    orderedEventCount,
  )
  const nextScheduledEvent = selectNextOrderedEvent(runQuery.data)

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only rankings page using existing active-run metadata only."
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
            label: 'Completed/persisted event count',
            value: renderLoadingValue(eventsQuery.isLoading, metadata.eventCount),
          },
          {
            label: 'Ordered calendar event count',
            value: renderLoadingValue(runQuery.isLoading, orderedEventCount),
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
          {
            label: 'Latest persisted event',
            value: renderLatestPersistedEventSourceValue(
              activeRunId,
              metadata.latestPersistedEvent,
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
        ]}
        deferredCopy={config.deferredCopy}
        sourceLinks={buildRankingDeferredSourceLinks(activeRunId)}
        sourceLinksAriaLabel={`${config.title} source links`}
      />
    </ViewerShellPage>
  )
}
