import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getFinalsSummary,
  getRun,
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
} from '../../../api/client'
import {
  ViewerActiveRunLinks,
  ViewerEmptyState,
} from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'
import { selectNextOrderedEvent } from '../tour/viewerTourDisplay'
import {
  buildDeferredSourceMetadata,
  hasAnyDeferredSourceMetadata,
  renderFinalsSourceValue,
  renderLatestPersistedEventSourceValue,
  renderLatestRaceSnapshotSourceValue,
  renderLatestRankingSnapshotSourceValue,
  renderLoadingValue,
  renderSourceMetadataList,
} from './index'
import {
  viewerRankingDeferredConfigs,
  type ViewerRankingDeferredKind,
} from './viewerDeferredConfigs'

export function ViewerRankingDeferredPage({
  kind,
}: {
  kind: ViewerRankingDeferredKind
}): JSX.Element {
  const config = viewerRankingDeferredConfigs[kind]
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({
    queryKey: ['viewer-ranking-deferred-run', kind, activeRunId],
    queryFn: () => getRun(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const statusQuery = useQuery({
    queryKey: ['viewer-ranking-deferred-status', kind, activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-ranking-deferred-events', kind, activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-ranking-deferred-ranking-snapshots', kind, activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-ranking-deferred-race-snapshots', kind, activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const finalsQuery = useQuery({
    queryKey: ['viewer-ranking-deferred-finals', kind, activeRunId],
    queryFn: () => getFinalsSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
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

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data,
  })
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
  const nextScheduledEvent = selectNextOrderedEvent(runQuery.data)
  const isLoadingMetadata =
    runQuery.isLoading ||
    statusQuery.isLoading ||
    eventsQuery.isLoading ||
    rankingSnapshotsQuery.isLoading ||
    raceSnapshotsQuery.isLoading ||
    finalsQuery.isLoading
  const hasMetadataError =
    runQuery.isError ||
    statusQuery.isError ||
    eventsQuery.isError ||
    rankingSnapshotsQuery.isError ||
    raceSnapshotsQuery.isError ||
    finalsQuery.isError
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(
    metadata,
    orderedEventCount,
  )

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only rankings page using existing active-run metadata only."
    >
      <article
        className="viewer-active-run-card"
        aria-label={`${config.title} active run metadata summary`}
      >
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">
          No real read model exists yet. This page only shows safe source
          availability from the active Viewer run.
        </p>
        {isLoadingMetadata ? (
          <p className="status">Loading active run metadata…</p>
        ) : null}
        {hasMetadataError ? (
          <ViewerEmptyState>
            Some active run metadata is temporarily unavailable.
          </ViewerEmptyState>
        ) : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList([
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
              value: renderLoadingValue(
                eventsQuery.isLoading,
                metadata.eventCount,
              ),
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
          ])}
          {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? (
            <ViewerEmptyState>
              No data is available for this run yet.
            </ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} source links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={[
              {
                label: 'Open active run rankings',
                to: viewerRankingsPath(activeRunId),
              },
              {
                label: 'Open active run race',
                to: viewerRacePath(activeRunId),
              },
              {
                label: 'Open active run tournaments',
                to: viewerTournamentsPath(activeRunId),
              },
              {
                label: 'Open active run calendar',
                to: viewerSeasonCalendarPath(activeRunId),
              },
              { label: 'Open run browser', to: viewerRunsPath() },
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}
