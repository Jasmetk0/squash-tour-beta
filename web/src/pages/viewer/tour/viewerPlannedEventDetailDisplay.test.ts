import { describe, expect, it } from 'vitest'

import type { EventRecord, SeasonStateResponse } from '../../../api/types'
import { findPersistedEventById, findPlannedEventById } from './viewerEventDetailDisplay'
import {
  buildPlannedEventContextLinks,
  buildPlannedEventDetailMetadataItems,
  resolvePlannedEventStatusLabel
} from './viewerPlannedEventDetailDisplay'

const seasonState: SeasonStateResponse['season_state'] = {
  season: 2028,
  next_event_index: 1,
  completed_event_ids: ['EVENT/1'],
  ordered_events: [
    { event_id: 'EVENT/1', season: 2028, week: 5, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
    { event_id: 'EVENT/10', season: 2028, week: 6, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
  ]
}

const persistedEvent: EventRecord = {
  event_sequence: 7,
  event_id: 'EVENT/1',
  season: 2028,
  week: 5,
  template_id: 'WT-PLAT',
  tournament_result: { hidden_payload: true }
}

describe('viewerPlannedEventDetailDisplay', () => {
  it('handles missing ordered_events without throwing', () => {
    expect(findPlannedEventById({ ...seasonState, ordered_events: [] }, 'EVENT/1')).toBeNull()
    expect(findPlannedEventById(undefined, 'EVENT/1')).toBeNull()
  })

  it('matches exact planned and persisted event IDs only', () => {
    expect(findPlannedEventById(seasonState, 'EVENT/1')).toMatchObject({ event_id: 'EVENT/1', planIndex: 0 })
    expect(findPlannedEventById(seasonState, 'EVENT')).toBeNull()
    expect(findPersistedEventById([persistedEvent, { ...persistedEvent, event_id: 'EVENT/10' }], 'EVENT/1')).toBe(persistedEvent)
  })

  it('builds safe planned event metadata with persisted source context only', () => {
    const planned = findPlannedEventById(seasonState, 'EVENT/1')

    expect(planned).not.toBeNull()
    expect(
      buildPlannedEventDetailMetadataItems({
        runId: 'run alpha',
        plannedEvent: planned!,
        orderedEventCount: 2,
        nextEventIndex: 1,
        completedEventIds: seasonState.completed_event_ids,
        persistedEvent
      })
    ).toEqual([
      { label: 'Run ID', value: 'run alpha' },
      { label: 'Event ID', value: 'EVENT/1' },
      { label: 'Season', value: 2028 },
      { label: 'Week', value: 'W5' },
      { label: 'Tour', value: 'World Tour' },
      { label: 'Category', value: 'Platinum' },
      { label: 'Template ID', value: 'WT-PLAT' },
      { label: 'Plan index', value: 0 },
      { label: 'Plan position', value: '1 of 2' },
      { label: 'Current next event index', value: 1 },
      { label: 'Planned event status', value: 'Completed' },
      { label: 'Persisted event record', value: 'Available' },
      { label: 'Persisted event sequence', value: 7 },
      { label: 'Persisted event week', value: 'W5' }
    ])
  })

  it('shows conservative persisted fallbacks when no persisted event matches', () => {
    const planned = findPlannedEventById(seasonState, 'EVENT/10')

    expect(planned).not.toBeNull()
    expect(
      buildPlannedEventDetailMetadataItems({
        runId: 'run alpha',
        plannedEvent: planned!,
        nextEventIndex: 1
      }).slice(-3)
    ).toEqual([
      { label: 'Persisted event record', value: 'Not available' },
      { label: 'Persisted event sequence', value: '—' },
      { label: 'Persisted event week', value: '—' }
    ])
  })

  it('resolves planned event status labels from completed IDs and next index', () => {
    expect(resolvePlannedEventStatusLabel({ eventId: 'A', planIndex: 0, nextEventIndex: 1, completedEventIds: ['A'] })).toBe('Completed')
    expect(resolvePlannedEventStatusLabel({ eventId: 'B', planIndex: 1, nextEventIndex: 1 })).toBe('Current/next')
    expect(resolvePlannedEventStatusLabel({ eventId: 'C', planIndex: 2, nextEventIndex: 1 })).toBe('Upcoming')
    expect(resolvePlannedEventStatusLabel({ eventId: 'D', planIndex: 0, nextEventIndex: 1 })).toBe('Planned')
  })

  it('builds encoded context links in stable order', () => {
    expect(buildPlannedEventContextLinks({ runId: 'run alpha', eventId: 'EVENT/1', week: 5, hasPersisted: true })).toEqual([
      { label: 'Run browser', href: '/viewer/runs' },
      { label: 'Tournament list', href: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Season calendar', href: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Planned calendar event', href: '/viewer/runs/run%20alpha/calendar/EVENT%2F1' },
      { label: 'Tournament detail', href: '/viewer/runs/run%20alpha/tournaments/EVENT%2F1' },
      { label: 'Week W5', href: '/viewer/runs/run%20alpha/weeks/5' },
      { label: 'Ranking snapshots', href: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Race snapshots', href: '/viewer/runs/run%20alpha/race' }
    ])
  })

  it('omits week and tournament links when no planned week or persisted event is available', () => {
    expect(buildPlannedEventContextLinks({ runId: 'run alpha', eventId: 'EVENT/1', hasPersisted: false })).toEqual([
      { label: 'Run browser', href: '/viewer/runs' },
      { label: 'Tournament list', href: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Season calendar', href: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Planned calendar event', href: '/viewer/runs/run%20alpha/calendar/EVENT%2F1' },
      { label: 'Ranking snapshots', href: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Race snapshots', href: '/viewer/runs/run%20alpha/race' }
    ])
  })

  it('encodes special characters in planned context links', () => {
    expect(buildPlannedEventContextLinks({ runId: 'run/alpha #1', eventId: 'EVENT ?/1&2', week: 7, hasPersisted: true })).toEqual([
      { label: 'Run browser', href: '/viewer/runs' },
      { label: 'Tournament list', href: '/viewer/runs/run%2Falpha%20%231/tournaments' },
      { label: 'Season calendar', href: '/viewer/runs/run%2Falpha%20%231/calendar' },
      { label: 'Planned calendar event', href: '/viewer/runs/run%2Falpha%20%231/calendar/EVENT%20%3F%2F1%262' },
      { label: 'Tournament detail', href: '/viewer/runs/run%2Falpha%20%231/tournaments/EVENT%20%3F%2F1%262' },
      { label: 'Week W7', href: '/viewer/runs/run%2Falpha%20%231/weeks/7' },
      { label: 'Ranking snapshots', href: '/viewer/runs/run%2Falpha%20%231/rankings' },
      { label: 'Race snapshots', href: '/viewer/runs/run%2Falpha%20%231/race' }
    ])
  })

  it('shows numeric plan position when ordered event count is not provided', () => {
    const planned = findPlannedEventById(seasonState, 'EVENT/10')

    expect(planned).not.toBeNull()
    expect(
      buildPlannedEventDetailMetadataItems({
        runId: 'run alpha',
        plannedEvent: planned!,
        nextEventIndex: 1
      }).find((item) => item.label === 'Plan position')
    ).toEqual({ label: 'Plan position', value: 2 })
  })

  it('uses persisted event fallbacks for null sequence and week', () => {
    const planned = findPlannedEventById(seasonState, 'EVENT/1')
    const persistedWithNulls = { ...persistedEvent, event_sequence: null, week: null } as unknown as EventRecord

    expect(planned).not.toBeNull()
    expect(
      buildPlannedEventDetailMetadataItems({
        runId: 'run alpha',
        plannedEvent: planned!,
        nextEventIndex: 1,
        persistedEvent: persistedWithNulls
      }).slice(-3)
    ).toEqual([
      { label: 'Persisted event record', value: 'Available' },
      { label: 'Persisted event sequence', value: '—' },
      { label: 'Persisted event week', value: '—' }
    ])
  })

  it('does not infer completed status from an old plan index alone', () => {
    expect(resolvePlannedEventStatusLabel({ eventId: 'OLD', planIndex: 0, nextEventIndex: 2, completedEventIds: [] })).toBe('Planned')
  })

})
