import { useQuery } from '@tanstack/react-query'

import { listRuns } from '../../api/client'
import { ViewerRunSelector } from '../../components/ViewerRunSelector'
import { ViewerShellPage } from '../../components/viewer/ViewerShellPage'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerMetadataList } from '../../components/viewer/ViewerLandingComponents'
import { buildViewerRunBrowserLinks, viewerRunMetadataFields, type ViewerRunBrowserListItem } from '../../viewer/runBrowserDisplay'
import { useActiveViewerRunId } from '../../viewer/useActiveViewerRunId'
import { findViewerTopLevelHubLink } from '../../viewer/viewerHubLinks'

const VIEWER_RUN_BROWSER_HUB_LINK = findViewerTopLevelHubLink('Run Browser')

export function ViewerRunBrowserPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const runsQuery = useQuery({ queryKey: ['viewer-run-selector-runs'], queryFn: listRuns, retry: false })
  const runs = (runsQuery.data?.runs ?? []) as ViewerRunBrowserListItem[]

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
        {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        {!runsQuery.isLoading && !runsQuery.isError && runs.length > 0 ? (
          <div className="viewer-run-browser-list">
            {runs.map((run) => {
              const fields = viewerRunMetadataFields(run)
              return (
                <article className="viewer-active-run-card" key={run.run_id} aria-label={`Run ${run.run_id}`}>
                  <h4>{run.run_id}</h4>
                  <ViewerMetadataList ariaLabel={`Run ${run.run_id} metadata`} items={fields} />
                  <div className="viewer-run-browser-links" aria-label={`Run ${run.run_id} links`}>
                    <h5>Links</h5>
                    <ViewerActiveRunLinks layout="grid" links={buildViewerRunBrowserLinks(run.run_id)} />
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
