import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getViewerCompletedTournaments, getViewerRunCalendar, listViewerOfficialRankingHistory } from '../api/client'
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
import { formatApiError } from '../utils/apiErrors'
import {
  buildWeekContextLinks,
  parseViewerWeekParam
} from './viewer/tour/viewerWeekDetailDisplay'
import {
  viewerPlannedEventPath,
  viewerRankingSnapshotPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

function isScalar(value: unknown): value is string | number {
  return typeof value === 'string' || typeof value === 'number'
}

function safeText(value: unknown, fallback: string | number = '—'): string | number {
  return isScalar(value) ? value : fallback
}

export function ViewerRunCalendarPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const completedQuery = useQuery({
    queryKey: ['viewer-completed-tournaments', runId],
    queryFn: () => getViewerCompletedTournaments(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const completedById = useMemo(
    () => new Map((completedQuery.data?.tournaments ?? []).map((item) => [item.event_id, item])),
    [completedQuery.data]
  )

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Calendar"
        runId={runId}
        subtitle="Read-only Saved-Revision Calendar Package for the selected Product Run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Saved seasons', value: calendarQuery.data?.season_count ?? 0 },
          { label: 'Saved calendar events', value: calendarQuery.data?.event_count ?? 0 },
          { label: 'Canonical completed results', value: completedQuery.data?.tournament_count ?? 0 }
        ]}
      />

      <SectionCard title="Season timeline overview">
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar…</p> : null}
        {calendarQuery.error ? (
          <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p>
        ) : null}
        {completedQuery.error ? (
          <p className="error">Failed to load canonical completed tournament history: {formatApiError(completedQuery.error)}</p>
        ) : null}
        {calendarQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Saved seasons', value: calendarQuery.data.season_count },
                { label: 'Calendar events', value: calendarQuery.data.event_count },
                { label: 'Completed result publications', value: completedQuery.data?.tournament_count ?? 0 }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Viewer Branch', value: calendarQuery.data.viewer_branch_id },
                { label: 'Calendar authority', value: 'Saved Run Package state' }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Season timeline">
        {calendarQuery.data?.event_count === 0 ? (
          <EmptyState message="The Saved Calendar Package contains no events." />
        ) : null}
        {calendarQuery.data?.seasons.map((season) => (
          <section key={String(season.season)}>
            <h3>{String(season.season)}</h3>
            <ol className="item-list" aria-label={`Viewer season calendar events ${String(season.season)}`}>
              {season.events.map((event, index) => {
                const canonicalResult = completedById.get(event.event_id)
                const status = canonicalResult
                  ? 'Completed · canonical result published'
                  : event.status.charAt(0).toUpperCase() + event.status.slice(1)

                return (
                  <li key={event.event_id}>
                    <strong>{event.event_id}</strong>
                    <MetadataList
                      items={[
                        { label: 'Status', value: status },
                        { label: 'Event ID', value: event.event_id },
                        { label: 'Event name', value: event.event_name || '—' },
                        { label: 'Season', value: event.season },
                        { label: 'Week', value: `W${event.season_week}` },
                        { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                        { label: 'Category', value: event.category || '—' },
                        { label: 'Template ID', value: event.template_id },
                        { label: 'Host', value: [event.host_city, event.host_country].filter(Boolean).join(', ') },
                        { label: 'Main / Q draw', value: `${event.main_draw_size} / ${event.qualification_draw_size}` },
                        { label: 'Seeds / Q spots / WC / BYE', value: `${event.seeds_count} / ${event.qualifier_spots} / ${event.wild_cards} / ${event.byes}` },
                        { label: 'Season position', value: `${index + 1} of ${season.events.length}` }
                      ]}
                    />
                    {canonicalResult ? (
                      <SummaryPills
                        items={[
                          { label: 'Champion', value: canonicalResult.champion_player_id },
                          { label: 'Finalist', value: canonicalResult.finalist_player_id },
                          { label: 'Matches', value: canonicalResult.match_count }
                        ]}
                      />
                    ) : null}
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

      {calendarQuery.data ? (
        <SectionCard title="Read-only data">
          <details>
            <summary>Show technical calendar data</summary>
            <p className="status">Read-only public Saved Calendar projection. Package/source fingerprints and Admin provenance are excluded by the API.</p>
            <JsonPayloadBlock title="Canonical Viewer Calendar" emptyText="No technical data is available." payload={calendarQuery.data} />
          </details>
        </SectionCard>
      ) : null}
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
  const completedQuery = useQuery({
    queryKey: ['viewer-completed-tournaments', runId],
    queryFn: () => getViewerCompletedTournaments(runId),
    enabled: Boolean(runId && eventId),
    retry: false
  })

  const calendarEvents = useMemo(
    () => (calendarQuery.data?.seasons ?? []).flatMap((season) => season.events),
    [calendarQuery.data]
  )
  const plannedEvent = useMemo(
    () => calendarEvents.find((event) => event.event_id === eventId) ?? null,
    [calendarEvents, eventId]
  )
  const completedResult = useMemo(
    () => completedQuery.data?.tournaments.find((item) => item.event_id === eventId) ?? null,
    [completedQuery.data, eventId]
  )
  const statusLabel = completedResult
    ? 'Completed · canonical result published'
    : plannedEvent
      ? plannedEvent.status.charAt(0).toUpperCase() + plannedEvent.status.slice(1)
      : null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Planned Event"
        runId={runId}
        subtitle="Read-only event from the selected Viewer Branch's Saved Calendar Package."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Season', value: plannedEvent?.season ?? '—' },
          { label: 'Week', value: plannedEvent ? `W${plannedEvent.season_week}` : '—' }
        ]}
      />

      <SectionCard title="Source context links">
        {!runId || !eventId ? <EmptyState message="No planned event route context was provided." /> : null}
        {runId && eventId ? (
          <ul className="item-list" aria-label="Planned event source links">
            <li><Link to={viewerSeasonCalendarPath(runId)}>Season calendar</Link></li>
            {plannedEvent ? <li><Link to={viewerWeekDetailPath(runId, plannedEvent.season_week)}>{`Week W${plannedEvent.season_week}`}</Link></li> : null}
            <li><Link to={viewerTournamentDetailPath(runId, eventId)}>Tournament detail</Link></li>
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard title="Planned event summary">
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar event…</p> : null}
        {calendarQuery.error ? <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p> : null}
        {completedQuery.error ? <p className="error">Failed to load canonical completed tournament history: {formatApiError(completedQuery.error)}</p> : null}
        {!eventId ? <EmptyState message="No planned event ID was provided in the URL." /> : null}
        {eventId && calendarQuery.data && !plannedEvent ? (
          <EmptyState message={`Event ${eventId} is not present in the Saved Calendar Package.`} />
        ) : null}
        {plannedEvent ? (
          <>
            <SummaryPills
              items={[
                { label: 'Status', value: statusLabel ?? 'Planned' },
                { label: 'Completed result', value: completedResult ? 'Published' : 'Not published' },
                { label: 'Main draw', value: plannedEvent.main_draw_size },
                { label: 'Qualification draw', value: plannedEvent.qualification_draw_size }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Active run id', value: runId || 'unknown' },
                { label: 'Event ID', value: plannedEvent.event_id },
                { label: 'Event name', value: plannedEvent.event_name || '—' },
                { label: 'Season', value: plannedEvent.season },
                { label: 'Week', value: `W${plannedEvent.season_week}` },
                { label: 'Tour', value: plannedEvent.tour_level?.replace(/_/g, ' ') ?? '—' },
                { label: 'Category', value: plannedEvent.category || '—' },
                { label: 'Template ID', value: plannedEvent.template_id },
                { label: 'Host', value: [plannedEvent.host_city, plannedEvent.host_country].filter(Boolean).join(', ') }
              ]}
            />
            <MetadataList
              items={[
                { label: 'Region', value: plannedEvent.region },
                { label: 'Duration', value: `${plannedEvent.duration_in_season_weeks} week(s)` },
                { label: 'Start / end', value: `W${plannedEvent.start_season_week} / W${plannedEvent.end_season_week}` },
                { label: 'Seeds', value: plannedEvent.seeds_count },
                { label: 'Qualifier spots', value: plannedEvent.qualifier_spots },
                { label: 'Wild Cards', value: plannedEvent.wild_cards },
                { label: 'BYEs', value: plannedEvent.byes },
                { label: 'Prestige', value: plannedEvent.prestige }
              ]}
            />
            {completedResult ? (
              <SummaryPills
                items={[
                  { label: 'Champion', value: completedResult.champion_player_id },
                  { label: 'Finalist', value: completedResult.finalist_player_id },
                  { label: 'Matches', value: completedResult.match_count }
                ]}
              />
            ) : null}
          </>
        ) : null}
      </SectionCard>

      {plannedEvent ? (
        <SectionCard title="Read-only data">
          <details>
            <summary>Show technical planned event data</summary>
            <p className="status">Read-only public Saved Calendar event. Package/source fingerprints and Admin provenance are excluded by the API.</p>
            <JsonPayloadBlock title="Canonical Saved Calendar event" emptyText="No technical data is available." payload={plannedEvent} />
          </details>
        </SectionCard>
      ) : null}
    </section>
  )
}

export function ViewerRunWeekPage(): JSX.Element {
  const { week = '' } = useParams()
  const {
    productRunId: runId,
    currentSeason
  } = useViewerProductRunRouteContext()
  const parsedWeek = parseViewerWeekParam(week)
  const hasValidWeek = parsedWeek != null
  const queriesEnabled = Boolean(runId && hasValidWeek)

  const calendarQuery = useQuery({
    queryKey: ['viewer-run-calendar', runId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled: queriesEnabled,
    retry: false
  })
  const completedQuery = useQuery({
    queryKey: ['viewer-completed-tournaments', runId],
    queryFn: () => getViewerCompletedTournaments(runId),
    enabled: queriesEnabled,
    retry: false
  })
  const rankingHistoryQuery = useQuery({
    queryKey: ['viewer-official-ranking-history', runId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    enabled: queriesEnabled,
    retry: false
  })
  const calendarEvents = useMemo(
    () => (calendarQuery.data?.seasons ?? []).flatMap((season) => season.events),
    [calendarQuery.data]
  )
  const weekEvents = useMemo(
    () => calendarEvents.filter((event) => {
      if (event.season_week !== parsedWeek) return false
      if (currentSeason == null) return true
      const seasonStart = Number.parseInt(String(event.season).split('/', 1)[0] ?? '', 10)
      return Number.isNaN(seasonStart) || seasonStart === currentSeason
    }),
    [calendarEvents, currentSeason, parsedWeek]
  )
  const completedWeekResults = useMemo(
    () => (completedQuery.data?.tournaments ?? []).filter((item) => {
      if (item.completed_week !== parsedWeek) return false
      return currentSeason == null || 2000 + item.completed_season_index === currentSeason
    }),
    [completedQuery.data, currentSeason, parsedWeek]
  )
  const completedById = useMemo(
    () => new Map((completedQuery.data?.tournaments ?? []).map((item) => [item.event_id, item])),
    [completedQuery.data]
  )
  const rankingPublications = useMemo(
    () => (rankingHistoryQuery.data?.publications ?? []).filter((publication) => {
      if (publication.week !== parsedWeek) return false
      return currentSeason == null || 2000 + publication.season_index === currentSeason
    }),
    [rankingHistoryQuery.data?.publications, currentSeason, parsedWeek]
  )
  const hasPublicationMatches = rankingPublications.length > 0
  const hasAnyWeekData = weekEvents.length > 0 || completedWeekResults.length > 0 || hasPublicationMatches
  const contextLinks = hasValidWeek
    ? buildWeekContextLinks({
        runId,
        week: parsedWeek,
        rankingPublicationOrdinals: rankingPublications.map((publication) => publication.week_ordinal)
      })
    : []

  return (
    <section className="panel">
      <RunScopedHeader title="Week Detail" runId={runId} subtitle="Read-only Saved Calendar schedule plus public tournament publications for the selected week." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Week', value: hasValidWeek ? `W${parsedWeek}` : '—' },
          { label: 'Current season', value: currentSeason ?? '—' },
          { label: 'Saved Calendar events', value: weekEvents.length },
          { label: 'Canonical completed results', value: completedWeekResults.length },
          { label: 'Ranking publications', value: rankingPublications.length }
        ]}
      />

      <SectionCard title="Week context">
        {!runId ? <EmptyState message="No run route context was provided." /> : null}
        {!hasValidWeek ? <EmptyState message="Week must be a positive whole number in the URL (for example /weeks/12)." /> : null}
        {calendarQuery.isLoading ? <p className="status">Loading canonical Saved Calendar…</p> : null}
        {calendarQuery.error ? <p className="error">Failed to load canonical Saved Calendar: {formatApiError(calendarQuery.error)}</p> : null}
        {completedQuery.error ? <p className="error">Failed to load canonical completed tournament history: {formatApiError(completedQuery.error)}</p> : null}
        {hasValidWeek && !calendarQuery.isLoading && !completedQuery.isLoading && !hasAnyWeekData ? (
          <EmptyState message="No Saved Calendar event or canonical publication is available for this week." />
        ) : null}
        {hasValidWeek ? (
          <CompactSummaryCard
            items={[
              { label: 'Run ID', value: runId || 'unknown' },
              { label: 'Week number', value: parsedWeek },
              { label: 'Current season', value: currentSeason ?? '—' },
              { label: 'Saved Calendar events this week', value: weekEvents.length },
              { label: 'Canonical completed tournaments this week', value: completedWeekResults.length },
              { label: 'Ranking publications this week', value: rankingPublications.length }
            ]}
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Source context links">
        {!hasValidWeek ? <EmptyState message="No valid week route context is available for source links." /> : null}
        {hasValidWeek ? (
          <ul className="item-list" aria-label="Week source links">
            {contextLinks.map((link) => (
              <li key={link.label}>
                <Link to={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        ) : null}
      </SectionCard>

      <SectionCard title="Saved Calendar events this week">
        {hasValidWeek && !calendarQuery.isLoading && weekEvents.length === 0 ? (
          <EmptyState message="No Saved Calendar tournaments are scheduled for this week." />
        ) : null}
        {weekEvents.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week Saved Calendar events">
            {weekEvents.map((event) => {
              const result = completedById.get(event.event_id)
              return (
                <li key={event.event_id}>
                  <strong>{event.event_id}</strong>
                  <MetadataList
                    items={[
                      { label: 'Event name', value: event.event_name || '—' },
                      { label: 'Season', value: event.season },
                      { label: 'Week', value: `W${event.season_week}` },
                      { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                      { label: 'Category', value: event.category || '—' },
                      { label: 'Template ID', value: event.template_id },
                      { label: 'Status', value: result ? 'Completed · canonical result published' : event.status },
                      { label: 'Host', value: [event.host_city, event.host_country].filter(Boolean).join(', ') }
                    ]}
                  />
                  {result ? (
                    <SummaryPills
                      items={[
                        { label: 'Champion', value: result.champion_player_id },
                        { label: 'Finalist', value: result.finalist_player_id },
                        { label: 'Matches', value: result.match_count }
                      ]}
                    />
                  ) : null}
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

      <SectionCard title="Canonical completed tournaments this week">
        {hasValidWeek && !completedQuery.isLoading && completedWeekResults.length === 0 ? (
          <EmptyState message="No canonical completed Tournament Result is published for this week." />
        ) : null}
        {completedWeekResults.length > 0 ? (
          <ol className="item-list" aria-label="Viewer week canonical completed tournaments">
            {completedWeekResults.map((result) => (
              <li key={result.event_id}>
                <strong>{result.event_id}</strong>
                <SummaryPills
                  items={[
                    { label: 'Champion', value: result.champion_player_id },
                    { label: 'Finalist', value: result.finalist_player_id },
                    { label: 'Players', value: result.player_count },
                    { label: 'Matches', value: result.match_count }
                  ]}
                />
                <p><Link to={viewerTournamentDetailPath(runId, result.event_id)}>Open tournament detail</Link></p>
              </li>
            ))}
          </ol>
        ) : null}
      </SectionCard>

      <SectionCard title="Publications this week">
        {rankingHistoryQuery.error ? <p className="error">Failed to load canonical ranking publications: {formatApiError(rankingHistoryQuery.error)}</p> : null}
        {!rankingHistoryQuery.error && hasValidWeek ? (
          <MetadataList
            items={[
              { label: 'Canonical Ranking publications count', value: rankingPublications.length },
              { label: 'Race publication status', value: 'Available only through the dedicated legacy Race compatibility route' }
            ]}
          />
        ) : null}
        {!rankingHistoryQuery.error && rankingPublications.length > 0 ? (
          <ul className="item-list" aria-label="Week ranking publications">
            {rankingPublications.map((publication) => (
              <li key={`ranking-${publication.week_ordinal}`}>
                <Link to={viewerRankingSnapshotPath(runId, publication.week_ordinal)}>Ranking publication #{publication.week_ordinal}</Link>{' '}
                <span className="status">Official · {publication.row_count} ranked players · {publication.policy_id}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {!rankingHistoryQuery.error && !hasPublicationMatches && weekEvents.length > 0 ? (
          <p className="status">No canonical Official Ranking publication is available for this week.</p>
        ) : null}
      </SectionCard>
    </section>
  )
}
