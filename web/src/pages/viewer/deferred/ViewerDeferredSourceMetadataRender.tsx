import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { ViewerActiveRunLinks } from '../../../components/viewer/ViewerLandingComponents'
import {
  viewerFinalsPath,
  viewerRacePath,
  viewerRankingSnapshotPath,
  viewerTournamentDetailPath,
} from '../../../viewer/viewerRoutes'
import type { ViewerDeferredCanonicalMetadata } from './useViewerDeferredSourceQueries'

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

export function renderLatestCompletedTournament(
  productRunId: string,
  metadata: ViewerDeferredCanonicalMetadata,
): ReactNode {
  const event = metadata.latestCompletedTournament
  return event ? (
    <Link to={viewerTournamentDetailPath(productRunId, event.event_id)}>
      {event.event_name || event.event_id}
    </Link>
  ) : '—'
}

export function renderLatestRankingPublication(
  productRunId: string,
  metadata: ViewerDeferredCanonicalMetadata,
): ReactNode {
  const publication = metadata.latestRankingPublication
  return publication ? (
    <Link to={viewerRankingSnapshotPath(productRunId, publication.week_ordinal)}>
      Season {publication.season_index} W{publication.week} · #{publication.week_ordinal}
    </Link>
  ) : '—'
}

export function renderLatestFinalsRacePublication(
  productRunId: string,
  metadata: ViewerDeferredCanonicalMetadata,
): ReactNode {
  const publication = metadata.latestFinalsRacePublication
  return publication ? (
    <Link to={viewerRacePath(productRunId)}>
      Target season {publication.target_season_index} · W{publication.cutoff_week}
    </Link>
  ) : '—'
}

export function renderFinalsAvailability(
  productRunId: string,
  metadata: ViewerDeferredCanonicalMetadata,
): ReactNode {
  const publication = metadata.latestFinalsRacePublication
  if (!publication) return 'Not published yet'
  const label = publication.selection_published
    ? publication.finals_event_id
      ? 'Finals selection published'
      : 'Finals selection published; event pending'
    : 'Finals Race published; selection pending'
  return <Link to={viewerFinalsPath(productRunId)}>{label}</Link>
}

export function commonDeferredSourceMetadataItems(args: {
  productRunId: string
  metadata: ViewerDeferredCanonicalMetadata
  isLoading: boolean
}): DeferredSourceMetadataItem[] {
  return [
    { label: 'Product Run', value: args.productRunId },
    { label: 'Viewer Branch', value: renderLoadingValue(args.isLoading, args.metadata.viewerBranchId) },
    { label: 'Saved seasons', value: renderLoadingValue(args.isLoading, args.metadata.seasonCount) },
    { label: 'Saved Calendar events', value: renderLoadingValue(args.isLoading, args.metadata.calendarEventCount) },
    { label: 'Completed tournaments', value: renderLoadingValue(args.isLoading, args.metadata.completedTournamentCount) },
    { label: 'Official Ranking publications', value: renderLoadingValue(args.isLoading, args.metadata.rankingPublicationCount) },
    { label: 'Finals Race publications', value: renderLoadingValue(args.isLoading, args.metadata.finalsRacePublicationCount) },
    { label: 'Finals availability', value: args.isLoading ? 'Loading…' : renderFinalsAvailability(args.productRunId, args.metadata) },
    { label: 'Latest completed tournament', value: args.isLoading ? 'Loading…' : renderLatestCompletedTournament(args.productRunId, args.metadata) },
    { label: 'Latest Official Ranking', value: args.isLoading ? 'Loading…' : renderLatestRankingPublication(args.productRunId, args.metadata) },
    { label: 'Latest Finals Race', value: args.isLoading ? 'Loading…' : renderLatestFinalsRacePublication(args.productRunId, args.metadata) },
  ]
}

export function renderDeferredSourceLinks(links: { label: string; to: string }[]): JSX.Element {
  return <ViewerActiveRunLinks links={links} />
}
