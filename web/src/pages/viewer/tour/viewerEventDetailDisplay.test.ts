import { describe, expect, it } from 'vitest'

import type { EventRecord, RaceSnapshot, RankingSnapshot, SeasonStateResponse } from '../../../api/types'
import {
  buildEventDetailLinks,
  buildPersistedEventMetadataItems,
  buildPlannedEventMetadataItems,
  findPersistedEventById,
  findPlannedEventById,
  snapshotsForSourceEvent
} from './viewerEventDetailDisplay'

const seasonState: SeasonStateResponse['season_state'] = {
  season: 2028,
  next_event_index: 1,
  completed_event_ids: ['EVENT/1'],
  ordered_events: [
    { event_id: 'EVENT/1', season: 2028, week: 5, tour: 'World Tour', category: 'Platinum', template_id: 'WT-PLAT' },
    { event_id: 'EVENT 2', season: 2028, week: 6, tour: 'Elite Tour', category: 'Gold', template_id: 'ET-GOLD' }
  ]
}

const persistedEvent: EventRecord = {
  event_sequence: 7,
  event_id: 'EVENT/1',
  season: 2028,
  week: 5,
  template_id: 'WT-PLAT',
  tournament_result: { summary: { status: 'completed' } }
}

describe('viewerEventDetailDisplay', () => {
  it('finds planned and persisted events by decoded event ID', () => {
    expect(findPlannedEventById(seasonState, 'EVENT/1')).toMatchObject({ event_id: 'EVENT/1', planIndex: 0 })
    expect(findPersistedEventById([persistedEvent], 'EVENT/1')).toBe(persistedEvent)
  })

  it('builds planned event metadata with all safe fields', () => {
    const planned = findPlannedEventById(seasonState, 'EVENT/1')

    expect(planned).not.toBeNull()
    expect(buildPlannedEventMetadataItems(planned!, 'run alpha', 2)).toEqual([
      { label: 'Run ID', value: 'run alpha' },
      { label: 'Event ID', value: 'EVENT/1' },
      { label: 'Season', value: 2028 },
      { label: 'Week', value: 'W5' },
      { label: 'Tour', value: 'World Tour' },
      { label: 'Category', value: 'Platinum' },
      { label: 'Template ID', value: 'WT-PLAT' },
      { label: 'Plan index', value: 0 },
      { label: 'Plan position', value: '1 of 2' }
    ])
  })

  it('builds persisted event metadata without inventing optional planned fields', () => {
    expect(buildPersistedEventMetadataItems({ ...persistedEvent, season: null, week: null, template_id: null, tournament_result: null }, 'run alpha')).toEqual([
      { label: 'Run ID', value: 'run alpha' },
      { label: 'Event ID', value: 'EVENT/1' },
      { label: 'Event sequence', value: 7 },
      { label: 'Season', value: '—' },
      { label: 'Week', value: '—' },
      { label: 'Tour', value: '—' },
      { label: 'Category', value: '—' },
      { label: 'Template ID', value: '—' },
      { label: 'Planned event match', value: 'Not available' },
      { label: 'Tournament result payload', value: 'Not available' }
    ])
  })

  it('filters ranking and race snapshots by exact source event ID', () => {
    const rankingSnapshots: RankingSnapshot[] = [
      { snapshot_sequence: 10, snapshot_kind: 'ranking', source_event_id: 'EVENT/1', payload: {} },
      { snapshot_sequence: 11, snapshot_kind: 'ranking', source_event_id: 'OTHER', payload: {} }
    ]
    const raceSnapshots: RaceSnapshot[] = [
      { snapshot_sequence: 12, snapshot_kind: 'race', source_event_id: 'EVENT/1', payload: {} }
    ]

    expect(snapshotsForSourceEvent(rankingSnapshots, 'EVENT/1')).toEqual([rankingSnapshots[0]])
    expect(snapshotsForSourceEvent(raceSnapshots, 'EVENT/1')).toEqual([raceSnapshots[0]])
  })

  it('builds encoded safe source links in stable order', () => {
    expect(
      buildEventDetailLinks({
        runId: 'run alpha',
        eventId: 'EVENT/1',
        week: 5,
        hasPlanned: true,
        hasPersisted: true,
        rankingSnapshotSequences: [10],
        raceSnapshotSequences: [12]
      })
    ).toEqual([
      { label: 'Run browser', href: '/viewer/runs' },
      { label: 'Tournament list', href: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Season calendar', href: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Planned calendar event', href: '/viewer/runs/run%20alpha/calendar/EVENT%2F1' },
      { label: 'Tournament detail', href: '/viewer/runs/run%20alpha/tournaments/EVENT%2F1' },
      { label: 'Week W5', href: '/viewer/runs/run%20alpha/weeks/5' },
      { label: 'Ranking snapshots', href: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Race snapshots', href: '/viewer/runs/run%20alpha/race' },
      { label: 'Ranking publication #10', href: '/viewer/runs/run%20alpha/rankings/10' },
      { label: 'Race publication #12', href: '/viewer/runs/run%20alpha/race/12' }
    ])
  })

  it('does not partially match snapshot source event IDs', () => {
    const rankingSnapshots: RankingSnapshot[] = [
      { snapshot_sequence: 10, snapshot_kind: 'ranking', source_event_id: 'EVENT/10', payload: {} },
      { snapshot_sequence: 11, snapshot_kind: 'ranking', source_event_id: 'EVENT/1', payload: {} }
    ]

    expect(snapshotsForSourceEvent(rankingSnapshots, 'EVENT/1')).toEqual([rankingSnapshots[1]])
  })

  it('handles null and undefined snapshot source event IDs safely', () => {
    const rankingSnapshots = [
      { snapshot_sequence: 10, snapshot_kind: 'ranking', source_event_id: null, payload: {} },
      { snapshot_sequence: 11, snapshot_kind: 'ranking', payload: {} },
      { snapshot_sequence: 12, snapshot_kind: 'ranking', source_event_id: 'EVENT/1', payload: {} }
    ] as RankingSnapshot[]

    expect(snapshotsForSourceEvent(rankingSnapshots, 'EVENT/1')).toEqual([rankingSnapshots[2]])
    expect(snapshotsForSourceEvent(undefined, 'EVENT/1')).toEqual([])
    expect(snapshotsForSourceEvent(null, 'EVENT/1')).toEqual([])
  })

  it('builds only base context and snapshot-list links without persisted, planned, or week context', () => {
    expect(
      buildEventDetailLinks({
        runId: 'run alpha',
        eventId: 'EVENT/1'
      })
    ).toEqual([
      { label: 'Run browser', href: '/viewer/runs' },
      { label: 'Tournament list', href: '/viewer/runs/run%20alpha/tournaments' },
      { label: 'Season calendar', href: '/viewer/runs/run%20alpha/calendar' },
      { label: 'Ranking snapshots', href: '/viewer/runs/run%20alpha/rankings' },
      { label: 'Race snapshots', href: '/viewer/runs/run%20alpha/race' }
    ])
  })

  it('keeps stable source-link order for multiple ranking and race publication sequences', () => {
    expect(
      buildEventDetailLinks({
        runId: 'run alpha',
        eventId: 'EVENT/1',
        week: 5,
        hasPlanned: true,
        hasPersisted: true,
        rankingSnapshotSequences: [10, 13],
        raceSnapshotSequences: [12, 14]
      }).map((link) => link.label)
    ).toEqual([
      'Run browser',
      'Tournament list',
      'Season calendar',
      'Planned calendar event',
      'Tournament detail',
      'Week W5',
      'Ranking snapshots',
      'Race snapshots',
      'Ranking publication #10',
      'Ranking publication #13',
      'Race publication #12',
      'Race publication #14'
    ])
  })

  it('returns null when planned event lists are missing or empty', () => {
    expect(findPlannedEventById({ ...seasonState, ordered_events: [] }, 'EVENT/1')).toBeNull()
    expect(findPlannedEventById({ ...seasonState, ordered_events: undefined } as unknown as SeasonStateResponse['season_state'], 'EVENT/1')).toBeNull()
  })

  it('returns null when persisted event lists are undefined', () => {
    expect(findPersistedEventById(undefined, 'EVENT/1')).toBeNull()
  })

})
