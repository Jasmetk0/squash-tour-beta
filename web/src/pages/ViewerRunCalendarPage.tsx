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
  const parsed = Number.parseInt(value, 10)
  return Number.isInteger(parsed) && parsed >= 1 && parsed <= 61 ? parsed : null
}

function calendarSeasonStart(value: string | number): number | null {
  const first = String(value).split('/', 1)[0]
  const parsed = Number.parseInt(first, 10)
  return Number.isNaN(parsed) ? null : parsed
}

function flattenCalendarEvents(seasons: Array<{ events: ViewerCalendarEvent[] }> | undefined): ViewerCalendarEvent[] {
  return (seasons ?? []).flatMap((season) => season.events)
}

export function ViewerRunCalendarPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const resultByEventId = useMemo(
    () => new Map((historyQuery.data?.tournaments ?? []).map((item) => [item.event_id, item])),
    [historyQuery.data?.tournaments]
  )

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
          { label: 'Viewer Branch', value: calendarQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Saved seasons', value: calendarQuery.data?.season_count ?? 0 },
          { label: 'Saved events', value: calendarQuery.data?.event_count ?? 0 },
          { label: 'Published results', value: historyQuery.data?.published_result_count ?? 0 }
        ]}
      />

      <SectionCard title="Saved Calendar overview">
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
        {calendarQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Saved seasons', value: calendarQuery.data.season_count },
                { label: 'Calendar events', value: calendarQuery.data.event_count },
                { label: 'Published results', value: historyQuery.data?.published_result_count ?? 0 }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Product Run', value: calendarQuery.data.product_run_id },
                { label: 'Viewer Branch', value: calendarQuery.data.viewer_branch_id },
                { label: 'Calendar authority', value: 'Saved Run Package state' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Canonical season timeline">
        {calendarQuery.data?.event_count === 0 ? (
          <EmptyState message="The Saved Calendar Package contains no events." />
        ) : null}
        {calendarQuery.data?.seasons.map((season) => (
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
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })

  const event = useMemo(
    () => flattenCalendarEvents(calendarQuery.data?.seasons).find((item) => item.event_id === eventId) ?? null,
    [calendarQuery.data?.seasons, eventId]
  )
  const result = historyQuery.data?.tournaments.find((item) => item.event_id === eventId) ?? null

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
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar event…</p> : null}
        {calendarQuery.error && !isApiNotFound(calendarQuery.error) ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {isApiNotFound(calendarQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}
        {eventId && calendarQuery.data && !event ? (
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
  const { productRunId: runId, currentSeason } = useViewerProductRunRouteContext()
  const parsedWeek = parseViewerWeekParam(week)
  const hasValidWeek = parsedWeek != null
  const enabled = Boolean(runId && hasValidWeek)

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled,
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled,
    retry: false
  })
  const rankingHistoryQuery = useQuery({
    queryKey: ['viewer-official-ranking-history', runId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    enabled,
    retry: false
  })
  const finalsRaceQuery = useQuery({
    queryKey: ['viewer-week-finals-race-history', runId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled,
    retry: false
  })

  const weekEvents = useMemo(
    () =>
      flattenCalendarEvents(calendarQuery.data?.seasons).filter((event) => {
        if (event.season_week !== parsedWeek) return false
        if (currentSeason == null) return true
        const start = calendarSeasonStart(event.season)
        return start == null || start === currentSeason
      }),
    [calendarQuery.data?.seasons, currentSeason, parsedWeek]
  )
  const weekEventIds = useMemo(() => new Set(weekEvents.map((event) => event.event_id)), [weekEvents])
  const completedResults = useMemo(
    () => (historyQuery.data?.tournaments ?? []).filter((item) => weekEventIds.has(item.event_id) && item.result_published),
    [historyQuery.data?.tournaments, weekEventIds]
  )
  const rankingPublications = useMemo(
    () =>
      (rankingHistoryQuery.data?.publications ?? []).filter((publication) => {
        if (publication.week !== parsedWeek) return false
        return currentSeason == null || 2000 + publication.season_index === currentSeason
      }),
    [rankingHistoryQuery.data?.publications, currentSeason, parsedWeek]
  )
  const finalsRacePublications = useMemo(
    () =>
      (finalsRaceQuery.data?.publications ?? []).filter((publication) => {
        if (publication.cutoff_week !== parsedWeek) return false
        return currentSeason == null || 2000 + publication.cutoff_season_index === currentSeason
      }),
    [finalsRaceQuery.data?.publications, currentSeason, parsedWeek]
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
        {!hasValidWeek ? <EmptyState message="Week must be a whole number from 1 to 61 in the URL." /> : null}
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar…</p> : null}
        {calendarQuery.error && !isApiNotFound(calendarQuery.error) ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {isApiNotFound(calendarQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {hasValidWeek && calendarQuery.data && !hasAnyData ? (
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
        {hasValidWeek && calendarQuery.data && weekEvents.length === 0 ? (
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
        {finalsRaceQuery.error ? <p className="error">Failed to load Finals Race publications: {formatApiError(raceQuery.error)}</p> : null}
        {!historyQuery.error && !rankingHistoryQuery.error && !raceQuery.error && hasValidWeek ? (
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
