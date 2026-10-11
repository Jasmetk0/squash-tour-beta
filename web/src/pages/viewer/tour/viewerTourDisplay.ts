import type { EventRecord, FinalsSummaryResponse, SeasonStateResponse } from '../../../api/types'

export type OrderedSeasonEvent = SeasonStateResponse['season_state']['ordered_events'][number]

export function buildPlannedEventMap(runData: SeasonStateResponse | undefined): Map<string, OrderedSeasonEvent> {
  const map = new Map<string, OrderedSeasonEvent>()
  ;(runData?.season_state.ordered_events ?? []).forEach((event) => {
    map.set(event.event_id, event)
  })
  return map
}

export function selectNextOrderedEvent(runData: SeasonStateResponse | undefined): OrderedSeasonEvent | null {
  const orderedEvents = runData?.season_state.ordered_events ?? []
  const nextIndex = runData?.season_state.next_event_index ?? runData?.run.next_event_index ?? null
  return nextIndex != null ? orderedEvents[nextIndex] ?? null : null
}

export function selectLatestPersistedEvent(events: EventRecord[]): EventRecord | null {
  return [...events].sort((a, b) => b.event_sequence - a.event_sequence)[0] ?? null
}

export function formatFinalsAvailability(summary: FinalsSummaryResponse | undefined): string {
  if (!summary) return 'Loading or unavailable'
  if (summary.result) return 'Finals result available'
  if (summary.qualification) return 'Finals qualification available'
  return 'Finals summary not available yet'
}
