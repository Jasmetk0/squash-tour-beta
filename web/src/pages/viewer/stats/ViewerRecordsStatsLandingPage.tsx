import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getFinalsSummary, getRunStatusSummary, listEvents, listRaceSnapshots, listRankingSnapshots } from '../../../api/client'
import type { EventRecord, FinalsSummaryResponse, RaceSnapshot, RankingSnapshot, RunStatusSummary } from '../../../api/types'
import { ViewerActiveRunLinks, ViewerDeferredFeatureList, ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerFinalsPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath
} from '../../../viewer/viewerRoutes'
import { latestSnapshot } from '../rankings/viewerSnapshotDisplay'
import { formatFinalsAvailability, selectLatestPersistedEvent } from '../tour/viewerTourDisplay'
import {
  buildStatsRecordsSourceLinks,
  getStatsRecordsDeferredGroups,
  getStatsRecordsLandingConfig,
  type ViewerRecordsLandingKind
} from './viewerStatsRecordsDisplay'

type DeferredSourceMetadata = {
  eventCount: number | null
  rankingSnapshotCount: number | null
  raceSnapshotCount: number | null
  latestPersistedEvent: EventRecord | null
  latestRankingSnapshot: RankingSnapshot | null
  latestRaceSnapshot: RaceSnapshot | null
  finalsAvailability: string
  hasFinalsAvailability: boolean
}

type DeferredSourceMetadataItem = {
  label: string
  value: ReactNode
}

function resolveFinalsAvailability(finals: FinalsSummaryResponse | undefined, status: RunStatusSummary | undefined): string {
  if (finals) return formatFinalsAvailability(finals)
  if (status?.finals.result_available) return 'Finals result available'
  if (status?.finals.qualification_available) return 'Finals qualification available'
  return 'Finals summary not available yet'
}

function hasAvailableFinals(finalsAvailability: string): boolean {
  return finalsAvailability !== 'Finals summary not available yet' && finalsAvailability !== 'Loading or unavailable'
}

function buildDeferredSourceMetadata(args: {
  events: EventRecord[] | undefined
  rankingSnapshots: RankingSnapshot[] | undefined
  raceSnapshots: RaceSnapshot[] | undefined
  status: RunStatusSummary | undefined
  finals: FinalsSummaryResponse | undefined
}): DeferredSourceMetadata {
  const events = args.events ?? []
  const rankingSnapshots = args.rankingSnapshots ?? []
  const raceSnapshots = args.raceSnapshots ?? []
  const eventCount = args.events?.length ?? args.status?.history_counts.events ?? null
  const rankingSnapshotCount = args.rankingSnapshots?.length ?? args.status?.history_counts.ranking_snapshots ?? null
  const raceSnapshotCount = args.raceSnapshots?.length ?? args.status?.history_counts.race_snapshots ?? null
  const finalsAvailability = resolveFinalsAvailability(args.finals, args.status)

  return {
    eventCount,
    rankingSnapshotCount,
    raceSnapshotCount,
    latestPersistedEvent: selectLatestPersistedEvent(events),
    latestRankingSnapshot: latestSnapshot(rankingSnapshots),
    latestRaceSnapshot: latestSnapshot(raceSnapshots),
    finalsAvailability,
    hasFinalsAvailability: hasAvailableFinals(finalsAvailability)
  }
}

function renderSourceMetadataList(items: DeferredSourceMetadataItem[]): JSX.Element {
  return (
    <dl className="metadata-list">
      {items.map((item) => (
        <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
      ))}
    </dl>
  )
}

function renderLoadingValue(isLoading: boolean, value: ReactNode | null | undefined): ReactNode {
  return isLoading && value == null ? 'Loading…' : value ?? '—'
}

function renderFinalsSourceValue(activeRunId: string, finalsAvailability: string, isLoading: boolean): ReactNode {
  if (isLoading) return 'Loading…'
  return hasAvailableFinals(finalsAvailability) ? <Link to={viewerFinalsPath(activeRunId)}>{finalsAvailability}</Link> : finalsAvailability
}

function renderLatestPersistedEventSourceValue(activeRunId: string, event: EventRecord | null): ReactNode {
  return event?.event_id ? <Link to={viewerTournamentDetailPath(activeRunId, event.event_id)}>{event.event_id}</Link> : '—'
}

function renderLatestRankingSnapshotSourceValue(activeRunId: string, snapshot: RankingSnapshot | null): ReactNode {
  return snapshot ? <Link to={viewerRankingSnapshotPath(activeRunId, snapshot.snapshot_sequence)}>#{snapshot.snapshot_sequence}</Link> : '—'
}

function renderLatestRaceSnapshotSourceValue(activeRunId: string, snapshot: RaceSnapshot | null): ReactNode {
  return snapshot ? <Link to={viewerRaceSnapshotPath(activeRunId, snapshot.snapshot_sequence)}>#{snapshot.snapshot_sequence}</Link> : '—'
}

function commonDeferredSourceMetadataItems(args: {
  activeRunId: string
  metadata: DeferredSourceMetadata
  eventsLoading: boolean
  rankingSnapshotsLoading: boolean
  raceSnapshotsLoading: boolean
  finalsLoading: boolean
}): DeferredSourceMetadataItem[] {
  return [
    { label: 'Active run ID', value: args.activeRunId },
    { label: 'Completed/persisted event count', value: renderLoadingValue(args.eventsLoading, args.metadata.eventCount) },
    { label: 'Ranking snapshot count', value: renderLoadingValue(args.rankingSnapshotsLoading, args.metadata.rankingSnapshotCount) },
    { label: 'Race snapshot count', value: renderLoadingValue(args.raceSnapshotsLoading, args.metadata.raceSnapshotCount) },
    { label: 'Finals availability', value: renderFinalsSourceValue(args.activeRunId, args.metadata.finalsAvailability, args.finalsLoading) },
    { label: 'Latest persisted event', value: renderLatestPersistedEventSourceValue(args.activeRunId, args.metadata.latestPersistedEvent) },
    { label: 'Latest ranking snapshot', value: renderLatestRankingSnapshotSourceValue(args.activeRunId, args.metadata.latestRankingSnapshot) },
    { label: 'Latest race snapshot', value: renderLatestRaceSnapshotSourceValue(args.activeRunId, args.metadata.latestRaceSnapshot) }
  ]
}

function hasAnyDeferredSourceMetadata(metadata: DeferredSourceMetadata): boolean {
  return (metadata.eventCount ?? 0) > 0 || (metadata.rankingSnapshotCount ?? 0) > 0 || (metadata.raceSnapshotCount ?? 0) > 0 || metadata.hasFinalsAvailability
}

export function ViewerRecordsStatsLandingPage({ kind }: { kind: ViewerRecordsLandingKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const statusQuery = useQuery({ queryKey: ['viewer-records-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-records-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-records-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-records-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-records-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const config = getStatsRecordsLandingConfig(kind)

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description={config.shellDescription}>
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data
  })
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata)
  const deferredGroups = getStatsRecordsDeferredGroups(kind)

  return (
    <ViewerShellPage title={config.title} description={config.activeShellDescription}>
      <article className="viewer-active-run-card" aria-label={`${config.title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.overviewTitle}</h3>
        <p className="subtitle">{config.overviewDescription}</p>
        {statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading ? <p className="status">Loading active run metadata…</p> : null}
        {statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList(commonDeferredSourceMetadataItems({
            activeRunId,
            metadata,
            eventsLoading: eventsQuery.isLoading,
            rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
            raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
            finalsLoading: finalsQuery.isLoading
          }))}
          {!statusQuery.isLoading && !eventsQuery.isLoading && !rankingSnapshotsQuery.isLoading && !raceSnapshotsQuery.isLoading && !finalsQuery.isLoading && !hasAnySourceMetadata ? (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={`${config.title} deferred groups`}>
          <ViewerDeferredFeatureList
            title={config.deferredGroupsTitle}
            label={config.deferredGroupsLabel}
            features={deferredGroups}
          />
        </section>
        <section aria-label={`${config.title} links`}>
          <h3>Links</h3>
          <ViewerActiveRunLinks
            links={buildStatsRecordsSourceLinks({
              activeRunId,
              viewerRunsPath,
              viewerTournamentsPath,
              viewerRankingsPath,
              viewerRacePath,
              viewerFinalsPath
            })}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}
