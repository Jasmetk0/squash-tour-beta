import { createContext, useContext, useEffect, useMemo, useRef } from 'react'
import { Link, Outlet, useLocation, useNavigate, useParams } from 'react-router-dom'
import type { ViewerOfficialRunContext } from '../api/types'
import { ApiError } from '../api/client'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { readViewerActiveProductRunId, writeViewerActiveProductRunId } from './activeProductRun'
import { readViewerActiveRunId, writeLastRunId, writeViewerActiveRunId } from './activeRun'
import { useViewerOfficialRunContext } from './useViewerOfficialRunContext'

type ViewerProductRunRouteValue = {
  productRunId: string
  legacySimulationRunId: string
  officialContext: ViewerOfficialRunContext
  productRunDisplayName: string
  officialBranchId: string
  officialBranchDisplayName: string
  currentSeason: number | null
  currentWeek: number | null
  isLoading: boolean
  isStale: boolean
  refetch: () => void
}
const Context = createContext<ViewerProductRunRouteValue | null>(null)
export function useViewerProductRunRouteContext(): ViewerProductRunRouteValue {
  const value = useContext(Context)
  // Direct component tests retain their legacy harness; routed production pages always receive the resolved context.
  const { runId = '' } = useParams()
  if (!value) return { productRunId: runId, legacySimulationRunId: runId, officialContext: {} as ViewerOfficialRunContext, productRunDisplayName: runId, officialBranchId: '', officialBranchDisplayName: '', currentSeason: null, currentWeek: null, isLoading: false, isStale: false, refetch: () => undefined }
  return value
}

export function ViewerProductRunRouteBoundary(): JSX.Element {
  const { runId: productRunId = '' } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const query = useViewerOfficialRunContext(productRunId)
  const last = useRef<ViewerOfficialRunContext | null>(null)
  const didRedirect = useRef(false)
  if (query.data) last.current = query.data
  const context = query.data ?? last.current
  const isStale = Boolean(context && query.isError)
  useEffect(() => {
    if (!query.data) return
    writeViewerActiveProductRunId(query.data.product_run_id)
    writeViewerActiveRunId(query.data.legacy_simulation_run_id)
    writeLastRunId(query.data.legacy_simulation_run_id)
  }, [query.data])
  useEffect(() => {
    if (didRedirect.current || !query.isError || !isApiNotFound(query.error)) return
    if (productRunId !== readViewerActiveRunId()) return
    const activeProductRunId = readViewerActiveProductRunId()
    if (!activeProductRunId) return
    didRedirect.current = true
    const suffix = location.pathname.replace(/^\/viewer\/runs\/[^/]+/, '')
    navigate(`/viewer/runs/${encodeURIComponent(activeProductRunId)}${suffix}${location.search}${location.hash}`, { replace: true })
  }, [location.hash, location.pathname, location.search, navigate, productRunId, query.error, query.isError])
  if (query.isLoading && !context) return <p className="status">Resolving this Product Run’s official Branch…</p>
  if (!context && query.isError) {
    if (query.error instanceof ApiError && query.error.status === 409) return <section className="panel"><h2>Official Viewer Branch is incoherent</h2><p>The Product Run exists, but its official Viewer Branch is currently incoherent.</p><p className="error">{formatApiError(query.error)}</p><button onClick={() => void query.refetch()}>Retry</button><p><Link to="/viewer/runs">Return to Product Runs</Link></p></section>
    return <section className="panel"><h2>Product Run not found</h2><p>Product Run ID: <strong>{productRunId}</strong></p><p>This Product Run could not be found.</p><p><Link to="/viewer/runs">Return to Product Runs</Link></p></section>
  }
  if (!context) return <p className="status">Resolving this Product Run’s official Branch…</p>
  const value = useMemo(() => ({ productRunId: context.product_run_id, legacySimulationRunId: context.legacy_simulation_run_id, officialContext: context, productRunDisplayName: context.product_run_display_name || context.product_run_id, officialBranchId: context.official_branch_id, officialBranchDisplayName: context.official_branch_display_name, currentSeason: context.current_season, currentWeek: context.current_week, isLoading: query.isLoading, isStale, refetch: () => { void query.refetch() } }), [context, isStale, query.isLoading, query.refetch])
  return <Context.Provider value={value}>{isStale ? <aside className="error">Official Branch context is temporarily stale. {formatApiError(query.error)} <button onClick={() => void query.refetch()}>Refresh</button></aside> : null}<Outlet /></Context.Provider>
}
