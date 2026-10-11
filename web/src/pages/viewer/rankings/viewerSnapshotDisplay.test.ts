import { describe, expect, it } from 'vitest'

import { latestSnapshot } from './viewerSnapshotDisplay'

describe('latestSnapshot', () => {
  it('returns null for an empty snapshot list', () => {
    expect(latestSnapshot([])).toBeNull()
  })

  it('returns the highest snapshot sequence without mutating input order', () => {
    const snapshots = [
      { snapshot_sequence: 2, snapshot_kind: 'ranking', source_event_id: 'EVT-2', payload: {} },
      { snapshot_sequence: 7, snapshot_kind: 'ranking', source_event_id: 'EVT-7', payload: {} },
      { snapshot_sequence: 4, snapshot_kind: 'ranking', source_event_id: 'EVT-4', payload: {} }
    ]

    expect(latestSnapshot(snapshots)).toEqual(snapshots[1])
    expect(snapshots.map((snapshot) => snapshot.snapshot_sequence)).toEqual([2, 7, 4])
  })
})
