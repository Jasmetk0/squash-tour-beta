import { describe, expect, it } from 'vitest'

import {
  formatSnapshotPayloadValue,
  getSnapshotPayloadRows,
  getSnapshotPayloadSummary,
  getSnapshotPayloadTableAuditStatus,
  isRecordArrayPayload,
  parseRaceSnapshotRows,
  parseRankingSnapshotRows
} from './viewerSnapshotPayloadDisplay'

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

  it('does not throw on weird nested payload values or render nested objects as [object Object]', () => {
    const symbolValue = Symbol('payload')
    const rows = getSnapshotPayloadRows({ nested: [{ odd: symbolValue }], nil: null, bool: true, objectValue: { nested: true } })

    expect(rows.map((row) => row.value)).not.toContain('[object Object]')
    expect(formatSnapshotPayloadValue(symbolValue)).toBe('Symbol(payload)')
  })

  it('defers ranking row parsing even for plausible known-looking ranking payloads', () => {
    const payload = {
      ranking_table: {
        table_type: 'ranking',
        rows: [{ rank: 1, player_id: 'p_alpha', player_name: 'Player Alpha', ranking_points: 1200 }]
      }
    }

    expect(parseRankingSnapshotRows(payload)).toEqual([])
    expect(getSnapshotPayloadTableAuditStatus('ranking', payload)).toMatchObject({ classification: 'B_NOT_STABLE_ENOUGH', tableSupported: false })
  })

  it('defers race row parsing even for plausible known-looking race payloads', () => {
    const payload = {
      race_table: {
        table_type: 'race',
        rows: [{ rank: 1, player_id: 'p_beta', player_name: 'Player Beta', race_points: 900 }]
      }
    }

    expect(parseRaceSnapshotRows(payload)).toEqual([])
    expect(getSnapshotPayloadTableAuditStatus('race', payload)).toMatchObject({ classification: 'B_NOT_STABLE_ENOUGH', tableSupported: false })
  })

  it('returns no ranking or race rows for unknown, empty, null, or undefined payloads', () => {
    for (const payload of [{ rows: [{ unknown: true }] }, {}, [], null, undefined]) {
      expect(parseRankingSnapshotRows(payload)).toEqual([])
      expect(parseRaceSnapshotRows(payload)).toEqual([])
    }
  })

  it('does not invent values for malformed or partial row shapes', () => {
    const malformedPayloads = [
      { rows: [{ rank: 1, points: 1000 }] },
      { rows: [{ player_name: 'Incomplete Player', points: 1000 }] },
      { rows: [{ player_id: 'p_missing_points', rank: 2 }] },
      { rows: [{ rank: { value: 1 }, player_name: { label: 'Nested' }, points: { total: 5 } }] }
    ]

    for (const payload of malformedPayloads) {
      expect(parseRankingSnapshotRows(payload)).toEqual([])
      expect(parseRaceSnapshotRows(payload)).toEqual([])
    }
  })

  it('does not accept race-only shapes as ranking rows or ranking-only shapes as race rows', () => {
    const rankingOnly = { ranking_table: { table_type: 'ranking', rows: [{ rank: 1, player_name: 'Player Alpha', ranking_points: 1 }] } }
    const raceOnly = { race_table: { table_type: 'race', rows: [{ rank: 1, player_name: 'Player Beta', race_points: 1 }] } }

    expect(parseRaceSnapshotRows(rankingOnly)).toEqual([])
    expect(parseRankingSnapshotRows(raceOnly)).toEqual([])
  })
})
