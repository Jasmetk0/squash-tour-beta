import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import type { EventRecord, RaceSnapshot, RankingSnapshot } from '../../../api/types'
import { ViewerActiveRunLinks } from '../../../components/viewer/ViewerLandingComponents'
import {
  viewerFinalsPath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerTournamentDetailPath
} from '../../../viewer/viewerRoutes'
import type { DeferredSourceMetadata } from './viewerDeferredSourceMetadata'
import { hasAvailableFinals } from './viewerDeferredSourceMetadata'

export type DeferredSourceMetadataItem = {
  label: string
  value: ReactNode
}

export function renderSourceMetadataList(items: DeferredSourceMetadataItem[]): JSX.Element {
  return (
    <dl className="metadata-list">
      {items.map((item) => (
        <div key={item.label}><dt>{item.label}</dt><dd>{item.value}</dd></div>
      ))}
    </dl>
  )
}

export function renderLoadingValue(isLoading: boolean, value: ReactNode | null | undefined): ReactNode {
  return isLoading && value == null ? 'Loading…' : value ?? '—'
}

export function renderFinalsSourceValue(activeRunId: string, finalsAvailability: string, isLoading: boolean): ReactNode {
  if (isLoading) return 'Loading…'
  return hasAvailableFinals(finalsAvailability) ? <Link to={viewerFinalsPath(activeRunId)}>{finalsAvailability}</Link> : finalsAvailability
}

export function renderLatestPersistedEventSourceValue(activeRunId: string, event: EventRecord | null): ReactNode {
  return event?.event_id ? <Link to={viewerTournamentDetailPath(activeRunId, event.event_id)}>{event.event_id}</Link> : '—'
}

export function renderLatestRankingSnapshotSourceValue(activeRunId: string, snapshot: RankingSnapshot | null): ReactNode {
  return snapshot ? <Link to={viewerRankingSnapshotPath(activeRunId, snapshot.snapshot_sequence)}>#{snapshot.snapshot_sequence}</Link> : '—'
}

export function renderLatestRaceSnapshotSourceValue(activeRunId: string, snapshot: RaceSnapshot | null): ReactNode {
  return snapshot ? <Link to={viewerRaceSnapshotPath(activeRunId, snapshot.snapshot_sequence)}>#{snapshot.snapshot_sequence}</Link> : '—'
}

export function commonDeferredSourceMetadataItems(args: {
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

export function renderDeferredSourceLinks(links: { label: string; to: string }[]): JSX.Element {
  return <ViewerActiveRunLinks links={links} />
}
