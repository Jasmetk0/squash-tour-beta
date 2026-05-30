import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useParams } from 'react-router-dom'

import { ViewerSeasonWeekSelector } from './ViewerContextControls'
import { VIEWER_ACTIVE_RUN_CHANGED_EVENT, readViewerActiveRunId } from '../viewer/activeRun'
import { ViewerContextProvider } from '../viewer/ViewerContext'

type NavItem = {
  to: string
  label: string
}

type ViewerDropdown = {
  label: string
  items: NavItem[]
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

export const viewerDropdowns: ViewerDropdown[] = [
  {
    label: 'Rankings',
    items: [
      { to: '/viewer/rankings', label: 'MSA Rankings' },
      { to: '/viewer/rankings/race', label: 'Race to Finals' },
      { to: '/viewer/rankings/next-gen', label: 'Next Gen Race' },
      { to: '/viewer/rankings/elo', label: 'Elo Ranking' },
      { to: '/viewer/rankings/power', label: 'Power Rating' },
      { to: '/viewer/rankings/form', label: 'Form Ranking' },
      { to: '/viewer/countries/ranking', label: 'Country Ranking' },
      { to: '/viewer/rankings/no1-history', label: 'No.1 History' }
    ]
  },
  {
    label: 'Tour',
    items: [
      { to: '/viewer/tour', label: 'Season Hub' },
      { to: '/viewer/tour/calendar', label: 'Season Calendar' },
      { to: '/viewer/tour/current-week', label: 'Current Week' },
      { to: '/viewer/tour/tournaments', label: 'All Tournaments' },
      { to: '/viewer/tour/matches', label: 'Match Center' },
      { to: '/viewer/tour/categories', label: 'Tournament Categories' },
      { to: '/viewer/tour/champions', label: 'Past Champions' }
    ]
  },
  {
    label: 'Players',
    items: [
      { to: '/viewer/players', label: 'Players Hub' },
      { to: '/viewer/players/all', label: 'All Players' },
      { to: '/viewer/players/active', label: 'Active Players' },
      { to: '/viewer/players/next-gen', label: 'Prospects / Next Gen' },
      { to: '/viewer/players/retired', label: 'Retired Players' },
      { to: '/viewer/players/compare', label: 'Compare Players' }
    ]
  },
  {
    label: 'Countries',
    items: [
      { to: '/viewer/countries', label: 'Countries Hub' },
      { to: '/viewer/countries/ranking', label: 'Country Ranking' },
      { to: '/viewer/countries/all', label: 'All Countries' },
      { to: '/viewer/countries/hosting', label: 'Hosting Nations' },
      { to: '/viewer/countries/talent-pipeline', label: 'Talent Pipeline' },
      { to: '/viewer/countries/records', label: 'Country Records' }
    ]
  },
  {
    label: 'H2H',
    items: [
      { to: '/viewer/h2h', label: 'H2H Explorer' },
      { to: '/viewer/h2h/rivalries', label: 'Rivalry Rankings' },
      { to: '/viewer/h2h/most-played', label: 'Most Played Matchups' },
      { to: '/viewer/h2h/finals-rivalries', label: 'Finals Rivalries' },
      { to: '/viewer/players/compare', label: 'Player Comparison' },
      { to: '/viewer/predictions/match-predictor', label: 'Predict Matchup' }
    ]
  },
  {
    label: 'Stats',
    items: [
      { to: '/viewer/stats', label: 'Records' },
      { to: '/viewer/stats/title-leaders', label: 'Title Leaders' },
      { to: '/viewer/stats/no1-weeks', label: 'Weeks at No.1' },
      { to: '/viewer/stats/streaks', label: 'Streaks' },
      { to: '/viewer/stats/upsets', label: 'Biggest Upsets' },
      { to: '/viewer/stats/best-seasons', label: 'Best Seasons' },
      { to: '/viewer/stats/player-stats', label: 'Player Stats' },
      { to: '/viewer/stats/tournament-stats', label: 'Tournament Stats' },
      { to: '/viewer/stats/country-stats', label: 'Country Stats' },
      { to: '/viewer/stats/awards', label: 'Awards' },
      { to: '/viewer/stats/hall-of-fame', label: 'Hall of Fame' },
      { to: '/viewer/stats/era-rankings', label: 'Era Rankings' }
    ]
  },
  {
    label: 'Predictions',
    items: [
      { to: '/viewer/predictions/match-predictor', label: 'Match Predictor' },
      { to: '/viewer/predictions/match-odds', label: 'Match Odds' },
      { to: '/viewer/predictions/tournament-odds', label: 'Tournament Odds' },
      { to: '/viewer/predictions/finals-qualification', label: 'Finals Qualification' },
      { to: '/viewer/predictions/season-end-no1', label: 'Season-End No.1' },
      { to: '/viewer/predictions/upset-watch', label: 'Upset Watch' },
      { to: '/viewer/predictions/futures', label: 'Futures Markets' }
    ]
  }
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

export function getModeSwitcherTarget(pathname: string): { viewerTarget: string; adminTarget: string } {
  const runCalendarMatch = pathname.match(/^\/(viewer|admin)\/runs\/([^/]+)\/calendar$/)
  if (runCalendarMatch) {
    return {
      viewerTarget: `/viewer/runs/${runCalendarMatch[2]}/calendar`,
      adminTarget: `/admin/runs/${runCalendarMatch[2]}/calendar`
    }
  }

  const runPlayersMatch = pathname.match(/^\/(viewer|admin)\/runs\/([^/]+)\/players$/)
  if (runPlayersMatch) {
    return {
      viewerTarget: `/viewer/runs/${runPlayersMatch[2]}/players`,
      adminTarget: `/admin/runs/${runPlayersMatch[2]}/players`
    }
  }

  const mappings: Record<string, { viewerTarget: string; adminTarget: string }> = {
    '/viewer': { viewerTarget: '/viewer', adminTarget: '/admin' },
    '/admin': { viewerTarget: '/viewer', adminTarget: '/admin' },
    '/viewer/players': { viewerTarget: '/viewer/players', adminTarget: '/admin/players' },
    '/admin/players': { viewerTarget: '/viewer/players', adminTarget: '/admin/players' },
    '/viewer/countries': { viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' },
    '/admin/world/countries': { viewerTarget: '/viewer/countries', adminTarget: '/admin/world/countries' },
    '/viewer/tour': { viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' },
    '/admin/tour-seasons': { viewerTarget: '/viewer/tour', adminTarget: '/admin/tour-seasons' }
  }

  if (mappings[pathname]) return mappings[pathname]
  if (pathname.startsWith('/viewer')) return { viewerTarget: pathname, adminTarget: '/admin' }
  if (pathname.startsWith('/admin')) return { viewerTarget: '/viewer', adminTarget: pathname }
  return { viewerTarget: '/viewer', adminTarget: '/admin' }
}

function runNavFor(runId: string): NavItem[] {
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

function ViewerTopbar(): JSX.Element {
  return (
    <nav className="viewer-topbar" aria-label="Viewer primary navigation" data-testid="viewer-primary-nav">
      <NavLink to="/viewer" end className={({ isActive }) => (isActive ? 'active viewer-brand-link' : 'viewer-brand-link')}>
        MSA
      </NavLink>
      {viewerDropdowns.map((dropdown) => (
        <details key={dropdown.label} className="viewer-dropdown">
          <summary aria-haspopup="menu">{dropdown.label}</summary>
          <div className="viewer-dropdown__menu" aria-label={`${dropdown.label} menu`}>
            {dropdown.items.map((item) => (
              <NavLink key={`${dropdown.label}-${item.label}`} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
                {item.label}
              </NavLink>
            ))}
          </div>
        </details>
      ))}
      <NavLink to="/viewer/search" className={({ isActive }) => (isActive ? 'active viewer-search-link' : 'viewer-search-link')}>
        Search
      </NavLink>
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
  const [viewerActiveRunId, setViewerActiveRunId] = useState(() => readViewerActiveRunId())
  const runNav = runId && mode === 'admin' ? runNavFor(runId) : []
  const { viewerTarget, adminTarget } = getModeSwitcherTarget(location.pathname)

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
        {mode === 'viewer' ? (
          viewerActiveRunId ? (
            <section className="viewer-active-run-bar" aria-label="Viewer active run">
              <p className="status">
                Viewing run: <strong>{viewerActiveRunId}</strong>
              </p>
            </section>
          ) : null
        ) : null}
        {runId ? <p className="status">Current run context: {runId}</p> : null}
        <main>
          <Outlet />
        </main>
      </div>
    </ViewerContextProvider>
  )
}
