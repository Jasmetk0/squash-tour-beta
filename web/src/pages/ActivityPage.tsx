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
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

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
    item.kind === 'admin_pre_draw_withdrawal_replacement' ||
    item.kind === 'admin_late_replacement_lucky_loser'
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

import { useHistoryText } from './runHistoryText'
export function ActivityPage(): JSX.Element {
  const t = useHistoryText()
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)
  const [kindFilter, setKindFilter] = useState('')
  const [seasonFilter, setSeasonFilter] = useState('')
  const [weekFilter, setWeekFilter] = useState('')
  const [textFilter, setTextFilter] = useState('')

  const requestedItemText = searchParams.get('selectedItem') ?? ''
  // The deep link indexes the original activity items; reject partial numbers.
  const requestedSelectedIndex = /^\d+$/.test(requestedItemText) ? Number(requestedItemText) : NaN
  const hasRequestedSelectedIndex = Number.isSafeInteger(requestedSelectedIndex) && requestedSelectedIndex >= 0

  const activityQuery = useQuery({
    queryKey: ['run-activity', runId],
    queryFn: () => getRunActivity(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })

  const activityMismatch = Boolean(activityQuery.data?.run_id && activityQuery.data.run_id !== runId)
  const eventsMismatch = Boolean(eventsQuery.data?.run_id && eventsQuery.data.run_id !== runId)
  const items = activityMismatch ? [] : activityQuery.data?.items ?? []
  const plannedContextUnavailable = runQuery.isLoading || Boolean(runQuery.error) ||
    !runQuery.data || runQuery.data.run.run_id !== runId
  const persistedContextUnavailable = eventsQuery.isLoading || Boolean(eventsQuery.error) ||
    !eventsQuery.data || eventsMismatch
  const indexedItems = useMemo<IndexedActivityItem[]>(() => items.map((item, index) => ({ item, index })), [items])

  const plannedContextByEventId = useMemo(() => {
    const orderedEvents = runQuery.data?.run.run_id === runId ? runQuery.data.season_state.ordered_events : []
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
  }, [runId, runQuery.data])

  const persistedEventById = useMemo(() => {
    const map = new Map<string, { week: number | null; eventSequence: number }>()
    ;(eventsMismatch ? [] : eventsQuery.data?.events ?? []).forEach((event) => {
      map.set(event.event_id, { week: event.week, eventSequence: event.event_sequence })
    })
    return map
  }, [eventsMismatch, eventsQuery.data?.events])

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
  const bridgeItems = selectedItem ? activityBridgeItems(runId, selectedItem, selectedWeek, t, {
    contextEventId: selectedContextEventId,
    hasPersistedContext: Boolean(selectedPersistedEvent),
    hasPlannedContext: Boolean(selectedPlannedContext),
    plannedContextUnavailable,
    persistedContextUnavailable
  }) : []
  const availableBridgeLinks = bridgeItems.filter(({ value }) => typeof value !== 'string').length

  return (
    <section className="panel">
      <RunScopedHeader
        title={t('Run activity')}
        runId={runId}
        subtitle={t('Deterministic run-level feed browser with filterable activity and compact bridge navigation.')}
      />
      <p className="status">{t('Stored legacy SimulationRun history. This view does not verify Product Run Saved Revision authority.')}</p>
      <p className="status">{t('History records shown are only those returned by this endpoint; they do not certify a complete Product Run history.')}</p>
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Items'), value: items.length },
          { label: t('Matching filters'), value: filteredItems.length },
          { label: t('Selected'), value: selectedItem?.label ?? t('None') }
        ]}
      />

      <SectionCard title={t('Filters')}>
        <div className="grid">
          <label>
            {t('Kind')}
            <select aria-label={t('Filter activity by kind')} value={kindFilter} onChange={(event) => setKindFilter(event.target.value)}>
              <option value="">{t('All kinds')}</option>
              {kindOptions.map((kind) => (
                <option key={kind} value={kind}>
                  {t(kind)}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Season')}
            <select aria-label={t('Filter activity by season')} value={seasonFilter} onChange={(event) => setSeasonFilter(event.target.value)}>
              <option value="">{t('All seasons')}</option>
              {seasonOptions.map((season) => (
                <option key={season} value={season}>
                  {season}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Week')}
            <select aria-label={t('Filter activity by week')} value={weekFilter} onChange={(event) => setWeekFilter(event.target.value)}>
              <option value="">{t('All weeks')}</option>
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
              aria-label={t('Filter activity by label or identifier text')}
              value={textFilter}
              onChange={(event) => setTextFilter(event.target.value)}
              placeholder={t('Label, event ID, or related run ID')}
            />
          </label>
        </div>
        <button type="button" onClick={() => { setKindFilter(''); setSeasonFilter(''); setWeekFilter(''); setTextFilter('') }}>{t('Reset filters')}</button>
      </SectionCard>

      <SectionCard title={t('Activity feed')}>
        {activityMismatch && <p role="alert" className="error">{t('Activity response belongs to another Run; its records are hidden.')}</p>}
        <button type="button" onClick={() => void activityQuery.refetch()}>{t('Refresh read-only data')}</button>
        {activityQuery.isLoading ? <p className="status">{t('Loading activity feed...')}</p> : null}
        {isApiNotFound(activityQuery.error)
          ? <EmptyState message={t('Run activity could not be found for this Run.')} />
          : activityQuery.error ? <p role="alert" className="error">{t('Failed to load activity feed')}: {formatApiError(activityQuery.error)}</p> : null}
        {!activityQuery.isLoading && !activityQuery.error && !activityMismatch && items.length === 0 ? (
          <EmptyState message={t('No activity has been persisted for this run yet.')} />
        ) : null}
        {!activityQuery.isLoading && !activityQuery.error && !activityMismatch && items.length > 0 && filteredItems.length === 0 ? (
          <EmptyState message={t('No activity items match the current filters.')} />
        ) : null}
        {filteredItems.length > 0 ? (
          <SelectableHistoryList
            items={filteredItems}
            getKey={({ index, item }) => `${index}-${item.kind}-${item.sequence ?? 'none'}`}
            getLabel={({ item, index }) => `${index + 1}. ${item.label}`}
            getSubLabel={({ item }) => {
              const segments: string[] = [t(item.kind)]
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
            ariaLabel={t('Run activity feed list')}
          />
        ) : null}
      </SectionCard>

      <SectionCard title={t('Selected activity detail')}>
        {selectedItem ? (
          <>
            <MetadataList
              items={[
                { label: t('Label'), value: selectedItem.label },
                { label: t('Kind'), value: t(selectedItem.kind) },
                { label: t('Sequence'), value: selectedItem.sequence ?? '—' },
                { label: t('Season'), value: selectedItem.season ?? '—' },
                { label: t('Week context'), value: t(makeWeekContext(selectedItem, selectedWeek)) },
                { label: t('Event ID'), value: selectedItem.event_id ?? '—' },
                { label: t('Source event ID'), value: selectedItem.source_event_id ?? '—' },
                { label: t('Related run ID'), value: selectedItem.related_run_id ?? '—' },
                {
                  label: t('Plan context'),
                  value: selectedPlannedContext
                    ? `Plan #${selectedPlannedContext.planPosition} (${selectedPlannedContext.category}, ${selectedPlannedContext.templateId})`
                    : plannedContextUnavailable ? t('Unavailable') : t('No ordered-plan match')
                }
              ]}
            />
            <SummaryPills
              items={[
                { label: t('Week detail'), value: selectedWeek != null ? `W${selectedWeek}` : t('Unavailable') },
                {
                  label: t('Bridge links'),
                  value:
                    availableBridgeLinks
                }
              ]}
            />
            <CompactSummaryCard
              items={bridgeItems}
            />
            {runQuery.error ? <p className="error">{t('Failed to load ordered-plan context')}: {formatApiError(runQuery.error)}</p> : null}
            {eventsQuery.error ? <p className="error">{t('Failed to load persisted events context')}: {formatApiError(eventsQuery.error)}</p> : null}
          </>
        ) : (
          <EmptyState message={t('Select an activity item to inspect details.')} />
        )}
      </SectionCard>
    </section>
  )
}

function activityBridgeItems(
  runId: string,
  item: RunActivityItem,
  selectedWeek: number | null,
  t: (english: string) => string,
  snapshotContext: {
    contextEventId: string | null
    hasPersistedContext: boolean
    hasPlannedContext: boolean
    plannedContextUnavailable: boolean
    persistedContextUnavailable: boolean
  }
): Array<{ label: string; value: JSX.Element | string }> {
  const { contextEventId, hasPersistedContext, hasPlannedContext, plannedContextUnavailable, persistedContextUnavailable } = snapshotContext
  const links: Array<{ label: string; value: JSX.Element | string }> = []

  if (item.kind === 'event' && item.event_id) {
    links.push({
      label: t('Persisted event detail'),
      value: <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(item.event_id)}`}>{t('Open persisted event detail')}</Link>
    })
    links.push({
      label: t('Planned-event detail'),
      value: hasPlannedContext
        ? <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(item.event_id)}`}>{t('Open planned-event detail')}</Link>
        : plannedContextUnavailable ? t('Unavailable') : t('No ordered-plan match')
    })
  }

  if ((item.kind === 'ranking_snapshot' || item.kind === 'race_snapshot') && item.snapshot_sequence != null) {
    const mode = item.kind === 'ranking_snapshot' ? 'ranking' : 'race'
    links.push({
      label: t('Snapshot detail'),
      value: <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${mode}/${item.snapshot_sequence}`}>{mode === 'ranking' ? t('Open ranking snapshot detail') : t('Open race snapshot detail')}</Link>
    })
    links.push({
      label: t('Source planned-event detail'),
      value:
        contextEventId && hasPlannedContext ? (
          <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(contextEventId)}`}>{t('Open source planned-event detail')}</Link>
        ) : (
          plannedContextUnavailable ? t('Unavailable') : t('No ordered-plan context for this snapshot source event.')
        )
    })
    links.push({
      label: t('Source persisted event detail'),
      value:
        contextEventId && hasPersistedContext ? (
          <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(contextEventId)}`}>{t('Open source persisted event detail')}</Link>
        ) : (
          persistedContextUnavailable ? t('Unavailable') : t('No persisted-event context for this snapshot source event.')
        )
    })
  }

  if (item.kind === 'finals_qualification') {
    links.push({
      label: t('Finals qualification detail'),
      value: <Link to={`/runs/${encodeURIComponent(runId)}/finals/qualification`}>{t('Open finals qualification detail')}</Link>
    })
  }

  if (item.kind === 'finals_result') {
    links.push({
      label: t('Finals result detail'),
      value: <Link to={`/runs/${encodeURIComponent(runId)}/finals/result`}>{t('Open finals result detail')}</Link>
    })
  }

  if (item.kind === 'rollover') {
    links.push({
      label: t('Rollover detail'),
      value:
        item.season != null ? (
          <Link to={`/runs/${encodeURIComponent(runId)}/rollover/${item.season}`}>{t('Open rollover season detail')}</Link>
        ) : (
          <Link to={`/runs/${encodeURIComponent(runId)}/rollover`}>{t('Open rollover page')}</Link>
        )
    })
  }

  if (item.kind === 'bootstrap_child' && item.related_run_id) {
    links.push({
      label: t('Child run detail'),
      value: <Link to={`/runs/${encodeURIComponent(item.related_run_id)}`}>{t('Open child run detail')}</Link>
    })
    links.push({
      label: t('Season chain'),
      value: <Link to={`/runs/${encodeURIComponent(item.related_run_id)}/season-chain`}>{t('Open child run season chain')}</Link>
    })
  }

  if (item.kind === 'admin_wildcard_assignment' && item.event_id) {
    links.push({
      label: t('Wildcard event planned detail'),
      value: hasPlannedContext ? <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(item.event_id)}`}>{t('Open wildcard event planned detail')}</Link> : plannedContextUnavailable ? t('Unavailable') : t('No ordered-plan match')
    })
    links.push({
      label: t('Wildcard event persisted detail'),
      value: hasPersistedContext ? (
        <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(item.event_id)}`}>{t('Open wildcard event persisted detail')}</Link>
      ) : (
        persistedContextUnavailable ? t('Unavailable') : t('Wildcard event has not been persisted yet.')
      )
    })
  }
  if (item.kind === 'admin_pre_draw_withdrawal_replacement' && item.event_id) {
    links.push({
      label: t('Pre-draw event planned detail'),
      value: (
        hasPlannedContext ? <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(item.event_id)}`}>{t('Open pre-draw event planned detail')}</Link> : plannedContextUnavailable ? t('Unavailable') : t('No ordered-plan match')
      )
    })
    links.push({
      label: t('Pre-draw event persisted detail'),
      value: hasPersistedContext ? (
        <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(item.event_id)}`}>{t('Open pre-draw event persisted detail')}</Link>
      ) : (
        persistedContextUnavailable ? t('Unavailable') : t('Pre-draw event has not been persisted yet.')
      )
    })
  }
  if (item.kind === 'admin_late_replacement_lucky_loser' && item.event_id) {
    links.push({
      label: t('Late-replacement event planned detail'),
      value: (
        hasPlannedContext ? <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(item.event_id)}`}>{t('Open late-replacement event planned detail')}</Link> : plannedContextUnavailable ? t('Unavailable') : t('No ordered-plan match')
      )
    })
    links.push({
      label: t('Late-replacement event persisted detail'),
      value: hasPersistedContext ? (
        <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(item.event_id)}`}>{t('Open late-replacement event persisted detail')}</Link>
      ) : (
        persistedContextUnavailable ? t('Unavailable') : t('Late-replacement event has not been persisted yet.')
      )
    })
  }

  const supportsWeekInspection =
    item.kind === 'event' ||
    item.kind === 'ranking_snapshot' ||
    item.kind === 'race_snapshot' ||
    item.kind === 'admin_wildcard_assignment' ||
    item.kind === 'admin_pre_draw_withdrawal_replacement' ||
    item.kind === 'admin_late_replacement_lucky_loser'
  if (supportsWeekInspection && selectedWeek != null) {
    links.push({
      label: t('Week detail'),
      value: <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${selectedWeek}`}>{t('Open week detail page')} (W{selectedWeek})</Link>
    })
  }

  if (links.length === 0) {
    links.push({ label: t('Links'), value: t('No direct bridge links available for this activity item.') })
  }

  return links
}
