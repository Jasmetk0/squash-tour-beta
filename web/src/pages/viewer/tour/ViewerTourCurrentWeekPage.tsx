import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getRun } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useViewerContext } from '../../../viewer/ViewerContext'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerRunsPath, viewerSeasonCalendarPath } from '../../../viewer/viewerRoutes'
import { renderOrderedEventMetadata } from './viewerTourEventRender'

export function ViewerCurrentWeekPage(): JSX.Element {
  const context = useViewerContext()
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-current-week-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Current Week" description="Read-only current week schedule for the active Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const eventsForWeek = (runQuery.data?.season_state.ordered_events ?? []).filter((event) => event.week === context.selectedWeek)

  return (
    <ViewerShellPage title="Current Week" description="Read-only current week schedule from the active Viewer run calendar.">
      <article className="viewer-active-run-card" aria-label="Current Week active run summary">
        <span className="eyebrow">Selected Viewer week</span>
        <h3>Season {context.selectedSeason} · W{context.selectedWeek}</h3>
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Selected season</dt><dd>{context.selectedSeason}</dd></div>
          <div><dt>Selected week</dt><dd>{context.selectedWeek}</dd></div>
        </dl>
        {runQuery.isLoading ? <p className="status">Loading selected-week events…</p> : null}
        {runQuery.isError ? <ViewerEmptyState>Selected-week event metadata is temporarily unavailable.</ViewerEmptyState> : null}
        {!runQuery.isLoading && !runQuery.isError && !eventsForWeek.length ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        {eventsForWeek.length ? (
          <ul className="viewer-home-list" aria-label="Selected week ordered events">
            {eventsForWeek.map((event) => (
              <li key={event.event_id}>{renderOrderedEventMetadata(event, activeRunId)}</li>
            ))}
          </ul>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
