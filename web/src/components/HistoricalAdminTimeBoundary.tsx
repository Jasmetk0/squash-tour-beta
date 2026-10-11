import { Link, Outlet, useLocation } from 'react-router-dom'

import { supportsHistoricalAdminTime } from '../admin/historicalAdminTimeRoutes'
import { useAdminTime } from '../admin/AdminTimeContext'

export function HistoricalAdminTimeBoundary(): JSX.Element {
  const location = useLocation()
  const time = useAdminTime()

  if (time.mode === 'present' || supportsHistoricalAdminTime(location.pathname, time.runId)) return <Outlet />

  return <section className="panel">
    <h1>Historical view is not available on this page yet.</h1>
    <p className="status">Present-only content is hidden so it cannot be mistaken for data from checkpoint {time.viewCheckpointId ?? 'unknown'}.</p>
    <div className="actions">
      <button type="button" onClick={time.selectPresent}>Return to Present</button>
      <Link to={`/admin/runs/${time.runId}`}>Open Run Home</Link>
    </div>
  </section>
}
