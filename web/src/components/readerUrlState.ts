import { useContext } from 'react'
import { UNSAFE_DataRouterContext, useLocation, useSearchParams } from 'react-router-dom'

import { allowConfirmedAdminNavigation } from '../navigation/runContextGuard'

/**
 * URL-backed controls for a single Saved reader. A scope token prevents query
 * parameters copied from another Run/Branch/revision/player from becoming active.
 * Search uses replace so typing does not fill the browser's Back stack.
 */
export function useReaderParams(prefix: 'career' | 'season' | 'alert', scope: string) {
  const [params, setParams] = useSearchParams()
  const location = useLocation()
  const dataRouter = useContext(UNSAFE_DataRouterContext)
  const key = (name: string) => `${prefix}_${name}`
  const active = params.get(key('scope')) === scope
  const get = (name: string, fallback = ''): string =>
    active ? params.get(key(name)) ?? fallback : fallback
  const navigateReader = (next: URLSearchParams, replace = false): void => {
    // Changing display-only filters must not require discarding a Working Draft.
    // This exact URL retains pathname, hash, all foreign parameters and Branch.
    // Other navigation remains fully subject to the Admin transition blocker.
    const query = next.toString()
    const href = location.pathname + (query ? '?' + query : '') + location.hash
    if (dataRouter && href !== location.pathname + location.search + location.hash &&
        next.get('branch') === params.get('branch')) {
      allowConfirmedAdminNavigation(href)
    }
    setParams(next, { replace })
  }
  const set = (values: Record<string, string | null>, replace = false): void => {
      const next = new URLSearchParams(params)
      for (const name of ['scope', ...Object.keys(values)]) next.delete(key(name))
      // Remove stale own selections whenever ownership changes.
      if (!active) {
        for (const name of Array.from(next.keys())) {
          if (name.startsWith(prefix + '_')) next.delete(name)
        }
      }
      next.set(key('scope'), scope)
      for (const [name, value] of Object.entries(values)) {
        if (value !== null && value !== '') next.set(key(name), value)
      }
      navigateReader(next, replace)
  }
  const reset = (): void => {
      const next = new URLSearchParams(params)
      for (const name of Array.from(next.keys())) {
        if (name.startsWith(prefix + '_')) next.delete(name)
      }
      navigateReader(next)
  }
  return { get, set, reset }
}

export function readerPage(value: string): number {
  const n = Number(value)
  return /^\d+$/.test(value) && Number.isSafeInteger(n) && n > 0 ? n : 1
}

export function readerSlice<T>(rows: readonly T[], page: number, size = 20): T[] {
  return rows.slice((page - 1) * size, page * size)
}

export function readerPageCount(length: number, size = 20): number {
  return Math.max(1, Math.ceil(length / size))
}
