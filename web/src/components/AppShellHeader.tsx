import { ModeSwitcher } from './ModeSwitcher'
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
      <ModeSwitcher pathname={pathname} />
    </header>
  )
}
