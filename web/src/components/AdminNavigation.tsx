import { NavLink } from 'react-router-dom'

import { adminNav, runNavFor } from '../navigation/adminNavigation'

type AdminNavigationProps = {
  runId?: string
}

export function AdminNavigation({ runId }: AdminNavigationProps): JSX.Element {
  const runNav = runId ? runNavFor(runId) : []

  return (
    <>
      <nav className="primary-nav" aria-label="Admin / Engine Mode navigation">
        {adminNav.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/admin'} className={({ isActive }) => (isActive ? 'active' : '')}>
            {item.label}
          </NavLink>
        ))}
      </nav>
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
    </>
  )
}
