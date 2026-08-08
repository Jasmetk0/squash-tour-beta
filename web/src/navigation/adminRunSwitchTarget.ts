const SAFE_RUN_SUFFIXES = new Set([
  '',
  '/activity',
  '/bootstrap-lineage',
  '/branches',
  '/calendar',
  '/diagnostics',
  '/events',
  '/finals',
  '/finals/qualification',
  '/finals/result',
  '/nations',
  '/players',
  '/rollover',
  '/season-chain',
  '/snapshots/race',
  '/snapshots/ranking',
  '/world-generation',
])

/** Returns a navigation-only destination when changing the route-backed Admin Run. */
export function adminRunSwitchTarget(currentPathname: string, nextRunId: string): string {
  const destinationHome = `/admin/runs/${encodeURIComponent(nextRunId)}`
  const match = currentPathname.match(/^\/admin\/runs\/[^/]+(\/.*)?$/)
  const suffix = match?.[1] ?? ''

  return SAFE_RUN_SUFFIXES.has(suffix) ? `${destinationHome}${suffix}` : destinationHome
}
