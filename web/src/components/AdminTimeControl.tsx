import { useAdminTime } from '../admin/AdminTimeContext'

export function AdminTimeControl(): JSX.Element {
  const time = useAdminTime()
  const unavailable = time.error || !time.branchId
  const locator = time.isLoading ? 'Loading…' : unavailable ? 'Unavailable' : time.currentSeason != null && time.currentWeek != null
    ? `S${time.currentSeason} · W${time.currentWeek}`
    : '—'
  const event = time.currentEventId ? `, event ${time.currentEventId}` : ''

  return (
    <div
      className="admin-time-compact"
      aria-label="Admin view time"
      title={`Present Branch HEAD: ${locator}${event}`}
    >
      <span>Time</span> <strong>Present · {locator}</strong>
      {time.error ? <span className="sr-only" role="status">Admin Time unavailable: {time.error}</span> : null}
    </div>
  )
}
