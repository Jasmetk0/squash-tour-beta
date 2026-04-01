import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRun, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { getPlannedEventStatus, getWeekStatus, getWeeksInSeasonOrder } from './plannedEventUtils'

export function WeekDetailPage(): JSX.Element {
  const { runId = '', week = '' } = useParams()

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const eventsQuery = useQuery({
    queryKey: ['events', runId],
    queryFn: () => listEvents(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['ranking-snapshots', runId],
    queryFn: () => listRankingSnapshots(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['race-snapshots', runId],
    queryFn: () => listRaceSnapshots(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const nextEventIndex = runQuery.data?.season_state.next_event_index ?? 0
  const completedEventIds = new Set(runQuery.data?.season_state.completed_event_ids ?? [])
  const persistedEventIds = new Set((eventsQuery.data?.events ?? []).map((event) => event.event_id))

  const parsedWeek = Number.parseInt(week, 10)
  const hasValidWeekParam = Number.isInteger(parsedWeek) && String(parsedWeek) === week

  const orderedWeeks = getWeeksInSeasonOrder(orderedEvents)
  const weekPosition = hasValidWeekParam ? orderedWeeks.indexOf(parsedWeek) : -1
  const weekExists = weekPosition >= 0

  const weekEvents = weekExists ? orderedEvents.filter((event) => event.week === parsedWeek) : []
  const weekEventIds = new Set(weekEvents.map((event) => event.event_id))

  const weekStatus =
    weekEvents.length > 0
      ? getWeekStatus(
          weekEvents.map((event) => {
            const index = orderedEvents.indexOf(event)
            return getPlannedEventStatus({
              index,
              nextEventIndex,
              completedEventIds,
              eventId: event.event_id
            })
          })
        )
      : null

  const relatedRankingSnapshots = (rankingSnapshotsQuery.data?.snapshots ?? []).filter((snapshot) =>
    snapshot.source_event_id ? weekEventIds.has(snapshot.source_event_id) : false
  )
  const relatedRaceSnapshots = (raceSnapshotsQuery.data?.snapshots ?? []).filter((snapshot) =>
    snapshot.source_event_id ? weekEventIds.has(snapshot.source_event_id) : false
  )

  const previousWeek = weekPosition > 0 ? orderedWeeks[weekPosition - 1] : null
  const nextWeek = weekPosition >= 0 && weekPosition < orderedWeeks.length - 1 ? orderedWeeks[weekPosition + 1] : null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Week detail"
        runId={runId}
        subtitle="Read-only weekly hub connecting planned events, persisted details, and generated snapshots."
      />

      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
          { label: 'Week', value: week ? `W${week}` : '—' }
        ]}
      />

      <SectionCard title="Week context">
        <p>
          <Link to={`/runs/${runId}/calendar`}>Back to Season Calendar</Link>
          {' · '}
          <Link to={`/runs/${runId}`}>Back to Run Detail</Link>
          {' · '}
          <Link to={`/runs/${runId}/events`}>Open persisted Events history</Link>
        </p>
      </SectionCard>

      <SectionCard title="Week summary">
        {runQuery.isLoading ? <p className="status">Loading week detail...</p> : null}
        {runQuery.error ? <p className="error">Failed to load run season state: {formatApiError(runQuery.error)}</p> : null}
        {hasValidWeekParam && runQuery.data && !weekExists ? (
          <EmptyState message={`Week ${parsedWeek} is not present in this run's ordered season plan.`} />
        ) : null}
        {!hasValidWeekParam ? <EmptyState message="Week must be a whole number in the URL (for example /weeks/12)." /> : null}

        {weekExists ? (
          <>
            <SummaryPills
              items={[
                { label: 'Week status', value: weekStatus ?? '—' },
                { label: 'Planned events', value: weekEvents.length },
                { label: 'Persisted events', value: weekEvents.filter((event) => persistedEventIds.has(event.event_id)).length }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: runId },
                { label: 'Season', value: runQuery.data?.season_state.season ?? '—' },
                { label: 'Week', value: parsedWeek }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      {weekExists ? (
        <SectionCard title="Planned events in week">
          <ol className="item-list" aria-label="Week planned events">
            {weekEvents.map((event) => {
              const index = orderedEvents.indexOf(event)
              const plannedStatus = getPlannedEventStatus({
                index,
                nextEventIndex,
                completedEventIds,
                eventId: event.event_id
              })
              const hasPersistedDetail = persistedEventIds.has(event.event_id)
              return (
                <li key={event.event_id}>
                  <MetadataList
                    items={[
                      { label: '#', value: index },
                      { label: 'Event ID', value: event.event_id },
                      { label: 'Status', value: plannedStatus },
                      { label: 'Tour', value: event.tour },
                      { label: 'Category', value: event.category },
                      { label: 'Template', value: event.template_id },
                      {
                        label: 'Links',
                        value: (
                          <>
                            <Link to={`/runs/${runId}/calendar/${encodeURIComponent(event.event_id)}`}>Planned detail</Link>
                            {hasPersistedDetail ? (
                              <>
                                {' '}·{' '}
                                <Link to={`/runs/${runId}/events/${encodeURIComponent(event.event_id)}`}>Persisted detail</Link>
                              </>
                            ) : null}
                          </>
                        )
                      }
                    ]}
                  />
                </li>
              )
            })}
          </ol>
          {eventsQuery.error ? <p className="error">Failed to load persisted events: {formatApiError(eventsQuery.error)}</p> : null}
        </SectionCard>
      ) : null}

      {weekExists ? (
        <SectionCard title="Related snapshots in week">
          <MetadataList
            items={[
              {
                label: 'Ranking snapshots',
                value:
                  relatedRankingSnapshots.length > 0 ? (
                    <ul className="item-list">
                      {relatedRankingSnapshots.map((snapshot) => (
                        <li key={`ranking-${snapshot.snapshot_sequence}`}>
                          <Link to={`/runs/${runId}/snapshots/ranking/${snapshot.snapshot_sequence}`}>
                            Ranking snapshot #{snapshot.snapshot_sequence}
                          </Link>
                          {' '}· Event {snapshot.source_event_id}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    'None linked to events in this week.'
                  )
              },
              {
                label: 'Race snapshots',
                value:
                  relatedRaceSnapshots.length > 0 ? (
                    <ul className="item-list">
                      {relatedRaceSnapshots.map((snapshot) => (
                        <li key={`race-${snapshot.snapshot_sequence}`}>
                          <Link to={`/runs/${runId}/snapshots/race/${snapshot.snapshot_sequence}`}>
                            Race snapshot #{snapshot.snapshot_sequence}
                          </Link>
                          {' '}· Event {snapshot.source_event_id}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    'None linked to events in this week.'
                  )
              }
            ]}
          />
          {rankingSnapshotsQuery.error ? (
            <p className="error">Failed to load ranking snapshots: {formatApiError(rankingSnapshotsQuery.error)}</p>
          ) : null}
          {raceSnapshotsQuery.error ? <p className="error">Failed to load race snapshots: {formatApiError(raceSnapshotsQuery.error)}</p> : null}
        </SectionCard>
      ) : null}

      {weekExists ? (
        <SectionCard title="Week navigation">
          <p>
            Previous week:{' '}
            {previousWeek !== null ? <Link to={`/runs/${runId}/weeks/${previousWeek}`}>W{previousWeek}</Link> : <span>None</span>}
            {' · '}
            Next week: {nextWeek !== null ? <Link to={`/runs/${runId}/weeks/${nextWeek}`}>W{nextWeek}</Link> : <span>None</span>}
          </p>
        </SectionCard>
      ) : null}
    </section>
  )
}
