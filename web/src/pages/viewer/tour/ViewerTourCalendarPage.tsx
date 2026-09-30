import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { ViewerJumpToWeekButton } from '../../../components/ViewerContextControls'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerSeasonCalendarPath } from '../../../viewer/viewerRoutes'

export function ViewerTourCalendarPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const calendarQuery = useQuery({
    queryKey: ['viewer-tour-calendar-saved-revision', productRunId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false
  })

  return (
    <ViewerShellPage
      title="Season Calendar"
      description="Read-only Saved-Revision season timeline and schedule destination for weekly tour browsing."
    >
      <div className="viewer-jump-demo" aria-label="Jump to Week demo">
        <p className="status">Schedule metadata comes from the selected Product Run Saved Revision.</p>
        <ViewerJumpToWeekButton week={24} />
      </div>

      {productRunId ? (
        <article className="viewer-active-run-card" aria-label="Saved Calendar summary">
          <span className="eyebrow">Selected Product Run</span>
          <h3>Open canonical run schedule</h3>
          {calendarQuery.isLoading ? <p className="status">Loading Saved Calendar…</p> : null}
          {calendarQuery.isError ? (
            <ViewerEmptyState>Saved Calendar metadata is temporarily unavailable.</ViewerEmptyState>
          ) : null}
          {calendarQuery.data ? (
            <dl className="metadata-list">
              <div><dt>Product Run</dt><dd>{calendarQuery.data.product_run_id}</dd></div>
              <div><dt>Viewer Branch</dt><dd>{calendarQuery.data.viewer_branch_id}</dd></div>
              <div><dt>Saved seasons</dt><dd>{calendarQuery.data.season_count}</dd></div>
              <div><dt>Saved events</dt><dd>{calendarQuery.data.event_count}</dd></div>
            </dl>
          ) : null}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(productRunId)}>
            Open active run schedule
          </Link>
        </article>
      ) : (
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      )}
    </ViewerShellPage>
  )
}
