import type { ViewerPlayer, ViewerPlayers } from '../../../api/types'

// viewer_players.v1 is a Saved-Revision read model. This helper never
// infers private Potential/Form/Sharpness/Fatigue or an Official Ranking.
const nonEmpty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0
const whole = (value: unknown, min: number, max: number): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max
const nullableWhole = (value: unknown, min: number, max: number): boolean =>
  value === null || whole(value, min, max)

export function playerViewerBranch(context: unknown, runId: string): string | null {
  if (!nonEmpty(runId) || !context || typeof context !== 'object') return null
  const record = context as { product_run_id?: unknown; official_branch_id?: unknown }
  // 'official_branch_id' is the API's legacy source field, not a special Main Branch.
  return record.product_run_id === runId && nonEmpty(record.official_branch_id)
    ? record.official_branch_id : null
}

export function verifiedViewerPlayers(payload: unknown, runId: string, branchId: string): ViewerPlayers | null {
  if (!nonEmpty(runId) || !nonEmpty(branchId) || !payload || typeof payload !== 'object') return null
  const data = payload as Partial<ViewerPlayers>
  if (
    data.schema_version !== 'viewer_players.v1' ||
    data.product_run_id !== runId || data.viewer_branch_id !== branchId ||
    !whole(data.season_index, 0, Number.MAX_SAFE_INTEGER) ||
    !whole(data.week, 1, 61) ||
    !whole(data.player_count, 0, Number.MAX_SAFE_INTEGER) ||
    !whole(data.active_player_count, 0, Number.MAX_SAFE_INTEGER) ||
    !whole(data.retired_player_count, 0, Number.MAX_SAFE_INTEGER) ||
    !Array.isArray(data.players) || data.players.length !== data.player_count ||
    data.active_player_count + data.retired_player_count !== data.player_count
  ) return null

  const playerIds = new Set<string>()
  let active = 0
  let retired = 0
  for (const value of data.players) {
    if (!value || typeof value !== 'object') return null
    const player = value as Partial<ViewerPlayer>
    if (
      !nonEmpty(player.player_id) || playerIds.has(player.player_id) ||
      !nonEmpty(player.name) ||
      typeof player.country_code !== 'string' || !/^[A-Z]{3}$/.test(player.country_code) ||
      !whole(player.age, 0, 120) ||
      (player.status !== 'active' && player.status !== 'retired') ||
      (player.identity_source !== 'initial_world' && player.identity_source !== 'run_prospect') ||
      !nullableWhole(player.tour_entry_season_index, 0, Number.MAX_SAFE_INTEGER) ||
      !nullableWhole(player.tour_entry_week, 1, 61) ||
      // The source lifecycle has one Tour-entry clock, not two independent
      // optional values. Never render an already-entered player whose entry
      // is dated after this immutable Saved Viewer week.
      (player.tour_entry_season_index === null) !== (player.tour_entry_week === null) ||
      (player.tour_entry_season_index !== null && player.tour_entry_week !== null &&
        (player.tour_entry_season_index > data.season_index ||
          (player.tour_entry_season_index === data.season_index &&
            player.tour_entry_week > data.week))) ||
      !nullableWhole(player.current_ovr, 0, 200) ||
      // The current viewer_people projection always withholds these four
      // private simulation fields. The old DTO still declares them nullable,
      // but their accidental exposure must fail closed at the public roster
      // boundary rather than silently trusting an unsupported response.
      player.potential_ovr !== null ||
      player.current_form !== null ||
      player.match_sharpness !== null ||
      player.long_term_fatigue !== null
    ) return null
    playerIds.add(player.player_id)
    if (player.status === 'active') active++
    else retired++
  }
  return active === data.active_player_count && retired === data.retired_player_count
    ? data as ViewerPlayers : null
}

export type PlayerStatusFilter = 'all' | 'active' | 'retired'
export type PlayerOriginFilter = 'all' | 'initial_world' | 'run_prospect'
export type PlayerDirectorySort = 'name' | 'public_ovr' | 'age'

export type PlayerDirectoryFilters = {
  search: string
  status: PlayerStatusFilter
  origin: PlayerOriginFilter
  country: string
  sort: PlayerDirectorySort
}

export function playerDirectoryCountries(players: ViewerPlayers): string[] {
  return [...new Set(players.players.map(player => player.country_code))].sort()
}

function identityOrder(a: ViewerPlayer, b: ViewerPlayer): number {
  return a.player_id.localeCompare(b.player_id)
}

export function filteredPlayerDirectory(players: ViewerPlayers, filters: PlayerDirectoryFilters): ViewerPlayer[] {
  const q = filters.search.trim().toLocaleLowerCase()
  const found = players.players.filter(player =>
    (filters.status === 'all' || player.status === filters.status) &&
    (filters.origin === 'all' || player.identity_source === filters.origin) &&
    (filters.country === 'all' || player.country_code === filters.country) &&
    (!q || [player.player_id, player.name, player.country_code].some(value => value.toLocaleLowerCase().includes(q)))
  )
  return [...found].sort((a, b) => {
    if (filters.sort === 'public_ovr') {
      if (a.current_ovr === null && b.current_ovr !== null) return 1
      if (b.current_ovr === null && a.current_ovr !== null) return -1
      const scoreDiff = (b.current_ovr ?? 0) - (a.current_ovr ?? 0)
      if (scoreDiff) return scoreDiff
    } else if (filters.sort === 'age') {
      const ageDiff = b.age - a.age
      if (ageDiff) return ageDiff
    } else {
      const nameOrder = a.name.localeCompare(b.name, 'cs', { sensitivity: 'base' })
      if (nameOrder) return nameOrder
    }
    return identityOrder(a, b)
  })
}

export const PLAYER_DIRECTORY_PAGE_SIZE = 50

export function parsePlayerDirectoryPage(text: string, totalPages: number): number | null {
  const trimmed = text.trim()
  if (!/^[1-9][0-9]*$/.test(trimmed)) return null
  const page = Number(trimmed)
  return Number.isSafeInteger(page) && page <= totalPages ? page : null
}
