import { useEffect, useState } from 'react'
import type { FormEvent, MouseEvent } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'

import { ViewerSeasonWeekSelector } from './ViewerContextControls'
import { ViewerActiveRunCompact } from './ViewerRunSelector'
import { ViewerContextProvider } from '../viewer/ViewerContext'
import { viewerDropdowns } from '../viewer/viewerNavigation'
import type { ViewerDropdown } from '../viewer/viewerNavigation'
import {
  viewerHomePath,
  viewerPlayersPath,
  viewerSeasonCalendarPath,
  viewerTopCountriesPath,
  viewerTopPlayersPath,
  viewerTopSearchPath,
  viewerTopTourPath
} from '../viewer/viewerRoutes'

type AdminNavItem = {
  to: string
  label: string
}

const adminNav: AdminNavItem[] = [
  { to: '/admin', label: 'Dashboard' },
  { to: '/admin/world', label: 'World' },
  { to: '/admin/players', label: 'Players' },
  { to: '/admin/tour-seasons', label: 'Tour & Seasons' },
  { to: '/admin/runs', label: 'Runs' },
  { to: '/admin/simulate', label: 'Simulate' },
  { to: '/admin/diagnostics', label: 'Diagnostics' },
  { to: '/admin/settings', label: 'Settings' }
]

function readMode(pathname: string): 'admin' | 'viewer' | 'landing' {
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/viewer')) return 'viewer'
  return 'landing'
}

function safeDecodePathSegment(segment: string): string {
  try {
    return decodeURIComponent(segment)
  } catch {
    return segment
  }
}

function readRunId(pathname: string, paramRunId?: string): string | undefined {
  if (paramRunId) return paramRunId
  const match = pathname.match(/^\/(?:admin|viewer)\/runs\/([^/]+)/)
  if (match?.[1] === 'new') return undefined
  return match?.[1]
}

export function getModeSwitcherTarget(pathname: string): { viewerTarget: string; adminTarget: string } {
  const runCalendarMatch = pathname.match(/^\/(viewer|admin)\/runs\/([^/]+)\/calendar$/)
  if (runCalendarMatch) {
    return {
      viewerTarget: viewerSeasonCalendarPath(safeDecodePathSegment(runCalendarMatch[2])),
      adminTarget: `/admin/runs/${runCalendarMatch[2]}/calendar`
    }
  }

  const runPlayersMatch = pathname.match(/^\/(viewer|admin)\/runs\/([^/]+)\/players$/)
  if (runPlayersMatch) {
    return {
      viewerTarget: viewerPlayersPath(safeDecodePathSegment(runPlayersMatch[2])),
      adminTarget: `/admin/runs/${runPlayersMatch[2]}/players`
    }
  }

  const mappings: Record<string, { viewerTarget: string; adminTarget: string }> = {
    [viewerHomePath()]: { viewerTarget: viewerHomePath(), adminTarget: '/admin' },
    '/admin': { viewerTarget: viewerHomePath(), adminTarget: '/admin' },
    [viewerTopPlayersPath()]: { viewerTarget: viewerTopPlayersPath(), adminTarget: '/admin/players' },
    '/admin/players': { viewerTarget: viewerTopPlayersPath(), adminTarget: '/admin/players' },
    [viewerTopCountriesPath()]: { viewerTarget: viewerTopCountriesPath(), adminTarget: '/admin/world/countries' },
    '/admin/world/countries': { viewerTarget: viewerTopCountriesPath(), adminTarget: '/admin/world/countries' },
    [viewerTopTourPath()]: { viewerTarget: viewerTopTourPath(), adminTarget: '/admin/tour-seasons' },
    '/admin/tour-seasons': { viewerTarget: viewerTopTourPath(), adminTarget: '/admin/tour-seasons' }
  }

  if (mappings[pathname]) return mappings[pathname]
  if (pathname.startsWith('/viewer')) return { viewerTarget: pathname, adminTarget: '/admin' }
  if (pathname.startsWith('/admin')) return { viewerTarget: viewerHomePath(), adminTarget: pathname }
  return { viewerTarget: viewerHomePath(), adminTarget: '/admin' }
}

function runNavFor(runId: string): AdminNavItem[] {
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

export function isExactViewerActivePath(currentPathname: string, targetPathname: string): boolean {
  return currentPathname.replace(/\/$/, '') === targetPathname.replace(/\/$/, '')
}

function isViewerRouteGroupActive(currentPathname: string, dropdown: ViewerDropdown): boolean {
  return dropdown.routePrefixes.some((prefix) => currentPathname === prefix || currentPathname.startsWith(`${prefix}/`))
}

function ViewerTopbarSearch(): JSX.Element {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    const trimmed = query.trim()
    navigate(trimmed ? `${viewerTopSearchPath()}?q=${encodeURIComponent(trimmed)}` : viewerTopSearchPath())
  }

  return (
    <form className="viewer-topbar-search" role="search" aria-label="Viewer search" onSubmit={handleSubmit}>
      <input
        aria-label="Search players, countries, tournaments"
        placeholder="Search players, countries, tournaments…"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />
      <button type="submit" aria-label="Open Viewer search">
        Search
      </button>
    </form>
  )
}

function ViewerTopbar(): JSX.Element {
  const location = useLocation()

  useEffect(() => {
    const activeElement = document.activeElement
    if (activeElement instanceof HTMLElement && activeElement.closest('.viewer-dropdown')) {
      activeElement.blur()
    }
  }, [location.pathname])

  function closeDropdownAfterNavigation(event: MouseEvent<HTMLAnchorElement>): void {
    event.currentTarget.blur()
  }

  return (
    <nav className="viewer-topbar" aria-label="Viewer primary navigation" data-testid="viewer-primary-nav">
      <NavLink to={viewerHomePath()} end className={({ isActive }) => (isActive ? 'active viewer-brand-link' : 'viewer-brand-link')}>
        MSA
      </NavLink>
      {viewerDropdowns.map((dropdown) => {
        const parentActive = isViewerRouteGroupActive(location.pathname, dropdown)
        return (
          <div key={dropdown.label} className="viewer-dropdown">
            <NavLink
              to={dropdown.to}
              className={parentActive ? 'active viewer-dropdown__label' : 'viewer-dropdown__label'}
              aria-haspopup="true"
            >
              {dropdown.label}
            </NavLink>
            <div className="viewer-dropdown__menu" aria-label={`${dropdown.label} menu`}>
              {dropdown.items.map((item) => (
                <Link
                  key={`${dropdown.label}-${item.label}`}
                  to={item.to}
                  className={isExactViewerActivePath(location.pathname, item.to) ? 'active' : ''}
                  onClick={closeDropdownAfterNavigation}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        )
      })}
      <ViewerTopbarSearch />
      <ViewerActiveRunCompact />
      <ViewerSeasonWeekSelector />
    </nav>
  )
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
