import type { ViewerCountries, ViewerCountry, ViewerPlayer, ViewerPlayers } from '../../../api/types'

// Cross-check the public projection against its roster, not private sporting
// state. This is consistency checking, not cryptographic revision verification.
export function joinedCountryRoster(value: unknown, roster: ViewerPlayers): Map<string, { country: ViewerCountry; players: ViewerPlayer[] }> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const data = value as ViewerCountries
  if (data.schema_version !== 'viewer_countries.v1' || data.product_run_id !== roster.product_run_id ||
      data.viewer_branch_id !== roster.viewer_branch_id || data.season_index !== roster.season_index ||
      data.week !== roster.week || !Array.isArray(data.countries) || data.country_count !== data.countries.length) return null
  const groups = new Map<string, ViewerPlayer[]>()
  for (const player of roster.players) {
    const group = groups.get(player.country_code)
    if (group) group.push(player)
    else groups.set(player.country_code, [player])
  }
  if (groups.size !== data.country_count) return null
  const result = new Map<string, { country: ViewerCountry; players: ViewerPlayer[] }>()
  for (const country of data.countries) {
    if (!country || typeof country !== 'object' || result.has(country.country_code)) return null
    const players = groups.get(country.country_code)
    if (!players || country.player_count !== players.length) return null
    let active = 0, sum = 0, rated = 0
    let top: ViewerPlayer | null = null
    for (const player of players) {
      if (player.status === 'active') active++
      if (player.current_ovr === null) continue
      sum += player.current_ovr
      rated++
      if (!top || player.current_ovr > (top.current_ovr ?? -1) ||
          (player.current_ovr === top.current_ovr && compareIds(player.player_id, top.player_id) < 0)) top = player
    }
    if (country.active_player_count !== active || country.retired_player_count !== players.length - active ||
        country.top_player_id !== (top?.player_id ?? null) || country.top_player_name !== (top?.name ?? null) ||
        country.top_player_current_ovr !== (top?.current_ovr ?? null)) return null
    // Backend uses Python rounding. Accept only a two-decimal value within
    // half a cent of the exact mean, including floating-point tie cases.
    const mean = country.average_current_ovr
    if (rated === 0 ? mean !== null : typeof mean !== 'number' || !Number.isFinite(mean) ||
        mean < 0 || mean > 200 || Math.abs(mean * 100 - Math.round(mean * 100)) > 1e-8 ||
        Math.abs(mean - sum / rated) > 0.00500000001) return null
    result.set(country.country_code, { country, players })
  }
  return result
}

function compareIds(a: string, b: string): number {
  const left = Array.from(a), right = Array.from(b)
  for (let i = 0; i < Math.min(left.length, right.length); i++) {
    const diff = left[i].codePointAt(0)! - right[i].codePointAt(0)!
    if (diff) return diff
  }
  return left.length - right.length
}
