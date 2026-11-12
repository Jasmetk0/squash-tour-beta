export const RECENT_PRODUCT_RUNS_STORAGE_KEY = 'squash-engine-recent-product-runs-v1'
const KEY = RECENT_PRODUCT_RUNS_STORAGE_KEY
const MAX_RECENT_RUNS = 8

/** Browser history is a navigation hint, never an authoritative Run record. */
export function readRecentProductRuns(): string[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) || '[]')
    if (!Array.isArray(parsed)) return []

    const seen = new Set<string>()
    const recent: string[] = []
    for (const value of parsed) {
      if (typeof value !== 'string' || !value.trim() || seen.has(value)) continue
      seen.add(value)
      recent.push(value)
      if (recent.length === MAX_RECENT_RUNS) break
    }
    return recent
  } catch {
    // Private browsing, disabled storage, or malformed older data must not block Home.
    return []
  }
}

export function rememberProductRun(runId: string): void {
  if (!runId.trim()) return
  try {
    const recent = readRecentProductRuns().filter(id => id !== runId)
    localStorage.setItem(KEY, JSON.stringify([runId, ...recent].slice(0, MAX_RECENT_RUNS)))
  } catch {
    // Navigation still works when browser storage is unavailable.
  }
}

/** A corrupt or stale history record should still be removable from Home. */
export function hasRecentProductRunsStorageEntry(): boolean {
  try {
    return localStorage.getItem(KEY) !== null
  } catch {
    return false
  }
}

/** Removes only this browser's navigation hint. Never changes a Run or preference. */
export function clearRecentProductRuns(): boolean {
  try {
    localStorage.removeItem(KEY)
    return localStorage.getItem(KEY) === null
  } catch {
    return false
  }
}
