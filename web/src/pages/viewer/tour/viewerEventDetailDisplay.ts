import type { EventRecord, RaceSnapshot, RankingSnapshot, SeasonStateResponse } from '../../../api/types'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingsPath,
  viewerRankingSnapshotPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath,
  viewerWeekDetailPath
} from '../../../viewer/viewerRoutes'

export type ViewerEventMetadataItem = {
  label: string
  value: string | number
}

export type ViewerEventDetailLink = {
  label: string
  href: string
}

export type PlannedEventContext = SeasonStateResponse['season_state']['ordered_events'][number] & {
  planIndex: number
}

function displayValue(value: string | number | null | undefined): string | number {
  return value ?? '—'
}

export function findPlannedEventById(
  seasonState: SeasonStateResponse['season_state'] | null | undefined,
  eventId: string
): PlannedEventContext | null {
  const matchIndex = seasonState?.ordered_events.findIndex((event) => event.event_id === eventId) ?? -1
  if (matchIndex < 0 || !seasonState) return null

  return { ...seasonState.ordered_events[matchIndex], planIndex: matchIndex }
}

export function findPersistedEventById(events: EventRecord[] | null | undefined, eventId: string): EventRecord | null {
  return events?.find((event) => event.event_id === eventId) ?? null
}

export function buildPlannedEventMetadataItems(
  event: PlannedEventContext,
  runId: string,
  orderedEventCount?: number
): ViewerEventMetadataItem[] {
  return [
    { label: 'Run ID', value: runId || 'unknown' },
    { label: 'Event ID', value: event.event_id },
    { label: 'Season', value: event.season },
    { label: 'Week', value: `W${event.week}` },
    { label: 'Tour', value: event.tour },
    { label: 'Category', value: event.category },
    { label: 'Template ID', value: event.template_id },
    { label: 'Plan index', value: event.planIndex },
    {
      label: 'Plan position',
      value: orderedEventCount == null ? event.planIndex + 1 : `${event.planIndex + 1} of ${orderedEventCount}`
    }
  ]
}

export function buildPersistedEventMetadataItems(
  event: EventRecord,
  runId: string,
  planned?: PlannedEventContext | null
): ViewerEventMetadataItem[] {
  const week = event.week ?? planned?.week ?? null

  return [
    { label: 'Run ID', value: runId || 'unknown' },
    { label: 'Event ID', value: event.event_id },
    { label: 'Event sequence', value: displayValue(event.event_sequence) },
    { label: 'Season', value: displayValue(event.season ?? planned?.season) },
    { label: 'Week', value: week == null ? '—' : `W${week}` },
    { label: 'Tour', value: displayValue(planned?.tour) },
    { label: 'Category', value: displayValue(planned?.category) },
    { label: 'Template ID', value: displayValue(planned?.template_id ?? event.template_id) },
    { label: 'Planned event match', value: planned ? 'Available' : 'Not available' },
    { label: 'Tournament result payload', value: event.tournament_result ? 'Available' : 'Not available' }
  ]
}

export function snapshotsForSourceEvent<T extends RankingSnapshot | RaceSnapshot>(snapshots: T[] | null | undefined, eventId: string): T[] {
  return (snapshots ?? []).filter((snapshot) => snapshot.source_event_id === eventId)
}

export function buildEventDetailLinks({
  runId,
  eventId,
  week,
  hasPlanned,
  hasPersisted,
  rankingSnapshotSequences = [],
  raceSnapshotSequences = []
}: {
  runId: string
  eventId: string
  week?: number | null
  hasPlanned?: boolean
  hasPersisted?: boolean
  rankingSnapshotSequences?: number[]
  raceSnapshotSequences?: number[]
}): ViewerEventDetailLink[] {
  const links: ViewerEventDetailLink[] = [
    { label: 'Run browser', href: viewerRunsPath() },
    { label: 'Tournament list', href: viewerTournamentsPath(runId) },
    { label: 'Season calendar', href: viewerSeasonCalendarPath(runId) }
  ]

  if (hasPlanned) {
    links.push({ label: 'Planned calendar event', href: viewerPlannedEventPath(runId, eventId) })
  }

  if (hasPersisted) {
    links.push({ label: 'Tournament detail', href: viewerTournamentDetailPath(runId, eventId) })
  }

  if (week != null) {
    links.push({ label: `Week W${week}`, href: viewerWeekDetailPath(runId, week) })
  }

  links.push({ label: 'Ranking snapshots', href: viewerRankingsPath(runId) })
  links.push({ label: 'Race snapshots', href: viewerRacePath(runId) })

  rankingSnapshotSequences.forEach((sequence) => {
    links.push({ label: `Ranking publication #${sequence}`, href: viewerRankingSnapshotPath(runId, sequence) })
  })

  raceSnapshotSequences.forEach((sequence) => {
    links.push({ label: `Race publication #${sequence}`, href: viewerRaceSnapshotPath(runId, sequence) })
  })

  return links
}
