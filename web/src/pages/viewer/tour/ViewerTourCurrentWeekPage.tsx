import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useViewerContext } from '../../../viewer/ViewerContext'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerPlannedEventPath, viewerRunsPath, viewerSeasonCalendarPath } from '../../../viewer/viewerRoutes'

export function ViewerCurrentWeekPage(): JSX.Element {
  const context = useViewerContext()
  const productRunId = useActiveViewerProductRunId()
  const calendarQuery = useQuery({
    queryKey: ['viewer-current-week-calendar', productRunId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title="Current Week" description="Read-only canonical current-week schedule.">
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const selectedSeason = String(context.selectedSeason)
  const eventsForWeek = (calendarQuery.data?.seasons ?? [])
    .filter((season) => String(season.season) === selectedSeason)
    .flatMap((season) => season.events)
    .filter((event) => event.season_week === context.selectedWeek)

  return (
    <ViewerShellPage title="Current Week" description="Read-only selected-week schedule from canonical Saved Calendar authority.">
      <article className="viewer-active-run-card" aria-label="Current Week canonical Product Run summary">
        <span className="eyebrow">Selected Viewer week</span>
        <h3>Season {context.selectedSeason} · W{context.selectedWeek}</h3>
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Viewer Branch</dt><dd>{calendarQuery.data?.viewer_branch_id ?? '—'}</dd></div>
          <div><dt>Selected season</dt><dd>{context.selectedSeason}</dd></div>
          <div><dt>Selected week</dt><dd>{context.selectedWeek}</dd></div>
        </dl>
        {calendarQuery.isLoading ? <p className="status">Loading canonical selected-week events…</p> : null}
        {calendarQuery.isError ? <ViewerEmptyState>Canonical selected-week event metadata is temporarily unavailable.</ViewerEmptyState> : null}
        {!calendarQuery.isLoading && !calendarQuery.isError && !eventsForWeek.length ? <ViewerEmptyState>No canonical events are scheduled for this selected week.</ViewerEmptyState> : null}
        {eventsForWeek.length ? (
          <ul className="viewer-home-list" aria-label="Selected week canonical events">
            {eventsForWeek.map((event) => (
              <li key={event.event_id}>
                <Link to={viewerPlannedEventPath(productRunId, event.event_id)}>{event.event_name || event.event_id}</Link> · {event.category} · {event.tour_level ?? '—'} · {event.status}
              </li>
            ))}
          </ul>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(productRunId)}>Open Product Run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
