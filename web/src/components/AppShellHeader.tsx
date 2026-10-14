import { Link } from 'react-router-dom'
import { ModeSwitcher } from './ModeSwitcher'
import { AdminRunSelector } from './AdminRunSelector'
import { AdminBranchSelector } from './AdminBranchSelector'
import { AdminTimeControl } from './AdminTimeControl'
import { ViewerActiveRunCompact } from './ViewerRunSelector'
import { appShellSubtitleForMode, appShellTitleForMode } from '../navigation/appShellMode'
import type { AdminScope, AppShellMode } from '../navigation/appShellMode'
import { useLanguage } from '../i18n/LanguageContext'

type AppShellHeaderProps = {
  mode: AppShellMode
  pathname: string
  adminScope: AdminScope
}

export function AppShellHeader({ mode, pathname, adminScope }: AppShellHeaderProps): JSX.Element {
  const { language, setLanguage } = useLanguage()
  return <header className="app-header">
    <div>
      {mode === 'admin' ? <Link className="app-header__logo" to="/admin" aria-label="Squash Engine global Home">◈ Squash Engine</Link> : <h1>{appShellTitleForMode(mode)}</h1>}
      <p className="subtitle">{mode === 'admin' ? (language === 'cs' ? 'Administrace · Pre-alpha' : 'Admin · Pre-alpha') : appShellSubtitleForMode(mode)}</p>
    </div>
    <div className="app-header__controls">
      {mode === 'admin' && adminScope.kind === 'run' && <>
        <AdminRunSelector pathname={pathname} runId={adminScope.runId} />
        <AdminBranchSelector />
        <AdminTimeControl />
      </>}
      {mode === 'admin' && <Link className="app-header__tasks" to="/admin/operations">
        {language === 'cs' ? 'Centrum simulací' : 'Simulation tasks'}
      </Link>}
      {mode === 'admin' && <label className="app-header__language">
        <span className="sr-only">Language / Jazyk</span>
        <select aria-label="Language / Jazyk" value={language} onChange={event => setLanguage(event.target.value === 'en' ? 'en' : 'cs')}>
          <option value="cs">Čeština</option><option value="en">English</option>
        </select>
      </label>}
      {mode === 'viewer' && <div className="app-header__viewer-context" aria-label="Viewer header context controls"><ViewerActiveRunCompact /></div>}
      {mode !== 'admin' && <ModeSwitcher pathname={pathname} />}
    </div>
  </header>
}
