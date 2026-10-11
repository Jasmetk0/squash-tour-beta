import { useQuery } from '@tanstack/react-query'

import { listRunContainers } from '../../api/client'
import { ViewerRunSelector } from '../../components/ViewerRunSelector'
import { ViewerShellPage } from '../../components/viewer/ViewerShellPage'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList } from '../../components/viewer/ViewerLandingComponents'
import {
  buildRunBrowserContextLinks,
  buildRunBrowserMetadataItems,
  buildRunBrowserPrimaryLinks,
  normalizeRunBrowserRuns
} from '../../viewer/runBrowserDisplay'
import { useActiveViewerProductRunId } from '../../viewer/useActiveViewerProductRunId'
import { findViewerTopLevelHubLink } from '../../viewer/viewerHubLinks'

const VIEWER_RUN_BROWSER_HUB_LINK = findViewerTopLevelHubLink('Run Browser')

export function ViewerRunBrowserPage(): JSX.Element {
  const activeRunId = useActiveViewerProductRunId()
  const runsQuery = useQuery({ queryKey: ['viewer-run-selector-runs'], queryFn: listRunContainers, retry: false })
  const runs = normalizeRunBrowserRuns(runsQuery.data?.run_containers)

  return (
    <ViewerShellPage
      title={VIEWER_RUN_BROWSER_HUB_LINK.label}
      kicker="Read-only Viewer runs"
      description={VIEWER_RUN_BROWSER_HUB_LINK.description}
    >
      <ViewerRunSelector />

      <section className="viewer-active-run-panel" aria-label="Run Browser active run">
        <span className="eyebrow">Active run</span>
        <h3>Active run</h3>
        {activeRunId ? (
          <p className="status">Current active Viewer run id: <strong>{activeRunId}</strong></p>
        ) : (
          <ViewerEmptyState>No active Viewer run selected.</ViewerEmptyState>
        )}
      </section>

      <section className="viewer-active-run-card" aria-label="Available runs">
        <span className="eyebrow">Run Browser</span>
        <h3>Available runs</h3>
        {runsQuery.isLoading ? <p className="status">Loading available runs…</p> : null}
        {runsQuery.isError ? <ViewerEmptyState>Run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? <ViewerEmptyState>No Viewer runs are available yet.</ViewerEmptyState> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length > 0 ? (
          <div className="viewer-run-browser-list">
            {runs.map((run, runIndex) => {
              const fields = buildRunBrowserMetadataItems(run)
              const isActiveRun = activeRunId === run.run_id
              return (
                <article className="viewer-active-run-card" key={`${run.run_id}:${runIndex}`} aria-label={`Run ${run.run_id}`}>
                  <span className="eyebrow">{isActiveRun ? 'Active Viewer run' : 'Available Viewer run'}</span>
                  <h4>{run.run_id}</h4>
                  {isActiveRun ? <p className="status">Currently selected for active-run Viewer pages.</p> : null}
                  <ViewerMetadataList ariaLabel={`Run ${run.run_id} metadata`} items={fields} />
                  <div className="viewer-run-browser-links" aria-label={`Run ${run.run_id} primary links`}>
                    <h5>Run entry points</h5>
                    <ViewerActiveRunLinks layout="grid" links={buildRunBrowserPrimaryLinks(run.run_id)} />
                  </div>
                  <div className="viewer-run-browser-links" aria-label={`Run ${run.run_id} context links`}>
                    <h5>Context and history</h5>
                    <ViewerActiveRunLinks layout="grid" links={buildRunBrowserContextLinks(run.run_id)} />
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>
    </ViewerShellPage>
  )
}
