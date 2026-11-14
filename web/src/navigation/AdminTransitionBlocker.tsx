import { useEffect, useRef } from 'react'
import { useBlocker } from 'react-router-dom'
import { allowConfirmedBranchLink, consumeApprovedAdminNavigation } from './runContextGuard'

type Props = {
  isDirty: () => boolean
  warning: string
  runId?: string
}

/**
 * A same-page query update touching ONLY reader display controls cannot discard
 * an Admin Working Draft. Back/Forward and typed search must behave identically.
 * Branch, tab, Run, path, and any non-reader URL state still pass the blocker.
 */
function isReaderQueryOnly(
  current: { pathname: string; search: string; hash: string },
  next: { pathname: string; search: string; hash: string }
): boolean {
  if (current.pathname !== next.pathname || current.hash !== next.hash) return false
  const before = new URLSearchParams(current.search)
  const after = new URLSearchParams(next.search)
  const keys = new Set([...before.keys(), ...after.keys()])
  let changed = false
  for (const key of keys) {
    if (JSON.stringify(before.getAll(key)) === JSON.stringify(after.getAll(key))) continue
    if (!/^(career|season|alert)_[a-z_]+$/.test(key)) return false
    changed = true
  }
  return changed
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
    if (next === current || isReaderQueryOnly(currentLocation, nextLocation)) return false
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
