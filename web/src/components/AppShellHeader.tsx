import { ModeSwitcher } from './ModeSwitcher'
import { ViewerSeasonWeekSelector } from './ViewerContextControls'
import { ViewerActiveRunCompact } from './ViewerRunSelector'
import { appShellSubtitleForMode, appShellTitleForMode } from '../navigation/appShellMode'
import type { AppShellMode } from '../navigation/appShellMode'

type AppShellHeaderProps = {
  mode: AppShellMode
  pathname: string
}

export function AppShellHeader({ mode, pathname }: AppShellHeaderProps): JSX.Element {
  return (
    <header className="app-header">
      <div>
        <h1>{appShellTitleForMode(mode)}</h1>
        <p className="subtitle">{appShellSubtitleForMode(mode)}</p>
      </div>
      <div className="app-header__controls">
        {mode === 'viewer' ? (
          <div className="app-header__viewer-context" aria-label="Viewer header context controls">
            <ViewerActiveRunCompact />
            <ViewerSeasonWeekSelector />
          </div>
        ) : null}
        <ModeSwitcher pathname={pathname} />
      </div>
    </header>
  )
}
