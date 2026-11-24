import type { ViewerCountry, ViewerCountries } from '../../../api/types'

// Legacy viewer_countries.v1 is a public Saved-Revision read model. It is not
// the working Admin world state, an Official Ranking or an all-time record.
// Call this only after confirming the selected Run's actual Viewer Branch.
const whole = (value: unknown, min = 0, max = Number.MAX_SAFE_INTEGER): value is number =>
  typeof value === 'number' && Number.isSafeInteger(value) && value >= min && value <= max
const nullableOvr = (value: unknown): value is number | null =>
  value === null || (typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= 200)
const nonempty = (value: unknown): value is string =>
  typeof value === 'string' && value.trim().length > 0

const PUBLIC_FIELDS = new Set([
  'country_code', 'player_count', 'active_player_count', 'retired_player_count',
  'average_current_ovr', 'top_player_id', 'top_player_name', 'top_player_current_ovr',
])

export function verifiedSavedCountries(
  payload: unknown, runId: string, branchId: string,
): ViewerCountries | null {
  if (!nonempty(runId) || !nonempty(branchId) || !payload || typeof payload !== 'object') return null
  const value = payload as Partial<ViewerCountries>
  if (
    value.schema_version !== 'viewer_countries.v1' ||
    value.product_run_id !== runId || value.viewer_branch_id !== branchId ||
    !whole(value.season_index) || !whole(value.week, 1, 61) ||
    !whole(value.country_count) || !Array.isArray(value.countries) ||
    value.countries.length !== value.country_count
  ) return null

  const countries = new Set<string>()
  for (const item of value.countries) {
    if (!item || typeof item !== 'object') return null
    const country = item as Partial<ViewerCountry>
    if (
      typeof country.country_code !== 'string' ||
      !/^[A-Z]{3}$/.test(country.country_code) ||
      countries.has(country.country_code) ||
      !whole(country.player_count) ||
      !whole(country.active_player_count) ||
      !whole(country.retired_player_count) ||
      country.active_player_count + country.retired_player_count !== country.player_count ||
      !nullableOvr(country.average_current_ovr) ||
      !nullableOvr(country.top_player_current_ovr) ||
      (country.top_player_id !== null && !nonempty(country.top_player_id)) ||
      (country.top_player_name !== null && !nonempty(country.top_player_name)) ||
      (country.top_player_id === null) !== (country.top_player_name === null) ||
      (country.player_count === 0 && country.top_player_id !== null) ||
      (country.top_player_id === null) !== (country.top_player_current_ovr === null) ||
      (country.top_player_id === null) !== (country.average_current_ovr === null) ||
      (country.top_player_current_ovr !== null && !Number.isInteger(country.top_player_current_ovr)) ||
      (typeof country.average_current_ovr === 'number' && typeof country.top_player_current_ovr === 'number' &&
        country.average_current_ovr > country.top_player_current_ovr) ||
      // Reject leaked private fields rather than rendering an unproven schema.
      Object.keys(item).some(key => !PUBLIC_FIELDS.has(key))
    ) return null
    countries.add(country.country_code)
  }
  return value as ViewerCountries
}

export type SavedCountrySort = 'country' | 'players' | 'active' | 'average_ovr'
export function filterSavedCountries(
  countries: ViewerCountry[], search: string, sort: SavedCountrySort,
): ViewerCountry[] {
  const text = search.trim().toLocaleLowerCase()
  const filtered = countries.filter(country =>
    !text || [
      country.country_code, country.top_player_name ?? '', country.top_player_id ?? '',
    ].some(value => value.toLocaleLowerCase().includes(text))
  )
  return [...filtered].sort((a, b) => {
    const byCode = () => a.country_code.localeCompare(b.country_code, 'cs')
    if (sort === 'players') return b.player_count - a.player_count || byCode()
    if (sort === 'active') return b.active_player_count - a.active_player_count || byCode()
    if (sort === 'average_ovr') {
      if (a.average_current_ovr === null && b.average_current_ovr !== null) return 1
      if (b.average_current_ovr === null && a.average_current_ovr !== null) return -1
      return (b.average_current_ovr ?? 0) - (a.average_current_ovr ?? 0) || byCode()
    }
    return byCode()
  })
}
