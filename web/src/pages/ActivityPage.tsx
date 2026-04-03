import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getRun, getRunActivity, listEvents } from '../api/client'
import { type RunActivityItem } from '../api/types'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { SelectableHistoryList } from '../components/SelectableHistoryList'
import { formatApiError } from '../utils/apiErrors'

type IndexedActivityItem = {
  item: RunActivityItem
  index: number
}

function makeWeekContext(item: RunActivityItem, effectiveWeek: number | null): string {
  const supportsWeekInspection =
    item.kind === 'event' ||
    item.kind === 'ranking_snapshot' ||
    item.kind === 'race_snapshot' ||
    item.kind === 'admin_wildcard_assignment' ||
    item.kind === 'admin_pre_draw_withdrawal_replacement'
  if (!supportsWeekInspection) {
    return 'Not meaningful for this activity kind'
  }
  if (effectiveWeek == null) {
    return 'No week context available'
  }
  return `W${effectiveWeek}`
}

function getEffectiveWeek(
  item: RunActivityItem,
  plannedContextByEventId: Map<string, { week: number; category: string; templateId: string; planPosition: number }>,
  persistedEventById: Map<string, { week: number | null; eventSequence: number }>
): number | null {
  if (item.week != null) {
    return item.week
  }

  const contextEventId = item.event_id ?? item.source_event_id
  if (!contextEventId) {
    return null
  }

  return persistedEventById.get(contextEventId)?.week ?? plannedContextByEventId.get(contextEventId)?.week ?? null
}

export function ActivityPage(): JSX.Element {
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [kindFilter, setKindFilter] = useState('')
  const [seasonFilter, setSeasonFilter] = useState('')
  const [weekFilter, setWeekFilter] = useState('')
  const [textFilter, setTextFilter] = useState('')

  const requestedSelectedIndex = Number.parseInt(searchParams.get('selectedItem') ?? '', 10)
  const hasRequestedSelectedIndex = Number.isInteger(requestedSelectedIndex)

  const activityQuery = useQuery({
    queryKey: ['run-activity', runId],
    queryFn: () => getRunActivity(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })

  const items = activityQuery.data?.items ?? []
  const indexedItems = useMemo<IndexedActivityItem[]>(() => items.map((item, index) => ({ item, index })), [items])

  const plannedContextByEventId = useMemo(() => {
    const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
    const map = new Map<string, { week: number; category: string; templateId: string; planPosition: number }>()
    orderedEvents.forEach((event, index) => {
      map.set(event.event_id, {
        week: event.week,
        category: event.category,
        templateId: event.template_id,
        planPosition: index + 1
      })
    })
    return map
  }, [runQuery.data?.season_state.ordered_events])

  const persistedEventById = useMemo(() => {
    const map = new Map<string, { week: number | null; eventSequence: number }>()
    ;(eventsQuery.data?.events ?? []).forEach((event) => {
      map.set(event.event_id, { week: event.week, eventSequence: event.event_sequence })
    })
    return map
  }, [eventsQuery.data?.events])

  const normalizedTextFilter = textFilter.trim().toLowerCase()
  const filteredItems = indexedItems.filter(({ item }) => {
    const effectiveWeek = getEffectiveWeek(item, plannedContextByEventId, persistedEventById)
    const kindMatches = kindFilter ? item.kind === kindFilter : true
    const seasonMatches = seasonFilter ? String(item.season) === seasonFilter : true
    const weekMatches = weekFilter ? String(effectiveWeek) === weekFilter : true
    const textMatches = normalizedTextFilter
      ? item.label.toLowerCase().includes(normalizedTextFilter) ||
        (item.event_id?.toLowerCase().includes(normalizedTextFilter) ?? false) ||
        (item.related_run_id?.toLowerCase().includes(normalizedTextFilter) ?? false)
      : true

    return kindMatches && seasonMatches && weekMatches && textMatches
  })

  const kindOptions = useMemo(() => {
    const seen = new Set<string>()
    const values: string[] = []
    items.forEach((item) => {
      if (!seen.has(item.kind)) {
        seen.add(item.kind)
        values.push(item.kind)
      }
    })
    return values
  }, [items])

  const seasonOptions = useMemo(() => {
    const seen = new Set<string>()
    const values: string[] = []
    items.forEach((item) => {
      if (item.season == null) return
      const normalized = String(item.season)
      if (!seen.has(normalized)) {
        seen.add(normalized)
        values.push(normalized)
      }
    })
    return values
  }, [items])

  const weekOptions = useMemo(() => {
    const seen = new Set<string>()
    const values: string[] = []
    items.forEach((item) => {
      const effectiveWeek = getEffectiveWeek(item, plannedContextByEventId, persistedEventById)
      if (effectiveWeek == null) return
      const normalized = String(effectiveWeek)
      if (!seen.has(normalized)) {
        seen.add(normalized)
        values.push(normalized)
      }
    })
    return values
  }, [items, plannedContextByEventId, persistedEventById])

  useEffect(() => {
    if (!filteredItems.length) {
      setSelectedIndex(null)
      return
    }

    if (hasRequestedSelectedIndex && filteredItems.some((entry) => entry.index === requestedSelectedIndex)) {
      if (selectedIndex !== requestedSelectedIndex) {
        setSelectedIndex(requestedSelectedIndex)
      }
      return
    }

    if (selectedIndex == null || !filteredItems.some((entry) => entry.index === selectedIndex)) {
      setSelectedIndex(filteredItems[0].index)
    }
  }, [filteredItems, hasRequestedSelectedIndex, requestedSelectedIndex, selectedIndex])

  const selectedEntry = filteredItems.find((entry) => entry.index === selectedIndex) ?? null
  const selectedItem = selectedEntry?.item ?? null
  const selectedContextEventId = selectedItem?.event_id ?? selectedItem?.source_event_id ?? null
  const selectedPlannedContext = selectedContextEventId ? plannedContextByEventId.get(selectedContextEventId) : undefined
  const selectedPersistedEvent = selectedContextEventId ? persistedEventById.get(selectedContextEventId) : undefined
  const selectedWeek = selectedItem ? getEffectiveWeek(selectedItem, plannedContextByEventId, persistedEventById) : null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Run activity"
        runId={runId}
        subtitle="Deterministic run-level feed browser with filterable activity and compact bridge navigation."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Items', value: items.length },
          { label: 'Matching filters', value: filteredItems.length },
          { label: 'Selected', value: selectedItem?.label ?? 'None' }
        ]}
      />

      <SectionCard title="Filters">
        <div className="grid">
          <label>
            Kind
            <select aria-label="Filter activity by kind" value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}>
              <option value="">All kinds</option>
              {kindOptions.map((kind) => (
                <option key={kind} value={kind}>
                  {kind}
                </option>
              ))}
            </select>
          </label>
          <label>
            Season
            <select aria-label="Filter activity by season" value={seasonFilter} onChange={(event) => setSeasonFilter(event.target.value)}>
              <option value="">All seasons</option>
              {seasonOptions.map((season) => (
                <option key={season} value={season}>
                  {season}
                </option>
              ))}
            </select>
          </label>
          <label>
            Week
            <select aria-label="Filter activity by week" value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">All weeks</option>
              {weekOptions.map((week) => (
                <option key={week} value={week}>
                  W{week}
                </option>
              ))}
            </select>
          </label>
          <label>
            Text
            <input
              aria-label="Filter activity by label or identifier text"
              value={textFilter}
              onChange={(event) => setTextFilter(event.target.value)}
              placeholder="Label, event ID, or related run ID"
            />
          </label>
        </div>
      </SectionCard>

      <SectionCard title="Activity feed">
        {activityQuery.isLoading ? <p className="status">Loading activity feed...</p> : null}
        {activityQuery.error ? <p className="error">Failed to load activity feed: {formatApiError(activityQuery.error)}</p> : null}
        {!activityQuery.isLoading && !activityQuery.error && items.length === 0 ? (
          <EmptyState message="No activity has been persisted for this run yet." />
        ) : null}
        {!activityQuery.isLoading && !activityQuery.error && items.length > 0 && filteredItems.length === 0 ? (
          <EmptyState message="No activity items match the current filters." />
        ) : null}
        {filteredItems.length > 0 ? (
          <SelectableHistoryList
            items={filteredItems}
            getKey={({ index, item }) => `${index}-${item.kind}-${item.sequence ?? 'none'}`}
            getLabel={({ item, index }) => `${index + 1}. ${item.label}`}
            getSubLabel={({ item }) => {
              const segments: string[] = [item.kind]
              if (item.season != null) segments.push(`S${item.season}`)
              if (item.week != null) segments.push(`W${item.week}`)
              if (item.event_id) segments.push(item.event_id)
              if (item.related_run_id) segments.push(`Run ${item.related_run_id}`)
              return segments.join(' · ')
            }}
            isSelected={(entry) => entry.index === selectedIndex}
            onSelect={(entry) => {
              setSelectedIndex(entry.index)
              setSearchParams((current) => {
                const next = new URLSearchParams(current)
                next.set('selectedItem', String(entry.index))
                return next
              })
            }}
            ariaLabel="Run activity feed list"
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Selected activity detail">
        {selectedItem ? (
          <>
            <MetadataList
              items={[
                { label: 'Label', value: selectedItem.label },
                { label: 'Kind', value: selectedItem.kind },
                { label: 'Sequence', value: selectedItem.sequence ?? '—' },
                { label: 'Season', value: selectedItem.season ?? '—' },
                { label: 'Week context', value: makeWeekContext(selectedItem, selectedWeek) },
                { label: 'Event ID', value: selectedItem.event_id ?? '—' },
                { label: 'Source event ID', value: selectedItem.source_event_id ?? '—' },
                { label: 'Related run ID', value: selectedItem.related_run_id ?? '—' },
                {
                  label: 'Plan context',
                  value: selectedPlannedContext
                    ? `Plan #${selectedPlannedContext.planPosition} (${selectedPlannedContext.category}, ${selectedPlannedContext.templateId})`
                    : 'No ordered-plan match'
                }
              ]}
            />
            <SummaryPills
              items={[
                { label: 'Week detail', value: selectedWeek != null ? `W${selectedWeek}` : 'Unavailable' },
                {
                  label: 'Bridge links',
                  value:
                    activityBridgeItems(runId, selectedItem, selectedWeek, {
                      contextEventId: selectedContextEventId,
                      hasPersistedContext: Boolean(selectedPersistedEvent),
                      hasPlannedContext: Boolean(selectedPlannedContext)
                    }).length || 'None'
                }
              ]}
            />
            <CompactSummaryCard
              items={activityBridgeItems(runId, selectedItem, selectedWeek, {
                contextEventId: selectedContextEventId,
                hasPersistedContext: Boolean(selectedPersistedEvent),
                hasPlannedContext: Boolean(selectedPlannedContext)
              })}
            />
            {runQuery.error ? <p className="error">Failed to load ordered-plan context: {formatApiError(runQuery.error)}</p> : null}
            {eventsQuery.error ? <p className="error">Failed to load persisted events context: {formatApiError(eventsQuery.error)}</p> : null}
          </>
        ) : (
          <EmptyState message="Select an activity item to inspect details." />
        )}
      </SectionCard>
    </section>
  )
}

function activityBridgeItems(
  runId: string,
  item: RunActivityItem,
  selectedWeek: number | null,
  snapshotContext: { contextEventId: string | null; hasPersistedContext: boolean; hasPlannedContext: boolean }
): Array<{ label: string; value: JSX.Element | string }> {
  const { contextEventId, hasPersistedContext, hasPlannedContext } = snapshotContext
  const links: Array<{ label: string; value: JSX.Element | string }> = []

  if (item.kind === 'event' && item.event_id) {
    links.push({
      label: 'Persisted event detail',
      value: <Link to={`/runs/${runId}/events/${encodeURIComponent(item.event_id)}`}>Open persisted event detail</Link>
    })
    links.push({
      label: 'Planned-event detail',
      value: <Link to={`/runs/${runId}/calendar/${encodeURIComponent(item.event_id)}`}>Open planned-event detail</Link>
    })
  }

  if ((item.kind === 'ranking_snapshot' || item.kind === 'race_snapshot') && item.snapshot_sequence != null) {
    const mode = item.kind === 'ranking_snapshot' ? 'ranking' : 'race'
    links.push({
      label: 'Snapshot detail',
      value: <Link to={`/runs/${runId}/snapshots/${mode}/${item.snapshot_sequence}`}>Open {mode} snapshot detail</Link>
    })
    links.push({
      label: 'Source planned-event detail',
      value:
        contextEventId && hasPlannedContext ? (
          <Link to={`/runs/${runId}/calendar/${encodeURIComponent(contextEventId)}`}>Open source planned-event detail</Link>
        ) : (
          'No ordered-plan context for this snapshot source event.'
        )
    })
    links.push({
      label: 'Source persisted event detail',
      value:
        contextEventId && hasPersistedContext ? (
          <Link to={`/runs/${runId}/events/${encodeURIComponent(contextEventId)}`}>Open source persisted event detail</Link>
        ) : (
          'No persisted-event context for this snapshot source event.'
        )
    })
  }

  if (item.kind === 'finals_qualification') {
    links.push({
      label: 'Finals qualification detail',
      value: <Link to={`/runs/${runId}/finals/qualification`}>Open finals qualification detail</Link>
    })
  }

  if (item.kind === 'finals_result') {
    links.push({
      label: 'Finals result detail',
      value: <Link to={`/runs/${runId}/finals/result`}>Open finals result detail</Link>
    })
  }

  if (item.kind === 'rollover') {
    links.push({
      label: 'Rollover detail',
      value:
        item.season != null ? (
          <Link to={`/runs/${runId}/rollover/${item.season}`}>Open rollover season detail</Link>
        ) : (
          <Link to={`/runs/${runId}/rollover`}>Open rollover page</Link>
        )
    })
  }

  if (item.kind === 'bootstrap_child' && item.related_run_id) {
    links.push({
      label: 'Child run detail',
      value: <Link to={`/runs/${item.related_run_id}`}>Open child run detail</Link>
    })
    links.push({
      label: 'Season chain',
      value: <Link to={`/runs/${item.related_run_id}/season-chain`}>Open child run season chain</Link>
    })
  }

  if (item.kind === 'admin_wildcard_assignment' && item.event_id) {
    links.push({
      label: 'Wildcard event planned detail',
      value: <Link to={`/runs/${runId}/calendar/${encodeURIComponent(item.event_id)}`}>Open wildcard event planned detail</Link>
    })
    links.push({
      label: 'Wildcard event persisted detail',
      value: hasPersistedContext ? (
        <Link to={`/runs/${runId}/events/${encodeURIComponent(item.event_id)}`}>Open wildcard event persisted detail</Link>
      ) : (
        'Wildcard event has not been persisted yet.'
      )
    })
  }
  if (item.kind === 'admin_pre_draw_withdrawal_replacement' && item.event_id) {
    links.push({
      label: 'Pre-draw event planned detail',
      value: (
        <Link to={`/runs/${runId}/calendar/${encodeURIComponent(item.event_id)}`}>Open pre-draw event planned detail</Link>
      )
    })
    links.push({
      label: 'Pre-draw event persisted detail',
      value: hasPersistedContext ? (
        <Link to={`/runs/${runId}/events/${encodeURIComponent(item.event_id)}`}>Open pre-draw event persisted detail</Link>
      ) : (
        'Pre-draw event has not been persisted yet.'
      )
    })
  }

  const supportsWeekInspection =
    item.kind === 'event' ||
    item.kind === 'ranking_snapshot' ||
    item.kind === 'race_snapshot' ||
    item.kind === 'admin_wildcard_assignment' ||
    item.kind === 'admin_pre_draw_withdrawal_replacement'
  if (supportsWeekInspection && selectedWeek != null) {
    links.push({
      label: 'Week detail',
      value: <Link to={`/runs/${runId}/weeks/${selectedWeek}`}>Open week detail page (W{selectedWeek})</Link>
    })
  }

  if (links.length === 0) {
    links.push({ label: 'Links', value: 'No direct bridge links available for this activity item.' })
  }

  return links
}
