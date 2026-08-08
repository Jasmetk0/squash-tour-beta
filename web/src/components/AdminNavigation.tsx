import { NavLink } from 'react-router-dom'

import { globalAdminNav, runAdminNavFor } from '../navigation/adminNavigation'
import type { AdminScope } from '../navigation/appShellMode'

type AdminNavigationProps = {
  scope: AdminScope
}

export function AdminNavigation({ scope }: AdminNavigationProps): JSX.Element {
  if (scope.kind === 'global') {
    return (
      <nav className="primary-nav" aria-label="Global Admin navigation">
        {globalAdminNav.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/admin'} className={({ isActive }) => (isActive ? 'active' : '')}>
            {item.label}
          </NavLink>
        ))}
      </nav>
    )
  }

  const runNav = runAdminNavFor(scope.runId)

  return (
    <>
      <nav className="run-nav" aria-label="Run Admin navigation">
        <NavLink to="/admin" end className={({ isActive }) => (isActive ? 'active' : '')}>
          Back to Global
        </NavLink>
        {runNav.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === `/admin/runs/${scope.runId}`} className={({ isActive }) => (isActive ? 'active' : '')}>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <p className="status">Current run context: {scope.runId}</p>
    </>
  )
}
