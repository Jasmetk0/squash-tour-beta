import { useEffect, useRef } from 'react'
import { useBlocker } from 'react-router-dom'
import { allowConfirmedBranchLink, consumeApprovedAdminNavigation } from './runContextGuard'

type Props = {
  isDirty: () => boolean
  warning: string
  runId?: string
}

/**
 * Must only mount under RouterProvider (a data router).
 * One navigation decision covers links, useNavigate, Back and Forward, BEFORE
 * the route components are discarded. Legacy MemoryRouter tests use the
 * fallback link guard; they never mount this component.
 */
export function AdminTransitionBlocker({ isDirty, warning, runId }: Props): null {
  const dirtyRef = useRef(isDirty)
  dirtyRef.current = isDirty
  const blocker = useBlocker(({ currentLocation, nextLocation }) => {
    const next = nextLocation.pathname + nextLocation.search + nextLocation.hash
    const current = currentLocation.pathname + currentLocation.search + currentLocation.hash
    if (next === current) return false
    if (consumeApprovedAdminNavigation(next)) return false
    return dirtyRef.current()
  })
  useEffect(() => {
    if (blocker.state !== 'blocked') return
    if (!window.confirm(warning)) {
      blocker.reset()
      return
    }
    if (runId) {
      const location = blocker.location
      allowConfirmedBranchLink(runId, new URL(
        location.pathname + location.search + location.hash, window.location.origin
      ))
    }
    blocker.proceed()
  }, [blocker, runId, warning])
  return null
}
