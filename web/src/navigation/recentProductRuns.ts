const KEY = 'squash-engine-recent-product-runs-v1'
export function readRecentProductRuns(): string[] {
  try {
    const data: unknown = JSON.parse(localStorage.getItem(KEY) || '[]')
    return Array.isArray(data) ? data.filter((id): id is string => typeof id === 'string' && Boolean(id.trim())).slice(0, 8) : []
  } catch { return [] }
}
export function rememberProductRun(runId: string): void {
  if (!runId.trim()) return
  try { localStorage.setItem(KEY, JSON.stringify([runId, ...readRecentProductRuns().filter(id => id !== runId)].slice(0, 8))) }
  catch { /* storage may be unavailable */ }
}
