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
import type { RaceSnapshot, RankingSnapshot, SeasonStateResponse } from '../api/types'
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

import { useHistoryText } from './runHistoryText'
export function SnapshotDetailPage({ mode }: { mode: SnapshotMode }): JSX.Element {
  const t = useHistoryText()
  const { runId = '', snapshotSequence = '' } = useParams()
  // parseInt accepts invalid route suffixes such as "12abc" or "1.5".
  // Only a complete positive safe integer may identify a stored snapshot.
  const parsedSequence = /^\d+$/.test(snapshotSequence) ? Number(snapshotSequence) : NaN
  const isValidSequence = Number.isSafeInteger(parsedSequence) && parsedSequence > 0

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

  const snapshotMismatch = Boolean(snapshotQuery.data && snapshotQuery.data.snapshot_sequence !== parsedSequence)
  const snapshot = snapshotMismatch ? null : snapshotQuery.data ?? null
  const historyMismatch = Boolean(snapshotsQuery.data?.run_id && snapshotsQuery.data.run_id !== runId)
  const siblingMismatch = Boolean(siblingSnapshotsQuery.data?.run_id && siblingSnapshotsQuery.data.run_id !== runId)
  const eventsMismatch = Boolean(eventsQuery.data?.run_id && eventsQuery.data.run_id !== runId)
  const planSeasonMismatch = Boolean(runQuery.data && runQuery.data.run.run_id === runId &&
    runQuery.data.season_state.season !== runQuery.data.run.season)
  const sourceEventId = snapshot?.source_event_id ?? null
  const neighboringSnapshots = historyMismatch ? [] : (snapshotsQuery.data?.snapshots ?? [])
  const neighborHistoryUnavailable = snapshotsQuery.isLoading || Boolean(snapshotsQuery.error) || historyMismatch ||
    !snapshotsQuery.data || !neighboringSnapshots.some((item) => item.snapshot_sequence === parsedSequence)
  const currentSnapshotIndex = neighboringSnapshots.findIndex((item) => item.snapshot_sequence === parsedSequence)
  const previousSnapshot = currentSnapshotIndex > 0 ? neighboringSnapshots[currentSnapshotIndex - 1] : null
  const nextSnapshot =
    currentSnapshotIndex >= 0 && currentSnapshotIndex < neighboringSnapshots.length - 1
      ? neighboringSnapshots[currentSnapshotIndex + 1]
      : null
  const title = mode === 'ranking' ? t('Ranking snapshot detail') : t('Race snapshot detail')
  const persistedSourceEvent = sourceEventId
    ? (eventsMismatch ? null : eventsQuery.data?.events.find((event) => event.event_id === sourceEventId) ?? null)
    : null
  const plannedCandidate = sourceEventId && runQuery.data?.run.run_id === runId && !planSeasonMismatch
    ? findPlannedEventContext(runQuery.data, sourceEventId) : null
  const plannedSourceEvent = plannedCandidate && (!persistedSourceEvent || persistedSourceEvent.season === plannedCandidate.season)
    ? plannedCandidate : null
  const relatedSiblingUnavailable = siblingSnapshotsQuery.isLoading || Boolean(siblingSnapshotsQuery.error) || siblingMismatch || !siblingSnapshotsQuery.data
  const relatedSiblingSnapshots = sourceEventId
    ? (siblingMismatch ? [] : siblingSnapshotsQuery.data?.snapshots.filter((item) => item.source_event_id === sourceEventId) ?? [])
    : []

  return (
    <section className="panel">
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle={t('Inspect snapshot metadata and payload for a single history snapshot sequence.')}
      />

      <p className="status">{t('Stored historical snapshot; it is not necessarily the current ranking. The endpoint does not provide a timestamp.')}</p>
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Mode'), value: mode },
          { label: t('Sequence'), value: snapshotSequence || 'unknown' },
          { label: t('Status'), value: snapshot ? t('Loaded') : snapshotMismatch ? t('Error') : snapshotQuery.isLoading ? t('Loading') : isApiNotFound(snapshotQuery.error) ? t('Missing') : snapshotQuery.error ? t('Failed') : t('Unavailable') }
        ]}
      />

      <SectionCard title={t('Snapshot context')}>
        <SummaryPills
          items={[
            {
              label: t('Previous snapshot'),
              value: previousSnapshot ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${mode}/${previousSnapshot.snapshot_sequence}`}>
                  #{previousSnapshot.snapshot_sequence}
                </Link>
              ) : (
                neighborHistoryUnavailable ? t('Unavailable') : t('None (start of history)')
              )
            },
            {
              label: t('Next snapshot'),
              value: nextSnapshot ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${mode}/${nextSnapshot.snapshot_sequence}`}>#{nextSnapshot.snapshot_sequence}</Link>
              ) : (
                neighborHistoryUnavailable ? t('Unavailable') : t('None (latest snapshot)')
              )
            }
          ]}
        />
        <p>
          <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${mode}`}>{t('Back to')} {mode} {t('snapshot history')}</Link>
        </p>
      </SectionCard>

      {!snapshotSequence && (
        <SectionCard title={t('Snapshot lookup')}>
          <EmptyState message={t('No snapshot sequence was provided in the URL.')} />
        </SectionCard>
      )}

      {snapshotSequence && !isValidSequence && (
        <SectionCard title={t('Snapshot lookup')}>
          <EmptyState message={`${t('Snapshot sequence')} "${snapshotSequence}" ${t('is invalid. Use a positive integer sequence.')}`} />
        </SectionCard>
      )}

      {snapshotSequence && isValidSequence && (
        <>
          <SectionCard title={t('Snapshot summary')}>
            <button type="button" onClick={() => void snapshotQuery.refetch()}>{t('Refresh read-only data')}</button>
            {snapshotMismatch && <p role="alert" className="error">{t('Snapshot detail does not match the requested sequence.')}</p>}
            {siblingMismatch && <p role="alert" className="error">{t('Snapshot sibling history belongs to another Run.')}</p>}
            {eventsMismatch && <p role="alert" className="error">{t('Event context belongs to another Run.')}</p>}
            {planSeasonMismatch && <p role="alert" className="error">{t('Run season and ordered plan disagree. Planned links are unavailable.')}</p>}
            {historyMismatch && <p role="alert" className="error">{t('Snapshot history belongs to another Run; its records are hidden.')}</p>}
            {snapshotsQuery.error && <p role="alert" className="error">{t('Failed to load snapshots history')}: {formatApiError(snapshotsQuery.error)}</p>}
            {snapshotQuery.isLoading && <p role="status" className="status">{t('Loading snapshot details...')}</p>}
            {snapshotQuery.error && !isApiNotFound(snapshotQuery.error) && (
              <p className="error">{t('Failed to load snapshot details')}: {formatApiError(snapshotQuery.error)}</p>
            )}
            {isApiNotFound(snapshotQuery.error) && (
              <EmptyState message={`${t('Snapshot sequence')} ${snapshotSequence} ${t('was not found for this run.')}`} />
            )}
            {snapshot && <SnapshotSummary mode={mode} snapshot={snapshot} runId={runId} />}
          </SectionCard>

          {snapshot ? (
            <SectionCard title={t('Source event context')}>
              <SourceEventContext
                runId={runId}
                sourceEventId={sourceEventId}
                persistedSourceEventSequence={persistedSourceEvent?.event_sequence ?? null}
                persistedSourceEventUnavailable={eventsQuery.isLoading || Boolean(eventsQuery.error) || eventsMismatch}
                plannedSourceEvent={plannedSourceEvent}
                plannedSourceEventUnavailable={runQuery.isLoading || Boolean(runQuery.error) || runQuery.data?.run.run_id !== runId || planSeasonMismatch}
                relatedSiblingSnapshots={relatedSiblingSnapshots}
                siblingMode={siblingMode}
                relatedSiblingUnavailable={relatedSiblingUnavailable}
              />
            </SectionCard>
          ) : null}

          <SectionCard title={t('Raw snapshot payload')}>
            {snapshot && (
              <JsonPayloadBlock
                title={t('Snapshot record')}
                emptyText={t('No snapshot payload is available for this snapshot.')}
                payload={snapshot.payload}
              />
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}

function SnapshotSummary({
  mode,
  snapshot,
  runId
}: {
  mode: SnapshotMode
  snapshot: RankingSnapshot | RaceSnapshot
  runId: string
}): JSX.Element {
  const t = useHistoryText()
  return (
    <CompactSummaryCard
      items={[
        { label: t('Sequence'), value: snapshot.snapshot_sequence },
        { label: t('Kind'), value: snapshot.snapshot_kind },
        { label: t('Mode'), value: mode },
        { label: t('Source event ID'), value: snapshot.source_event_id ?? '—' },
        {
          label: t('Navigation'),
          value: <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${mode}`}>{t('Back to snapshot history')}</Link>
        }
      ]}
    />
  )
}

function SourceEventContext({
  runId,
  sourceEventId,
  persistedSourceEventSequence,
  persistedSourceEventUnavailable,
  plannedSourceEvent,
  plannedSourceEventUnavailable,
  relatedSiblingSnapshots,
  siblingMode,
  relatedSiblingUnavailable
}: {
  runId: string
  sourceEventId: string | null
  persistedSourceEventSequence: number | null
  persistedSourceEventUnavailable: boolean
  plannedSourceEvent: PlannedEventContext | null
  plannedSourceEventUnavailable: boolean
  relatedSiblingSnapshots: Array<RankingSnapshot | RaceSnapshot>
  siblingMode: SnapshotMode
  relatedSiblingUnavailable: boolean
}): JSX.Element {
  const t = useHistoryText()
  if (!sourceEventId) {
    return <EmptyState message={t('This snapshot has no source_event_id, so event-level context links are unavailable.')} />
  }

  return (
    <>
      <CompactSummaryCard
        items={[
          { label: t('Source event ID'), value: sourceEventId },
          {
            label: t('Persisted event'),
            value:
              persistedSourceEventSequence !== null
                ? `${t('Found')} (${t('Event')} ${t('Sequence').toLowerCase()} ${persistedSourceEventSequence})`
                 : persistedSourceEventUnavailable ? t('Unavailable') : t('Not found in persisted event history')
          },
          { label: t('Season plan context'), value: plannedSourceEvent ? t('Found in ordered season plan') : plannedSourceEventUnavailable ? t('Unavailable') : t('No ordered-plan match') }
        ]}
      />

      <p>
        <Link to={`/runs/${encodeURIComponent(runId)}/events`}>{t('Open events history')}</Link> ·{' '}
        <Link to={`/runs/${encodeURIComponent(runId)}/calendar`}>{t('Open season calendar')}</Link> · <Link to={`/runs/${encodeURIComponent(runId)}/activity`}>{t('Open activity')}</Link>
      </p>

      <p>
        {persistedSourceEventSequence !== null ? (
          <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(sourceEventId)}`}>{t('Open source event detail')}</Link>
        ) : (
          <span>{persistedSourceEventUnavailable ? t('Unavailable') : t('Source event detail unavailable (event not present in persisted event history).')}</span>
        )}{' '}
        {plannedSourceEvent ? <>· <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(sourceEventId)}`}>{t('Open planned-event detail')}</Link></> : null}
        {plannedSourceEvent ? (
          <>
            {' '}
            · <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${plannedSourceEvent.week}`}>{t('Open week detail')} (W{plannedSourceEvent.week})</Link>
          </>
        ) : null}
      </p>

      {plannedSourceEvent ? (
        <MetadataList
          items={[
            { label: t('Season'), value: plannedSourceEvent.season },
            { label: t('Week'), value: plannedSourceEvent.week },
            { label: t('Tour'), value: plannedSourceEvent.tour },
            { label: t('Category'), value: plannedSourceEvent.category },
            { label: t('Template ID'), value: plannedSourceEvent.templateId },
            { label: t('Plan position'), value: plannedSourceEvent.planPosition },
            { label: t('Planned status'), value: plannedSourceEvent.plannedStatus }
          ]}
        />
      ) : plannedSourceEventUnavailable ? (
        <p className="status">{t('Unavailable')}</p>
      ) : (
        <EmptyState message={t('source_event_id is present, but this event is not in season_state.ordered_events for the current run.')} />
      )}

      {relatedSiblingUnavailable ? (
        <p role="status" className="status">{t('Related snapshots currently unavailable')}</p>
      ) : relatedSiblingSnapshots.length > 0 ? (
        <>
          <h4>{t('Related')} {siblingMode} {t('snapshots from the same source event')}</h4>
          <ul className="item-list" aria-label={`${t('Related')} ${siblingMode} snapshots`}>
            {relatedSiblingSnapshots.map((item) => (
              <li key={`${siblingMode}-${item.snapshot_sequence}`}>
                <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${siblingMode}/${item.snapshot_sequence}`}>
                  {t(siblingMode === 'ranking' ? 'Ranking' : 'Race').toLowerCase()} {t('snapshot')} #{item.snapshot_sequence}
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
  if (!runData || runData.run.season !== runData.season_state.season) return null
  const orderedEvents = runData.season_state.ordered_events
  const matchedIndex = orderedEvents.findIndex((event) => event.event_id === eventId)
  if (matchedIndex < 0) {
    return null
  }

  const matchedEvent = orderedEvents[matchedIndex]
  if (matchedEvent.season !== runData.season_state.season) return null
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
