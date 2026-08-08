import { Outlet, useLocation, useParams } from 'react-router-dom'

import { AdminNavigation } from './AdminNavigation'
import { AppShellHeader } from './AppShellHeader'
import { ViewerTopbar } from './ViewerTopbar'
import { appShellClassNameForMode, readAppShellMode, readAppShellRunId, resolveAdminScope } from '../navigation/appShellMode'
import { ViewerContextProvider } from '../viewer/ViewerContext'
import { AdminBranchProvider } from '../admin/AdminBranchContext'

export function Layout(): JSX.Element {
  const location = useLocation()
  const { runId: paramRunId } = useParams()
  const mode = readAppShellMode(location.pathname)
  const runId = readAppShellRunId(location.pathname, paramRunId)
  const adminScope = resolveAdminScope(location.pathname)

  const shell = (
      <div className={appShellClassNameForMode(mode)}>
        <AppShellHeader mode={mode} pathname={location.pathname} adminScope={adminScope} />
        {mode === 'admin' ? <AdminNavigation scope={adminScope} /> : null}
        {mode === 'viewer' ? <ViewerTopbar /> : null}
        {mode !== 'admin' && runId ? <p className="status">Current run context: {runId}</p> : null}
        <main>
          <Outlet />
        </main>
      </div>
  )

  return (
    <ViewerContextProvider>
      {mode === 'admin' && adminScope.kind === 'run'
        ? <AdminBranchProvider runId={adminScope.runId}>{shell}</AdminBranchProvider>
        : shell}
    </ViewerContextProvider>
  )
}
