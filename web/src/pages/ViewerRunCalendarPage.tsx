import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import {
  getViewerFinalsRace,
  getViewerRunCalendar,
  getViewerTournamentHistory,
  listViewerOfficialRankingHistory
} from '../api/client'
import type { ViewerCalendarEvent, ViewerTournamentHistoryItem } from '../api/types'
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
  // A malformed season must not inherit a prefix from a different year.
  const text = String(value)
  if (!/^\d+(?:\/\d+)?$/.test(text)) return null
  const parsed = Number(text.split('/', 1)[0])
  return Number.isSafeInteger(parsed) ? parsed : null
}

function flattenCalendarEvents(seasons: Array<{ events: ViewerCalendarEvent[] }> | undefined): ViewerCalendarEvent[] {
  return (seasons ?? []).flatMap((season) => season.events)
}

function viewerWeekSeasonPath(runId: string, week: number, season: string | number): string {
  return `${viewerWeekDetailPath(runId, week)}?season=${encodeURIComponent(String(season))}`
}

function viewerPlannedEventContextPath(runId: string, event: ViewerCalendarEvent): string {
  return `${viewerPlannedEventPath(runId, event.event_id)}?season=${encodeURIComponent(String(event.season))}&week=${event.season_week}`
}

// Event IDs can be reused in different seasons. Never join by ID alone.
function calendarEventKey(event: Pick<ViewerCalendarEvent, 'event_id' | 'season' | 'season_week'>): string {
  return JSON.stringify([event.event_id, String(event.season), event.season_week])
}

function uniquelyAddressableEventIds(events: ViewerCalendarEvent[]): Set<string> {
  const counts = new Map<string, number>()
  for (const event of events) counts.set(event.event_id, (counts.get(event.event_id) ?? 0) + 1)
  return new Set([...counts].filter(([, count]) => count === 1).map(([id]) => id))
}

function canonicalPublishedResults(
  events: ViewerCalendarEvent[],
  history: ViewerTournamentHistoryItem[]
): Map<string, ViewerTournamentHistoryItem> {
  const calendarCounts = new Map<string, number>()
  for (const event of events) {
    const key = calendarEventKey(event)
    calendarCounts.set(key, (calendarCounts.get(key) ?? 0) + 1)
  }
  const seenHistoryKeys = new Set<string>()
  const published = new Map<string, ViewerTournamentHistoryItem>()
  for (const item of history) {
    if (!item.result_published) continue
    const key = calendarEventKey(item)
    if (seenHistoryKeys.has(key)) {
      published.delete(key) // Duplicate result rows are ambiguous, not an authority.
      continue
    }
    seenHistoryKeys.add(key)
    if (calendarCounts.get(key) === 1) published.set(key, item)
  }
  return published
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

  const addressableEventIds = useMemo(
    () => uniquelyAddressableEventIds(flattenCalendarEvents(calendar?.seasons)),
    [calendar?.seasons]
  )
  const resultByEventKey = useMemo(
    () => canonicalPublishedResults(
      flattenCalendarEvents(calendar?.seasons), history?.tournaments ?? []
    ),
    [calendar?.seasons, history?.tournaments]
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
                const result = resultByEventKey.get(calendarEventKey(event))
                return (
                  <li key={`${calendarEventKey(event)}-${index}`}>
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
                      <Link to={viewerPlannedEventContextPath(runId, event)}>Open planned event</Link>
                      {' · '}
                      <Link to={viewerWeekSeasonPath(runId, event.season_week, event.season)}>Open week detail</Link>
                      {' · '}
                      {addressableEventIds.has(event.event_id) ? (
                        <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                      ) : (
                        <span className="status">Tournament detail unavailable for a reused event ID.</span>
                      )}
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
  const [searchParams] = useSearchParams()
  const requestedSeason = searchParams.get('season')
  const requestedWeek = searchParams.get('week')
  const hasExplicitEventContext = requestedSeason !== null || requestedWeek !== null
  const validExplicitEventContext = !hasExplicitEventContext ||
    (requestedSeason !== null && requestedWeek !== null && parseViewerWeekParam(requestedWeek) !== null)
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

  const calendarEvents = useMemo(() => flattenCalendarEvents(calendar?.seasons), [calendar?.seasons])
  const eventCandidates = useMemo(
    () => calendarEvents.filter((item) => item.event_id === eventId),
    [calendarEvents, eventId]
  )
  const selectedCandidates = eventCandidates.filter((item) =>
    !hasExplicitEventContext ||
    (validExplicitEventContext &&
      String(item.season) === requestedSeason &&
      String(item.season_week) === requestedWeek)
  )
  const event = selectedCandidates.length === 1 ? selectedCandidates[0] : null
  const result = event ? canonicalPublishedResults(
    calendarEvents, history?.tournaments ?? []
  ).get(calendarEventKey(event)) : null
  const availableCandidates = eventCandidates.filter((candidate) =>
    eventCandidates.filter((other) => calendarEventKey(other) === calendarEventKey(candidate)).length === 1
  )

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
            <li><Link to={viewerWeekSeasonPath(runId, event.season_week, event.season)}>{`Week W${event.season_week}`}</Link></li>
            {eventCandidates.length === 1 ? (
              <li><Link to={viewerTournamentDetailPath(runId, event.event_id)}>Tournament detail</Link></li>
            ) : (
              <li className="status">Tournament detail unavailable for a reused event ID.</li>
            )}
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
        {eventId && calendar && eventCandidates.length === 0 ? (
          <EmptyState message="This event is not present in the Saved Calendar Package." />
        ) : null}
        {eventId && calendar && eventCandidates.length > 0 && !validExplicitEventContext ? (
          <EmptyState message="Planned Event links require both an exact season and a valid week when either is supplied." />
        ) : null}
        {eventId && calendar && hasExplicitEventContext && validExplicitEventContext && selectedCandidates.length === 0 ? (
          <EmptyState message="The requested event season/week does not match the Saved Calendar." />
        ) : null}
        {eventId && calendar && selectedCandidates.length > 1 ? (
          <>
            <EmptyState message="Multiple Saved Calendar events have this ID. Choose an exact season and week; indistinguishable duplicates cannot be opened." />
            {availableCandidates.length > 0 ? (
              <ul className="item-list" aria-label="Planned event occurrence choices">
                {availableCandidates.map((candidate) => (
                  <li key={calendarEventKey(candidate)}>
                    <Link to={viewerPlannedEventContextPath(runId, candidate)}>
                      {String(candidate.season)} · W{candidate.season_week} · {candidate.event_name || candidate.event_id}
                    </Link>
                  </li>
                ))}
              </ul>
            ) : null}
          </>
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
  const [searchParams] = useSearchParams()
  const requestedSeason = searchParams.get('season')
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

  // A week number is not unique across seasons. Explicit season links are
  // based on exact Saved Calendar labels, never on guessed publication years.
  const matchingWeekEvents = useMemo(
    () => flattenCalendarEvents(calendar?.seasons).filter((event) => event.season_week === parsedWeek),
    [calendar?.seasons, parsedWeek]
  )
  const availableWeekSeasons = useMemo(
    () => Array.from(new Set(matchingWeekEvents.map((event) => String(event.season)))),
    [matchingWeekEvents]
  )
  const calendarSeasonLabels = calendar?.seasons.map((item) => String(item.season)) ?? []
  const selectedSeason = requestedSeason !== null
    ? calendarSeasonLabels.includes(requestedSeason) ? requestedSeason : null
    : currentSeason !== null
      ? calendarSeasonLabels.find((label) => calendarSeasonStart(label) === currentSeason) ?? null
      : availableWeekSeasons.length === 1 ? availableWeekSeasons[0] : null
  const unresolvedSeason = requestedSeason === null && currentSeason === null &&
    availableWeekSeasons.length > 1
  const unknownRequestedSeason = requestedSeason !== null && selectedSeason === null && calendar !== null
  // Existing published ranking/Race sources use the legacy 2000-based season_index.
  // Do not attribute a publication to an unspecified or unverified calendar season.
  const selectedPublicationYear = requestedSeason !== null || currentSeason === null
    ? selectedSeason !== null ? calendarSeasonStart(selectedSeason) : null
    : currentSeason
  const weekEvents = useMemo(
    () => selectedSeason === null
      ? []
      : matchingWeekEvents.filter((event) => String(event.season) === selectedSeason),
    [matchingWeekEvents, selectedSeason]
  )
  const addressableEventIds = useMemo(
    () => uniquelyAddressableEventIds(flattenCalendarEvents(calendar?.seasons)),
    [calendar?.seasons]
  )
  const publishedByEventKey = useMemo(
    () => canonicalPublishedResults(
      flattenCalendarEvents(calendar?.seasons), history?.tournaments ?? []
    ),
    [calendar?.seasons, history?.tournaments]
  )
  const completedResults = weekEvents.flatMap((event) => {
    const result = publishedByEventKey.get(calendarEventKey(event))
    return result ? [result] : []
  })
  const rankingPublications = useMemo(
    () =>
      (rankings?.publications ?? []).filter((publication) => {
        if (publication.week !== parsedWeek) return false
        return selectedPublicationYear !== null && 2000 + publication.season_index === selectedPublicationYear
      }),
    [rankings?.publications, selectedPublicationYear, parsedWeek]
  )
  const finalsRacePublications = useMemo(
    () =>
      (race?.publications ?? []).filter((publication) => {
        if (!matchesViewerSource(publication, runId, effectiveBranchId)) return false
        if (publication.cutoff_week !== parsedWeek) return false
        return selectedPublicationYear !== null && 2000 + publication.cutoff_season_index === selectedPublicationYear
      }),
    [race?.publications, runId, effectiveBranchId, selectedPublicationYear, parsedWeek]
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
          { label: 'Displayed season', value: selectedSeason ?? '—' },
          { label: 'Saved Calendar events', value: weekEvents.length },
          { label: 'Published results', value: completedResults.length },
          { label: 'Ranking publications', value: rankingPublications.length },
          { label: 'Finals Race publications', value: finalsRacePublications.length }
        ]}
      />

      <SectionCard title="Week context">
        {!hasValidWeek ? <EmptyState message="Week must be a positive safe integer in the URL." /> : null}
        {unresolvedSeason ? (
          <EmptyState message="This week occurs in multiple Saved seasons. Choose an exact season below to avoid mixing historical results." />
        ) : null}
        {unknownRequestedSeason ? (
          <EmptyState message="The requested season is not present in this Viewer Branch's Saved Calendar." />
        ) : null}
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
        {hasValidWeek && calendar && !hasAnyData && !unresolvedSeason && !unknownRequestedSeason ? (
          <EmptyState message="No Saved Calendar event or canonical publication is available for this week." />
        ) : null}
        {hasValidWeek ? (
          <CompactSummaryCard
            items={[
              { label: 'Run ID', value: runId || 'unknown' },
              { label: 'Week number', value: parsedWeek },
              { label: 'Current season', value: currentSeason ?? '—' },
              { label: 'Displayed season', value: selectedSeason ?? '—' },
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
            {availableWeekSeasons.map((season) => (
              <li key={season}>
                <Link to={viewerWeekSeasonPath(runId, parsedWeek ?? 0, season)}>
                  Week W{parsedWeek} · season {season}
                </Link>
              </li>
            ))}
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
        {hasValidWeek && calendar && weekEvents.length === 0 && !unresolvedSeason && !unknownRequestedSeason ? (
          <EmptyState message="No Saved Calendar events are scheduled for this week." />
        ) : null}
        {weekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week Saved Calendar events">
            {weekEvents.map((event, index) => {
              const result = publishedByEventKey.get(calendarEventKey(event))
              return (
                <li key={`${calendarEventKey(event)}-${index}`}>
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
                    <Link to={viewerPlannedEventContextPath(runId, event)}>Open planned event</Link>
                    {' · '}
                    {addressableEventIds.has(event.event_id) ? (
                        <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                      ) : (
                        <span className="status">Tournament detail unavailable for a reused event ID.</span>
                      )}
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
