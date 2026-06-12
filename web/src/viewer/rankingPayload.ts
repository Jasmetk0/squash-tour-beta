export type RankingPreviewRow = {
  rank: number | string | null
  playerId: string | null
  playerName: string | null
  country: string | null
  points: number | string | null
  tournamentsCounted: number | string | null
  movement: number | string | null
  previousRank: number | string | null
}

export type RankingPreviewParseResult = {
  rows: RankingPreviewRow[]
  unsupportedReason: string | null
  sourceKey: string | null
}

type UnknownRecord = Record<string, unknown>

const ROW_CONTAINER_KEYS = ['rankings', 'ranking', 'rows', 'standings', 'entries', 'top_100', 'top100'] as const

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function compactString(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed ? trimmed : null
  }
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  return null
}

function numberish(value: unknown): number | string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return null
    const normalized = trimmed.replace(/,/g, '')
    const parsed = Number(normalized)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function numericRank(value: number | string | null): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : null
  }
  return null
}

function firstString(record: UnknownRecord, keys: string[]): string | null {
  for (const key of keys) {
    const value = compactString(record[key])
    if (value) return value
  }
  return null
}

function firstNumberish(record: UnknownRecord, keys: string[]): number | string | null {
  for (const key of keys) {
    const value = numberish(record[key])
    if (value !== null) return value
  }
  return null
}

function firstMovementValue(record: UnknownRecord, keys: string[]): number | string | null {
  for (const key of keys) {
    const raw = record[key]
    if (typeof raw === 'string') {
      const trimmed = raw.trim()
      if (trimmed) return trimmed
    }
    if (typeof raw === 'number' && Number.isFinite(raw)) return raw
  }
  return null
}

function nestedRecord(record: UnknownRecord, key: string): UnknownRecord | null {
  const value = record[key]
  return isRecord(value) ? value : null
}

function hasNestedObjectValue(record: UnknownRecord, keys: string[]): boolean {
  return keys.some((key) => isRecord(record[key]))
}

function hasInvalidNumberishValue(record: UnknownRecord, keys: string[]): boolean {
  return keys.some((key) => record[key] !== undefined && record[key] !== null && numberish(record[key]) === null)
}

function candidateRows(payload: UnknownRecord): { rows: unknown[]; sourceKey: string } | null {
  for (const key of ROW_CONTAINER_KEYS) {
    const value = payload[key]
    if (Array.isArray(value)) return { rows: value, sourceKey: key }
    if (isRecord(value) && Array.isArray(value.rows)) return { rows: value.rows, sourceKey: `${key}.rows` }
  }

  const rankingTable = nestedRecord(payload, 'ranking_table')
  if (rankingTable && Array.isArray(rankingTable.rows)) return { rows: rankingTable.rows, sourceKey: 'ranking_table.rows' }

  return null
}

function parseRankingRow(value: unknown): RankingPreviewRow | null {
  if (!isRecord(value)) return null

  const player = nestedRecord(value, 'player')
  const standingValueKeys = ['rank', 'position', 'current_rank', 'ranking', 'place', 'points', 'ranking_points', 'total_points', 'point_total']
  if (hasNestedObjectValue(value, ['rank', 'position', 'current_rank', 'ranking', 'place', 'player_id', 'playerId', 'player_name', 'playerName', 'name', 'full_name', 'display_name', 'points', 'ranking_points', 'total_points', 'point_total'])) return null
  if (hasInvalidNumberishValue(value, standingValueKeys)) return null

  const rank = firstNumberish(value, ['rank', 'position', 'current_rank', 'ranking', 'place'])
  const playerId = firstString(value, ['player_id', 'playerId']) ?? (player ? firstString(player, ['player_id', 'playerId', 'id']) : null)
  const playerName =
    firstString(value, ['player_name', 'playerName', 'name', 'full_name', 'display_name']) ??
    (player ? firstString(player, ['player_name', 'playerName', 'name', 'full_name', 'display_name']) : null)
  const country =
    firstString(value, ['country', 'country_code', 'countryCode', 'nationality']) ??
    (player ? firstString(player, ['country', 'country_code', 'countryCode', 'nationality']) : null)
  const points = firstNumberish(value, ['points', 'ranking_points', 'total_points', 'point_total'])
  const tournamentsCounted = firstNumberish(value, ['tournaments_counted', 'tournamentsCounted', 'events_counted', 'eventsCounted', 'counted_tournaments'])
  const movement = firstMovementValue(value, ['movement', 'movement_label', 'movementLabel', 'rank_change', 'change'])
  const previousRank = firstNumberish(value, ['previous_rank', 'previousRank', 'prior_rank', 'last_rank'])

  const hasIdentity = Boolean(playerId || playerName)
  const hasStandingValue = rank !== null || points !== null
  if (!hasIdentity || !hasStandingValue) return null

  return { rank, playerId, playerName, country, points, tournamentsCounted, movement, previousRank }
}

export function parseRankingPreviewPayload(payload: unknown): RankingPreviewParseResult {
  if (!isRecord(payload)) return { rows: [], unsupportedReason: 'Ranking snapshot payload is not an object.', sourceKey: null }

  const candidate = candidateRows(payload)
  if (!candidate) return { rows: [], unsupportedReason: 'No supported ranking row container was found.', sourceKey: null }

  const rows = candidate.rows
    .map(parseRankingRow)
    .filter((row): row is RankingPreviewRow => row !== null)
    .sort((left, right) => {
      const leftRank = numericRank(left.rank)
      const rightRank = numericRank(right.rank)
      if (leftRank !== null && rightRank !== null) return leftRank - rightRank
      if (leftRank !== null) return -1
      if (rightRank !== null) return 1
      return 0
    })
    .slice(0, 10)

  return rows.length
    ? { rows, unsupportedReason: null, sourceKey: candidate.sourceKey }
    : { rows: [], unsupportedReason: 'Supported ranking row container had no parseable ranking rows.', sourceKey: candidate.sourceKey }
}
