import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getRun } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { ViewerJumpToWeekButton } from '../../../components/ViewerContextControls'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerSeasonCalendarPath } from '../../../viewer/viewerRoutes'

export function ViewerTourCalendarPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-tour-calendar-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const orderedEventCount = runQuery.data?.season_state.ordered_events.length ?? runQuery.data?.run.total_events ?? null

  return (
    <ViewerShellPage title="Season Calendar" description="Read-only season timeline and schedule destination for weekly tour browsing.">
      <div className="viewer-jump-demo" aria-label="Jump to Week demo">
        <p className="status">This section uses existing read-only run data only.</p>
        <ViewerJumpToWeekButton week={24} />
      </div>
      {activeRunId ? (
        <article className="viewer-active-run-card">
          <span className="eyebrow">Active Viewer run</span>
          <h3>Open active run schedule</h3>
          <p className="status">Use the real read-only calendar for Viewer run {activeRunId}.</p>
          <dl className="metadata-list">
            <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
            <div><dt>Ordered event count</dt><dd>{runQuery.isLoading ? 'Loading…' : orderedEventCount ?? '—'}</dd></div>
          </dl>
          {runQuery.isError ? <ViewerEmptyState>Active run calendar metadata is temporarily unavailable.</ViewerEmptyState> : null}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>
            Open active run schedule
          </Link>
        </article>
      ) : (
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      )}
    </ViewerShellPage>
  )
}
