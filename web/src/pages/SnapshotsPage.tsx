import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getRun, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'
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
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

type Mode = 'ranking' | 'race'

const MISSING_SOURCE_EVENT_ID_FALLBACK = 'Missing source_event_id'

import { useHistoryText } from './runHistoryText'
export function SnapshotsPage({ mode }: { mode: Mode }): JSX.Element {
  const t = useHistoryText()
  const { language } = useLanguage()
  const { runId = '' } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const weekFilter = searchParams.get('filterWeek') ?? ''
  const categoryFilter = searchParams.get('filterCategory') ?? ''
  const sourceEventFilter = searchParams.get('filterSourceEvent') ?? ''
  const requestedSequenceText = searchParams.get('selectedSequence') ?? ''
  // A partial number like "3abc" must not select snapshot #3.
  const requestedSequence = /^\d+$/.test(requestedSequenceText) ? Number(requestedSequenceText) : NaN
  // Newly selected sequences are scoped to both the route's Run and mode.
  // Old single-key bookmarks remain readable within the route where opened.
  const selectionMode = searchParams.get('selectedMode')
  const selectionRun = searchParams.get('selectedRun')
  const selectionContextMatches = (!selectionMode && !selectionRun) || (selectionMode === mode && selectionRun === runId)
  const hasRequestedSequence = selectionContextMatches && Number.isSafeInteger(requestedSequence) && requestedSequence > 0

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
  const snapshots = snapshotMismatch || query.error ? [] : query.data?.snapshots ?? []
  const siblingMismatch = Boolean(siblingSnapshotsQuery.data?.run_id && siblingSnapshotsQuery.data.run_id !== runId)
  const eventsMismatch = Boolean(eventsQuery.data?.run_id && eventsQuery.data.run_id !== runId)
  const runMismatch = Boolean(runQuery.data?.run.run_id && runQuery.data.run.run_id !== runId)
  const planSeasonMismatch = Boolean(runQuery.data && runQuery.data.run.run_id === runId &&
    runQuery.data.season_state.season != null &&
    runQuery.data.season_state.season !== runQuery.data.run.season)
  const planUnavailable = runQuery.isLoading || Boolean(runQuery.error) || !runQuery.data || runMismatch || planSeasonMismatch
  const eventsUnavailable = eventsQuery.isLoading || Boolean(eventsQuery.error) || !eventsQuery.data || eventsMismatch
  const orderedEvents = !planUnavailable ? runQuery.data?.season_state.ordered_events ?? [] : []
  const plannedContext = useMemo(() => {
    const map = new Map<string, { season: number; week: number; category: string; tour: string; templateId: string; planPosition: number }>()
    orderedEvents.forEach((event, index) => {
      if (event.season !== runQuery.data?.season_state.season) return
      map.set(event.event_id, {
        season: event.season,
        week: event.week,
        category: event.category,
        tour: event.tour,
        templateId: event.template_id,
        planPosition: index + 1
      })
    })
    return map
  }, [orderedEvents])
  const persistedEvidence = useMemo(() => {
    const byId = new Map<string, { season: number | null; eventSequence: number; week: number | null }>()
    const ambiguousIds = new Set<string>()
    ;(eventsMismatch || eventsQuery.error ? [] : eventsQuery.data?.events ?? []).forEach((event) => {
      if (byId.has(event.event_id) || ambiguousIds.has(event.event_id)) {
        byId.delete(event.event_id)
        ambiguousIds.add(event.event_id)
      } else {
        byId.set(event.event_id, { season: event.season, eventSequence: event.event_sequence, week: event.week })
      }
    })
    return { byId, ambiguousIds }
  }, [eventsMismatch, eventsQuery.error, eventsQuery.data?.events])
  const persistedEventsById = persistedEvidence.byId
  const ambiguousPersistedEventIds = persistedEvidence.ambiguousIds
  const plannedForSource = (sourceEventId: string) => {
    if (ambiguousPersistedEventIds.has(sourceEventId)) return undefined
    const plan = plannedContext.get(sourceEventId)
    const persisted = persistedEventsById.get(sourceEventId)
    return plan && (!persisted || persisted.season == null || persisted.season === plan.season) ? plan : undefined
  }
  const matchesFilters = (snapshot: (typeof snapshots)[number], week: string, category: string, sourceText: string) => {
    const sourceEventId = snapshot.source_event_id
    const planContext = sourceEventId ? plannedForSource(sourceEventId) : undefined
    const persistedContext = sourceEventId ? persistedEventsById.get(sourceEventId) : undefined
    const effectiveWeek = persistedContext?.week ?? planContext?.week ?? null
    const query = sourceText.trim().toLowerCase()
    // Missing source week is absence, not the literal "null"/"undefined".
    return (!week || (effectiveWeek != null && String(effectiveWeek) === week)) &&
      (!category || planContext?.category === category) &&
      (!query || (sourceEventId?.toLowerCase().includes(query) ?? false))
  }
  const filteredSnapshots = snapshots.filter(snapshot => matchesFilters(snapshot, weekFilter, categoryFilter, sourceEventFilter))
  const weekOptions = useMemo(() => {
    const values = new Set<string>()
    snapshots.forEach((snapshot) => {
      const sourceEventId = snapshot.source_event_id
      if (!sourceEventId) return
      const plan = plannedForSource(sourceEventId)
      const persisted = persistedEventsById.get(sourceEventId)
      const effectiveWeek = persisted?.week ?? plan?.week
      if (effectiveWeek != null) values.add(String(effectiveWeek))
    })
    return Array.from(values)
  }, [plannedContext, persistedEventsById, ambiguousPersistedEventIds, snapshots])
  const categoryOptions = useMemo(() => {
    const values = new Set<string>()
    snapshots.forEach((snapshot) => {
      const sourceEventId = snapshot.source_event_id
      if (!sourceEventId) return
      const category = plannedForSource(sourceEventId)?.category
      if (category) values.add(category)
    })
    return Array.from(values)
  }, [plannedContext, ambiguousPersistedEventIds, snapshots])

  const unknownWeek = weekFilter !== '' && !weekOptions.includes(weekFilter)
  const unknownCategory = categoryFilter !== '' && !categoryOptions.includes(categoryFilter)

  // Filter writes touch only this page's keys. An exact snapshot bookmark is
  // retained only when its mode/Run identity and new filter set still agree.
  const updateFilters = (key: 'filterWeek' | 'filterCategory' | 'filterSourceEvent' | null, value = '', replaceEntry = false) => {
    setSearchParams(current => {
      const next = new URLSearchParams(current)
      if (key === null) {
        next.delete('filterWeek')
        next.delete('filterCategory')
        next.delete('filterSourceEvent')
      } else if (value) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
      const sequenceText = current.get('selectedSequence') ?? ''
      const sequence = /^\d+$/.test(sequenceText) ? Number(sequenceText) : NaN
      const currentMode = current.get('selectedMode')
      const currentRun = current.get('selectedRun')
      const inContext = (!currentMode && !currentRun) || (currentMode === mode && currentRun === runId)
      const bookmarked = inContext && Number.isSafeInteger(sequence) && sequence > 0
        ? snapshots.find(snapshot => snapshot.snapshot_sequence === sequence) : undefined
      if ((current.has('selectedSequence') || current.has('selectedMode') || current.has('selectedRun')) &&
        (!bookmarked || !matchesFilters(bookmarked, next.get('filterWeek') ?? '', next.get('filterCategory') ?? '', next.get('filterSourceEvent') ?? ''))) {
        next.delete('selectedSequence')
        next.delete('selectedMode')
        next.delete('selectedRun')
      }
      return next
    }, { replace: replaceEntry })
  }

  // URL-backed selection follows Back/Forward and filters without a second
  // local state that may momentarily select an outdated snapshot.
  const selected = (hasRequestedSequence
    ? filteredSnapshots.find((snapshot) => snapshot.snapshot_sequence === requestedSequence)
    : undefined) ?? filteredSnapshots[0] ?? null
  const selectedSequence = selected?.snapshot_sequence ?? null

  const title = mode === 'ranking' ? t('Ranking snapshots') : t('Race snapshots')
  const selectedSourceAmbiguous = Boolean(selected?.source_event_id && ambiguousPersistedEventIds.has(selected.source_event_id))
  const siblingMatchCount = selectedSourceAmbiguous ? null : !selected?.source_event_id ? 0
    : siblingMismatch || siblingSnapshotsQuery.isLoading || siblingSnapshotsQuery.error || !siblingSnapshotsQuery.data ? null
    : siblingSnapshotsQuery.data.snapshots.filter((item) => item.source_event_id === selected.source_event_id).length

  return (
    <section className="panel">
      <RunScopedHeader
        title={title}
        runId={runId}
        subtitle={t('Browse stored snapshot history and inspect payload details by sequence.')}
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
            <select aria-label={t('Filter snapshots by week')} value={weekFilter} onChange={(event) => updateFilters('filterWeek', event.target.value)}>
              <option value="">{t('All weeks')}</option>
              {unknownWeek && <option value={weekFilter}>{language === 'cs' ? `Neznámý týden: ${weekFilter}` : `Unknown week: ${weekFilter}`}</option>}
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
              aria-label={t('Filter snapshots by category')}
              value={categoryFilter}
              onChange={(event) => updateFilters('filterCategory', event.target.value)}
            >
              <option value="">{t('All categories')}</option>
              {unknownCategory && <option value={categoryFilter}>{language === 'cs' ? `Neznámá kategorie: ${categoryFilter}` : `Unknown category: ${categoryFilter}`}</option>}
              {categoryOptions.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label>
            {t('Source event text')}
            <input
              aria-label={t('Filter snapshots by source event')}
              value={sourceEventFilter}
              onChange={(event) => updateFilters('filterSourceEvent', event.target.value, true)}
              placeholder="source_event_id"
            />
          </label>
        </div>
        {(unknownWeek || unknownCategory) && !query.isLoading && <p role="status" className="status">{language === 'cs' ? 'Zadaný týden nebo kategorie nepatří mezi dostupné filtry. Zůstává vybraný neznámý filtr, nikoliv Vše.' : 'The requested week or category is unavailable. The view has not switched to All.'}</p>}
        <button type="button" onClick={() => updateFilters(null)}>{t('Reset filters')}</button>
      </SectionCard>

      {runMismatch && <p role="alert" className="error">{t('Planned context belongs to another Run.')}</p>}
      {planSeasonMismatch && <p role="alert" className="error">{t('Run season and ordered plan disagree. Planned links are unavailable.')}</p>}
      {eventsMismatch && <p role="alert" className="error">{t('Event context belongs to another Run.')}</p>}
      {siblingMismatch && <p role="alert" className="error">{t('Snapshot sibling history belongs to another Run.')}</p>}
      {runQuery.error && <p role="alert" className="error">{t('Failed to load planned season context')}: {formatApiError(runQuery.error)}</p>}
      {eventsQuery.error && <p role="alert" className="error">{t('Failed to load persisted events context')}: {formatApiError(eventsQuery.error)}</p>}
      <SectionCard title={t('Snapshot timeline')}>
        {snapshotMismatch && <p role="alert" className="error">{t('Snapshot history belongs to another Run; its records are hidden.')}</p>}
        <button type="button" onClick={() => void query.refetch()}>{t('Refresh read-only data')}</button>
        {query.isLoading && <p className="status">{t('Loading snapshots history...')}</p>}
        {isApiNotFound(query.error)
          ? <EmptyState message={t('Snapshot history could not be found for this Run.')} />
          : query.error && <p role="alert" className="error">{t('Failed to load snapshots history')}: {formatApiError(query.error)}</p>}
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
              if (ambiguousPersistedEventIds.has(sourceEventId)) return t('Source event ID is reused in persisted history. Source links and week context are unavailable.')
              const plan = plannedForSource(sourceEventId)
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
              setSearchParams((current) => {
                const next = new URLSearchParams(current)
                next.set('selectedSequence', String(snapshot.snapshot_sequence))
                next.set('selectedMode', mode)
                next.set('selectedRun', runId)
                return next
              })
            }}
            ariaLabel={t(mode === 'ranking' ? 'Ranking snapshots list' : 'Race snapshots list')}
          />
        )}
      </SectionCard>

      <SectionCard title={t('Selected snapshot detail')}>
        {selected ? (
          <SnapshotDetail
            snapshot={selected}
            mode={mode}
            runId={runId}
            plannedContext={selected.source_event_id ? plannedForSource(selected.source_event_id) : undefined}
            persistedEvent={selected.source_event_id && !selectedSourceAmbiguous ? persistedEventsById.get(selected.source_event_id) : undefined}
            siblingMode={siblingMode}
            siblingMatchCount={siblingMatchCount}
            currentRunSeason={planUnavailable ? null : runQuery.data?.run.season ?? null}
            planUnavailable={planUnavailable}
            eventsUnavailable={eventsUnavailable || selectedSourceAmbiguous}
            sourceIdentityAmbiguous={selectedSourceAmbiguous}
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
  siblingMatchCount,
  currentRunSeason,
  planUnavailable,
  eventsUnavailable,
  sourceIdentityAmbiguous
}: {
  snapshot: RankingSnapshot | RaceSnapshot
  mode: Mode
  runId: string
  plannedContext?: { season: number; week: number; category: string; tour: string; templateId: string; planPosition: number }
  persistedEvent?: { season: number | null; eventSequence: number; week: number | null }
  siblingMode: Mode
  siblingMatchCount: number | null
  currentRunSeason: number | null
  planUnavailable: boolean
  eventsUnavailable: boolean
  sourceIdentityAmbiguous: boolean
}): JSX.Element {
  const t = useHistoryText()
  const sourceEventId = snapshot.source_event_id
  const sourceWeek = persistedEvent?.week ?? plannedContext?.week
  const sourceEvidenceSeason = persistedEvent?.season ?? plannedContext?.season ?? null
  const canNavigateWeek = currentRunSeason != null && sourceEvidenceSeason === currentRunSeason
  const missingPlan = planUnavailable || sourceIdentityAmbiguous ? t('Unavailable') : t('No ordered-plan match')

  return (
    <>
      {sourceIdentityAmbiguous && <p role="alert" className="error">{t('Source event ID is reused in persisted history. Source links and week context are unavailable.')}</p>}
      <MetadataList
        items={[
          { label: t('Sequence'), value: snapshot.snapshot_sequence },
          { label: t('Kind'), value: snapshot.snapshot_kind },
          { label: t('Mode'), value: mode },
          { label: t('Source event ID'), value: sourceEventId ?? '—' },
          { label: t('Week context'), value: sourceWeek != null ? `W${sourceWeek}` : planUnavailable || eventsUnavailable ? t('Unavailable') : t('No week context') },
          { label: t('Planned category'), value: plannedContext?.category ?? missingPlan },
          { label: t('Planned tour'), value: plannedContext?.tour ?? missingPlan },
          { label: t('Planned template'), value: plannedContext?.templateId ?? missingPlan },
          { label: t('Plan position'), value: plannedContext?.planPosition ?? missingPlan },
          { label: t('Persisted source event'), value: persistedEvent ? `${t('Found')} (${t('Sequence').toLowerCase()} ${persistedEvent.eventSequence})` : eventsUnavailable ? t('Unavailable') : t('Not found') }
        ]}
      />
      <SummaryPills
        items={[
          { label: t('Source event context'), value: sourceEventId ? t('Present') : t(MISSING_SOURCE_EVENT_ID_FALLBACK) },
          { label: `${t(siblingMode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots')} (${t('Source event')})`, value: siblingMatchCount === null ? t('Unavailable') : siblingMatchCount > 0 ? siblingMatchCount : t('No snapshot result matching this source event was returned.') }
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
                eventsUnavailable ? t('Unavailable') : t('Source persisted event detail unavailable.')
              )
          },
          {
            label: t('Source planned event'),
            value: sourceEventId && plannedContext ? (
              <Link to={`/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(sourceEventId)}`}>{t('Open planned-event detail page')}</Link>
            ) : (
              planUnavailable || sourceIdentityAmbiguous ? t('Unavailable') : t('No ordered-plan match for source_event_id.')
            )
          },
          {
            label: t('Source week detail'),
            value:
              sourceWeek != null && canNavigateWeek ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${sourceWeek}`}>{t('Open week detail page')} (W{sourceWeek})</Link>
              ) : (
                sourceWeek == null ? t('No source week context available.') : !canNavigateWeek ? t('Current-season week link unavailable for this historic event.') : t('No source week context available.')
              )
          },
          { label: t('Season calendar'), value: <Link to={`/runs/${encodeURIComponent(runId)}/calendar`}>{t('Open season calendar browser')}</Link> },
          {
            label: t(siblingMode === 'ranking' ? 'Ranking snapshots' : 'Race snapshots'),
            value:
              sourceEventId && siblingMatchCount !== null && siblingMatchCount > 0 ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/${siblingMode}`}>{t(siblingMode === 'ranking' ? 'Open ranking snapshot history' : 'Open race snapshot history')}</Link>
              ) : (
                siblingMatchCount === null ? t('Unavailable') : t('No snapshots share this source_event_id.')
              )
          }
        ]}
      />

      <JsonPayloadBlock title={t('Snapshot payload')} emptyText={t('No snapshot payload is available for this item.')} payload={snapshot.payload} />
    </>
  )
}
