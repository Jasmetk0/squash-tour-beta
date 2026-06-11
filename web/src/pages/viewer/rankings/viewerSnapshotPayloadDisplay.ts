export type SnapshotPayloadSummary = {
  payloadType: string
  topLevelKeys: string[]
  itemCount: number | null
  isEmpty: boolean
}

export type SnapshotPayloadRow = {
  label: string
  value: string
}

export type SnapshotPayloadTableAuditKind = 'ranking' | 'race'

export type SnapshotPayloadTableAuditStatus = {
  kind: SnapshotPayloadTableAuditKind
  classification: 'B_NOT_STABLE_ENOUGH'
  tableSupported: false
  reason: string
}

export type SnapshotPayloadTypedRow = never

const SNAPSHOT_TABLE_DEFERRED_REASON =
  'Snapshot payload detail records are typed as unknown record payloads; row containers, player labels, ranks, and points are not stable enough for table rendering without inference.'

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isRecordArrayPayload(payload: unknown): payload is Array<Record<string, unknown>> {
  return Array.isArray(payload) && payload.every(isPlainRecord)
}

export function formatSnapshotPayloadValue(value: unknown): string {
  if (value === null) return 'null'
  if (value === undefined) return 'undefined'
  if (typeof value === 'string') return value || 'empty string'
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  if (Array.isArray(value)) return `Array (${value.length} item${value.length === 1 ? '' : 's'})`
  if (isPlainRecord(value)) return `Object (${Object.keys(value).length} key${Object.keys(value).length === 1 ? '' : 's'})`
  if (typeof value === 'function') return 'function'
  if (typeof value === 'symbol') return value.toString()
  return String(value)
}

export function getSnapshotPayloadSummary(payload: unknown): SnapshotPayloadSummary {
  if (payload === null) {
    return { payloadType: 'null', topLevelKeys: [], itemCount: null, isEmpty: true }
  }

  if (Array.isArray(payload)) {
    return {
      payloadType: 'array',
      topLevelKeys: [],
      itemCount: payload.length,
      isEmpty: payload.length === 0
    }
  }

  if (isPlainRecord(payload)) {
    const topLevelKeys = Object.keys(payload).sort()
    return {
      payloadType: 'object',
      topLevelKeys,
      itemCount: null,
      isEmpty: topLevelKeys.length === 0
    }
  }

  return {
    payloadType: typeof payload,
    topLevelKeys: [],
    itemCount: null,
    isEmpty: payload === ''
  }
}

export function getSnapshotPayloadRows(payload: unknown): SnapshotPayloadRow[] {
  const summary = getSnapshotPayloadSummary(payload)
  const rows: SnapshotPayloadRow[] = [
    { label: 'Payload type', value: summary.payloadType },
    { label: 'Top-level keys', value: summary.topLevelKeys.length ? summary.topLevelKeys.join(', ') : 'None' }
  ]

  if (summary.itemCount !== null) {
    rows.push({ label: 'Item count', value: String(summary.itemCount) })
  }

  if (summary.isEmpty) {
    rows.push({ label: 'Payload status', value: 'Empty payload' })
  }

  if (isPlainRecord(payload)) {
    for (const key of summary.topLevelKeys) {
      rows.push({ label: `Field: ${key}`, value: formatSnapshotPayloadValue(payload[key]) })
    }
  }

  return rows
}

export function getSnapshotPayloadTableAuditStatus(kind: SnapshotPayloadTableAuditKind, _payload: unknown): SnapshotPayloadTableAuditStatus {
  return {
    kind,
    classification: 'B_NOT_STABLE_ENOUGH',
    tableSupported: false,
    reason: SNAPSHOT_TABLE_DEFERRED_REASON
  }
}

export function parseRankingSnapshotRows(_payload: unknown): SnapshotPayloadTypedRow[] {
  return []
}

export function parseRaceSnapshotRows(_payload: unknown): SnapshotPayloadTypedRow[] {
  return []
}
