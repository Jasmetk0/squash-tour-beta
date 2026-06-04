import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getFinalsSummary, getRun, getRunStatusSummary, listEvents } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerFinalsPath, viewerRunsPath, viewerSeasonCalendarPath, viewerTournamentsPath } from '../../../viewer/viewerRoutes'
import { buildPlannedEventMap, formatFinalsAvailability, selectLatestPersistedEvent, selectNextOrderedEvent } from './viewerTourDisplay'
import { renderEventSummary, renderPersistedEventSummary } from './viewerTourEventRender'

export function ViewerSeasonHubPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()

  const runQuery = useQuery({ queryKey: ['viewer-season-hub-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-season-hub-status', activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-season-hub-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-season-hub-finals', activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="Season Hub" description="Read-only season hub for the selected Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const persistedEvents = eventsQuery.data?.events ?? []
  const plannedMap = buildPlannedEventMap(runQuery.data)
  const nextEvent = selectNextOrderedEvent(runQuery.data)
  const latestPersistedEvent = selectLatestPersistedEvent(persistedEvents)
  const progress = statusQuery.data?.progress
  const season = statusQuery.data?.season ?? runQuery.data?.season_state.season ?? runQuery.data?.run.season ?? '—'
  const eventCount = orderedEvents.length || runQuery.data?.run.total_events || persistedEvents.length

  return (
    <ViewerShellPage title="Season Hub" description="Read-only top-level season summary from the active Viewer run's existing calendar and event APIs.">
      <article className="viewer-active-run-card" aria-label="Season Hub active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>Season Hub summary</h3>
        {runQuery.isLoading || statusQuery.isLoading || eventsQuery.isLoading || finalsQuery.isLoading ? <p className="status">Loading active run tour summary…</p> : null}
        {runQuery.isError || statusQuery.isError || eventsQuery.isError || finalsQuery.isError ? <ViewerEmptyState>Some active run tour metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Season</dt><dd>{season}</dd></div>
          <div><dt>Progress</dt><dd>{progress ? `${progress.completed_event_count}/${progress.total_events} events complete` : `${runQuery.data?.run.completed_event_ids.length ?? persistedEvents.length}/${eventCount} events complete`}</dd></div>
          <div><dt>Next event index</dt><dd>{progress?.next_event_index ?? runQuery.data?.season_state.next_event_index ?? runQuery.data?.run.next_event_index ?? '—'}</dd></div>
          <div><dt>Event count</dt><dd>{eventCount}</dd></div>
          <div><dt>Next scheduled event</dt><dd>{nextEvent ? renderEventSummary(nextEvent, activeRunId) : '—'}</dd></div>
          <div><dt>Most recent persisted event</dt><dd>{renderPersistedEventSummary(latestPersistedEvent, plannedMap, activeRunId)}</dd></div>
          <div><dt>Finals availability</dt><dd>{formatFinalsAvailability(finalsQuery.data)}</dd></div>
        </dl>
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(activeRunId)}>Open active run tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsPath(activeRunId)}>Open active run finals</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
