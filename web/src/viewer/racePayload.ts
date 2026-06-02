export type RacePreviewRow = {
  rank: number | string | null
  playerId: string | null
  playerName: string | null
  country: string | null
  racePoints: number | string | null
  tournamentsCounted: number | string | null
  qualificationStatus: string | null
  nextMaxPoints: number | string | null
}

export type RacePreviewParseResult = {
  rows: RacePreviewRow[]
  unsupportedReason: string | null
  sourceKey: string | null
}

type UnknownRecord = Record<string, unknown>

const ROW_CONTAINER_KEYS = [
  'race',
  'race_rows',
  'rows',
  'standings',
  'entries',
  'race_standings',
  'race_to_finals',
  'rtf',
  'race_table'
] as const

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function compactString(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed ? trimmed : null
  }
  if (typeof value === 'number' && Number.isFinite(value)) return String(value)
  if (typeof value === 'boolean') return value ? 'Qualified' : 'Not qualified'
  return null
}

function numberish(value: unknown): number | string | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string') {
    const trimmed = value.trim()
    if (!trimmed) return null
    const parsed = Number(trimmed)
    return Number.isFinite(parsed) ? parsed : trimmed
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

function nestedRecord(record: UnknownRecord, key: string): UnknownRecord | null {
  const value = record[key]
  return isRecord(value) ? value : null
}

function candidateRows(payload: UnknownRecord): { rows: unknown[]; sourceKey: string } | null {
  for (const key of ROW_CONTAINER_KEYS) {
    const value = payload[key]
    if (Array.isArray(value)) return { rows: value, sourceKey: key }
    if (isRecord(value) && Array.isArray(value.rows)) return { rows: value.rows, sourceKey: `${key}.rows` }
  }

  return null
}

function parseRaceRow(value: unknown): RacePreviewRow | null {
  if (!isRecord(value)) return null

  const player = nestedRecord(value, 'player')
  const rank = firstNumberish(value, ['rank', 'position', 'race_rank', 'raceRank', 'place'])
  const playerId = firstString(value, ['player_id', 'playerId']) ?? (player ? firstString(player, ['player_id', 'playerId', 'id']) : null)
  const playerName =
    firstString(value, ['player_name', 'playerName', 'name', 'full_name', 'fullName', 'display_name', 'displayName', 'player']) ??
    (player ? firstString(player, ['player_name', 'playerName', 'name', 'full_name', 'fullName', 'display_name', 'displayName']) : null)
  const country =
    firstString(value, ['country', 'country_code', 'countryCode', 'nationality']) ??
    (player ? firstString(player, ['country', 'country_code', 'countryCode', 'nationality']) : null)
  const racePoints = firstNumberish(value, ['race_points', 'racePoints', 'points', 'total_points', 'totalPoints', 'point_total'])
  const tournamentsCounted = firstNumberish(value, [
    'tournaments_counted',
    'tournamentsCounted',
    'events_counted',
    'eventsCounted',
    'counted_tournaments',
    'countedTournaments'
  ])
  const qualificationStatus = firstString(value, [
    'qualification_status',
    'qualificationStatus',
    'qualifying_status',
    'qualifyingStatus',
    'status',
    'qualified'
  ])
  const nextMaxPoints = firstNumberish(value, [
    'next_max_points_possible',
    'nextMaxPointsPossible',
    'next_max_points',
    'nextMaxPoints',
    'max_points_possible',
    'maxPointsPossible'
  ])

  const hasIdentity = Boolean(playerId || playerName)
  const hasStandingValue = rank !== null || racePoints !== null
  if (!hasIdentity || !hasStandingValue) return null

  return { rank, playerId, playerName, country, racePoints, tournamentsCounted, qualificationStatus, nextMaxPoints }
}

export function parseRacePreviewPayload(payload: unknown): RacePreviewParseResult {
  if (!isRecord(payload)) return { rows: [], unsupportedReason: 'Race snapshot payload is not an object.', sourceKey: null }

  const candidate = candidateRows(payload)
  if (!candidate) return { rows: [], unsupportedReason: 'No supported race row container was found.', sourceKey: null }

  const rows = candidate.rows
    .map(parseRaceRow)
    .filter((row): row is RacePreviewRow => row !== null)
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
    : { rows: [], unsupportedReason: 'Supported race row container had no parseable race rows.', sourceKey: candidate.sourceKey }
}
