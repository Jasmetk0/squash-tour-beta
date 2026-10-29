import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  getViewerFinalsRace,
  getViewerRunCalendar,
  getViewerTournamentHistory,
  listViewerOfficialRankingHistory
} from '../api/client'
import type { ViewerCalendarEvent } from '../api/types'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

function parseViewerWeekParam(value: string): number | null {
  if (!/^\d+$/.test(value)) return null
  // Run calendars can have W52, W61, W80 or another fixed positive W.
  // Reject malformed/unsafe route coordinates without guessing the Run horizon.
  const parsed = Number(value)
  return Number.isSafeInteger(parsed) && parsed > 0 ? parsed : null
}

function calendarSeasonStart(value: string | number): number | null {
  const first = String(value).split('/', 1)[0]
  const parsed = Number.parseInt(first, 10)
  return Number.isNaN(parsed) ? null : parsed
}

function flattenCalendarEvents(seasons: Array<{ events: ViewerCalendarEvent[] }> | undefined): ViewerCalendarEvent[] {
  return (seasons ?? []).flatMap((season) => season.events)
}

type ViewerSourceIdentity = { product_run_id: string; viewer_branch_id: string }

function matchesViewerSource<T extends ViewerSourceIdentity>(
  data: T | null | undefined,
  runId: string,
  branchId: string
): data is T {
  return Boolean(data && runId && data.product_run_id === runId &&
    typeof data.viewer_branch_id === 'string' && data.viewer_branch_id.length > 0 &&
    (!branchId || data.viewer_branch_id === branchId))
}

export function ViewerRunCalendarPage(): JSX.Element {
  const { productRunId: runId, officialBranchId } = useViewerProductRunRouteContext()

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId, officialBranchId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId, officialBranchId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const calendar = matchesViewerSource(calendarQuery.data, runId, officialBranchId) ? calendarQuery.data : null
  const effectiveBranchId = officialBranchId || calendar?.viewer_branch_id || ''
  const history = effectiveBranchId && matchesViewerSource(historyQuery.data, runId, effectiveBranchId)
    ? historyQuery.data : null

  const resultByEventId = useMemo(() => {
    const calendarById = new Map(
      (calendar?.seasons ?? []).flatMap((season) => season.events).map((event) => [event.event_id, event])
    )
    return new Map((history?.tournaments ?? [])
      .filter((item) => {
        const event = calendarById.get(item.event_id)
        return event && String(event.season) === String(item.season) &&
          event.season_week === item.season_week
      })
      .map((item) => [item.event_id, item]))
  }, [calendar, history])

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Calendar"
        runId={runId}
        subtitle="Canonical Saved-Revision Calendar Package for the selected Viewer Branch."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: calendar?.viewer_branch_id ?? '—' },
          { label: 'Saved seasons', value: calendar?.season_count ?? 0 },
          { label: 'Saved events', value: calendar?.event_count ?? 0 },
          { label: 'Published results', value: history?.published_result_count ?? 0 }
        ]}
      />

      <SectionCard title="Saved Calendar overview">
        {calendarQuery.data && !calendar ? (
          <p className="error">Saved Calendar source does not match this Product Run / Viewer Branch.</p>
        ) : null}
        {historyQuery.data && !history ? (
          <p className="error">Tournament History source does not match the Saved Calendar Viewer Branch.</p>
        ) : null}
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar…</p> : null}
        {calendarQuery.error && !isApiNotFound(calendarQuery.error) ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {isApiNotFound(calendarQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {historyQuery.error && !isApiNotFound(historyQuery.error) ? (
          <p className="error">Failed to load canonical Tournament History: {formatApiError(historyQuery.error)}</p>
        ) : null}
        {calendar ? (
          <>
            <SummaryPills
              items={[
                { label: 'Saved seasons', value: calendar.season_count },
                { label: 'Calendar events', value: calendar.event_count },
                { label: 'Published results', value: history?.published_result_count ?? 0 }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Product Run', value: calendar.product_run_id },
                { label: 'Viewer Branch', value: calendar.viewer_branch_id },
                { label: 'Calendar authority', value: 'Saved Run Package state' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Canonical season timeline">
        {calendar?.event_count === 0 ? (
          <EmptyState message="The Saved Calendar Package contains no events." />
        ) : null}
        {calendar?.seasons.map((season) => (
          <section key={String(season.season)}>
            <h3>{String(season.season)}</h3>
            <ol className="item-list" aria-label={`Viewer season calendar events ${String(season.season)}`}>
              {season.events.map((event, index) => {
                const result = resultByEventId.get(event.event_id)
                return (
                  <li key={event.event_id}>
                    <strong>{event.event_name || event.event_id}</strong>
                    <MetadataList
                      items={[
                        { label: 'Event ID', value: event.event_id },
                        { label: 'Season', value: event.season },
                        { label: 'Week', value: `W${event.season_week}` },
                        { label: 'Status', value: result?.result_published ? 'Completed · result published' : event.status },
                        { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                        { label: 'Category', value: event.category || '—' },
                        { label: 'Template ID', value: event.template_id },
                        { label: 'Host', value: [event.host_city, event.host_country].filter(Boolean).join(', ') },
                        { label: 'Main / Q draw', value: `${event.main_draw_size} / ${event.qualification_draw_size}` },
                        { label: 'Seeds / Q spots / WC / BYE', value: `${event.seeds_count} / ${event.qualifier_spots} / ${event.wild_cards} / ${event.byes}` },
                        { label: 'Season position', value: `${index + 1} of ${season.events.length}` },
                        { label: 'Champion', value: result?.champion_player_id ?? '—' },
                        { label: 'Finalist', value: result?.finalist_player_id ?? '—' }
                      ]}
                    />
                    <p>
                      <Link to={viewerPlannedEventPath(runId, event.event_id)}>Open planned event</Link>
                      {' · '}
                      <Link to={viewerWeekDetailPath(runId, event.season_week)}>Open week detail</Link>
                      {' · '}
                      <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                    </p>
                  </li>
                )
              })}
            </ol>
          </section>
        ))}
      </SectionCard>
    </section>
  )
}

export function ViewerRunPlannedEventPage(): JSX.Element {
  const { eventId = '' } = useParams()
  const { productRunId: runId, officialBranchId } = useViewerProductRunRouteContext()

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId, officialBranchId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId, officialBranchId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })

  const calendar = matchesViewerSource(calendarQuery.data, runId, officialBranchId) ? calendarQuery.data : null
  const effectiveBranchId = officialBranchId || calendar?.viewer_branch_id || ''
  const history = effectiveBranchId && matchesViewerSource(historyQuery.data, runId, effectiveBranchId)
    ? historyQuery.data : null

  const event = useMemo(
    () => flattenCalendarEvents(calendar?.seasons).find((item) => item.event_id === eventId) ?? null,
    [calendar?.seasons, eventId]
  )
  const result = history?.tournaments.find((item) =>
    event && item.event_id === eventId &&
    String(item.season) === String(event.season) &&
    item.season_week === event.season_week
  ) ?? null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Planned Event"
        runId={runId}
        subtitle="Canonical event from the selected Viewer Branch's Saved Calendar Package."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Season', value: event?.season ?? '—' },
          { label: 'Week', value: event ? `W${event.season_week}` : '—' }
        ]}
      />

      <SectionCard title="Source context links">
        {!runId || !eventId ? <EmptyState message="No planned event route context was provided." /> : null}
        {runId && event ? (
          <ul className="item-list" aria-label="Planned event source links">
            <li><Link to={viewerSeasonCalendarPath(runId)}>Season calendar</Link></li>
            <li><Link to={viewerWeekDetailPath(runId, event.season_week)}>{`Week W${event.season_week}`}</Link></li>
            <li><Link to={viewerTournamentDetailPath(runId, event.event_id)}>Tournament detail</Link></li>
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned event summary">
        {calendarQuery.data && !calendar ? (
          <p className="error">Saved Calendar source does not match this Product Run / Viewer Branch.</p>
        ) : null}
        {historyQuery.data && !history ? (
          <p className="error">Tournament History source does not match the Saved Calendar Viewer Branch.</p>
        ) : null}
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar event…</p> : null}
        {calendarQuery.error && !isApiNotFound(calendarQuery.error) ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {isApiNotFound(calendarQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}
        {eventId && calendar && !event ? (
          <EmptyState message="This event is not present in the Saved Calendar Package." />
        ) : null}
        {event ? (
          <>
            <SummaryPills
              items={[
                { label: 'Status', value: result?.result_published ? 'Completed · result published' : event.status },
                { label: 'Main draw', value: event.main_draw_size },
                { label: 'Qualification draw', value: event.qualification_draw_size },
                { label: 'Seeds', value: event.seeds_count },
                { label: 'Qualifier spots', value: event.qualifier_spots },
                { label: 'Wild Cards', value: event.wild_cards },
                { label: 'BYEs', value: event.byes }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Event ID', value: event.event_id },
                { label: 'Event name', value: event.event_name || event.event_id },
                { label: 'Season', value: event.season },
                { label: 'Week', value: `W${event.season_week}` },
                { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                { label: 'Category', value: event.category || '—' },
                { label: 'Template ID', value: event.template_id },
                { label: 'Host', value: [event.host_city, event.host_country].filter(Boolean).join(', ') },
                { label: 'Region', value: event.region },
                { label: 'Duration', value: `${event.duration_in_season_weeks} week(s)` },
                { label: 'Start / end', value: `W${event.start_season_week} / W${event.end_season_week}` },
                { label: 'Prestige', value: event.prestige },
                { label: 'Champion', value: result?.champion_player_id ?? '—' },
                { label: 'Finalist', value: result?.finalist_player_id ?? '—' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunWeekPage(): JSX.Element {
  const { week = '' } = useParams()
  const { productRunId: runId, officialBranchId, currentSeason } = useViewerProductRunRouteContext()
  const parsedWeek = parseViewerWeekParam(week)
  const hasValidWeek = parsedWeek != null
  const enabled = Boolean(runId && hasValidWeek)

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId, officialBranchId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled,
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId, officialBranchId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled,
    retry: false
  })
  const rankingHistoryQuery = useQuery({
    queryKey: ['viewer-official-ranking-history', runId, officialBranchId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    enabled,
    retry: false
  })
  const finalsRaceQuery = useQuery({
    queryKey: ['viewer-week-finals-race-history', runId, officialBranchId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled,
    retry: false
  })

  const calendar = matchesViewerSource(calendarQuery.data, runId, officialBranchId) ? calendarQuery.data : null
  const effectiveBranchId = officialBranchId || calendar?.viewer_branch_id || ''
  const history = effectiveBranchId && matchesViewerSource(historyQuery.data, runId, effectiveBranchId)
    ? historyQuery.data : null
  const rankings = effectiveBranchId && matchesViewerSource(rankingHistoryQuery.data, runId, effectiveBranchId)
    ? rankingHistoryQuery.data : null
  const race = effectiveBranchId && matchesViewerSource(finalsRaceQuery.data, runId, effectiveBranchId)
    ? finalsRaceQuery.data : null

  const weekEvents = useMemo(
    () =>
      flattenCalendarEvents(calendar?.seasons).filter((event) => {
        if (event.season_week !== parsedWeek) return false
        if (currentSeason == null) return true
        const start = calendarSeasonStart(event.season)
        return start == null || start === currentSeason
      }),
    [calendar?.seasons, currentSeason, parsedWeek]
  )
  const weekEventIds = useMemo(() => new Set(weekEvents.map((event) => event.event_id)), [weekEvents])
  const completedResults = useMemo(
    () => (history?.tournaments ?? []).filter((item) =>
      weekEventIds.has(item.event_id) && item.result_published &&
      weekEvents.some((event) =>
        event.event_id === item.event_id &&
        String(event.season) === String(item.season) &&
        event.season_week === item.season_week
      )
    ),
    [history?.tournaments, weekEventIds, weekEvents]
  )
  const rankingPublications = useMemo(
    () =>
      (rankings?.publications ?? []).filter((publication) => {
        if (publication.week !== parsedWeek) return false
        return currentSeason == null || 2000 + publication.season_index === currentSeason
      }),
    [rankings?.publications, currentSeason, parsedWeek]
  )
  const finalsRacePublications = useMemo(
    () =>
      (race?.publications ?? []).filter((publication) => {
        if (publication.cutoff_week !== parsedWeek) return false
        return currentSeason == null || 2000 + publication.cutoff_season_index === currentSeason
      }),
    [race?.publications, currentSeason, parsedWeek]
  )
  const hasAnyData =
    weekEvents.length > 0 ||
    completedResults.length > 0 ||
    rankingPublications.length > 0 ||
    finalsRacePublications.length > 0

  return (
    <section className="panel">
      <RunScopedHeader
        title="Week Detail"
        runId={runId}
        subtitle="Canonical Saved Calendar schedule plus public ranking, result and Finals Race publications for the selected week."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Week', value: hasValidWeek ? `W${parsedWeek}` : '—' },
          { label: 'Current season', value: currentSeason ?? '—' },
          { label: 'Saved Calendar events', value: weekEvents.length },
          { label: 'Published results', value: completedResults.length },
          { label: 'Ranking publications', value: rankingPublications.length },
          { label: 'Finals Race publications', value: finalsRacePublications.length }
        ]}
      />

      <SectionCard title="Week context">
        {!hasValidWeek ? <EmptyState message="Week must be a positive safe integer in the URL." /> : null}
        {calendarQuery.data && !calendar ? (
          <p className="error">Saved Calendar source does not match this Product Run / Viewer Branch.</p>
        ) : null}
        {historyQuery.data && !history ? (
          <p className="error">Tournament History source does not match the Saved Calendar Viewer Branch.</p>
        ) : null}
        {rankingHistoryQuery.data && !rankings ? (
          <p className="error">Ranking History source does not match the Saved Calendar Viewer Branch.</p>
        ) : null}
        {finalsRaceQuery.data && !race ? (
          <p className="error">Finals Race source does not match the Saved Calendar Viewer Branch.</p>
        ) : null}
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar…</p> : null}
        {calendarQuery.error && !isApiNotFound(calendarQuery.error) ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {isApiNotFound(calendarQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {hasValidWeek && calendar && !hasAnyData ? (
          <EmptyState message="No Saved Calendar event or canonical publication is available for this week." />
        ) : null}
        {hasValidWeek ? (
          <CompactSummaryCard
            items={[
              { label: 'Run ID', value: runId || 'unknown' },
              { label: 'Week number', value: parsedWeek },
              { label: 'Current season', value: currentSeason ?? '—' },
              { label: 'Saved Calendar events', value: weekEvents.length },
              { label: 'Published tournament results', value: completedResults.length },
              { label: 'Official Ranking publications', value: rankingPublications.length },
              { label: 'Finals Race publications', value: finalsRacePublications.length }
            ]}
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Source context links">
        {hasValidWeek ? (
          <ul className="item-list" aria-label="Week source links">
            <li><Link to={viewerSeasonCalendarPath(runId)}>Season calendar</Link></li>
            <li><Link to={viewerRankingsPath(runId)}>Official Ranking history</Link></li>
            <li><Link to={viewerRacePath(runId)}>Finals Race publications</Link></li>
            {rankingPublications.map((publication) => (
              <li key={`ranking-${publication.week_ordinal}`}>
                <Link to={viewerRankingSnapshotPath(runId, publication.week_ordinal)}>
                  Ranking publication #{publication.week_ordinal}
                </Link>
              </li>
            ))}
            {finalsRacePublications.length ? (
              <li>
                <Link to={viewerRacePath(runId)}>
                  Open canonical Finals Race publication for this cutoff week
                </Link>
              </li>
            ) : null}
          </ul>
        ) : (
          <EmptyState message="No valid week route context is available for source links." />
        )}
      </SectionCard>

      <SectionCard title="Saved Calendar events this week">
        {hasValidWeek && calendar && weekEvents.length === 0 ? (
          <EmptyState message="No Saved Calendar events are scheduled for this week." />
        ) : null}
        {weekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week Saved Calendar events">
            {weekEvents.map((event) => {
              const result = completedResults.find((item) => item.event_id === event.event_id)
              return (
                <li key={event.event_id}>
                  <strong>{event.event_name || event.event_id}</strong>
                  <MetadataList
                    items={[
                      { label: 'Event ID', value: event.event_id },
                      { label: 'Season', value: event.season },
                      { label: 'Week', value: `W${event.season_week}` },
                      { label: 'Status', value: result ? 'Completed · result published' : event.status },
                      { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                      { label: 'Category', value: event.category || '—' },
                      { label: 'Template ID', value: event.template_id },
                      { label: 'Champion', value: result?.champion_player_id ?? '—' },
                      { label: 'Finalist', value: result?.finalist_player_id ?? '—' }
                    ]}
                  />
                  <p>
                    <Link to={viewerPlannedEventPath(runId, event.event_id)}>Open planned event</Link>
                    {' · '}
                    <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                  </p>
                </li>
              )
            })}
          </ol>
        ) : null}
      </SectionCard>

      <SectionCard title="Publications this week">
        {historyQuery.error ? <p className="error">Failed to load Tournament History: {formatApiError(historyQuery.error)}</p> : null}
        {rankingHistoryQuery.error ? <p className="error">Failed to load Official Ranking history: {formatApiError(rankingHistoryQuery.error)}</p> : null}
        {finalsRaceQuery.error ? <p className="error">Failed to load Finals Race publications: {formatApiError(finalsRaceQuery.error)}</p> : null}
        {!historyQuery.error && !rankingHistoryQuery.error && !finalsRaceQuery.error && hasValidWeek ? (
          <MetadataList
            items={[
              { label: 'Published tournament results', value: completedResults.length },
              { label: 'Official Ranking publications', value: rankingPublications.length },
              { label: 'Finals Race publications', value: finalsRacePublications.length }
            ]}
          />
        ) : null}
      </SectionCard>
    </section>
  )
}
