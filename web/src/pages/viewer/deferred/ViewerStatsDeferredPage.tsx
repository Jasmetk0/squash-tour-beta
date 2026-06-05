import { useQuery } from '@tanstack/react-query'

import {
  getFinalsSummary,
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
} from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTopRecordsPath,
  viewerTopStatsPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'
import {
  commonDeferredSourceMetadataItems,
  renderDeferredSourceLinks,
  renderSourceMetadataList,
} from './ViewerDeferredSourceMetadata'
import {
  buildDeferredSourceMetadata,
  hasAnyDeferredSourceMetadata,
} from './viewerDeferredSourceMetadata'
import {
  type ViewerStatsDeferredKind,
  viewerStatsDeferredConfigs,
} from './viewerDeferredConfigs'

export function ViewerStatsDeferredPage({
  kind,
}: {
  kind: ViewerStatsDeferredKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerStatsDeferredConfigs[kind]
  const statusQuery = useQuery({
    queryKey: ['viewer-stats-deferred-status', kind, activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-stats-deferred-events', kind, activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-stats-deferred-ranking-snapshots', kind, activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-stats-deferred-race-snapshots', kind, activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const finalsQuery = useQuery({
    queryKey: ['viewer-stats-deferred-finals', kind, activeRunId],
    queryFn: () => getFinalsSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
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

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data,
  })
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata)
  const isLoadingMetadata =
    statusQuery.isLoading ||
    eventsQuery.isLoading ||
    rankingSnapshotsQuery.isLoading ||
    raceSnapshotsQuery.isLoading ||
    finalsQuery.isLoading
  const hasMetadataError =
    statusQuery.isError ||
    eventsQuery.isError ||
    rankingSnapshotsQuery.isError ||
    raceSnapshotsQuery.isError ||
    finalsQuery.isError

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only stats and records page using existing active-run metadata only."
    >
      <article
        className="viewer-active-run-card"
        aria-label={`${config.title} active run metadata summary`}
      >
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">
          No records or statistics are calculated here yet. This page only shows
          safe source availability from the active Viewer run.
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
          {renderSourceMetadataList(
            commonDeferredSourceMetadataItems({
              activeRunId,
              metadata,
              eventsLoading: eventsQuery.isLoading,
              rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
              raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
              finalsLoading: finalsQuery.isLoading,
            }),
          )}
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
        <section aria-label={`${config.title} links`}>
          <h3>Source links</h3>
          {renderDeferredSourceLinks([
            { label: 'Open records', to: viewerTopRecordsPath() },
            { label: 'Open stats', to: viewerTopStatsPath() },
            {
              label: 'Open active run tournaments',
              to: viewerTournamentsPath(activeRunId),
            },
            {
              label: 'Open active run rankings',
              to: viewerRankingsPath(activeRunId),
            },
            { label: 'Open active run race', to: viewerRacePath(activeRunId) },
            { label: 'Open run browser', to: viewerRunsPath() },
          ])}
        </section>
      </article>
    </ViewerShellPage>
  )
}
