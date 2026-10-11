import type { SeasonStateResponse } from '../api/types'

export type PlannedEventStatus = 'Completed' | 'Next' | 'Upcoming'
export type WeekStatus = 'Completed week' | 'Current week' | 'Upcoming week'

export function getPlannedEventStatus({
  index,
  nextEventIndex,
  completedEventIds,
  eventId
}: {
  index: number
  nextEventIndex: number
  completedEventIds: Set<string>
  eventId: string
}): PlannedEventStatus {
  if (completedEventIds.has(eventId)) return 'Completed'
  if (index === nextEventIndex) return 'Next'
  return 'Upcoming'
}

export function getWeeksInSeasonOrder(
  orderedEvents: SeasonStateResponse['season_state']['ordered_events']
): number[] {
  const seen = new Set<number>()
  const weeks: number[] = []

  for (const event of orderedEvents) {
    if (!seen.has(event.week)) {
      weeks.push(event.week)
      seen.add(event.week)
    }
  }

  return weeks
}

export function getWeekStatus(statuses: PlannedEventStatus[]): WeekStatus {
  if (statuses.every((status) => status === 'Completed')) return 'Completed week'
  if (statuses.some((status) => status === 'Next')) return 'Current week'
  return 'Upcoming week'
}
