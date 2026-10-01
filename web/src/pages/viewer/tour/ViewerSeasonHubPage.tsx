import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerFinalsRace, getViewerRunCalendar, getViewerTournamentHistory } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import {
  viewerFinalsPath,
  viewerPlannedEventPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath,
  viewerWeekDetailPath,
} from '../../../viewer/viewerRoutes'

export function ViewerSeasonHubPage(): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const calendarQuery = useQuery({
    queryKey: ['viewer-season-hub-calendar', productRunId],
    queryFn: () => getViewerRunCalendar(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-season-hub-history', productRunId],
    queryFn: () => getViewerTournamentHistory(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })
  const finalsQuery = useQuery({
    queryKey: ['viewer-season-hub-finals-race', productRunId],
    queryFn: () => getViewerFinalsRace(productRunId ?? ''),
    enabled: Boolean(productRunId),
    retry: false,
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title="Season Hub" description="Read-only canonical season hub for the selected Product Run.">
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const seasons = calendarQuery.data?.seasons ?? []
  const orderedEvents = seasons.flatMap((season) => season.events)
  const history = historyQuery.data?.tournaments ?? []
  const resultIds = new Set(history.filter((event) => event.result_published).map((event) => event.event_id))
  const nextScheduled = orderedEvents.find((event) => !resultIds.has(event.event_id)) ?? null
  const latestPublished = [...history]
    .filter((event) => event.result_published)
    .sort((a, b) => String(b.season).localeCompare(String(a.season)) || b.season_week - a.season_week)[0] ?? null
  const latestFinals = finalsQuery.data?.publications.at(-1) ?? null
  const isLoading = calendarQuery.isLoading || historyQuery.isLoading || finalsQuery.isLoading
  const hasError = calendarQuery.isError || historyQuery.isError || finalsQuery.isError

  return (
    <ViewerShellPage title="Season Hub" description="Read-only Saved-Revision season summary for the selected Product Run.">
      <article className="viewer-active-run-card" aria-label="Season Hub canonical Product Run summary">
        <span className="eyebrow">Selected Product Run</span>
        <h3>Season Hub summary</h3>
        {isLoading ? <p className="status">Loading canonical tour summary…</p> : null}
        {hasError ? <ViewerEmptyState>Some canonical tour metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Product Run</dt><dd>{productRunId}</dd></div>
          <div><dt>Viewer Branch</dt><dd>{calendarQuery.data?.viewer_branch_id ?? historyQuery.data?.viewer_branch_id ?? finalsQuery.data?.viewer_branch_id ?? '—'}</dd></div>
          <div><dt>Season count</dt><dd>{calendarQuery.data?.season_count ?? '—'}</dd></div>
          <div><dt>Calendar event count</dt><dd>{calendarQuery.data?.event_count ?? '—'}</dd></div>
          <div><dt>Published tournament results</dt><dd>{historyQuery.data?.published_result_count ?? '—'}</dd></div>
          <div><dt>Next scheduled event</dt><dd>{nextScheduled ? <Link to={viewerPlannedEventPath(productRunId, nextScheduled.event_id)}>{nextScheduled.event_name || nextScheduled.event_id}</Link> : '—'}</dd></div>
          <div><dt>Latest published result</dt><dd>{latestPublished ? <Link to={viewerPlannedEventPath(productRunId, latestPublished.event_id)}>{latestPublished.event_name || latestPublished.event_id}</Link> : '—'}</dd></div>
          <div><dt>Finals Race publication</dt><dd>{latestFinals ? `S${latestFinals.target_season_index} · cutoff S${latestFinals.cutoff_season_index} W${latestFinals.cutoff_week}` : 'Not published yet'}</dd></div>
        </dl>
        {nextScheduled ? (
          <p className="status">
            Next event: <Link to={viewerWeekDetailPath(productRunId, nextScheduled.season_week)}>W{nextScheduled.season_week}</Link> · {nextScheduled.category} · {nextScheduled.tour_level ?? '—'}
          </p>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(productRunId)}>Open Product Run tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(productRunId)}>Open Product Run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsPath(productRunId)}>Open Product Run finals</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
