import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

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
import { SelectableHistoryList } from '../components/SelectableHistoryList'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { RacePreviewTable } from '../viewer/RacePreviewTable'
import { RankingPreviewTable } from '../viewer/RankingPreviewTable'
import { parseRacePreviewPayload } from '../viewer/racePayload'
import { parseRankingPreviewPayload } from '../viewer/rankingPayload'
import { getSnapshotPayloadRows, getSnapshotPayloadTableAuditStatus } from './viewer/rankings/viewerSnapshotPayloadDisplay'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

type ViewerSnapshotMode = 'ranking' | 'race'

type PlannedSnapshotContext = {
  week: number
  category: string
  tour: string
  templateId: string
  planPosition: number
}

type PersistedEventContext = {
  eventSequence: number
  week: number | null
}

type SnapshotPageCopy = {
  listTitle: string
  detailTitle: string
  publicationLabel: string
  pluralPublicationLabel: string
  listDescription: string
  detailDescription: string
  detailLinkLabel: string
  listPathSegment: string
}

const SNAPSHOT_COPY: Record<ViewerSnapshotMode, SnapshotPageCopy> = {
  ranking: {
    listTitle: 'MSA Rankings',
    detailTitle: 'MSA Rankings',
    publicationLabel: 'Ranking publication',
    pluralPublicationLabel: 'Ranking publications',
    listDescription: 'Read-only weekly ranking publications for the selected run.',
    detailDescription: 'Read-only ranking publication metadata for the selected run.',
    detailLinkLabel: 'Open ranking detail',
    listPathSegment: 'rankings'
  },
  race: {
    listTitle: 'Race to Finals',
    detailTitle: 'Race to Finals',
    publicationLabel: 'Race publication',
    pluralPublicationLabel: 'Race publications',
    listDescription: 'Read-only Race publications for the selected run.',
    detailDescription: 'Read-only Race publication metadata for the selected run.',
    detailLinkLabel: 'Open race detail',
    listPathSegment: 'race'
  }
}

function getSnapshotCopy(mode: ViewerSnapshotMode): SnapshotPageCopy {
  return SNAPSHOT_COPY[mode]
}

function listSnapshots(mode: ViewerSnapshotMode, runId: string): Promise<{ snapshots: Array<RankingSnapshot | RaceSnapshot> }> {
  return mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)
}

function getSnapshot(mode: ViewerSnapshotMode, runId: string, sequence: number): Promise<RankingSnapshot | RaceSnapshot> {
  return mode === 'ranking' ? getRankingSnapshot(runId, sequence) : getRaceSnapshot(runId, sequence)
}

function buildPlannedContext(runData: SeasonStateResponse | undefined): Map<string, PlannedSnapshotContext> {
  const map = new Map<string, PlannedSnapshotContext>()
  ;(runData?.season_state.ordered_events ?? []).forEach((event, index) => {
    map.set(event.event_id, {
      week: event.week,
      category: event.category,
      tour: event.tour,
      templateId: event.template_id,
      planPosition: index + 1
    })
  })
  return map
}

function resolveWeek(plannedContext?: PlannedSnapshotContext, persistedEvent?: PersistedEventContext): number | null {
  return persistedEvent?.week ?? plannedContext?.week ?? null
}

function detailPath(mode: ViewerSnapshotMode, runId: string, sequence: number): string {
  return mode === 'ranking' ? viewerRankingSnapshotPath(runId, sequence) : viewerRaceSnapshotPath(runId, sequence)
}

function listPath(mode: ViewerSnapshotMode, runId: string): string {
  return mode === 'ranking' ? viewerRankingsPath(runId) : viewerRacePath(runId)
}

export function ViewerRunSnapshotListPage({ mode }: { mode: ViewerSnapshotMode }): JSX.Element {
  const { runId = '' } = useParams()
  const copy = getSnapshotCopy(mode)
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedSequence, setSelectedSequence] = useState<number | null>(null)
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [sourceEventFilter, setSourceEventFilter] = useState('')
  const requestedSequence = Number.parseInt(searchParams.get('selectedSequence') ?? '', 10)
  const hasRequestedSequence = Number.isInteger(requestedSequence)

  const snapshotsQuery = useQuery({
    queryKey: [`viewer-${mode}-publications`, runId],
    queryFn: () => listSnapshots(mode, runId),
    enabled: Boolean(runId)
  })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })

  const snapshots = snapshotsQuery.data?.snapshots ?? []
  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const persistedEventsById = useMemo(() => {
    const map = new Map<string, PersistedEventContext>()
    ;(eventsQuery.data?.events ?? []).forEach((event) => {
      map.set(event.event_id, { eventSequence: event.event_sequence, week: event.week })
    })
    return map
  }, [eventsQuery.data?.events])

  const normalizedSourceEventFilter = sourceEventFilter.trim().toLowerCase()
  const filteredSnapshots = snapshots.filter((snapshot) => {
    const sourceEventId = snapshot.source_event_id
    const planned = sourceEventId ? plannedContext.get(sourceEventId) : undefined
    const persisted = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
    const effectiveWeek = resolveWeek(planned, persisted)
    const weekMatches = weekFilter ? String(effectiveWeek) === weekFilter : true
    const categoryMatches = categoryFilter ? planned?.category === categoryFilter : true
    const sourceEventMatches = normalizedSourceEventFilter
      ? (sourceEventId?.toLowerCase().includes(normalizedSourceEventFilter) ?? false)
      : true
    return weekMatches && categoryMatches && sourceEventMatches
  })

  const weekOptions = useMemo(() => {
    const values = new Set<string>()
    snapshots.forEach((snapshot) => {
      const sourceEventId = snapshot.source_event_id
      const planned = sourceEventId ? plannedContext.get(sourceEventId) : undefined
      const persisted = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
      const effectiveWeek = resolveWeek(planned, persisted)
      if (effectiveWeek != null) values.add(String(effectiveWeek))
    })
    return Array.from(values)
  }, [persistedEventsById, plannedContext, snapshots])

  const categoryOptions = useMemo(() => {
    const values = new Set<string>()
    snapshots.forEach((snapshot) => {
      const sourceEventId = snapshot.source_event_id
      const category = sourceEventId ? plannedContext.get(sourceEventId)?.category : undefined
      if (category) values.add(category)
    })
    return Array.from(values)
  }, [plannedContext, snapshots])

  useEffect(() => {
    if (!filteredSnapshots.length) {
      setSelectedSequence(null)
      return
    }

    if (hasRequestedSequence && filteredSnapshots.some((snapshot) => snapshot.snapshot_sequence === requestedSequence)) {
      if (selectedSequence !== requestedSequence) setSelectedSequence(requestedSequence)
      return
    }

    if (!selectedSequence || !filteredSnapshots.some((snapshot) => snapshot.snapshot_sequence === selectedSequence)) {
      setSelectedSequence(filteredSnapshots[0].snapshot_sequence)
    }
  }, [filteredSnapshots, hasRequestedSequence, requestedSequence, selectedSequence])

  const selected = filteredSnapshots.find((snapshot) => snapshot.snapshot_sequence === selectedSequence) ?? null
  const selectedPlanned = selected?.source_event_id ? plannedContext.get(selected.source_event_id) : undefined
  const selectedPersisted = selected?.source_event_id ? persistedEventsById.get(selected.source_event_id) : undefined
  const selectedWeek = resolveWeek(selectedPlanned, selectedPersisted)
  const selectedRankingPreview = mode === 'ranking' && selected ? parseRankingPreviewPayload(selected.payload) : null
  const selectedRacePreview = mode === 'race' && selected ? parseRacePreviewPayload(selected.payload) : null

  return (
    <section className="panel">
      <RunScopedHeader title={copy.listTitle} runId={runId} subtitle={copy.listDescription} />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: copy.pluralPublicationLabel, value: snapshots.length },
          { label: 'Matching filters', value: filteredSnapshots.length },
          { label: 'Featured publication', value: selected ? `#${selected.snapshot_sequence}` : 'None' }
        ]}
      />

      {selected ? (
        <SectionCard title="Latest selected publication summary">
          <CompactSummaryCard
            items={[
              { label: 'Snapshot sequence', value: selected.snapshot_sequence },
              { label: 'Kind', value: selected.snapshot_kind },
              { label: 'Source event', value: selected.source_event_id ?? 'No source event recorded' },
              { label: 'Week', value: selectedWeek != null ? `W${selectedWeek}` : 'No week context' },
              { label: 'Planned category', value: selectedPlanned?.category ?? 'No ordered-plan match' },
              { label: 'Planned tour', value: selectedPlanned?.tour ?? 'No ordered-plan match' },
              { label: 'Planned template', value: selectedPlanned?.templateId ?? 'No ordered-plan match' }
            ]}
          />
          {selectedRankingPreview?.rows.length ? (
            <>
              <h4>Top 10 Ranking Preview</h4>
              <RankingPreviewTable rows={selectedRankingPreview.rows} ariaLabel="Latest selected Top 10 ranking preview table" runId={runId} />
            </>
          ) : null}
          {selectedRacePreview?.rows.length ? (
            <>
              <h4>Top 10 Race Preview</h4>
              <RacePreviewTable rows={selectedRacePreview.rows} ariaLabel="Latest selected Top 10 race preview table" runId={runId} />
            </>
          ) : null}
          <p>
            <Link to={detailPath(mode, runId, selected.snapshot_sequence)}>{copy.detailLinkLabel}</Link>
          </p>
        </SectionCard>
      ) : null}

      <SectionCard title="Publication filters">
        <div className="grid">
          <label>
            Week
            <select aria-label="Filter publications by week" value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">All weeks</option>
              {weekOptions.map((week) => (
                <option key={week} value={week}>
                  W{week}
                </option>
              ))}
            </select>
          </label>
          <label>
            Category
            <select aria-label="Filter publications by category" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="">All categories</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source event
            <input
              aria-label="Filter publications by source event"
              value={sourceEventFilter}
              onChange={(event) => setSourceEventFilter(event.target.value)}
              placeholder="source event id"
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Publication timeline">
        {snapshotsQuery.isLoading && <p className="status">Loading publications...</p>}
        {snapshotsQuery.error && <p className="error">Failed to load publications: {formatApiError(snapshotsQuery.error)}</p>}
        {!snapshotsQuery.isLoading && !snapshotsQuery.error && snapshots.length === 0 && (
          <EmptyState message="No data is available for this run yet." />
        )}
        {!snapshotsQuery.isLoading && !snapshotsQuery.error && snapshots.length > 0 && filteredSnapshots.length === 0 && (
          <EmptyState message="No publications match the current filters." />
        )}

        {filteredSnapshots.length > 0 && (
          <SelectableHistoryList
            items={filteredSnapshots}
            getKey={(snapshot) => `${snapshot.snapshot_kind}-${snapshot.snapshot_sequence}`}
            getLabel={(snapshot) => `${copy.publicationLabel} #${snapshot.snapshot_sequence}`}
            getSubLabel={(snapshot) => {
              const sourceEventId = snapshot.source_event_id
              const planned = sourceEventId ? plannedContext.get(sourceEventId) : undefined
              const persisted = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
              const week = resolveWeek(planned, persisted)
              const segments = [`Snapshot sequence ${snapshot.snapshot_sequence}`, `Kind ${snapshot.snapshot_kind}`]
              segments.push(sourceEventId ? `Source event ${sourceEventId}` : 'No source event recorded')
              if (week != null) segments.push(`Week W${week}`)
              if (planned) {
                segments.push(`Plan #${planned.planPosition}`)
                segments.push(planned.category)
                segments.push(planned.tour)
                segments.push(planned.templateId)
              } else {
                segments.push('No ordered-plan match')
              }
              return segments.join(' · ')
            }}
            isSelected={(snapshot) => snapshot.snapshot_sequence === selectedSequence}
            onSelect={(snapshot) => {
              setSelectedSequence(snapshot.snapshot_sequence)
              setSearchParams((current) => {
                const next = new URLSearchParams(current)
                next.set('selectedSequence', String(snapshot.snapshot_sequence))
                return next
              })
            }}
            ariaLabel={`${copy.pluralPublicationLabel} timeline`}
          />
        )}

        {filteredSnapshots.length > 0 ? (
          <ul className="item-list" aria-label={`${copy.pluralPublicationLabel} sports metadata`}>
            {filteredSnapshots.map((snapshot) => {
              const sourceEventId = snapshot.source_event_id
              const planned = sourceEventId ? plannedContext.get(sourceEventId) : undefined
              const persisted = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
              const week = resolveWeek(planned, persisted)
              return (
                <li key={`${mode}-${snapshot.snapshot_sequence}-publication-card`}>
                  <article aria-label={`${copy.publicationLabel} ${snapshot.snapshot_sequence}`}>
                    <h4>
                      {copy.publicationLabel} #{snapshot.snapshot_sequence}
                    </h4>
                    <MetadataList
                      items={[
                        { label: 'Snapshot sequence', value: snapshot.snapshot_sequence },
                        { label: 'Publication kind', value: snapshot.snapshot_kind },
                        { label: 'Source event ID', value: sourceEventId ?? 'No source event recorded' },
                        {
                          label: 'Week',
                          value: week != null ? <Link to={viewerWeekDetailPath(runId, week)}>W{week}</Link> : 'No ordered-plan match'
                        },
                        { label: 'Planned category', value: planned?.category ?? 'No ordered-plan match' },
                        { label: 'Planned tour', value: planned?.tour ?? 'No ordered-plan match' },
                        { label: 'Planned template', value: planned?.templateId ?? 'No ordered-plan match' },
                        {
                          label: 'Publication detail',
                          value: (
                            <Link to={detailPath(mode, runId, snapshot.snapshot_sequence)}>
                              Open {mode === 'ranking' ? 'ranking' : 'race'} publication detail
                            </Link>
                          )
                        },
                        {
                          label: 'Planned event',
                          value:
                            sourceEventId && planned ? (
                              <Link to={viewerPlannedEventPath(runId, sourceEventId)}>Open planned event</Link>
                            ) : (
                              'No ordered-plan match'
                            )
                        },
                        {
                          label: 'Tournament detail',
                          value:
                            sourceEventId && persisted ? (
                              <Link to={viewerTournamentDetailPath(runId, sourceEventId)}>Open tournament detail</Link>
                            ) : (
                              'No persisted event record'
                            )
                        }
                      ]}
                    />
                  </article>
                </li>
              )
            })}
          </ul>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunSnapshotDetailPage({ mode }: { mode: ViewerSnapshotMode }): JSX.Element {
  const { runId = '', snapshotSequence = '' } = useParams()
  const copy = getSnapshotCopy(mode)
  const parsedSequence = Number.parseInt(snapshotSequence, 10)
  const isValidSequence = Number.isInteger(parsedSequence) && parsedSequence > 0

  const snapshotQuery = useQuery({
    queryKey: [`viewer-${mode}-publication`, runId, parsedSequence],
    queryFn: () => getSnapshot(mode, runId, parsedSequence),
    enabled: Boolean(runId && isValidSequence),
    retry: false
  })
  const snapshotsQuery = useQuery({
    queryKey: [`viewer-${mode}-publications`, runId],
    queryFn: () => listSnapshots(mode, runId),
    enabled: Boolean(runId && isValidSequence)
  })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId && isValidSequence) })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId && isValidSequence) })

  const snapshot = snapshotQuery.data ?? null
  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const persistedEventsById = useMemo(() => {
    const map = new Map<string, PersistedEventContext>()
    ;(eventsQuery.data?.events ?? []).forEach((event) => {
      map.set(event.event_id, { eventSequence: event.event_sequence, week: event.week })
    })
    return map
  }, [eventsQuery.data?.events])

  const neighboringSnapshots = snapshotsQuery.data?.snapshots ?? []
  const currentSnapshotIndex = neighboringSnapshots.findIndex((item) => item.snapshot_sequence === parsedSequence)
  const previousSnapshot = currentSnapshotIndex > 0 ? neighboringSnapshots[currentSnapshotIndex - 1] : null
  const nextSnapshot =
    currentSnapshotIndex >= 0 && currentSnapshotIndex < neighboringSnapshots.length - 1
      ? neighboringSnapshots[currentSnapshotIndex + 1]
      : null
  const sourceEventId = snapshot?.source_event_id ?? null
  const planned = sourceEventId ? plannedContext.get(sourceEventId) : undefined
  const persisted = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
  const week = resolveWeek(planned, persisted)
  const payloadRows = snapshot ? getSnapshotPayloadRows(snapshot.payload) : []
  const payloadTableAudit = snapshot ? getSnapshotPayloadTableAuditStatus(mode, snapshot.payload) : null

  return (
    <section className="panel">
      <RunScopedHeader title={copy.detailTitle} runId={runId} subtitle={copy.detailDescription} />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Snapshot sequence', value: snapshotSequence || 'unknown' },
          { label: 'Publication type', value: mode === 'ranking' ? 'MSA Rankings' : 'Race to Finals' },
          { label: 'Status', value: snapshot ? 'Loaded' : 'Pending' }
        ]}
      />

      <SectionCard title="Publication navigation">
        <SummaryPills
          items={[
            {
              label: 'Previous publication',
              value: previousSnapshot ? <Link to={detailPath(mode, runId, previousSnapshot.snapshot_sequence)}>#{previousSnapshot.snapshot_sequence}</Link> : 'None'
            },
            {
              label: 'Next publication',
              value: nextSnapshot ? <Link to={detailPath(mode, runId, nextSnapshot.snapshot_sequence)}>#{nextSnapshot.snapshot_sequence}</Link> : 'None'
            }
          ]}
        />
        <p>
          <Link to={listPath(mode, runId)}>Back to {copy.pluralPublicationLabel.toLowerCase()}</Link>
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
                  { label: 'Planned category', value: planned?.category ?? 'No ordered-plan match' },
                  { label: 'Planned tour', value: planned?.tour ?? 'No ordered-plan match' },
                  { label: 'Planned template', value: planned?.templateId ?? 'No ordered-plan match' },
                  { label: 'Plan position', value: planned?.planPosition ?? 'No ordered-plan match' },
                  { label: 'Persisted source event', value: persisted ? `Found (sequence ${persisted.eventSequence})` : 'Not found' }
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
                        'No ordered-plan match for source event.'
                      )
                  },
                  {
                    label: 'Week detail',
                    value: week != null ? <Link to={viewerWeekDetailPath(runId, week)}>Open week W{week}</Link> : 'No week context available.'
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
