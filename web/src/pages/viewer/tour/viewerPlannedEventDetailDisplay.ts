import type { EventRecord } from '../../../api/types'
import {
  buildEventDetailLinks,
  type PlannedEventContext,
  type ViewerEventDetailLink,
  type ViewerEventMetadataItem
} from './viewerEventDetailDisplay'

function displayValue(value: string | number | null | undefined): string | number {
  return value ?? '—'
}

export function resolvePlannedEventStatusLabel({
  eventId,
  planIndex,
  nextEventIndex,
  completedEventIds = []
}: {
  eventId: string
  planIndex: number
  nextEventIndex: number
  completedEventIds?: Iterable<string>
}): string {
  const completed = new Set(completedEventIds)
  if (completed.has(eventId)) return 'Completed'
  if (planIndex === nextEventIndex) return 'Current/next'
  if (planIndex > nextEventIndex) return 'Upcoming'
  return 'Planned'
}

export function buildPlannedEventDetailMetadataItems({
  runId,
  plannedEvent,
  orderedEventCount,
  nextEventIndex,
  completedEventIds = [],
  persistedEvent
}: {
  runId: string
  plannedEvent: PlannedEventContext
  orderedEventCount?: number
  nextEventIndex: number
  completedEventIds?: Iterable<string>
  persistedEvent?: EventRecord | null
}): ViewerEventMetadataItem[] {
  const persistedWeek = persistedEvent?.week ?? null

  return [
    { label: 'Run ID', value: runId || 'unknown' },
    { label: 'Event ID', value: plannedEvent.event_id },
    { label: 'Season', value: plannedEvent.season },
    { label: 'Week', value: `W${plannedEvent.week}` },
    { label: 'Tour', value: plannedEvent.tour },
    { label: 'Category', value: plannedEvent.category },
    { label: 'Template ID', value: plannedEvent.template_id },
    { label: 'Plan index', value: plannedEvent.planIndex },
    {
      label: 'Plan position',
      value: orderedEventCount == null ? plannedEvent.planIndex + 1 : `${plannedEvent.planIndex + 1} of ${orderedEventCount}`
    },
    { label: 'Current next event index', value: nextEventIndex },
    {
      label: 'Planned event status',
      value: resolvePlannedEventStatusLabel({
        eventId: plannedEvent.event_id,
        planIndex: plannedEvent.planIndex,
        nextEventIndex,
        completedEventIds
      })
    },
    { label: 'Persisted event record', value: persistedEvent ? 'Available' : 'Not available' },
    { label: 'Persisted event sequence', value: displayValue(persistedEvent?.event_sequence) },
    { label: 'Persisted event week', value: persistedWeek == null ? '—' : `W${persistedWeek}` }
  ]
}

export function buildPlannedEventContextLinks({
  runId,
  eventId,
  week,
  hasPersisted
}: {
  runId: string
  eventId: string
  week?: number | null
  hasPersisted?: boolean
}): ViewerEventDetailLink[] {
  return buildEventDetailLinks({
    runId,
    eventId,
    week,
    hasPlanned: true,
    hasPersisted
  })
}
