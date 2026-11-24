import type { VisiblePreTourProspects, VisibleProspectWeek } from '../../../api/types'

// The shipped public projection is a W61 lifecycle read model. Its identity,
// birth-week visibility and pagination must be verified before any row renders.
// Never forward unknown fields (which might contain private pregeneration data).
const publicPageFields = [
  'schema_version', 'run_id', 'branch_id', 'week', 'lifecycle_fingerprint',
  'total', 'limit', 'offset', 'prospects',
]
const publicProspectFields = [
  'player_id', 'display_name', 'short_name', 'country_code', 'country_name',
  'age', 'birth_year', 'birth_year_week', 'lifecycle_status', 'tour_status',
  'visible_since_week',
]

function exactObject(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  return Object.keys(value).length === keys.length &&
    Object.keys(value).every(key => keys.includes(key))
}

function whole(value: unknown, min: number, max = Number.MAX_SAFE_INTEGER): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) &&
    value >= min && value <= max
}

function nonblank(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function nullableName(value: unknown): value is string | null {
  return value === null || nonblank(value)
}

function publicWeek(value: unknown): value is VisibleProspectWeek {
  return exactObject(value, ['season_index', 'week']) &&
    whole(value.season_index, 0) && whole(value.week, 1, 61)
}

function notFuture(visible: VisibleProspectWeek, current: VisibleProspectWeek): boolean {
  return visible.season_index < current.season_index ||
    (visible.season_index === current.season_index && visible.week <= current.week)
}

/** Fail closed on foreign/invalid projections, truncated pages and future cohorts. */
export function verifiedVisibleProspects(
  raw: unknown, runId: string, branchId: string, requestedLimit: number,
  requestedOffset: number,
): VisiblePreTourProspects | null {
  if (!nonblank(runId) || !nonblank(branchId) ||
      !whole(requestedLimit, 1, 500) || !whole(requestedOffset, 0) ||
      !exactObject(raw, publicPageFields) ||
      raw.schema_version !== 'visible_pre_tour_prospects.v1' ||
      raw.run_id !== runId || raw.branch_id !== branchId ||
      !publicWeek(raw.week) ||
      typeof raw.lifecycle_fingerprint !== 'string' ||
      !/^[0-9a-f]{64}$/.test(raw.lifecycle_fingerprint) ||
      !whole(raw.total, 0) ||
      raw.limit !== requestedLimit || raw.offset !== requestedOffset ||
      !Array.isArray(raw.prospects)) return null

  const total = raw.total
  const prospects: unknown[] = raw.prospects
  // The actual read model returns a full page of the visible population
  // (or its final remainder), never a sample of pregenerated future rows.
  const expectedSize = Math.min(requestedLimit, Math.max(0, total - requestedOffset))
  if (prospects.length !== expectedSize) return null

  const ids = new Set<string>()
  for (const item of prospects) {
    if (!exactObject(item, publicProspectFields) ||
        !nonblank(item.player_id) || ids.has(item.player_id) ||
        !nonblank(item.display_name) ||
        !nullableName(item.short_name) ||
        typeof item.country_code !== 'string' ||
        !/^[A-Z]{3}$/.test(item.country_code) ||
        !nullableName(item.country_name) ||
        !whole(item.age, 0, 120) ||
        !whole(item.birth_year, 0) ||
        !whole(item.birth_year_week, 1, 61) ||
        (item.lifecycle_status !== 'active' && item.lifecycle_status !== 'retired') ||
        item.tour_status !== 'pre_tour' ||
        !publicWeek(item.visible_since_week) ||
        !notFuture(item.visible_since_week, raw.week)) return null
    ids.add(item.player_id)
  }
  return raw as unknown as VisiblePreTourProspects
}
