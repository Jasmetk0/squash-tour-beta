import { describe, expect, it } from 'vitest'

import { formatSnapshotPayloadValue, getSnapshotPayloadRows, getSnapshotPayloadSummary, isRecordArrayPayload } from './viewerSnapshotPayloadDisplay'

describe('viewerSnapshotPayloadDisplay', () => {
  it('summarizes null payloads', () => {
    expect(getSnapshotPayloadSummary(null)).toEqual({ payloadType: 'null', topLevelKeys: [], itemCount: null, isEmpty: true })
    expect(getSnapshotPayloadRows(null)).toContainEqual({ label: 'Payload status', value: 'Empty payload' })
  })

  it('summarizes empty object payloads', () => {
    expect(getSnapshotPayloadRows({})).toEqual([
      { label: 'Payload type', value: 'object' },
      { label: 'Top-level keys', value: 'None' },
      { label: 'Payload status', value: 'Empty payload' }
    ])
  })

  it('summarizes array payloads without assuming standings', () => {
    expect(isRecordArrayPayload([{ player_id: 'p1' }])).toBe(true)
    expect(getSnapshotPayloadRows([{ player_id: 'p1' }, { player_id: 'p2' }])).toEqual([
      { label: 'Payload type', value: 'array' },
      { label: 'Top-level keys', value: 'None' },
      { label: 'Item count', value: '2' }
    ])
  })

  it('summarizes object top-level keys and field shapes', () => {
    expect(getSnapshotPayloadRows({ rows: [{ player_id: 'p1' }], as_of_week: 7, metadata: { source: 'weekly' } })).toEqual([
      { label: 'Payload type', value: 'object' },
      { label: 'Top-level keys', value: 'as_of_week, metadata, rows' },
      { label: 'Field: as_of_week', value: '7' },
      { label: 'Field: metadata', value: 'Object (1 key)' },
      { label: 'Field: rows', value: 'Array (1 item)' }
    ])
  })

  it('summarizes primitive payloads', () => {
    expect(getSnapshotPayloadRows('published')).toEqual([
      { label: 'Payload type', value: 'string' },
      { label: 'Top-level keys', value: 'None' }
    ])
    expect(formatSnapshotPayloadValue(false)).toBe('false')
  })

  it('does not throw on weird nested payload values', () => {
    const symbolValue = Symbol('payload')
    expect(() => getSnapshotPayloadRows({ nested: [{ odd: symbolValue }], nil: null, bool: true })).not.toThrow()
    expect(formatSnapshotPayloadValue(symbolValue)).toBe('Symbol(payload)')
  })
})
