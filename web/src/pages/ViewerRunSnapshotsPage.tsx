import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import {
  getRaceSnapshot,
  getViewerRunCalendar,
  getViewerTournamentHistory,
  listRaceSnapshots
} from '../api/client'
import type { RaceSnapshot, ViewerCalendarEvent, ViewerTournamentHistoryItem } from '../api/types'
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
import { getSnapshotPayloadRows, getSnapshotPayloadTableAuditStatus } from './viewer/rankings/viewerSnapshotPayloadDisplay'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

type CanonicalCalendarContext = {
  eventId: string
  week: number
  category: string
  tour: string | null
  templateId: string
  season: string | number
}

function buildCanonicalCalendarContext(events: ViewerCalendarEvent[]): Map<string, CanonicalCalendarContext> {
  return new Map(events.map((event) => [
    event.event_id,
    {
      eventId: event.event_id,
      week: event.season_week,
      category: event.category,
      tour: event.tour_level,
      templateId: event.template_id,
      season: event.season,
    }
  ]))
}

function buildCanonicalHistoryContext(events: ViewerTournamentHistoryItem[]): Map<string, ViewerTournamentHistoryItem> {
  return new Map(events.map((event) => [event.event_id, event]))
}

const RACE_COPY = {
  detailTitle: 'Race to Finals',
  pluralPublicationLabel: 'Race publications',
  detailDescription: 'Read-only legacy Race snapshot metadata with canonical Saved-Revision source context.'
}

function normalizeSourceEventId(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isSnapshotListItem(value: unknown): value is RaceSnapshot {
  if (!isPlainRecord(value)) return false
  const sequence = value.snapshot_sequence
  if (typeof sequence !== 'number' || !Number.isInteger(sequence) || sequence <= 0) return false
  if (typeof value.snapshot_kind !== 'string') return false
  if (!Object.prototype.hasOwnProperty.call(value, 'payload')) return false
  return true
}

function normalizeSnapshots(data: { snapshots?: unknown } | undefined): RaceSnapshot[] {
  return Array.isArray(data?.snapshots) ? data.snapshots.filter(isSnapshotListItem) : []
}

function detailPath(runId: string, sequence: number): string {
  return viewerRaceSnapshotPath(runId, sequence)
}

function listPath(runId: string): string {
  return viewerRacePath(runId)
}

export function ViewerRunSnapshotDetailPage(): JSX.Element {
  const { snapshotSequence = '' } = useParams()
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()
  const copy = RACE_COPY
  const parsedSequence = Number(snapshotSequence)
  const isValidSequence = /^\d+$/.test(snapshotSequence) && Number.isSafeInteger(parsedSequence) && parsedSequence > 0

  const snapshotQuery = useQuery({
    queryKey: ['viewer-race-publication', runId, parsedSequence],
    queryFn: () => getRaceSnapshot(legacySimulationRunId, parsedSequence),
    enabled: Boolean(runId && isValidSequence),
    retry: false
  })
  const snapshotsQuery = useQuery({
    queryKey: ['viewer-race-publications', runId, legacySimulationRunId],
    queryFn: () => listRaceSnapshots(legacySimulationRunId),
    enabled: Boolean(runId && isValidSequence)
  })
  const calendarQuery = useQuery({
    queryKey: ['viewer-race-publication-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId && isValidSequence),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-race-publication-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId && isValidSequence),
    retry: false
  })

  const snapshot = snapshotQuery.data ?? null
  const calendarEvents = useMemo(
    () => (calendarQuery.data?.seasons ?? []).flatMap((season) => season.events),
    [calendarQuery.data?.seasons]
  )
  const calendarContext = useMemo(() => buildCanonicalCalendarContext(calendarEvents), [calendarEvents])
  const historyContext = useMemo(
    () => buildCanonicalHistoryContext(historyQuery.data?.tournaments ?? []),
    [historyQuery.data?.tournaments]
  )

  const neighboringSnapshots = normalizeSnapshots(snapshotsQuery.data)
  const currentSnapshotIndex = neighboringSnapshots.findIndex((item) => item.snapshot_sequence === parsedSequence)
  const previousSnapshot = currentSnapshotIndex > 0 ? neighboringSnapshots[currentSnapshotIndex - 1] : null
  const nextSnapshot =
    currentSnapshotIndex >= 0 && currentSnapshotIndex < neighboringSnapshots.length - 1
      ? neighboringSnapshots[currentSnapshotIndex + 1]
      : null
  const sourceEventId = normalizeSourceEventId(snapshot?.source_event_id)
  const planned = sourceEventId ? calendarContext.get(sourceEventId) : undefined
  const persisted = sourceEventId ? historyContext.get(sourceEventId) : undefined
  const week = planned?.week ?? persisted?.season_week ?? null
  const payloadRows = snapshot ? getSnapshotPayloadRows(snapshot.payload) : []
  const payloadTableAudit = snapshot ? getSnapshotPayloadTableAuditStatus('race', snapshot.payload) : null

  return (
    <section className="panel">
      <RunScopedHeader title={copy.detailTitle} runId={runId} subtitle={copy.detailDescription} />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Snapshot sequence', value: snapshotSequence || 'unknown' },
          { label: 'Publication type', value: 'Race to Finals' },
          { label: 'Status', value: snapshot ? 'Loaded' : 'Pending' }
        ]}
      />

      <SectionCard title="Publication navigation">
        <SummaryPills
          items={[
            {
              label: 'Previous publication',
              value: previousSnapshot ? <Link to={detailPath(runId, previousSnapshot.snapshot_sequence)}>#{previousSnapshot.snapshot_sequence}</Link> : 'None'
            },
            {
              label: 'Next publication',
              value: nextSnapshot ? <Link to={detailPath(runId, nextSnapshot.snapshot_sequence)}>#{nextSnapshot.snapshot_sequence}</Link> : 'None'
            }
          ]}
        />
        <p>
          <Link to={listPath(runId)}>Back to {copy.pluralPublicationLabel.toLowerCase()}</Link>
        </p>
      </SectionCard>

      {!snapshotSequence && (
        <SectionCard title="Publication lookup">
          <EmptyState message="No snapshot sequence was provided in the URL." />
        </SectionCard>
      )}

      {snapshotSequence && !isValidSequence && (
        <SectionCard title="Publication lookup">
          <EmptyState message={`Snapshot sequence "${snapshotSequence}" is invalid. Use a positive integer sequence.`} />
        </SectionCard>
      )}

      {snapshotSequence && isValidSequence && (
        <>
          <SectionCard title="Publication summary">
            {snapshotQuery.isLoading && <p className="status">Loading publication...</p>}
            {snapshotQuery.error && !isApiNotFound(snapshotQuery.error) && (
              <p className="error">Failed to load publication: {formatApiError(snapshotQuery.error)}</p>
            )}
            {isApiNotFound(snapshotQuery.error) && <EmptyState message={`Snapshot sequence ${snapshotSequence} was not found for this run.`} />}
            {snapshot ? (
              <MetadataList
                items={[
                  { label: 'Snapshot sequence', value: snapshot.snapshot_sequence },
                  { label: 'Kind', value: snapshot.snapshot_kind },
                  { label: 'Source event', value: sourceEventId ?? 'No source event recorded' },
                  { label: 'Week', value: week != null ? `W${week}` : 'No week context' },
                  { label: 'Planned category', value: planned?.category ?? 'No Saved Calendar match' },
                  { label: 'Planned tour', value: planned?.tour ?? 'No Saved Calendar match' },
                  { label: 'Planned template', value: planned?.templateId ?? 'No Saved Calendar match' },
                  { label: 'Calendar season', value: planned?.season ?? persisted?.season ?? 'No canonical source context' },
                  { label: 'Canonical tournament history', value: persisted ? (persisted.result_published ? 'Published result available' : 'Tournament recorded') : 'No canonical history match' }
                ]}
              />
            ) : null}
          </SectionCard>

          {snapshot ? (
            <SectionCard title="Source links">
              <CompactSummaryCard
                items={[
                  {
                    label: 'Source event detail',
                    value:
                      sourceEventId && persisted ? (
                        <Link to={viewerTournamentDetailPath(runId, sourceEventId)}>Open source event</Link>
                      ) : (
                        'Source event detail unavailable.'
                      )
                  },
                  {
                    label: 'Planned calendar detail',
                    value:
                      sourceEventId && planned ? (
                        <Link to={viewerPlannedEventPath(runId, sourceEventId)}>Open planned event</Link>
                      ) : (
                        'No Saved Calendar match for source event.'
                      )
                  },
                  {
                    label: 'Week detail',
                    value: week != null ? <Link to={viewerWeekDetailPath(runId, week)}>Open week W{week}</Link> : 'No canonical week context available.'
                  },
                  { label: 'Season calendar', value: <Link to={viewerSeasonCalendarPath(runId)}>Open season calendar</Link> }
                ]}
              />
            </SectionCard>
          ) : null}

          {snapshot ? (
            <SectionCard title="Payload summary">
              <p className="status">Conservative read-only payload summary. The Viewer does not infer standings from unknown fields.</p>
              {payloadTableAudit ? <p className="status">Snapshot payload table rendering deferred: {payloadTableAudit.reason}</p> : null}
              <MetadataList items={payloadRows} />
            </SectionCard>
          ) : null}

          {snapshot ? (
            <SectionCard title="Read-only data">
              <details>
                <summary>Show technical payload</summary>
                <p className="status">Read-only technical snapshot data for audit/debugging. Viewer standings remain non-mutating.</p>
                <JsonPayloadBlock title="Technical snapshot record" emptyText="No technical data is available for this publication." payload={snapshot.payload} />
              </details>
            </SectionCard>
          ) : null}
        </>
      )}
    </section>
  )
}
