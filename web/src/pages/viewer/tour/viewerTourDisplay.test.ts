import { describe, expect, it } from 'vitest'

import type { EventRecord, SeasonStateResponse } from '../../../api/types'
import { buildPlannedEventMap, formatFinalsAvailability, selectLatestPersistedEvent, selectNextOrderedEvent } from './viewerTourDisplay'

function makeRun(overrides: Partial<SeasonStateResponse> = {}): SeasonStateResponse {
  return {
    run: {
      run_id: 'run alpha',
      season: 2024,
      seed: 123,
      config_version: null,
      config_fingerprint: null,
      total_events: 3,
      completed_event_ids: [],
      next_event_index: 1
    },
    season_state: {
      season: 2024,
      ordered_events: [
        { event_id: 'EVT-1', season: 2024, week: 1, category: 'Gold', tour: 'World Tour', template_id: 'tmpl-1' },
        { event_id: 'EVT-2', season: 2024, week: 2, category: 'Platinum', tour: 'World Tour', template_id: 'tmpl-2' },
        { event_id: 'EVT-3', season: 2024, week: 3, category: 'Silver', tour: 'Elite Tour', template_id: 'tmpl-3' }
      ],
      completed_event_ids: [],
      next_event_index: 2
    },
    ...overrides
  }
}

describe('viewer tour display helpers', () => {
  it('builds planned event lookup by event ID', () => {
    const map = buildPlannedEventMap(makeRun())

    expect(map.get('EVT-2')?.template_id).toBe('tmpl-2')
    expect(map.has('EVT-missing')).toBe(false)
  })

  it('selects the next ordered event from season_state next_event_index first', () => {
    expect(selectNextOrderedEvent(makeRun())?.event_id).toBe('EVT-3')
  })

  it('selects the latest persisted event without mutating input order', () => {
    const events = [
      { event_id: 'EVT-1', event_sequence: 1, season: 2024, week: 1, template_id: 'tmpl-1', tournament_result: null },
      { event_id: 'EVT-3', event_sequence: 3, season: 2024, week: 3, template_id: 'tmpl-3', tournament_result: null },
      { event_id: 'EVT-2', event_sequence: 2, season: 2024, week: 2, template_id: 'tmpl-2', tournament_result: null }
    ] as EventRecord[]

    expect(selectLatestPersistedEvent(events)?.event_id).toBe('EVT-3')
    expect(events.map((event) => event.event_id)).toEqual(['EVT-1', 'EVT-3', 'EVT-2'])
  })

  it('preserves finals availability display strings', () => {
    expect(formatFinalsAvailability(undefined)).toBe('Loading or unavailable')
    expect(formatFinalsAvailability({ run_id: 'run alpha', season: 2024, qualification: null, result: null })).toBe('Finals summary not available yet')
    expect(formatFinalsAvailability({ run_id: 'run alpha', season: 2024, qualification: { players: [] } as never, result: null })).toBe('Finals qualification available')
    expect(formatFinalsAvailability({ run_id: 'run alpha', season: 2024, qualification: null, result: { champion_player_id: 'p1' } as never })).toBe('Finals result available')
  })
})
