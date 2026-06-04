import { NavLink, Outlet, useLocation, useParams } from 'react-router-dom'

import { ViewerTopbar } from './ViewerTopbar'
import { adminNav, runNavFor } from '../navigation/adminNavigation'
import { ViewerContextProvider } from '../viewer/ViewerContext'
import { getModeSwitcherTarget } from '../viewer/modeSwitcherRoutes'

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
  const runNav = runId && mode === 'admin' ? runNavFor(runId) : []
  const { viewerTarget, adminTarget } = getModeSwitcherTarget(location.pathname)

  return (
    <ViewerContextProvider>
      <div className={`app-shell app-shell--${mode}`}>
        <header className="app-header">
          <div>
            <h1>{mode === 'viewer' ? 'MSA Squash' : 'Squash Tour Beta Engine'}</h1>
            <p className="subtitle">{modeLabel}</p>
          </div>
          <div className="mode-switcher" aria-label="Mode switcher">
            <NavLink to={viewerTarget} className={({ isActive }) => (isActive ? 'active' : '')}>
              Viewer / MSA
            </NavLink>
            <NavLink to={adminTarget} className={({ isActive }) => (isActive ? 'active' : '')}>
              Admin / Engine
            </NavLink>
          </div>
        </header>
        {mode === 'admin' ? (
          <nav className="primary-nav" aria-label="Admin / Engine Mode navigation">
            {adminNav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to === '/admin'} className={({ isActive }) => (isActive ? 'active' : '')}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        ) : null}
        {mode === 'viewer' ? <ViewerTopbar /> : null}
        {runNav.length > 0 ? (
          <nav className="run-nav" aria-label="Run navigation">
            {runNav.map((item) => (
              <NavLink key={item.to} to={item.to} end={item.to.endsWith(runId ?? '')} className={({ isActive }) => (isActive ? 'active' : '')}>
                {item.label}
              </NavLink>
            ))}
          </nav>
        ) : null}
        {runId ? <p className="status">Current run context: {runId}</p> : null}
        <main>
          <Outlet />
        </main>
      </div>
    </ViewerContextProvider>
  )
}
