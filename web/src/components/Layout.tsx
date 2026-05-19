import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useParams } from 'react-router-dom'

import { VIEWER_ACTIVE_RUN_CHANGED_EVENT, readViewerActiveRunId } from '../viewer/activeRun'

type NavItem = {
  to: string
  label: string
}

const adminNav: NavItem[] = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/world', label: 'World' },
  { to: '/admin/players', label: 'Players' },
  { to: '/admin/tour-seasons', label: 'Tour & Seasons' },
  { to: '/admin/runs', label: 'Runs' },
  { to: '/admin/simulate', label: 'Simulate' },
  { to: '/admin/diagnostics', label: 'Diagnostics' },
  { to: '/admin/settings', label: 'Settings' }
]

const viewerNav: NavItem[] = [
  { to: '/viewer', label: 'Home' },
  { to: '/viewer/rankings', label: 'Rankings' },
  { to: '/viewer/tournaments', label: 'Tournaments' },
  { to: '/viewer/players', label: 'Players' },
  { to: '/viewer/countries', label: 'Countries' },
  { to: '/viewer/history', label: 'History' },
  { to: '/viewer/records', label: 'Records' }
]

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

function runNavFor(mode: 'admin' | 'viewer', runId: string): NavItem[] {
  if (mode === 'viewer') {
    return [
      { to: `/viewer/runs/${runId}/rankings`, label: 'Rankings' },
      { to: `/viewer/runs/${runId}/race`, label: 'Race' },
      { to: `/viewer/runs/${runId}/tournaments`, label: 'Tournaments' },
      { to: `/viewer/runs/${runId}/calendar`, label: 'Calendar' },
      { to: `/viewer/runs/${runId}/players`, label: 'Players' },
      { to: `/viewer/runs/${runId}/countries`, label: 'Countries' },
      { to: `/viewer/runs/${runId}/history`, label: 'History' },
      { to: `/viewer/runs/${runId}/finals`, label: 'World Tour Finals' }
    ]
  }

  return [
    { to: `/admin/runs/${runId}`, label: 'Run Detail' },
    { to: `/admin/runs/${runId}/events`, label: 'Events' },
    { to: `/admin/runs/${runId}/calendar`, label: 'Season Calendar' },
    { to: `/admin/runs/${runId}/activity`, label: 'Activity' },
    { to: `/admin/runs/${runId}/players`, label: 'Players' },
    { to: `/admin/runs/${runId}/nations`, label: 'Nations' },
    { to: `/admin/runs/${runId}/diagnostics`, label: 'Diagnostics' },
    { to: `/admin/runs/${runId}/world-generation`, label: 'World Generation' },
    { to: `/admin/runs/${runId}/finals`, label: 'World Tour Finals' },
    { to: `/admin/runs/${runId}/rollover`, label: 'Season Rollover' },
    { to: `/admin/runs/${runId}/bootstrap-lineage`, label: 'Bootstrap / Lineage' },
    { to: `/admin/runs/${runId}/season-chain`, label: 'Season Chain' },
    { to: `/admin/runs/${runId}/snapshots/ranking`, label: 'Ranking Snapshots' },
    { to: `/admin/runs/${runId}/snapshots/race`, label: 'Race Snapshots' }
  ]
}

export function Layout(): JSX.Element {
  const location = useLocation()
  const { runId: paramRunId } = useParams()
  const mode = readMode(location.pathname)
  const runId = readRunId(location.pathname, paramRunId)
  const modeLabel = mode === 'admin' ? 'Admin / Engine Mode' : mode === 'viewer' ? 'Viewer / MSA Website Mode' : 'Mode selection'
  const modeNav = mode === 'admin' ? adminNav : mode === 'viewer' ? viewerNav : []
  const [viewerActiveRunId, setViewerActiveRunId] = useState(() => readViewerActiveRunId())
  const runNav = runId && mode !== 'landing' ? runNavFor(mode, runId) : []
  const viewerActiveRunNav = mode === 'viewer' && viewerActiveRunId && runNav.length === 0 ? runNavFor('viewer', viewerActiveRunId) : []

  useEffect(() => {
    function handleViewerActiveRunChange(): void {
      setViewerActiveRunId(readViewerActiveRunId())
    }

    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, handleViewerActiveRunChange)
    window.addEventListener('storage', handleViewerActiveRunChange)
    return () => {
      window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, handleViewerActiveRunChange)
      window.removeEventListener('storage', handleViewerActiveRunChange)
    }
  }, [])

  return (
    <div className={`app-shell app-shell--${mode}`}>
      <header className="app-header">
        <div>
          <h1>Squash Tour Beta Engine</h1>
          <p className="subtitle">{modeLabel}</p>
        </div>
        <div className="mode-switcher" aria-label="Mode switcher">
          <NavLink to="/viewer" className={({ isActive }) => (isActive ? 'active' : '')}>
            Viewer / MSA
          </NavLink>
          <NavLink to="/admin" className={({ isActive }) => (isActive ? 'active' : '')}>
            Admin / Engine
          </NavLink>
        </div>
      </header>
      {modeNav.length > 0 ? (
        <nav className="primary-nav" aria-label={`${modeLabel} navigation`}>
          {modeNav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === '/admin' || item.to === '/viewer'} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      ) : null}
      {runNav.length > 0 ? (
        <nav className="run-nav" aria-label="Run navigation">
          {runNav.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to.endsWith(runId ?? '')} className={({ isActive }) => (isActive ? 'active' : '')}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      ) : null}
      {mode === 'viewer' ? (
        viewerActiveRunId ? (
          <section className="viewer-active-run-bar" aria-label="Viewer active run">
            <p className="status">
              Viewing run: <strong>{viewerActiveRunId}</strong>
            </p>
            {viewerActiveRunNav.length > 0 ? (
              <nav className="run-nav" aria-label="Viewer active run quick links">
                {viewerActiveRunNav.map((item) => (
                  <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
                    {item.label}
                  </NavLink>
                ))}
              </nav>
            ) : null}
          </section>
        ) : (
          <p className="status">
            No Viewer run selected. <Link to="/viewer">Select a run</Link>.
          </p>
        )
      ) : null}
      {runId ? <p className="status">Current run context: {runId}</p> : null}
      <main>
        <Outlet />
      </main>
    </div>
  )
}
