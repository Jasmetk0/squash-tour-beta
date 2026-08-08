import { ModeSwitcher } from './ModeSwitcher'
import { AdminRunSelector } from './AdminRunSelector'
import { AdminBranchSelector } from './AdminBranchSelector'
import { ViewerActiveRunCompact } from './ViewerRunSelector'
import { appShellSubtitleForMode, appShellTitleForMode } from '../navigation/appShellMode'
import type { AdminScope, AppShellMode } from '../navigation/appShellMode'

type AppShellHeaderProps = {
  mode: AppShellMode
  pathname: string
  adminScope: AdminScope
}

export function AppShellHeader({ mode, pathname, adminScope }: AppShellHeaderProps): JSX.Element {
  return (
    <header className="app-header">
      <div>
        <h1>{appShellTitleForMode(mode)}</h1>
        <p className="subtitle">{appShellSubtitleForMode(mode)}</p>
      </div>
      <div className="app-header__controls">
        {mode === 'admin' && adminScope.kind === 'run' ? (
          <>
            <AdminRunSelector pathname={pathname} runId={adminScope.runId} />
            <AdminBranchSelector />
          </>
        ) : null}
        {mode === 'viewer' ? (
          <div className="app-header__viewer-context" aria-label="Viewer header context controls">
            <ViewerActiveRunCompact />
          </div>
        ) : null}
        <ModeSwitcher pathname={pathname} />
      </div>
    </header>
  )
}
