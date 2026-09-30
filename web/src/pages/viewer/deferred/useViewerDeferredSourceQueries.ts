import { useQuery } from '@tanstack/react-query'

import {
  getViewerFinalsRace,
  getViewerRunCalendar,
  getViewerTournamentHistory,
  listViewerOfficialRankingHistory,
} from '../../../api/client'
import type {
  ViewerCalendarEvent,
  ViewerFinalsRacePublication,
  ViewerOfficialRankingHistoryItem,
  ViewerTournamentHistoryItem,
} from '../../../api/types'

export type ViewerDeferredSourceQueryOptions = {
  productRunId: string | null
  kind: string
  scope: string
}

export type ViewerDeferredCanonicalMetadata = {
  viewerBranchId: string | null
  seasonCount: number
  calendarEventCount: number
  completedTournamentCount: number
  rankingPublicationCount: number
  finalsRacePublicationCount: number
  latestCompletedTournament: ViewerTournamentHistoryItem | null
  latestRankingPublication: ViewerOfficialRankingHistoryItem | null
  latestFinalsRacePublication: ViewerFinalsRacePublication | null
  nextCalendarEvent: ViewerCalendarEvent | null
}

function firstPendingCalendarEvent(events: ViewerCalendarEvent[]): ViewerCalendarEvent | null {
  return (
    events.find((event) => event.status === 'active') ??
    events.find((event) => event.status === 'planned' || event.status === 'scheduled') ??
    null
  )
}

export function useViewerDeferredSourceQueries({
  productRunId,
  kind,
  scope,
}: ViewerDeferredSourceQueryOptions) {
  const enabled = Boolean(productRunId)

  const calendarQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-calendar`, kind, productRunId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled,
    retry: false,
  })
  const tournamentsQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-tournaments`, kind, productRunId],
    queryFn: () => getViewerTournamentHistory(productRunId ?? ''),
    enabled,
    retry: false,
  })
  const rankingsQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-rankings`, kind, productRunId],
    queryFn: () => listViewerOfficialRankingHistory(productRunId ?? ''),
    enabled,
    retry: false,
  })
  const finalsRaceQuery = useQuery({
    queryKey: [`viewer-${scope}-deferred-finals-race`, kind, productRunId],
    queryFn: () => getViewerFinalsRace(productRunId ?? ''),
    enabled,
    retry: false,
  })

  const calendarEvents = (calendarQuery.data?.seasons ?? []).flatMap((season) => season.events)
  const completedTournaments = (tournamentsQuery.data?.tournaments ?? []).filter(
    (event) => event.result_published,
  )
  const rankingPublications = rankingsQuery.data?.publications ?? []
  const finalsRacePublications = finalsRaceQuery.data?.publications ?? []

  const metadata: ViewerDeferredCanonicalMetadata = {
    viewerBranchId:
      calendarQuery.data?.viewer_branch_id ??
      tournamentsQuery.data?.viewer_branch_id ??
      rankingsQuery.data?.viewer_branch_id ??
      finalsRaceQuery.data?.viewer_branch_id ??
      null,
    seasonCount: calendarQuery.data?.season_count ?? 0,
    calendarEventCount: calendarQuery.data?.event_count ?? 0,
    completedTournamentCount: completedTournaments.length,
    rankingPublicationCount: rankingsQuery.data?.publication_count ?? rankingPublications.length,
    finalsRacePublicationCount: finalsRacePublications.length,
    latestCompletedTournament:
      completedTournaments.length > 0 ? completedTournaments[completedTournaments.length - 1] : null,
    latestRankingPublication:
      rankingPublications.length > 0 ? rankingPublications[rankingPublications.length - 1] : null,
    latestFinalsRacePublication:
      finalsRacePublications.length > 0 ? finalsRacePublications[finalsRacePublications.length - 1] : null,
    nextCalendarEvent: firstPendingCalendarEvent(calendarEvents),
  }

  const queries = [calendarQuery, tournamentsQuery, rankingsQuery, finalsRaceQuery]
  const isLoadingMetadata = enabled && queries.some((query) => query.isLoading)
  const hasMetadataError = enabled && queries.some((query) => query.isError)
  const hasAnySourceMetadata =
    metadata.calendarEventCount > 0 ||
    metadata.completedTournamentCount > 0 ||
    metadata.rankingPublicationCount > 0 ||
    metadata.finalsRacePublicationCount > 0

  return {
    calendarQuery,
    tournamentsQuery,
    rankingsQuery,
    finalsRaceQuery,
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  }
}
