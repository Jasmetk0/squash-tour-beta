/** Read-only, immutable Run-owned Calendar projection returned by production Package adapter. */
export type RunCalendarEvent = {
  event_id: string
  season: string | number
  season_week: number
  event_name: string
  template_id: string
  category: string
  tour_level: string | null
  host_country: string
  main_draw_size: number
  qualification_draw_size: number
}

export type RunCalendarProjection = {
  run_id: string
  branch_id: string
  package_id: string
  season: string
  run_package_state_fingerprint: string
  fingerprint: string
  content_fingerprint: string
  calendar: {
    season: string
    events: RunCalendarEvent[]
    validation_errors: unknown[]
  }
}

const sha256 = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

export function isRunCalendarProjection(
  value: RunCalendarProjection,
  runId: string,
  branchId: string,
  packageId: string
): boolean {
  if (!value || value.run_id !== runId || value.branch_id !== branchId ||
    value.package_id !== packageId || value.season !== '2000/2001' ||
    !sha256(value.run_package_state_fingerprint) ||
    !sha256(value.fingerprint) || !sha256(value.content_fingerprint) ||
    value.calendar?.season !== '2000/2001' ||
    !Array.isArray(value.calendar.events) ||
    !Array.isArray(value.calendar.validation_errors) ||
    value.calendar.validation_errors.length !== 0) return false
  const seen = new Set<string>()
  for (const event of value.calendar.events) {
    if (!event || typeof event.event_id !== 'string' || event.event_id.length === 0 ||
      seen.has(event.event_id) ||
      String(event.season) !== '2000/2001' ||
      !Number.isInteger(event.season_week) || event.season_week < 1 || event.season_week > 61 ||
      typeof event.template_id !== 'string' || !event.template_id ||
      !Number.isInteger(event.main_draw_size) || event.main_draw_size < 0) return false
    seen.add(event.event_id)
  }
  return true
}

export function runCalendarPackageIds(state: unknown): string[] {
  if (!state || typeof state !== 'object' || !('package_versions' in state)) return []
  const packages = (state as { package_versions?: unknown }).package_versions
  if (!Array.isArray(packages)) return []
  return [...new Set(packages.filter((item): item is { package_id: string; package_type: string } =>
    Boolean(item && typeof item === 'object' && item.package_type === 'Calendar' &&
      typeof item.package_id === 'string' && item.package_id.length)
  ).map(item => item.package_id))].sort()
}

export function firstRunCalendarWeek(events: RunCalendarEvent[]): RunCalendarEvent[] {
  if (!events.length) return []
  const sorted = [...events].sort((a, b) =>
    a.season_week - b.season_week || a.event_id.localeCompare(b.event_id))
  return sorted.filter(event => event.season_week === sorted[0].season_week)
}
