import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getRun, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
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
import type { RaceSnapshot, RankingSnapshot } from '../api/types'
import { formatApiError } from '../utils/apiErrors'

type Mode = 'ranking' | 'race'

export function SnapshotsPage({ mode }: { mode: Mode }): JSX.Element {
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedSequence, setSelectedSequence] = useState<number | null>(null)
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [sourceEventFilter, setSourceEventFilter] = useState('')
  const requestedSequence = Number.parseInt(searchParams.get('selectedSequence') ?? '', 10)
  const hasRequestedSequence = Number.isInteger(requestedSequence)

  const query = useQuery({
    queryKey: [`${mode}-snapshots`, runId],
    queryFn: () => (mode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId)
  })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
  const siblingMode: Mode = mode === 'ranking' ? 'race' : 'ranking'
  const siblingSnapshotsQuery = useQuery({
    queryKey: [`${siblingMode}-snapshots`, runId],
    queryFn: () => (siblingMode === 'ranking' ? listRankingSnapshots(runId) : listRaceSnapshots(runId)),
    enabled: Boolean(runId)
  })

  const snapshots = query.data?.snapshots ?? []
  const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
  const plannedContext = useMemo(() => {
    const map = new Map<string, { week: number; category: string; tour: string; templateId: string; planPosition: number }>()
    orderedEvents.forEach((event, index) => {
      map.set(event.event_id, {
        week: event.week,
        category: event.category,
        tour: event.tour,
        templateId: event.template_id,
        planPosition: index + 1
      })
    })
    return map
  }, [orderedEvents])
  const persistedEventsById = useMemo(() => {
    const map = new Map<string, { eventSequence: number; week: number | null }>()
    ;(eventsQuery.data?.events ?? []).forEach((event) => {
      map.set(event.event_id, { eventSequence: event.event_sequence, week: event.week })
    })
    return map
  }, [eventsQuery.data?.events])
  const normalizedSourceEventFilter = sourceEventFilter.trim().toLowerCase()
  const filteredSnapshots = snapshots.filter((snapshot) => {
    const sourceEventId = snapshot.source_event_id
    const planContext = sourceEventId ? plannedContext.get(sourceEventId) : undefined
    const persistedContext = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
    const effectiveWeek = persistedContext?.week ?? planContext?.week
    const weekMatches = weekFilter ? String(effectiveWeek) === weekFilter : true
    const categoryMatches = categoryFilter ? planContext?.category === categoryFilter : true
    const sourceEventMatches = normalizedSourceEventFilter
      ? (sourceEventId?.toLowerCase().includes(normalizedSourceEventFilter) ?? false)
      : true
    return weekMatches && categoryMatches && sourceEventMatches
  })
  const weekOptions = useMemo(() => {
    const values = new Set<string>()
    snapshots.forEach((snapshot) => {
      const sourceEventId = snapshot.source_event_id
      if (!sourceEventId) return
      const plan = plannedContext.get(sourceEventId)
      const persisted = persistedEventsById.get(sourceEventId)
      const effectiveWeek = persisted?.week ?? plan?.week
      if (effectiveWeek != null) values.add(String(effectiveWeek))
    })
    return Array.from(values)
  }, [plannedContext, persistedEventsById, snapshots])
  const categoryOptions = useMemo(() => {
    const values = new Set<string>()
    snapshots.forEach((snapshot) => {
      const sourceEventId = snapshot.source_event_id
      if (!sourceEventId) return
      const category = plannedContext.get(sourceEventId)?.category
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
      if (selectedSequence !== requestedSequence) {
        setSelectedSequence(requestedSequence)
      }
      return
    }

    if (!selectedSequence || !filteredSnapshots.some((snapshot) => snapshot.snapshot_sequence === selectedSequence)) {
      setSelectedSequence(filteredSnapshots[0].snapshot_sequence)
    }
  }, [filteredSnapshots, hasRequestedSequence, requestedSequence, selectedSequence])

  const selected = filteredSnapshots.find((snapshot) => snapshot.snapshot_sequence === selectedSequence) ?? null

  const title = mode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots'
  const siblingMatchCount = selected?.source_event_id
    ? (siblingSnapshotsQuery.data?.snapshots.filter((item) => item.source_event_id === selected.source_event_id).length ?? 0)
    : 0

  return (
    <section className="panel">
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle="Browse stored snapshot history and inspect payload details by sequence."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Mode', value: mode },
          { label: 'Snapshots', value: snapshots.length },
          { label: 'Matching filters', value: filteredSnapshots.length },
          { label: 'Selected', value: selected?.snapshot_sequence ?? 'None' }
        ]}
      />

      <SectionCard title="Filters">
        <div className="grid">
          <label>
            Week
            <select aria-label="Filter snapshots by week" value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
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
            <select
              aria-label="Filter snapshots by category"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">All categories</option>
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            Source event text
            <input
              aria-label="Filter snapshots by source event"
              value={sourceEventFilter}
              onChange={(event) => setSourceEventFilter(event.target.value)}
              placeholder="source_event_id"
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Snapshot timeline">
        {query.isLoading && <p className="status">Loading snapshots history...</p>}
        {query.error && <p className="error">Failed to load snapshots history: {formatApiError(query.error)}</p>}
        {!query.isLoading && !query.error && snapshots.length === 0 && (
          <EmptyState message="No snapshots are available for this run yet." />
        )}
        {!query.isLoading && !query.error && snapshots.length > 0 && filteredSnapshots.length === 0 && (
          <EmptyState message="No snapshots match the current filters." />
        )}

        {filteredSnapshots.length > 0 && (
          <SelectableHistoryList
            items={filteredSnapshots}
            getKey={(snapshot) => `${snapshot.snapshot_kind}-${snapshot.snapshot_sequence}`}
            getLabel={(snapshot) => `${snapshot.snapshot_sequence}. ${snapshot.snapshot_kind}`}
            getSubLabel={(snapshot) => {
              const sourceEventId = snapshot.source_event_id
              if (!sourceEventId) return 'No source_event_id'
              const plan = plannedContext.get(sourceEventId)
              const persisted = persistedEventsById.get(sourceEventId)
              const week = persisted?.week ?? plan?.week
              const segments = [`Source ${sourceEventId}`]
              if (week != null) segments.push(`W${week}`)
              if (plan) {
                segments.push(`Plan #${plan.planPosition}`)
                segments.push(plan.category)
                segments.push(plan.tour)
                segments.push(plan.templateId)
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
            ariaLabel={`${title} list`}
          />
        )}
      </SectionCard>

      <SectionCard title="Selected snapshot detail">
        {selected ? (
          <SnapshotDetail
            snapshot={selected}
            mode={mode}
            runId={runId}
            plannedContext={selected.source_event_id ? plannedContext.get(selected.source_event_id) : undefined}
            persistedEvent={selected.source_event_id ? persistedEventsById.get(selected.source_event_id) : undefined}
            siblingMode={siblingMode}
            siblingMatchCount={siblingMatchCount}
          />
        ) : (
          <EmptyState message="Select a snapshot to inspect details." />
        )}
      </SectionCard>
    </section>
  )
}

function SnapshotDetail({
  snapshot,
  mode,
  runId,
  plannedContext,
  persistedEvent,
  siblingMode,
  siblingMatchCount
}: {
  snapshot: RankingSnapshot | RaceSnapshot
  mode: Mode
  runId: string
  plannedContext?: { week: number; category: string; tour: string; templateId: string; planPosition: number }
  persistedEvent?: { eventSequence: number; week: number | null }
  siblingMode: Mode
  siblingMatchCount: number
}): JSX.Element {
  const sourceEventId = snapshot.source_event_id
  const sourceWeek = persistedEvent?.week ?? plannedContext?.week

  return (
    <>
      <MetadataList
        items={[
          { label: 'Sequence', value: snapshot.snapshot_sequence },
          { label: 'Kind', value: snapshot.snapshot_kind },
          { label: 'Mode', value: mode },
          { label: 'Source event ID', value: sourceEventId ?? '—' },
          { label: 'Week context', value: sourceWeek != null ? `W${sourceWeek}` : 'No week context' },
          { label: 'Planned category', value: plannedContext?.category ?? 'No ordered-plan match' },
          { label: 'Planned tour', value: plannedContext?.tour ?? 'No ordered-plan match' },
          { label: 'Planned template', value: plannedContext?.templateId ?? 'No ordered-plan match' },
          { label: 'Plan position', value: plannedContext?.planPosition ?? 'No ordered-plan match' },
          { label: 'Persisted source event', value: persistedEvent ? `Found (sequence ${persistedEvent.eventSequence})` : 'Not found' }
        ]}
      />
      <SummaryPills
        items={[
          { label: 'Source event context', value: sourceEventId ? 'Present' : 'Missing source_event_id' },
          { label: `${siblingMode} siblings`, value: siblingMatchCount > 0 ? siblingMatchCount : 'None for this source event' }
        ]}
      />
      <CompactSummaryCard
        items={[
          {
            label: 'Snapshot detail',
            value: <Link to={`/runs/${runId}/snapshots/${mode}/${snapshot.snapshot_sequence}`}>Open dedicated snapshot detail page</Link>
          },
          {
            label: 'Source persisted event',
            value:
              sourceEventId && persistedEvent ? (
                <Link to={`/runs/${runId}/events/${encodeURIComponent(sourceEventId)}`}>Open source event detail page</Link>
              ) : (
                'Source persisted event detail unavailable.'
              )
          },
          {
            label: 'Source planned event',
            value: sourceEventId && plannedContext ? (
              <Link to={`/runs/${runId}/calendar/${encodeURIComponent(sourceEventId)}`}>Open planned-event detail page</Link>
            ) : (
              'No ordered-plan match for source_event_id.'
            )
          },
          {
            label: 'Source week detail',
            value:
              sourceWeek != null ? (
                <Link to={`/runs/${runId}/weeks/${sourceWeek}`}>Open week detail page (W{sourceWeek})</Link>
              ) : (
                'No source week context available.'
              )
          },
          { label: 'Season calendar', value: <Link to={`/runs/${runId}/calendar`}>Open season calendar browser</Link> },
          {
            label: `${siblingMode} snapshots`,
            value:
              sourceEventId && siblingMatchCount > 0 ? (
                <Link to={`/runs/${runId}/snapshots/${siblingMode}`}>Open {siblingMode} snapshots for matching source_event_id</Link>
              ) : (
                `No ${siblingMode} snapshots share this source_event_id.`
              )
          }
        ]}
      />

      <JsonPayloadBlock title="Snapshot payload" emptyText="No snapshot payload is available for this item." payload={snapshot.payload} />
    </>
  )
}
