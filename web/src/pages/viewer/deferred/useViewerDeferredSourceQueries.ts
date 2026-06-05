import { useQuery } from '@tanstack/react-query'

import {
  getFinalsSummary,
  getRun,
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
} from '../../../api/client'
import {
  buildDeferredSourceMetadata,
  hasAnyDeferredSourceMetadata,
} from './viewerDeferredSourceMetadata'

export type ViewerDeferredSourceQueryOptions = {
  activeRunId: string | null
  kind: string
  scope: string
  includeRun?: boolean
  includeFinals?: boolean
  eventCountMode?: 'events' | 'status-progress' | 'run-ordered'
}

export function useViewerDeferredSourceQueries({
  activeRunId,
  kind,
  scope,
  includeRun = false,
  includeFinals = true,
  eventCountMode = 'events',
}: ViewerDeferredSourceQueryOptions) {
  const queryEnabled = Boolean(activeRunId)
  const runQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-run`, kind, activeRunId],
    queryFn: () => getRun(activeRunId ?? ''),
    enabled: queryEnabled && includeRun,
    retry: false,
  })
  const statusQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-status`, kind, activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const eventsQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-events`, kind, activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-ranking-snapshots`, kind, activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-race-snapshots`, kind, activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const finalsQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-finals`, kind, activeRunId],
    queryFn: () => getFinalsSummary(activeRunId ?? ''),
    enabled: queryEnabled && includeFinals,
    retry: false,
  })

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data,
    eventCount: resolveDeferredEventCount({
      eventCountMode,
      eventsQuery,
      statusQuery,
      runQuery,
    }),
  })
  const orderedEventCount =
    runQuery.data?.season_state.ordered_events.length ??
    runQuery.data?.run.total_events ??
    statusQuery.data?.progress.total_events ??
    null
  const season =
    runQuery.data?.season_state.season ??
    runQuery.data?.run.season ??
    statusQuery.data?.season ??
    finalsQuery.data?.season ??
    null
  const metadataQueries = includeRun
    ? [
        runQuery,
        statusQuery,
        eventsQuery,
        rankingSnapshotsQuery,
        raceSnapshotsQuery,
        finalsQuery,
      ]
    : [statusQuery, eventsQuery, rankingSnapshotsQuery, raceSnapshotsQuery, finalsQuery]
  const isLoadingMetadata = metadataQueries.some((query) => query.isLoading)
  const hasMetadataError = metadataQueries.some((query) => query.isError)
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(
    metadata,
    includeRun ? orderedEventCount : undefined,
  )

  return {
    runQuery,
    statusQuery,
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
  }
}

type DeferredEventCountQueryArgs = Pick<
  ViewerDeferredSourceQueryOptions,
  'eventCountMode'
> & {
  eventsQuery: { data?: Awaited<ReturnType<typeof listEvents>> }
  statusQuery: { data?: Awaited<ReturnType<typeof getRunStatusSummary>> }
  runQuery: { data?: Awaited<ReturnType<typeof getRun>> }
}

function resolveDeferredEventCount({
  eventCountMode,
  eventsQuery,
  statusQuery,
  runQuery,
}: DeferredEventCountQueryArgs): number | null | undefined {
  if (eventCountMode === 'status-progress') {
    return (
      eventsQuery.data?.events.length ??
      statusQuery.data?.progress.completed_event_count ??
      statusQuery.data?.history_counts.events ??
      null
    )
  }

  if (eventCountMode === 'run-ordered') {
    return runQuery.data?.season_state.ordered_events.length ?? null
  }

  return undefined
}
