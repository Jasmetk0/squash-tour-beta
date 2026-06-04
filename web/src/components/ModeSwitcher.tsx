import { NavLink } from 'react-router-dom'

import { getModeSwitcherTarget } from '../viewer/modeSwitcherRoutes'

type ModeSwitcherProps = {
  pathname: string
}

export function ModeSwitcher({ pathname }: ModeSwitcherProps): JSX.Element {
  const { viewerTarget, adminTarget } = getModeSwitcherTarget(pathname)

  return (
    <div className="mode-switcher" aria-label="Mode switcher">
      <NavLink to={viewerTarget} className={({ isActive }) => (isActive ? 'active' : '')}>
        Viewer / MSA
      </NavLink>
      <NavLink to={adminTarget} className={({ isActive }) => (isActive ? 'active' : '')}>
        Admin / Engine
      </NavLink>
    </div>
  )
}
