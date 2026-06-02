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
import { RankingPreviewTable } from '../viewer/RankingPreviewTable'
import { parseRankingPreviewPayload } from '../viewer/rankingPayload'

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
  return `/viewer/runs/${runId}/${getSnapshotCopy(mode).listPathSegment}/${sequence}`
}

function listPath(mode: ViewerSnapshotMode, runId: string): string {
  return `/viewer/runs/${runId}/${getSnapshotCopy(mode).listPathSegment}`
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
              <RankingPreviewTable rows={selectedRankingPreview.rows} ariaLabel="Latest selected Top 10 ranking preview table" />
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
          <ul className="item-list" aria-label={`${copy.pluralPublicationLabel} detail links`}>
            {filteredSnapshots.map((snapshot) => {
              const planned = snapshot.source_event_id ? plannedContext.get(snapshot.source_event_id) : undefined
              const persisted = snapshot.source_event_id ? persistedEventsById.get(snapshot.source_event_id) : undefined
              const week = resolveWeek(planned, persisted)
              return (
                <li key={`${mode}-${snapshot.snapshot_sequence}-detail-link`}>
                  <strong>{copy.publicationLabel} #{snapshot.snapshot_sequence}</strong> · Kind {snapshot.snapshot_kind} · Source event{' '}
                  {snapshot.source_event_id ?? '—'} · Week {week != null ? `W${week}` : '—'}
                  {planned ? ` · ${planned.category} · ${planned.tour} · ${planned.templateId}` : ' · No ordered-plan match'} ·{' '}
                  <Link to={detailPath(mode, runId, snapshot.snapshot_sequence)}>View {mode === 'ranking' ? 'ranking' : 'race'} publication</Link>
                  {snapshot.source_event_id && persisted ? (
                    <>
                      {' '}
                      · <Link to={`/viewer/runs/${runId}/tournaments/${encodeURIComponent(snapshot.source_event_id)}`}>Source event</Link>
                    </>
                  ) : null}
                  {snapshot.source_event_id && planned ? (
                    <>
                      {' '}
                      · <Link to={`/viewer/runs/${runId}/calendar/${encodeURIComponent(snapshot.source_event_id)}`}>Calendar event</Link>
                    </>
                  ) : null}
                  {week != null ? (
                    <>
                      {' '}
                      · <Link to={`/viewer/runs/${runId}/weeks/${week}`}>Week</Link>
                    </>
                  ) : null}
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
  const rankingPreview = mode === 'ranking' && snapshot ? parseRankingPreviewPayload(snapshot.payload) : null

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
                        <Link to={`/viewer/runs/${runId}/tournaments/${encodeURIComponent(sourceEventId)}`}>Open source event</Link>
                      ) : (
                        'Source event detail unavailable.'
                      )
                  },
                  {
                    label: 'Planned calendar detail',
                    value:
                      sourceEventId && planned ? (
                        <Link to={`/viewer/runs/${runId}/calendar/${encodeURIComponent(sourceEventId)}`}>Open planned event</Link>
                      ) : (
                        'No ordered-plan match for source event.'
                      )
                  },
                  {
                    label: 'Week detail',
                    value: week != null ? <Link to={`/viewer/runs/${runId}/weeks/${week}`}>Open week W{week}</Link> : 'No week context available.'
                  },
                  { label: 'Season calendar', value: <Link to={`/viewer/runs/${runId}/calendar`}>Open season calendar</Link> }
                ]}
              />
            </SectionCard>
          ) : null}

          {snapshot ? (
            <SectionCard title={rankingPreview?.rows.length ? 'Top 10 Ranking Preview' : 'Standings preview'}>
              {rankingPreview?.rows.length ? (
                <RankingPreviewTable rows={rankingPreview.rows} />
              ) : (
                <EmptyState message="This preview is not connected for this data shape yet." />
              )}
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
