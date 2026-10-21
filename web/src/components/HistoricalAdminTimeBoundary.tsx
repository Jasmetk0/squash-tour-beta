import { Link, Outlet, useLocation } from 'react-router-dom'

import { supportsHistoricalAdminTime } from '../admin/historicalAdminTimeRoutes'
import { useAdminTime } from '../admin/AdminTimeContext'
import { useLanguage } from '../i18n/LanguageContext'

export function HistoricalAdminTimeBoundary(): JSX.Element {
  const location = useLocation()
  const time = useAdminTime()
  const { language } = useLanguage()

  if (time.mode === 'present' || supportsHistoricalAdminTime(location.pathname, time.runId)) return <Outlet />

  const cs = language === 'cs'
  return <section className="panel">
    <h1>{cs ? 'Historický pohled na této stránce zatím není dostupný.' : 'Historical view is not available on this page yet.'}</h1>
    <p className="status">{cs
      ? 'Obsah platný pouze pro současnost je skrytý, aby nebyl zaměněn za data checkpointu'
      : 'Present-only content is hidden so it cannot be mistaken for data from checkpoint'}{' '}
      <code>{time.viewCheckpointId ?? (cs ? 'neznámý' : 'unknown')}</code>.
    </p>
    <div className="actions">
      <button type="button" onClick={time.selectPresent}>{cs ? 'Vrátit se do současnosti' : 'Return to Present'}</button>
      <Link to={`/admin/runs/${encodeURIComponent(time.runId)}`}>{cs ? 'Otevřít přehled Runu' : 'Open Run Home'}</Link>
    </div>
  </section>
}
