import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { getFinalsSummary, getRun, getRunActivity, getRunStatusSummary, listEvents, listRaceSnapshots, listRankingSnapshots } from '../../api/client'
import type { EventRecord, RaceSnapshot, RankingSnapshot, RunActivityItem, SeasonStateResponse } from '../../api/types'
import { ViewerActiveRunLinks, ViewerEmptyState, ViewerLandingGrid, ViewerMetadataList, ViewerSectionCard } from '../../components/viewer/ViewerLandingComponents'
import { ViewerRunSelector } from '../../components/ViewerRunSelector'
import { useViewerContext } from '../../viewer/ViewerContext'
import { useActiveViewerRunId } from '../../viewer/useActiveViewerRunId'
import { buildActiveRunHubLinks } from '../../viewer/viewerHubLinks'
import {
  viewerHistoryPath,
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRaceSnapshotPath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../../viewer/viewerRoutes'

type HomepageEventSummary = {
  eventId: string
  week: number | null
  category: string | null
  tour: string | null
  templateId: string | null
  status: 'Next scheduled event' | 'Most recent completed event'
}

type OrderedSeasonEvent = SeasonStateResponse['season_state']['ordered_events'][number]

function buildPlannedEventMap(runData: SeasonStateResponse | undefined): Map<string, OrderedSeasonEvent> {
  const map = new Map<string, OrderedSeasonEvent>()
  ;(runData?.season_state.ordered_events ?? []).forEach((event) => {
    map.set(event.event_id, event)
  })
  return map
}

function renderLinkedEventId(runId: string, eventId: string | null | undefined): ReactNode {
  if (!eventId) return '—'
  return <Link to={viewerPlannedEventPath(runId, eventId)}>{eventId}</Link>
}

function renderLinkedWeek(runId: string, week: number | string | null | undefined): ReactNode {
  if (week == null || week === '') return '—'
  return <Link to={viewerWeekDetailPath(runId, week)}>W{week}</Link>
}

function selectHomepageEvent(runData: SeasonStateResponse | undefined, events: EventRecord[]): HomepageEventSummary | null {
  const orderedEvents = runData?.season_state.ordered_events ?? []
  const nextIndex = runData?.season_state.next_event_index ?? runData?.run.next_event_index ?? null
  const plannedMap = buildPlannedEventMap(runData)

  if (nextIndex != null && orderedEvents[nextIndex]) {
    const event = orderedEvents[nextIndex]
    return {
      eventId: event.event_id,
      week: event.week,
      category: event.category,
      tour: event.tour,
      templateId: event.template_id,
      status: 'Next scheduled event'
    }
  }

  const mostRecentCompleted = [...events].sort((a, b) => b.event_sequence - a.event_sequence)[0]
  if (mostRecentCompleted) {
    const planned = plannedMap.get(mostRecentCompleted.event_id)
    return {
      eventId: mostRecentCompleted.event_id,
      week: mostRecentCompleted.week ?? planned?.week ?? null,
      category: planned?.category ?? null,
      tour: planned?.tour ?? null,
      templateId: mostRecentCompleted.template_id ?? planned?.template_id ?? null,
      status: 'Most recent completed event'
    }
  }

  return null
}

function latestSnapshot<T extends RankingSnapshot | RaceSnapshot>(snapshots: T[]): T | null {
  return [...snapshots].sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0] ?? null
}

function formatSource(sourceType: string | undefined, parentRunId: string | null | undefined): string {
  if (!sourceType) return 'Not available yet'
  return parentRunId ? `${sourceType} from ${parentRunId}` : sourceType
}

type ActivityLinkContext = {
  plannedEvents: Map<string, OrderedSeasonEvent>
  persistedEvents: Map<string, EventRecord>
}

function renderActivityItem(item: RunActivityItem, runId: string, context: ActivityLinkContext): ReactNode {
  const eventId = item.event_id
  const plannedEvent = eventId ? context.plannedEvents.get(eventId) : null
  const persistedEvent = eventId ? context.persistedEvents.get(eventId) : null
  const resolvedWeek = plannedEvent?.week ?? persistedEvent?.week ?? null

  const parts: ReactNode[] = [item.label]
  if (item.season != null) parts.push(`Season ${item.season}`)
  if (resolvedWeek != null) {
    parts.push(renderLinkedWeek(runId, resolvedWeek))
  } else if (item.week != null) {
    parts.push(`W${item.week}`)
  }
  if (eventId) {
    parts.push(plannedEvent ? renderLinkedEventId(runId, eventId) : eventId)
    if (persistedEvent) {
      parts.push(<Link to={viewerTournamentDetailPath(runId, eventId)}>Tournament detail {eventId}</Link>)
    }
  }
  if (item.snapshot_sequence != null) {
    if (item.kind === 'ranking_snapshot') {
      parts.push(<Link to={viewerRankingSnapshotPath(runId, item.snapshot_sequence)}>Ranking snapshot #{item.snapshot_sequence}</Link>)
    } else if (item.kind === 'race_snapshot') {
      parts.push(<Link to={viewerRaceSnapshotPath(runId, item.snapshot_sequence)}>Race snapshot #{item.snapshot_sequence}</Link>)
    }
  }

  return parts.map((part, index) => (
    <span key={index}>
      {index > 0 ? ' · ' : null}
      {part}
    </span>
  ))
}

export function ViewerHomePage(): JSX.Element {
  const context = useViewerContext()
  const activeRunId = useActiveViewerRunId()
  const queryEnabled = Boolean(activeRunId)

  const runQuery = useQuery({ queryKey: ['viewer-home-run', activeRunId], queryFn: () => getRun(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const statusQuery = useQuery({ queryKey: ['viewer-home-run-status', activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-home-events', activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-home-ranking-snapshots', activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-home-race-snapshots', activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const activityQuery = useQuery({ queryKey: ['viewer-home-activity', activeRunId], queryFn: () => getRunActivity(activeRunId ?? ''), enabled: queryEnabled, retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-home-finals', activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: queryEnabled, retry: false })

  const activeQueries = [runQuery, statusQuery, eventsQuery, rankingSnapshotsQuery, raceSnapshotsQuery, activityQuery, finalsQuery]
  const isActiveSummaryLoading = queryEnabled && activeQueries.some((query) => query.isLoading)
  const isActiveSummaryUnavailable = queryEnabled && activeQueries.some((query) => query.isError)

  const featuredEvent = useMemo(() => selectHomepageEvent(runQuery.data, eventsQuery.data?.events ?? []), [eventsQuery.data?.events, runQuery.data])
  const nearbyEvents = useMemo(() => {
    const orderedEvents = runQuery.data?.season_state.ordered_events ?? []
    if (!featuredEvent) return orderedEvents.slice(0, 3)
    return orderedEvents.filter((event) => event.event_id !== featuredEvent.eventId && event.week === featuredEvent.week).slice(0, 3)
  }, [featuredEvent, runQuery.data?.season_state.ordered_events])
  const latestRankingSnapshot = latestSnapshot(rankingSnapshotsQuery.data?.snapshots ?? [])
  const latestRaceSnapshot = latestSnapshot(raceSnapshotsQuery.data?.snapshots ?? [])
  const activityItems = activityQuery.data?.items ?? []
  const latestActivityItem = activityItems[0] ?? null
  const activityLinkContext = useMemo<ActivityLinkContext>(() => ({
    plannedEvents: buildPlannedEventMap(runQuery.data),
    persistedEvents: new Map((eventsQuery.data?.events ?? []).map((event) => [event.event_id, event]))
  }), [eventsQuery.data?.events, runQuery.data])

  return (
    <section className="panel viewer-home viewer-home--msa">
      <div className="page-intro viewer-home__hero">
        <span className="eyebrow">MSA Homepage</span>
        <h2>MSA Squash — Season {context.selectedSeason} · W{context.selectedWeek}</h2>
        <p className="subtitle">
          A premium, public-style squash tour homepage for the selected Viewer context. These cards are read-only and show small real summaries only when existing safe run APIs provide them.
        </p>
      </div>
      <ViewerRunSelector compact />
      <p className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerRunsPath()}>Open run browser</Link>
      </p>
      <section className="viewer-active-run-panel" aria-label="Active Viewer run status">
        {activeRunId ? (
          <>
            <div>
              <span className="eyebrow">Active Viewer run</span>
              <h3>Active run data is available</h3>
              {isActiveSummaryLoading ? <p className="status">Loading current tour summary from the active Viewer run…</p> : null}
              {isActiveSummaryUnavailable ? <ViewerEmptyState>Active run summary is temporarily unavailable. Try opening the run pages below for more detail.</ViewerEmptyState> : null}
              {!isActiveSummaryLoading && !isActiveSummaryUnavailable ? (
                <>
                  <p className="status">Using Viewer run <strong>{activeRunId}</strong> for read-only run pages.</p>
                  <ViewerMetadataList
                    className="viewer-home-summary-list"
                    ariaLabel="Active run summary fields"
                    items={[
                      { label: 'Run id', value: statusQuery.data?.run_id ?? runQuery.data?.run.run_id ?? activeRunId },
                      { label: 'Season', value: statusQuery.data?.season ?? runQuery.data?.run.season ?? 'Not available yet' },
                      { label: 'Seed', value: statusQuery.data?.seed ?? runQuery.data?.run.seed ?? 'Not available yet' },
                      { label: 'Progress', value: statusQuery.data ? `${statusQuery.data.progress.completed_event_count}/${statusQuery.data.progress.total_events} events complete` : `${runQuery.data?.run.completed_event_ids.length ?? 0}/${runQuery.data?.run.total_events ?? 0} events complete` },
                      { label: 'Next event index', value: statusQuery.data?.progress.next_event_index ?? runQuery.data?.run.next_event_index ?? 'Not available yet' },
                      { label: 'Finals', value: statusQuery.data?.finals.result_available || finalsQuery.data?.result ? 'Result available' : statusQuery.data?.finals.qualification_available || finalsQuery.data?.qualification ? 'Qualification available' : 'Not available yet' },
                      { label: 'Lineage/source', value: formatSource(statusQuery.data?.source?.source_type, statusQuery.data?.source?.parent_run_id) }
                    ]}
                  />
                </>
              ) : null}
            </div>
            <ViewerActiveRunLinks
              layout="grid"
              links={buildActiveRunHubLinks(activeRunId)}
            />
          </>
        ) : (
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        )}
      </section>
      <ViewerLandingGrid>
        <ViewerSectionCard kicker="Featured Tournament Hero" title="Featured Tournament Hero" variant="hero">
          {activeRunId && featuredEvent ? (
            <>
              <p>{featuredEvent.status}: <strong>{renderLinkedEventId(activeRunId, featuredEvent.eventId)}</strong></p>
              <p className="status">{featuredEvent.category ?? 'Category unavailable'} · {featuredEvent.tour ?? 'Tour unavailable'} · {featuredEvent.week != null ? renderLinkedWeek(activeRunId, featuredEvent.week) : 'Week unavailable'} · Template {featuredEvent.templateId ?? 'unavailable'}</p>
              <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(activeRunId)}>Open active run schedule</Link>
            </>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only schedule" title="Other Tournaments This Week">
          {activeRunId && nearbyEvents.length ? (
            <ul>
              {nearbyEvents.map((event) => (
                <li key={event.event_id}>{renderLinkedEventId(activeRunId, event.event_id)} · {event.category} · {renderLinkedWeek(activeRunId, event.week)}</li>
              ))}
            </ul>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only rankings" title="Top 10 Rankings">
          {activeRunId && latestRankingSnapshot ? (
            <p>Latest ranking snapshot <Link to={viewerRankingSnapshotPath(activeRunId, latestRankingSnapshot.snapshot_sequence)}>#{latestRankingSnapshot.snapshot_sequence}</Link> from {latestRankingSnapshot.source_event_id ?? 'run history'} · {rankingSnapshotsQuery.data?.snapshots.length ?? 0} snapshots stored.</p>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerRankingsPath(activeRunId)}>Open active run rankings</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only race" title="Race to Finals">
          {activeRunId && latestRaceSnapshot ? (
            <p>Latest race snapshot <Link to={viewerRaceSnapshotPath(activeRunId, latestRaceSnapshot.snapshot_sequence)}>#{latestRaceSnapshot.snapshot_sequence}</Link> from {latestRaceSnapshot.source_event_id ?? 'run history'} · {raceSnapshotsQuery.data?.snapshots.length ?? 0} snapshots stored.</p>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerRacePath(activeRunId)}>Open active run race</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only matches" title="Featured Matches">
          <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerTournamentsPath(activeRunId)}>Open active run tournaments</Link> : null}
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only analytics" title="Predictions &amp; Upset Watch">
          <ViewerEmptyState>This preview is not connected for this data shape yet.</ViewerEmptyState>
        </ViewerSectionCard>

        <ViewerSectionCard kicker="Read-only storylines" title="Storylines">
          {activeRunId && latestActivityItem ? (
            <p>{activityItems.length} activity items · Latest: {renderActivityItem(latestActivityItem, activeRunId, activityLinkContext)}</p>
          ) : (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          )}
          {activeRunId ? <Link className="viewer-active-run-link" to={viewerHistoryPath(activeRunId)}>Open active run history</Link> : null}
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </section>
  )
}
