import { NavLink } from 'react-router-dom'

import { getModeSwitcherTarget } from '../viewer/modeSwitcherRoutes'
import { useActiveViewerProductRunId } from '../viewer/useActiveViewerProductRunId'
import { useActiveViewerRunId } from '../viewer/useActiveViewerRunId'

type ModeSwitcherProps = {
  pathname: string
}

export function ModeSwitcher({ pathname }: ModeSwitcherProps): JSX.Element {
  const activeProductRunId = useActiveViewerProductRunId()
  const activeLegacySimulationRunId = useActiveViewerRunId()
  const { viewerTarget, adminTarget } = getModeSwitcherTarget(pathname, { activeProductRunId, activeLegacySimulationRunId })

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
