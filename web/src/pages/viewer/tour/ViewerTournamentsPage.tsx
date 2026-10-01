import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerPlannedEventPath, viewerRunsPath, viewerSeasonCalendarPath, viewerTournamentsPath, viewerWeekDetailPath } from '../../../viewer/viewerRoutes'

export function ViewerTournamentsPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const calendarQuery = useQuery({
    queryKey: ['viewer-tournaments-calendar', productRunId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournaments-history', productRunId],
    queryFn: () => getViewerTournamentHistory(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title="All Tournaments" description="Read-only canonical tournament schedule and results archive.">
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const events = calendarQuery.data?.seasons.flatMap((season) => season.events) ?? []
  const published = historyQuery.data?.tournaments.filter((event) => event.result_published) ?? []
  const sampleEvents = events.slice(0, 8)
  const isLoading = calendarQuery.isLoading || historyQuery.isLoading
  const hasError = calendarQuery.isError || historyQuery.isError

  return (
    <ViewerShellPage title="All Tournaments" description="Read-only Saved-Revision tournament schedule and published result metadata.">
      <article className="viewer-active-run-card" aria-label="All Tournaments canonical Product Run summary">
        <span className="eyebrow">Selected Product Run</span>
        <h3>All Tournaments summary</h3>
        {isLoading ? <p className="status">Loading canonical tournament metadata…</p> : null}
        {hasError ? <ViewerEmptyState>Canonical tournament metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Viewer Branch</dt><dd>{calendarQuery.data?.viewer_branch_id ?? historyQuery.data?.viewer_branch_id ?? '—'}</dd></div>
          <div><dt>Total calendar events</dt><dd>{calendarQuery.data?.event_count ?? '—'}</dd></div>
          <div><dt>Published result count</dt><dd>{historyQuery.data?.published_result_count ?? '—'}</dd></div>
        </dl>
        {!isLoading && !hasError && !events.length ? <ViewerEmptyState>No canonical tournament data is available yet.</ViewerEmptyState> : null}
        {sampleEvents.length ? (
          <div>
            <h4>Sample schedule events</h4>
            <ul className="viewer-home-list" aria-label="Sample canonical tournament events">
              {sampleEvents.map((event) => (
                <li key={event.event_id}>
                  <dl className="metadata-list">
                    <div><dt>Event</dt><dd><Link to={viewerPlannedEventPath(productRunId, event.event_id)}>{event.event_name || event.event_id}</Link></dd></div>
                    <div><dt>Week</dt><dd><Link to={viewerWeekDetailPath(productRunId, event.season_week)}>W{event.season_week}</Link></dd></div>
                    <div><dt>Category</dt><dd>{event.category}</dd></div>
                    <div><dt>Tour</dt><dd>{event.tour_level ?? '—'}</dd></div>
                    <div><dt>Status</dt><dd>{event.status}</dd></div>
                  </dl>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {published.length ? <p className="status">{published.length} tournament result publication(s) are available in canonical history.</p> : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(productRunId)}>Open Product Run tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(productRunId)}>Open Product Run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
