import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getRaceSnapshot,
  getRankingSnapshot,
  getRun,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots
} from '../api/client'
import type { RankingSnapshot, SeasonStateResponse } from '../api/types'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  JsonPayloadBlock,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { getPlannedEventStatus } from './plannedEventUtils'
import type { PlannedEventStatus } from './plannedEventUtils'

type SnapshotMode = 'ranking' | 'race'

type PlannedEventContext = {
  eventId: string
  season: number
  week: number
  tour: string
  category: string
  templateId: string
  planPosition: number
  plannedStatus: PlannedEventStatus
}

export function SnapshotDetailPage({ mode }: { mode: SnapshotMode }): JSX.Element {
  const { runId = '', snapshotSequence = '' } = useParams()
  const parsedSequence = Number.parseInt(snapshotSequence, 10)
  const isValidSequence = Number.isInteger(parsedSequence) && parsedSequence > 0

  const snapshotQuery = useQuery({
    queryKey: [`${mode}-snapshot`, runId, parsedSequence],
    queryFn: () => (mode === 'ranking' ? getRankingSnapshot(runId, parsedSequence) : getRaceSnapshot(runId, parsedSequence)),
    enabled: Boolean(runId && isValidSequence),
    retry: false
  })

  const snapshotsQuery = useQuery({
    queryKey: [`${mode}-snapshots`, runId],
    queryFn: () => (mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId && isValidSequence)
  })

  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId && isValidSequence)
  })

  const eventsQuery = useQuery({
    queryKey: ['events', runId],
    queryFn: () => listEvents(runId),
    enabled: Boolean(runId && isValidSequence)
  })

  const siblingMode: SnapshotMode = mode === 'ranking' ? 'race' : 'ranking'
  const siblingSnapshotsQuery = useQuery({
    queryKey: [`${siblingMode}-snapshots`, runId],
    queryFn: () => (siblingMode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId && isValidSequence)
  })

  const snapshot = snapshotQuery.data ?? null
  const sourceEventId = snapshot?.source_event_id ?? null
  const neighboringSnapshots = snapshotsQuery.data?.snapshots ?? []
  const currentSnapshotIndex = neighboringSnapshots.findIndex((item) => item.snapshot_sequence === parsedSequence)
  const previousSnapshot = currentSnapshotIndex > 0 ? neighboringSnapshots[currentSnapshotIndex - 1] : null
  const nextSnapshot =
    currentSnapshotIndex >= 0 && currentSnapshotIndex < neighboringSnapshots.length - 1
      ? neighboringSnapshots[currentSnapshotIndex + 1]
      : null
  const title = mode === 'ranking' ? 'Ranking snapshot detail' : 'Race snapshot detail'
  const persistedSourceEvent = sourceEventId
    ? (eventsQuery.data?.events.find((event) => event.event_id === sourceEventId) ?? null)
    : null
  const plannedSourceEvent = sourceEventId ? findPlannedEventContext(runQuery.data, sourceEventId) : null
  const relatedSiblingSnapshots = sourceEventId
    ? (siblingSnapshotsQuery.data?.snapshots.filter((item) => item.source_event_id === sourceEventId) ?? [])
    : []

  return (
    <section className="panel">
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle="Inspect snapshot metadata and payload for a single history snapshot sequence."
      />

      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Mode', value: mode },
          { label: 'Sequence', value: snapshotSequence || 'unknown' },
          { label: 'Status', value: snapshot ? 'Loaded' : 'Pending' }
        ]}
      />

      <SectionCard title="Snapshot context">
        <SummaryPills
          items={[
            {
              label: 'Previous snapshot',
              value: previousSnapshot ? (
                <Link to={`/runs/${runId}/snapshots/${mode}/${previousSnapshot.snapshot_sequence}`}>
                  #{previousSnapshot.snapshot_sequence}
                </Link>
              ) : (
                'None (start of history)'
              )
            },
            {
              label: 'Next snapshot',
              value: nextSnapshot ? (
                <Link to={`/runs/${runId}/snapshots/${mode}/${nextSnapshot.snapshot_sequence}`}>#{nextSnapshot.snapshot_sequence}</Link>
              ) : (
                'None (latest snapshot)'
              )
            }
          ]}
        />
        <p>
          <Link to={`/runs/${runId}/snapshots/${mode}`}>Back to {mode} snapshots history</Link>
        </p>
      </SectionCard>

      {!snapshotSequence && (
        <SectionCard title="Snapshot lookup">
          <EmptyState message="No snapshot sequence was provided in the URL." />
        </SectionCard>
      )}

      {snapshotSequence && !isValidSequence && (
        <SectionCard title="Snapshot lookup">
          <EmptyState message={`Snapshot sequence "${snapshotSequence}" is invalid. Use a positive integer sequence.`} />
        </SectionCard>
      )}

      {snapshotSequence && isValidSequence && (
        <>
          <SectionCard title="Snapshot summary">
            {snapshotQuery.isLoading && <p className="status">Loading snapshot details...</p>}
            {snapshotQuery.error && !isApiNotFound(snapshotQuery.error) && (
              <p className="error">Failed to load snapshot details: {formatApiError(snapshotQuery.error)}</p>
            )}
            {isApiNotFound(snapshotQuery.error) && (
              <EmptyState message={`Snapshot sequence ${snapshotSequence} was not found for this run.`} />
            )}
            {snapshot && <SnapshotSummary mode={mode} snapshot={snapshot} runId={runId} />}
          </SectionCard>

          {snapshot ? (
            <SectionCard title="Source event context">
              <SourceEventContext
                runId={runId}
                sourceEventId={sourceEventId}
                persistedSourceEventSequence={persistedSourceEvent?.event_sequence ?? null}
                plannedSourceEvent={plannedSourceEvent}
                relatedSiblingSnapshots={relatedSiblingSnapshots}
                siblingMode={siblingMode}
              />
            </SectionCard>
          ) : null}

          <SectionCard title="Raw snapshot payload">
            {snapshot && (
              <JsonPayloadBlock
                title="Snapshot record"
                emptyText="No snapshot payload is available for this snapshot."
                payload={snapshot.payload}
              />
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}

function SnapshotSummary({ mode, snapshot, runId }: { mode: SnapshotMode; snapshot: RankingSnapshot; runId: string }): JSX.Element {
  return (
    <CompactSummaryCard
      items={[
        { label: 'Sequence', value: snapshot.snapshot_sequence },
        { label: 'Kind', value: snapshot.snapshot_kind },
        { label: 'Mode', value: mode },
        { label: 'Source event ID', value: snapshot.source_event_id ?? '—' },
        {
          label: 'Navigation',
          value: <Link to={`/runs/${runId}/snapshots/${mode}`}>Back to snapshot history</Link>
        }
      ]}
    />
  )
}

function SourceEventContext({
  runId,
  sourceEventId,
  persistedSourceEventSequence,
  plannedSourceEvent,
  relatedSiblingSnapshots,
  siblingMode
}: {
  runId: string
  sourceEventId: string | null
  persistedSourceEventSequence: number | null
  plannedSourceEvent: PlannedEventContext | null
  relatedSiblingSnapshots: RankingSnapshot[]
  siblingMode: SnapshotMode
}): JSX.Element {
  if (!sourceEventId) {
    return <EmptyState message="This snapshot has no source_event_id, so event-level context links are unavailable." />
  }

  return (
    <>
      <CompactSummaryCard
        items={[
          { label: 'Source event ID', value: sourceEventId },
          {
            label: 'Persisted event',
            value:
              persistedSourceEventSequence !== null
                ? `Found (event sequence ${persistedSourceEventSequence})`
                : 'Not found in persisted event history'
          },
          { label: 'Season plan context', value: plannedSourceEvent ? 'Found in ordered season plan' : 'No ordered-plan match' }
        ]}
      />

      <p>
        <Link to={`/runs/${runId}/events`}>Open events history</Link> ·{' '}
        <Link to={`/runs/${runId}/calendar`}>Open season calendar</Link> · <Link to={`/runs/${runId}/activity`}>Open activity</Link>
      </p>

      <p>
        {persistedSourceEventSequence !== null ? (
          <Link to={`/runs/${runId}/events/${encodeURIComponent(sourceEventId)}`}>Open source event detail</Link>
        ) : (
          <span>Source event detail unavailable (event not present in persisted event history).</span>
        )}{' '}
        · <Link to={`/runs/${runId}/calendar/${encodeURIComponent(sourceEventId)}`}>Open planned-event detail</Link>
        {plannedSourceEvent ? (
          <>
            {' '}
            · <Link to={`/runs/${runId}/weeks/${plannedSourceEvent.week}`}>Open week detail (W{plannedSourceEvent.week})</Link>
          </>
        ) : null}
      </p>

      {plannedSourceEvent ? (
        <MetadataList
          items={[
            { label: 'Season', value: plannedSourceEvent.season },
            { label: 'Week', value: plannedSourceEvent.week },
            { label: 'Tour', value: plannedSourceEvent.tour },
            { label: 'Category', value: plannedSourceEvent.category },
            { label: 'Template ID', value: plannedSourceEvent.templateId },
            { label: 'Plan position', value: plannedSourceEvent.planPosition },
            { label: 'Planned status', value: plannedSourceEvent.plannedStatus }
          ]}
        />
      ) : (
        <EmptyState message="source_event_id is present, but this event is not in season_state.ordered_events for the current run." />
      )}

      {relatedSiblingSnapshots.length > 0 ? (
        <>
          <h4>Related {siblingMode} snapshots from the same source event</h4>
          <ul className="item-list" aria-label={`Related ${siblingMode} snapshots`}>
            {relatedSiblingSnapshots.map((item) => (
              <li key={`${siblingMode}-${item.snapshot_sequence}`}>
                <Link to={`/runs/${runId}/snapshots/${siblingMode}/${item.snapshot_sequence}`}>
                  {siblingMode} snapshot #{item.snapshot_sequence}
                </Link>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </>
  )
}

function findPlannedEventContext(runData: SeasonStateResponse | undefined, eventId: string): PlannedEventContext | null {
  const orderedEvents = runData?.season_state?.ordered_events ?? []
  const matchedIndex = orderedEvents.findIndex((event) => event.event_id === eventId)
  if (matchedIndex < 0) {
    return null
  }

  const matchedEvent = orderedEvents[matchedIndex]
  const completedEventIds = new Set(runData?.season_state?.completed_event_ids ?? [])
  const nextEventIndex = runData?.season_state?.next_event_index ?? 0
  const plannedStatus = getPlannedEventStatus({
    index: matchedIndex,
    nextEventIndex,
    completedEventIds,
    eventId
  })

  return {
    eventId,
    season: matchedEvent.season,
    week: matchedEvent.week,
    tour: matchedEvent.tour,
    category: matchedEvent.category,
    templateId: matchedEvent.template_id,
    planPosition: matchedIndex + 1,
    plannedStatus
  }
}
