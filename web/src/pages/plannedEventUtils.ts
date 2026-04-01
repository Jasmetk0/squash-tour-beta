export type PlannedEventStatus = 'Completed' | 'Next' | 'Upcoming'

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
