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

const MISSING_SOURCE_EVENT_ID_FALLBACK = 'Missing source_event_id'

import { useHistoryText } from './runHistoryText'
export function SnapshotsPage({ mode }: { mode: Mode }): JSX.Element {
  const t = useHistoryText()
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedSequence, setSelectedSequence] = useState<number | null>(null)
  const [weekFilter, setWeekFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [sourceEventFilter, setSourceEventFilter] = useState('')
  const requestedSequenceText = searchParams.get('selectedSequence') ?? ''
  // A partial number like "3abc" must not select snapshot #3.
  const requestedSequence = /^\d+$/.test(requestedSequenceText) ? Number(requestedSequenceText) : NaN
  const hasRequestedSequence = Number.isSafeInteger(requestedSequence) && requestedSequence > 0

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

  const snapshotMismatch = Boolean(query.data?.run_id && query.data.run_id !== runId)
  const snapshots = snapshotMismatch ? [] : query.data?.snapshots ?? []
  const siblingMismatch = Boolean(siblingSnapshotsQuery.data?.run_id && siblingSnapshotsQuery.data.run_id !== runId)
  const eventsMismatch = Boolean(eventsQuery.data?.run_id && eventsQuery.data.run_id !== runId)
  const runMismatch = Boolean(runQuery.data?.run.run_id && runQuery.data.run.run_id !== runId)
  const orderedEvents = runQuery.data?.run.run_id === runId ? runQuery.data.season_state.ordered_events : []
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
    ;(eventsMismatch ? [] : eventsQuery.data?.events ?? []).forEach((event) => {
      map.set(event.event_id, { eventSequence: event.event_sequence, week: event.week })
    })
    return map
  }, [eventsMismatch, eventsQuery.data?.events])
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

  const title = mode === 'ranking' ? t('Ranking snapshots') : t('Race snapshots')
  const siblingMatchCount = selected?.source_event_id
    ? (siblingMismatch ? 0 : siblingSnapshotsQuery.data?.snapshots.filter((item) => item.source_event_id === selected.source_event_id).length ?? 0)
    : 0

  return (
    <section className="panel">
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle="Browse stored snapshot history and inspect payload details by sequence."
      />
      <p className="status">{t('Stored historical snapshot; it is not necessarily the current ranking. The endpoint does not provide a timestamp.')}</p>
      <p className="status">{t('Stored legacy SimulationRun history. This view does not verify Product Run Saved Revision authority.')}</p>
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Mode'), value: mode },
          { label: t('Snapshots'), value: snapshots.length },
          { label: t('Matching filters'), value: filteredSnapshots.length },
          { label: t('Selected'), value: selected?.snapshot_sequence ?? t('None') }
        ]}
      />

      <SectionCard title={t('Filters')}>
        <div className="grid">
          <label>
            {t('Week')}
            <select aria-label="Filter snapshots by week" value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">{t('All weeks')}</option>
              {weekOptions.map((week) => (
                <option key={week} value={week}>
                  W{week}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Category')}
            <select
              aria-label="Filter snapshots by category"
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.target.value)}
            >
              <option value="">{t('All categories')}</option>
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
        <button type="button" onClick={() => { setWeekFilter(''); setCategoryFilter(''); setSourceEventFilter('') }}>{t('Reset filters')}</button>
      </SectionCard>

      {(runMismatch || eventsMismatch || siblingMismatch) && <p role="alert" className="error">{t('Snapshot sibling history belongs to another Run.')}</p>}
      <SectionCard title={t('Snapshot timeline')}>
        {snapshotMismatch && <p role="alert" className="error">{t('Snapshot history belongs to another Run; its records are hidden.')}</p>}
        <button type="button" onClick={() => void query.refetch()}>{t('Refresh read-only data')}</button>
        {query.isLoading && <p className="status">{t('Loading snapshots history...')}</p>}
        {query.error && <p className="error">{t('Failed to load snapshots history')}: {formatApiError(query.error)}</p>}
        {!query.isLoading && !query.error && !snapshotMismatch && snapshots.length === 0 && (
          <EmptyState message={t('No snapshots are available for this run yet.')} />
        )}
        {!query.isLoading && !query.error && snapshots.length > 0 && filteredSnapshots.length === 0 && (
          <EmptyState message={t('No snapshots match the current filters.')} />
        )}

        {filteredSnapshots.length > 0 && (
          <SelectableHistoryList
            items={filteredSnapshots}
            getKey={(snapshot) => `${snapshot.snapshot_kind}-${snapshot.snapshot_sequence}`}
            getLabel={(snapshot) => `${snapshot.snapshot_sequence}. ${snapshot.snapshot_kind}`}
            getSubLabel={(snapshot) => {
              const sourceEventId = snapshot.source_event_id
              if (!sourceEventId) return t('No source_event_id')
              const plan = plannedContext.get(sourceEventId)
              const persisted = persistedEventsById.get(sourceEventId)
              const week = persisted?.week ?? plan?.week
              const segments = [`${t('Source event')} ${sourceEventId}`]
              if (week != null) segments.push(`W${week}`)
              if (plan) {
                segments.push(`${t('Plan')} #${plan.planPosition}`)
                segments.push(plan.category)
                segments.push(plan.tour)
                segments.push(plan.templateId)
              } else {
                segments.push(t('No ordered-plan match'))
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

      <SectionCard title={t('Selected snapshot detail')}>
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
          <EmptyState message={t('Select a snapshot to inspect details.')} />
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
  const t = useHistoryText()
  const sourceEventId = snapshot.source_event_id
  const sourceWeek = persistedEvent?.week ?? plannedContext?.week

  return (
    <>
      <MetadataList
        items={[
          { label: t('Sequence'), value: snapshot.snapshot_sequence },
          { label: t('Kind'), value: snapshot.snapshot_kind },
          { label: t('Mode'), value: mode },
          { label: t('Source event ID'), value: sourceEventId ?? '—' },
          { label: t('Week context'), value: sourceWeek != null ? `W${sourceWeek}` : t('No week context') },
          { label: t('Planned category'), value: plannedContext?.category ?? t('No ordered-plan match') },
          { label: t('Planned tour'), value: plannedContext?.tour ?? t('No ordered-plan match') },
          { label: t('Planned template'), value: plannedContext?.templateId ?? t('No ordered-plan match') },
          { label: t('Plan position'), value: plannedContext?.planPosition ?? t('No ordered-plan match') },
          { label: t('Persisted source event'), value: persistedEvent ? `${t('Found')} (${t('Sequence').toLowerCase()} ${persistedEvent.eventSequence})` : t('Not found') }
        ]}
      />
      <SummaryPills
        items={[
          { label: t('Source event context'), value: sourceEventId ? t('Present') : t(MISSING_SOURCE_EVENT_ID_FALLBACK) },
          { label: `${t(siblingMode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots')} (${t('Source event')})`, value: siblingMatchCount > 0 ? siblingMatchCount : t('No snapshot result matching this source event was returned.') }
        ]}
      />
      <CompactSummaryCard
        items={[
          {
            label: t('Snapshot detail'),
            value: <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${mode}/${snapshot.snapshot_sequence}`}>{t('Open dedicated snapshot detail page')}</Link>
          },
          {
            label: t('Source persisted event'),
            value:
              sourceEventId && persistedEvent ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(sourceEventId)}`}>{t('Open source event detail page')}</Link>
              ) : (
                t('Source persisted event detail unavailable.')
              )
          },
          {
            label: t('Source planned event'),
            value: sourceEventId && plannedContext ? (
              <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(sourceEventId)}`}>{t('Open planned-event detail page')}</Link>
            ) : (
              t('No ordered-plan match for source_event_id.')
            )
          },
          {
            label: t('Source week detail'),
            value:
              sourceWeek != null ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${sourceWeek}`}>{t('Open week detail page')} (W{sourceWeek})</Link>
              ) : (
                t('No source week context available.')
              )
          },
          { label: t('Season calendar'), value: <Link to={`/runs/${encodeURIComponent(runId)}/calendar`}>{t('Open season calendar browser')}</Link> },
          {
            label: t(siblingMode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots'),
            value:
              sourceEventId && siblingMatchCount > 0 ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${siblingMode}`}>Open {siblingMode} snapshots for matching source_event_id</Link>
              ) : (
                t('No snapshots share this source_event_id.')
              )
          }
        ]}
      />

      <JsonPayloadBlock title={t('Snapshot payload')} emptyText={t('No snapshot payload is available for this item.')} payload={snapshot.payload} />
    </>
  )
}
