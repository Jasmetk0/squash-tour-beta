export function supportsHistoricalAdminTime(pathname: string, runId: string): boolean {
  const base = `/admin/runs/${encodeURIComponent(runId)}`
  if ([base, `${base}/`, `${base}/simulate`, `${base}/simulate/`, `${base}/calendar`, `${base}/calendar/`].includes(pathname)) return true
  const suffix = pathname.startsWith(`${base}/`) ? pathname.slice(base.length + 1).replace(/\/$/, '') : ''
  const parts = suffix.split('/')
  return (parts.length === 2 && parts[0] === 'weeks' && parts[1].length > 0) ||
    (parts.length === 2 && parts[0] === 'calendar' && parts[1].length > 0)
}
