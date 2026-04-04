import { NavLink, Outlet, useParams } from 'react-router-dom'

const baseNav = [
  { to: '/', label: 'Dashboard' },
  { to: '/runs', label: 'Runs' },
  { to: '/world/countries', label: 'Countries Editor' },
  { to: '/world/talent-preview', label: 'Talent Preview' },
  { to: '/world/manual-player-overrides', label: 'Manual Player Overrides' }
]

export function Layout(): JSX.Element {
  const { runId } = useParams()
  const runNav = runId
    ? [
        { to: `/runs/${runId}`, label: 'Run Detail' },
        { to: `/runs/${runId}/events`, label: 'Events' },
        { to: `/runs/${runId}/calendar`, label: 'Season Calendar' },
        { to: `/runs/${runId}/activity`, label: 'Activity' },
        { to: `/runs/${runId}/players`, label: 'Players' },
        { to: `/runs/${runId}/diagnostics`, label: 'Diagnostics' },
        { to: `/runs/${runId}/world-generation`, label: 'World Generation' },
        { to: `/runs/${runId}/finals`, label: 'World Tour Finals' },
        { to: `/runs/${runId}/rollover`, label: 'Season Rollover' },
        { to: `/runs/${runId}/bootstrap-lineage`, label: 'Bootstrap / Lineage' },
        { to: `/runs/${runId}/season-chain`, label: 'Season Chain' },
        { to: `/runs/${runId}/snapshots/ranking`, label: 'Ranking Snapshots' },
        { to: `/runs/${runId}/snapshots/race`, label: 'Race Snapshots' }
      ]
    : []

  return (
    <div className="app-shell">
      <header>
        <h1>Squash Tour Beta Engine</h1>
        <p className="subtitle">Deterministic simulation UI shell (MVP module 11)</p>
      </header>
      <nav>
        {[...baseNav, ...runNav].map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? 'active' : '')}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      {runId ? <p className="status">Current run context: {runId}</p> : null}
      <main>
        <Outlet />
      </main>
    </div>
  )
}
