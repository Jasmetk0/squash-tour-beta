import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getRun, listEvents } from '../../../api/client'
import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { viewerRunsPath, viewerSeasonCalendarPath, viewerTournamentsPath } from '../../../viewer/viewerRoutes'
import { buildPlannedEventMap, selectLatestPersistedEvent, selectNextOrderedEvent } from './viewerTourDisplay'
import { renderEventSummary, renderOrderedEventMetadata, renderPersistedEventSummary } from './viewerTourEventRender'

export function ViewerTournamentsPage(): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const runQuery = useQuery({ queryKey: ['viewer-tournaments-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-tournaments-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })

  if (!activeRunId) {
    return (
      <ViewerShellPage title="All Tournaments" description="Read-only tournament schedule and results archive for the selected Viewer run.">
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const persistedEvents = eventsQuery.data?.events ?? []
  const plannedMap = buildPlannedEventMap(runQuery.data)
  const nextEvent = selectNextOrderedEvent(runQuery.data)
  const latestPersistedEvent = selectLatestPersistedEvent(persistedEvents)
  const sampleEvents = orderedEvents.slice(0, 5)
  const hasMetadata = orderedEvents.length > 0 || persistedEvents.length > 0

  return (
    <ViewerShellPage title="All Tournaments" description="Read-only tournament schedule and publications from the active Viewer run.">
      <article className="viewer-active-run-card" aria-label="All Tournaments active run summary">
        <span className="eyebrow">Active Viewer run</span>
        <h3>All Tournaments summary</h3>
        {runQuery.isLoading || eventsQuery.isLoading ? <p className="status">Loading tournament metadata…</p> : null}
        {runQuery.isError || eventsQuery.isError ? <ViewerEmptyState>Tournament metadata is temporarily unavailable for this run.</ViewerEmptyState> : null}
        <dl className="metadata-list">
          <div><dt>Active run ID</dt><dd>{activeRunId}</dd></div>
          <div><dt>Total ordered calendar events</dt><dd>{runQuery.isLoading ? 'Loading…' : orderedEvents.length || '—'}</dd></div>
          <div><dt>Persisted event count</dt><dd>{eventsQuery.isLoading ? 'Loading…' : persistedEvents.length}</dd></div>
          <div><dt>Next scheduled event</dt><dd>{nextEvent ? renderEventSummary(nextEvent, activeRunId) : '—'}</dd></div>
          <div><dt>Latest persisted event</dt><dd>{renderPersistedEventSummary(latestPersistedEvent, plannedMap, activeRunId)}</dd></div>
        </dl>
        {!runQuery.isLoading && !eventsQuery.isLoading && !runQuery.isError && !eventsQuery.isError && !hasMetadata ? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState> : null}
        {sampleEvents.length ? (
          <div>
            <h4>Sample schedule events</h4>
            <ul className="viewer-home-list" aria-label="Sample ordered tournament events">
              {sampleEvents.map((event) => (
                <li key={event.event_id}>{renderOrderedEventMetadata(event, activeRunId)}</li>
              ))}
            </ul>
          </div>
        ) : null}
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(activeRunId)}>Open active run tournaments</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
        </p>
      </article>
    </ViewerShellPage>
  )
}
