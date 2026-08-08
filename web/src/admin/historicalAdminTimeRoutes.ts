export function supportsHistoricalAdminTime(pathname: string, runId: string): boolean {
  const base = `/admin/runs/${encodeURIComponent(runId)}`
  return pathname === base || pathname === `${base}/` || pathname === `${base}/simulate` || pathname === `${base}/simulate/`
}
