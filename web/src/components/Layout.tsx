import { Outlet, useLocation, useParams } from 'react-router-dom'

import { AdminNavigation } from './AdminNavigation'
import { ModeSwitcher } from './ModeSwitcher'
import { ViewerTopbar } from './ViewerTopbar'
import { ViewerContextProvider } from '../viewer/ViewerContext'

function readMode(pathname: string): 'admin' | 'viewer' | 'landing' {
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/viewer')) return 'viewer'
  return 'landing'
}

function readRunId(pathname: string, paramRunId?: string): string | undefined {
  if (paramRunId) return paramRunId
  const match = pathname.match(/^\/(?:admin|viewer)\/runs\/([^/]+)/)
  if (match?.[1] === 'new') return undefined
  return match?.[1]
}

export function Layout(): JSX.Element {
  const location = useLocation()
  const { runId: paramRunId } = useParams()
  const mode = readMode(location.pathname)
  const runId = readRunId(location.pathname, paramRunId)
  const modeLabel = mode === 'admin' ? 'Admin / Engine Mode' : mode === 'viewer' ? 'Viewer / MSA Website Mode' : 'Mode selection'
  return (
    <ViewerContextProvider>
      <div className={`app-shell app-shell--${mode}`}>
        <header className="app-header">
          <div>
            <h1>{mode === 'viewer' ? 'MSA Squash' : 'Squash Tour Beta Engine'}</h1>
            <p className="subtitle">{modeLabel}</p>
          </div>
          <ModeSwitcher pathname={location.pathname} />
        </header>
        {mode === 'admin' ? <AdminNavigation runId={runId} /> : null}
        {mode === 'viewer' ? <ViewerTopbar /> : null}
        {mode !== 'admin' && runId ? <p className="status">Current run context: {runId}</p> : null}
        <main>
          <Outlet />
        </main>
      </div>
    </ViewerContextProvider>
  )
}
