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

  it('summarizes empty array payloads as empty without assuming standings', () => {
    expect(isRecordArrayPayload([])).toBe(true)
    expect(getSnapshotPayloadRows([])).toEqual([
      { label: 'Payload type', value: 'array' },
      { label: 'Top-level keys', value: 'None' },
      { label: 'Item count', value: '0' },
      { label: 'Payload status', value: 'Empty payload' }
    ])
  })

  it('summarizes arrays with non-record values without treating them as record arrays', () => {
    expect(isRecordArrayPayload(['p1', 2, null])).toBe(false)
    expect(getSnapshotPayloadRows(['p1', 2, null])).toEqual([
      { label: 'Payload type', value: 'array' },
      { label: 'Top-level keys', value: 'None' },
      { label: 'Item count', value: '3' }
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
    expect(formatSnapshotPayloadValue(undefined)).toBe('undefined')
    expect(formatSnapshotPayloadValue('')).toBe('empty string')
  })

  it('summarizes undefined and empty string object fields conservatively', () => {
    expect(getSnapshotPayloadRows({ blank: '', missing: undefined })).toEqual([
      { label: 'Payload type', value: 'object' },
      { label: 'Top-level keys', value: 'blank, missing' },
      { label: 'Field: blank', value: 'empty string' },
      { label: 'Field: missing', value: 'undefined' }
    ])
  })

  it('summarizes Date objects safely without throwing', () => {
    const date = new Date('2029-02-03T00:00:00.000Z')

    expect(() => getSnapshotPayloadRows(date)).not.toThrow()
    expect(getSnapshotPayloadSummary(date)).toEqual({ payloadType: 'object', topLevelKeys: [], itemCount: null, isEmpty: true })
    expect(formatSnapshotPayloadValue(date)).toBe('Object (0 keys)')
  })

  it('does not throw on weird nested payload values', () => {
    const symbolValue = Symbol('payload')
    expect(() => getSnapshotPayloadRows({ nested: [{ odd: symbolValue }], nil: null, bool: true })).not.toThrow()
    expect(formatSnapshotPayloadValue(symbolValue)).toBe('Symbol(payload)')
  })
})
