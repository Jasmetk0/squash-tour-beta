/** Product Run time axis uses either a zero-based Season index or an explicit start year.
 * A missing/null marker is not a claim that the world is at its first Season or Week.
 */
export const SEASONS = 50
export const WEEKS = 61

export function seasonOrdinal(value: number | null | undefined): number | null {
  if (value == null || !Number.isInteger(value)) return null
  if (value >= 0 && value < SEASONS) return value
  if (value >= 2000 && value < 2050) return value - 2000
  return null
}

export function weekOrdinal(value: number | null | undefined): number | null {
  return value != null && Number.isInteger(value) && value >= 1 && value <= WEEKS ? value : null
}

export function seasonLabel(ordinal: number): string {
  const year = 2000 + ordinal
  return year + '/' + String((year + 1) % 100).padStart(2, '0')
}

export type RunHomeSignal =
  | { kind: 'loading' }
  | { kind: 'unavailable'; reason: string }
  | { kind: 'empty' }
  | { kind: 'ready'; value: string }

export function positionSignal(value: number | null | undefined, kind: 'season' | 'week', failed: string | null = null): RunHomeSignal {
  if (failed) return { kind: 'unavailable', reason: failed }
  const index = kind === 'season' ? seasonOrdinal(value) : weekOrdinal(value)
  if (index === null) return value == null ? { kind: 'empty' } : { kind: 'unavailable', reason: 'Position is outside the canonical timeline' }
  return { kind: 'ready', value: kind === 'season' ? seasonLabel(index) : 'W' + index }
}
