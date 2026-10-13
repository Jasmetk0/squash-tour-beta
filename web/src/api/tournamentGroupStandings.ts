/** Run-owned immutable completed-group table. This is not a provisional live ranking. */
export type CompletedGroupRow = {
  group_index: number
  position: number
  player_id: string
  wins: number
  losses: number
  group_points: number
  played_matches: number
  walkovers_received: number
  walkovers_conceded: number
  games_won: number
  games_lost: number
  points_won: number
  points_lost: number
}
export type CompletedGroupStandings = {
  schema_version: 'tournament_group_standings_authority.v1' | 'tournament_group_standings_authority.v2'
  run_id: string
  branch_id: string
  event_id: string
  authority_fingerprint: string
  group_match_schedule_fingerprint: string
  generated_by_command_id: string
  source_results: { match_id: string; result_kind: 'played' | 'walkover' }[]
  groups: { group_index: number; rows: CompletedGroupRow[] }[]
}

export type GroupStandingsTieState = {
  schema_version: 'tournament_group_tie_resolution_state.v1'
  run_id: string
  branch_id: string
  event_id: string
  unresolved_case: { group_index: number; reason: string; player_ids: string[] } | null
  resolutions: unknown[]
}

const hexSha = (s: unknown): boolean => typeof s === 'string' && /^[a-f0-9]{64}$/.test(s)

/** Reject any foreign, incomplete, or structurally corrupted final table. */
export function isScopedCompletedGroupStandings(
  data: unknown, runId: string, branchId: string, eventId: string
): data is CompletedGroupStandings {
  if (!data || typeof data !== 'object') return false
  const result = data as Partial<CompletedGroupStandings>
  if (!['tournament_group_standings_authority.v1', 'tournament_group_standings_authority.v2'].includes(result.schema_version ?? '') ||
    result.run_id !== runId || result.branch_id !== branchId || result.event_id !== eventId ||
    !hexSha(result.authority_fingerprint) || !hexSha(result.group_match_schedule_fingerprint) ||
    typeof result.generated_by_command_id !== 'string' || !result.generated_by_command_id ||
    !Array.isArray(result.groups) || result.groups.length === 0 ||
    !Array.isArray(result.source_results) || result.source_results.length === 0) return false

  const sourceIds = new Set<string>()
  for (const receipt of result.source_results) {
    if (!receipt || typeof receipt.match_id !== 'string' || !receipt.match_id ||
      !['played', 'walkover'].includes(receipt.result_kind) || sourceIds.has(receipt.match_id)) return false
    sourceIds.add(receipt.match_id)
  }

  const allPlayers = new Set<string>()
  return result.groups.every((group, index) => {
    if (group.group_index !== index + 1 || !Array.isArray(group.rows) || group.rows.length < 2) return false
    return group.rows.every((row, rowIndex) => {
      if (!row || row.group_index !== group.group_index || row.position !== rowIndex + 1 ||
        typeof row.player_id !== 'string' || !row.player_id || allPlayers.has(row.player_id)) return false
      for (const k of ['wins', 'losses', 'group_points', 'played_matches', 'walkovers_received',
        'walkovers_conceded', 'games_won', 'games_lost', 'points_won', 'points_lost'] as const) {
        if (!Number.isSafeInteger(row[k]) || row[k] < 0) return false
      }
      allPlayers.add(row.player_id)
      return true
    })
  })
}

export function isScopedGroupTieState(
  data: unknown, runId: string, branchId: string, eventId: string
): data is GroupStandingsTieState {
  if (!data || typeof data !== 'object') return false
  const state = data as Partial<GroupStandingsTieState>
  if (state.schema_version !== 'tournament_group_tie_resolution_state.v1' ||
    state.run_id !== runId || state.branch_id !== branchId || state.event_id !== eventId ||
    !Array.isArray(state.resolutions)) return false
  if (state.unresolved_case === null) return true
  const value = state.unresolved_case
  return Boolean(value && Number.isInteger(value.group_index) && value.group_index >= 1 &&
    typeof value.reason === 'string' && value.reason &&
    Array.isArray(value.player_ids) && value.player_ids.length >= 2 &&
    value.player_ids.every(id => typeof id === 'string' && id.length > 0) &&
    new Set(value.player_ids).size === value.player_ids.length)
}
