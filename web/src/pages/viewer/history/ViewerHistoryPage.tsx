import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getRun, getRunActivity, getRunStatusSummary, listEvents, listRaceSnapshots, listRankingSnapshots } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerHistoryPath, viewerRaceSnapshotPath, viewerRankingSnapshotPath } from '../../../viewer/viewerRoutes'
import { latestSnapshot } from '../rankings/viewerSnapshotDisplay'
import { buildPlannedEventMap } from '../tour/viewerTourDisplay'
import { selectLatestActivityItem } from './viewerHistoryDisplay'
import { renderActivityItem } from './viewerHistoryRender'
import type { ActivityLinkContext } from './viewerHistoryRender'

export function ViewerHistoryPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const activityQuery = useQuery({ queryKey: ['viewer-history-activity', activeRunId], queryFn: () => getRunActivity(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const runQuery = useQuery({ queryKey: ['viewer-history-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-history-run-status', activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-history-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-history-ranking-snapshots', activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-history-race-snapshots', activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="History" description="Read-only history and season timeline for the selected Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const activityItems = activityQuery.data?.items ?? []
  const latestActivity = selectLatestActivityItem(activityItems)
  const eventCount = eventsQuery.data?.events.length ?? statusQuery.data?.history_counts.events ?? null
  const rankingSnapshotCount = rankingSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = raceSnapshotsQuery.data?.snapshots.length ?? statusQuery.data?.history_counts.race_snapshots ?? null
  const latestRankingSnapshot = latestSnapshot(rankingSnapshotsQuery.data?.snapshots ?? [])
  const latestRaceSnapshot = latestSnapshot(raceSnapshotsQuery.data?.snapshots ?? [])
  const activityLinkContext: ActivityLinkContext = {
    plannedEvents: buildPlannedEventMap(runQuery.data),
    persistedEvents: new Map((eventsQuery.data?.events ?? []).map((event) => [event.event_id, event]))
  }
  const hasAnyMetadata = activityItems.length > 0 || (eventCount ?? 0) > 0 || (rankingSnapshotCount ?? 0) > 0 || (raceSnapshotCount ?? 0) > 0

  return (
    <ViewerShellPage title="History" description="Read-only history using existing active-run activity, event, and publication data only.">
      <article className="viewer-active-run-card" aria-label="History active run metadata summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>History summary</h3>
        {activityQuery.isLoading || runQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading ? <p className="status">Loading active run history metadata…</p> : null}
        {activityQuery.isError || runQuery.isError || statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError ? <ViewerEmptyState>Some active run history metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Activity item count</dt><dd>{activityQuery.isLoading ? 'Loading…' : activityItems.length}</dd></div>
          <div><dt>Latest activity item</dt><dd>{latestActivity ? renderActivityItem(latestActivity, activeRunId, activityLinkContext) : '—'}</dd></div>
          <div><dt>Event count</dt><dd>{eventsQuery.isLoading && eventCount == null ? 'Loading…' : eventCount ?? '—'}</dd></div>
          <div><dt>Ranking snapshot count</dt><dd>{rankingSnapshotsQuery.isLoading && rankingSnapshotCount == null ? 'Loading…' : rankingSnapshotCount ?? '—'}</dd></div>
          <div><dt>Latest ranking snapshot sequence</dt><dd>{latestRankingSnapshot ? <Link to={viewerRankingSnapshotPath(activeRunId, latestRankingSnapshot.snapshot_sequence)}>#{latestRankingSnapshot.snapshot_sequence}</Link> : '—'}</dd></div>
          <div><dt>Race snapshot count</dt><dd>{raceSnapshotsQuery.isLoading && raceSnapshotCount == null ? 'Loading…' : raceSnapshotCount ?? '—'}</dd></div>
          <div><dt>Latest race snapshot sequence</dt><dd>{latestRaceSnapshot ? <Link to={viewerRaceSnapshotPath(activeRunId, latestRaceSnapshot.snapshot_sequence)}>#{latestRaceSnapshot.snapshot_sequence}</Link> : '—'}</dd></div>
        </dl>
        {!activityQuery.isLoading && !runQuery.isLoading && !statusQuery.isLoading && !eventsQuery.isLoading && !rankingSnapshotsQuery.isLoading && !raceSnapshotsQuery.isLoading && !hasAnyMetadata ? (
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerHistoryPath(activeRunId)}>Open active run history</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
