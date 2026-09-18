import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, type RenderResult } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'

import type { ViewerOfficialRunContext } from '../api/types'
import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../viewer/activeRun'
import { VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY } from '../viewer/activeProductRun'
import {
  ViewerProductRunRouteContextProvider,
  type ViewerProductRunRouteValue
} from '../viewer/ViewerProductRunRouteContext'
import { ViewerContextProvider } from '../viewer/ViewerContext'

export const forbiddenViewerActionLabels = [
  'Simulate',
  'Generate',
  'Persist',
  'Apply',
  'Execute',
  'Delete',
  'Edit',
  'Import',
  'Rollover',
  'Rebuild',
  'Override',
  'Save changes',
  'Commit',
  'Regenerate',
  'Repair',
  'Merge',
  'Overwrite',
]

type ViewerActionQueries = Pick<typeof screen, 'queryByText'>

export type RenderWithViewerProvidersOptions = {
  route?: string
  activeRunId?: string | null
  queryClient?: QueryClient
  includeViewerContext?: boolean
  includeProductRunRouteContext?: boolean
  legacySimulationRunId?: string
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

export function makeViewerProductRunRouteTestValue(
  productRunId: string,
  legacySimulationRunId = productRunId,
): ViewerProductRunRouteValue {
  return {
    productRunId,
    legacySimulationRunId,
    officialContext: {} as ViewerOfficialRunContext,
    productRunDisplayName: productRunId,
    officialBranchId: '',
    officialBranchDisplayName: '',
    currentSeason: null,
    currentWeek: null,
    isLoading: false,
    isStale: false,
    refetch: () => undefined,
  }
}

function productRunIdFromRoute(route: string): string | null {
  const pathname = route.split(/[?#]/, 1)[0]
  const match = pathname.match(/^\/viewer\/runs\/([^/]+)/)
  if (!match) return null
  try {
    return decodeURIComponent(match[1])
  } catch {
    return match[1]
  }
}

export function setViewerActiveRunId(runId: string): void {
  localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, runId)
  // Historical Viewer tests used one ID before Product Run / SimulationRun
  // identity was split. Keep the helper as a same-ID fixture convenience.
  localStorage.setItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY, runId)
}

export function setViewerActiveProductRunId(productRunId: string): void {
  localStorage.setItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY, productRunId)
}

export function clearViewerStorage(): void {
  localStorage.removeItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)
  localStorage.removeItem(VIEWER_ACTIVE_PRODUCT_RUN_STORAGE_KEY)
}

export function expectNoForbiddenViewerActions(
  screenOrQueries: ViewerActionQueries = screen,
): void {
  for (const label of forbiddenViewerActionLabels) {
    expect(
      screenOrQueries.queryByText(label, { exact: true }),
    ).not.toBeInTheDocument()
  }
}

export function renderWithViewerProviders(
  ui: ReactElement,
  {
    route = '/',
    activeRunId,
    queryClient = createTestQueryClient(),
    includeViewerContext = true,
    includeProductRunRouteContext,
    legacySimulationRunId,
  }: RenderWithViewerProvidersOptions = {},
): RenderResult {
  if (activeRunId !== undefined && activeRunId !== null) {
    setViewerActiveRunId(activeRunId)
  }

  const viewerContextTree = includeViewerContext ? (
    <ViewerContextProvider>{ui}</ViewerContextProvider>
  ) : (
    ui
  )
  const productRunId = productRunIdFromRoute(route)
  const shouldProvideProductRunContext =
    includeProductRunRouteContext ?? Boolean(productRunId)
  const viewerTree =
    shouldProvideProductRunContext && productRunId ? (
      <ViewerProductRunRouteContextProvider
        value={makeViewerProductRunRouteTestValue(
          productRunId,
          legacySimulationRunId ?? productRunId,
        )}
      >
        {viewerContextTree}
      </ViewerProductRunRouteContextProvider>
    ) : (
      viewerContextTree
    )

  function Providers({ children }: { children: ReactNode }): JSX.Element {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
      </QueryClientProvider>
    )
  }

  return render(viewerTree, { wrapper: Providers })
}
