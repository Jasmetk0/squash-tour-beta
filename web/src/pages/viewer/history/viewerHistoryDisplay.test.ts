import { describe, expect, it } from 'vitest'

import type { RunActivityItem } from '../../../api/types'
import { selectLatestActivityItem } from './viewerHistoryDisplay'

describe('selectLatestActivityItem', () => {
  it('returns null for an empty activity list', () => {
    expect(selectLatestActivityItem([])).toBeNull()
  })

  it('returns the highest sequence item without mutating input order', () => {
    const items: RunActivityItem[] = [
      { kind: 'event', sequence: 2, label: 'Second event', season: null, week: null, event_id: null, snapshot_sequence: null, source_event_id: null, related_run_id: null },
      { kind: 'ranking_snapshot', sequence: 8, label: 'Ranking stored', season: null, week: null, event_id: null, snapshot_sequence: null, source_event_id: null, related_run_id: null },
      { kind: 'race_snapshot', sequence: 4, label: 'Race stored', season: null, week: null, event_id: null, snapshot_sequence: null, source_event_id: null, related_run_id: null }
    ]

    expect(selectLatestActivityItem(items)).toEqual(items[1])
    expect(items.map((item) => item.sequence)).toEqual([2, 8, 4])
  })
})
