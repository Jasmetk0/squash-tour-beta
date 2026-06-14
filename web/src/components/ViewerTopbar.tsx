import { useEffect, useState } from 'react'
import type { FormEvent, MouseEvent } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'

import { viewerDropdowns } from '../viewer/viewerNavigation'
import type { ViewerDropdown } from '../viewer/viewerNavigation'
import { viewerHomePath, viewerTopSearchPath } from '../viewer/viewerRoutes'

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

export function ViewerTopbar(): JSX.Element {
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
      <div className="viewer-topbar__primary">
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
      </div>
      <div className="viewer-topbar__utility">
        <ViewerTopbarSearch />
      </div>
    </nav>
  )
}
