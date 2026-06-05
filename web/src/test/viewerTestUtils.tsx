import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, type RenderResult } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'

import { VIEWER_ACTIVE_RUN_STORAGE_KEY } from '../viewer/activeRun'
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
}

export function createTestQueryClient(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

export function setViewerActiveRunId(runId: string): void {
  localStorage.setItem(VIEWER_ACTIVE_RUN_STORAGE_KEY, runId)
}

export function clearViewerStorage(): void {
  localStorage.removeItem(VIEWER_ACTIVE_RUN_STORAGE_KEY)
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
  }: RenderWithViewerProvidersOptions = {},
): RenderResult {
  if (activeRunId !== undefined && activeRunId !== null) {
    setViewerActiveRunId(activeRunId)
  }

  const viewerTree = includeViewerContext ? (
    <ViewerContextProvider>{ui}</ViewerContextProvider>
  ) : (
    ui
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
