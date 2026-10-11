export type TournamentPlayerSummary = {
  playerId: string | null
  name: string | null
  country: string | null
}

export type TournamentResultSummary = {
  champion: TournamentPlayerSummary | null
  finalist: TournamentPlayerSummary | null
  finalScore: string | number | null
  matchCount: number | string | null
  completedMatchCount: number | string | null
  drawSize: number | string | null
  roundCount: number | string | null
  resultStatus: string | null
}

export type TournamentResultParseResult = {
  summary: TournamentResultSummary | null
  unsupportedReason: string | null
  sourceKey: string | null
}

type UnknownRecord = Record<string, unknown>

const SUMMARY_KEYS = ['summary', 'result', 'tournament_result'] as const
const WINNER_KEYS = ['champion', 'winner'] as const
const FINAL_KEYS = ['final', 'final_match'] as const

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
    const parsed = Number(trimmed)
    return Number.isFinite(parsed) ? parsed : trimmed
  }
  return null
}

function nestedRecord(record: UnknownRecord, key: string): UnknownRecord | null {
  const value = record[key]
  return isRecord(value) ? value : null
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

function parsePlayer(value: unknown): TournamentPlayerSummary | null {
  if (!isRecord(value)) return null

  const player = nestedRecord(value, 'player')
  const playerId = firstString(value, ['player_id', 'playerId', 'id']) ?? (player ? firstString(player, ['player_id', 'playerId', 'id']) : null)
  const name =
    firstString(value, ['player_name', 'playerName', 'name', 'full_name', 'fullName', 'display_name', 'displayName']) ??
    (player ? firstString(player, ['player_name', 'playerName', 'name', 'full_name', 'fullName', 'display_name', 'displayName']) : null)
  const country =
    firstString(value, ['country', 'country_code', 'countryCode', 'nationality']) ??
    (player ? firstString(player, ['country', 'country_code', 'countryCode', 'nationality']) : null)

  return playerId || name || country ? { playerId, name, country } : null
}

function firstPlayer(record: UnknownRecord, keys: readonly string[]): TournamentPlayerSummary | null {
  for (const key of keys) {
    const player = parsePlayer(record[key])
    if (player) return player
  }
  return null
}

function candidatePayload(payload: UnknownRecord): { record: UnknownRecord; sourceKey: string } {
  for (const key of SUMMARY_KEYS) {
    const value = payload[key]
    if (isRecord(value)) return { record: value, sourceKey: key }
  }
  return { record: payload, sourceKey: 'root' }
}

function countCompletedMatches(matches: unknown[]): number | null {
  let completed = 0
  let parseable = 0

  matches.forEach((match) => {
    if (!isRecord(match)) return
    const hasResultIdentity = Boolean(firstPlayer(match, WINNER_KEYS) || firstString(match, ['winner_id', 'winnerId', 'winner_name', 'winnerName']))
    const status = firstString(match, ['status', 'result_status', 'resultStatus'])
    if (hasResultIdentity || status) parseable += 1
    if (hasResultIdentity || status?.toLowerCase() === 'completed') completed += 1
  })

  return parseable > 0 ? completed : null
}

function deriveDrawSize(record: UnknownRecord): number | string | null {
  const direct = firstNumberish(record, ['draw_size', 'drawSize', 'main_draw_size', 'mainDrawSize'])
  if (direct !== null) return direct

  const draw = nestedRecord(record, 'draw') ?? nestedRecord(record, 'bracket')
  if (!draw) return null
  const drawDirect = firstNumberish(draw, ['draw_size', 'drawSize', 'size', 'main_draw_size', 'mainDrawSize'])
  if (drawDirect !== null) return drawDirect

  for (const key of ['entries', 'players', 'seeds']) {
    const rows = draw[key]
    if (Array.isArray(rows)) return rows.length
  }
  return null
}

function deriveRoundCount(record: UnknownRecord): number | string | null {
  const direct = firstNumberish(record, ['round_count', 'roundCount', 'rounds_count', 'roundsCount'])
  if (direct !== null) return direct
  const rounds = record.rounds
  if (Array.isArray(rounds)) return rounds.length
  const bracket = nestedRecord(record, 'bracket')
  if (bracket && Array.isArray(bracket.rounds)) return bracket.rounds.length
  return null
}

export function parseTournamentResultPayload(payload: unknown): TournamentResultParseResult {
  try {
    if (!isRecord(payload)) return { summary: null, unsupportedReason: 'Tournament result payload is not an object.', sourceKey: null }

    const candidate = candidatePayload(payload)
    const { record } = candidate
    const final = nestedRecord(record, 'final') ?? nestedRecord(record, 'final_match')
    const matches = Array.isArray(record.matches) ? record.matches : final && Array.isArray(final.matches) ? final.matches : null

    const champion = firstPlayer(record, WINNER_KEYS) ?? (final ? firstPlayer(final, WINNER_KEYS) : null)
    const finalist =
      firstPlayer(record, ['finalist', 'runner_up', 'runnerUp', 'runnerup']) ??
      (final ? firstPlayer(final, ['finalist', 'runner_up', 'runnerUp', 'runnerup', 'loser']) : null)
    const finalScore = firstNumberish(record, ['final_score', 'finalScore', 'score']) ?? (final ? firstNumberish(final, ['score', 'final_score', 'finalScore']) : null)
    const matchCount = firstNumberish(record, ['match_count', 'matchCount', 'matches_count', 'matchesCount']) ?? (matches ? matches.length : null)
    const completedMatchCount =
      firstNumberish(record, ['completed_match_count', 'completedMatchCount', 'completed_matches', 'completedMatches']) ??
      (matches ? countCompletedMatches(matches) : null)
    const drawSize = deriveDrawSize(record)
    const roundCount = deriveRoundCount(record)
    const resultStatus = firstString(record, ['result_status', 'resultStatus', 'status']) ?? (final ? firstString(final, ['status', 'result_status', 'resultStatus']) : null)

    const summary = { champion, finalist, finalScore, matchCount, completedMatchCount, drawSize, roundCount, resultStatus }
    const hasParsedValue = Boolean(
      champion || finalist || finalScore !== null || matchCount !== null || completedMatchCount !== null || drawSize !== null || roundCount !== null || resultStatus
    )

    return hasParsedValue
      ? { summary, unsupportedReason: null, sourceKey: candidate.sourceKey }
      : { summary: null, unsupportedReason: 'No supported tournament result fields were found.', sourceKey: candidate.sourceKey }
  } catch {
    return { summary: null, unsupportedReason: 'Tournament result payload could not be safely parsed.', sourceKey: null }
  }
}
