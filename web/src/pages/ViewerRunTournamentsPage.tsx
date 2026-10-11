import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getViewerFinalsRace, getViewerRunCalendar, getViewerTournamentDraw, getViewerTournamentEntryField, getViewerTournamentHistory, getViewerTournamentResult, getViewerTournamentWildCards, listViewerOfficialRankingHistory } from '../api/client'
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
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import {
  viewerPlannedEventPath,
  viewerRacePath,
  viewerRankingSnapshotPath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentsPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'

function drawSlotLabel(slot: {
  slot_index: number
  entrant_kind: string
  player_id: string | null
  placeholder_id: string | null
  seed_number: number | null
  entry_status: string | null
}): string {
  if (slot.entrant_kind === 'bye') return `#${slot.slot_index} · BYE`
  const identity = slot.player_id ?? slot.placeholder_id ?? 'Unknown'
  const seed = slot.seed_number == null ? '' : ` · seed ${slot.seed_number}`
  const status = slot.entry_status == null ? '' : ` · ${slot.entry_status.replace(/_/g, ' ')}`
  return `#${slot.slot_index} · ${identity}${seed}${status}`
}

function displayWeekDetailLink(runId: string, week: number | null): ReactNode {
  if (week == null) return '—'

  return <Link to={viewerWeekDetailPath(runId, week)}>{`W${week}`}</Link>
}


export function ViewerRunTournamentsPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()

  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-history', runId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const tournaments = historyQuery.data?.tournaments ?? []

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournaments"
        runId={runId}
        subtitle="Canonical multi-season tournament schedule and saved results for the selected Viewer Branch."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: historyQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Tournament count', value: historyQuery.data?.tournament_count ?? 0 },
          { label: 'Published results', value: historyQuery.data?.published_result_count ?? 0 }
        ]}
      />

      <SectionCard title="Canonical Tournament History">
        {historyQuery.isLoading ? <p className="status">Loading canonical tournament history...</p> : null}
        {historyQuery.error && !isApiNotFound(historyQuery.error) ? (
          <p className="error">Failed to load canonical tournament history: {formatApiError(historyQuery.error)}</p>
        ) : null}
        {isApiNotFound(historyQuery.error) ? (
          <EmptyState message="No saved Calendar Package is available for this Viewer Branch yet." />
        ) : null}
        {historyQuery.data && tournaments.length === 0 ? (
          <EmptyState message="No tournaments are present in the saved Calendar Packages." />
        ) : null}
        {tournaments.length > 0 ? (
          <ul className="item-list" aria-label="Canonical tournament history list">
            {tournaments.map((event) => (
              <li key={event.event_id} id={`event-${event.event_id}`}>
                <strong>{event.event_name || event.event_id}</strong>
                <MetadataList
                  items={[
                    { label: 'Event ID', value: event.event_id },
                    { label: 'Season', value: event.season },
                    { label: 'Week', value: displayWeekDetailLink(runId, event.season_week) },
                    { label: 'Template', value: event.template_id },
                    { label: 'Category', value: event.category || '—' },
                    { label: 'Tour', value: event.tour_level?.replace(/_/g, ' ') ?? '—' },
                    { label: 'Host', value: event.host_city ? `${event.host_city}, ${event.host_country}` : event.host_country },
                    { label: 'Main / Qualification', value: `${event.main_draw_size} / ${event.qualification_draw_size}` },
                    { label: 'Ranking status', value: event.ranking_status },
                    { label: 'Result publication', value: event.result_published ? 'Published' : 'Not published' },
                    { label: 'Champion', value: event.champion_player_id ?? '—' },
                    { label: 'Finalist', value: event.finalist_player_id ?? '—' }
                  ]}
                />
                <p>
                  <Link to={viewerTournamentDetailPath(runId, event.event_id)}>Open tournament detail</Link>
                </p>
              </li>
            ))}
          </ul>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunTournamentDetailPage(): JSX.Element {
  const { eventId = '' } = useParams()
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const enabled = Boolean(runId && eventId)

  const calendarQuery = useQuery({
    queryKey: ['viewer-tournament-detail-calendar', runId, eventId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled,
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['viewer-tournament-detail-history', runId, eventId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled,
    retry: false
  })
  const rankingHistoryQuery = useQuery({
    queryKey: ['viewer-tournament-detail-ranking-history', runId, eventId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    enabled,
    retry: false
  })
  const finalsRaceQuery = useQuery({
    queryKey: ['viewer-tournament-detail-finals-race', runId, eventId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled,
    retry: false
  })
  const entryFieldQuery = useQuery({
    queryKey: ['viewer-tournament-entry-field', runId, eventId],
    queryFn: () => getViewerTournamentEntryField(runId, eventId),
    enabled,
    retry: false
  })
  const drawQuery = useQuery({
    queryKey: ['viewer-tournament-draw', runId, eventId],
    queryFn: () => getViewerTournamentDraw(runId, eventId),
    enabled,
    retry: false
  })
  const wildCardsQuery = useQuery({
    queryKey: ['viewer-tournament-wild-cards', runId, eventId],
    queryFn: () => getViewerTournamentWildCards(runId, eventId),
    enabled,
    retry: false
  })
  const resultQuery = useQuery({
    queryKey: ['viewer-tournament-result', runId, eventId],
    queryFn: () => getViewerTournamentResult(runId, eventId),
    enabled,
    retry: false
  })

  const calendarEvent = useMemo(
    () => (calendarQuery.data?.seasons ?? []).flatMap((season) => season.events).find((event) => event.event_id === eventId) ?? null,
    [calendarQuery.data?.seasons, eventId]
  )
  const historyEvent = useMemo(
    () => (historyQuery.data?.tournaments ?? []).find((event) => event.event_id === eventId) ?? null,
    [historyQuery.data?.tournaments, eventId]
  )

  const week = calendarEvent?.season_week ?? historyEvent?.season_week ?? null
  const season = calendarEvent?.season ?? historyEvent?.season ?? null
  const seasonStart = season == null ? null : Number.parseInt(String(season).split('/')[0] ?? '', 10)
  const seasonIndex = Number.isFinite(seasonStart) ? Number(seasonStart) - 2000 : null
  const canonicalEventAvailable = Boolean(calendarEvent || historyEvent)

  const rankingPublications = useMemo(
    () =>
      (rankingHistoryQuery.data?.publications ?? []).filter((publication) => {
        if (week == null || publication.week !== week) return false
        return seasonIndex == null || publication.season_index === seasonIndex
      }),
    [rankingHistoryQuery.data?.publications, seasonIndex, week]
  )
  const finalsRacePublications = useMemo(
    () =>
      (finalsRaceQuery.data?.publications ?? []).filter((publication) => {
        if (week == null || publication.cutoff_week !== week) return false
        return seasonIndex == null || publication.cutoff_season_index === seasonIndex
      }),
    [finalsRaceQuery.data?.publications, seasonIndex, week]
  )

  const canonicalError =
    calendarQuery.error ??
    historyQuery.error ??
    rankingHistoryQuery.error ??
    finalsRaceQuery.error

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournament Detail"
        runId={runId}
        subtitle="Canonical Saved-Revision tournament detail for the selected Product Run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Product Run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Viewer Branch', value: calendarQuery.data?.viewer_branch_id ?? historyQuery.data?.viewer_branch_id ?? '—' },
          { label: 'Result availability', value: resultQuery.data || historyEvent?.result_published ? 'Published' : 'Not published' }
        ]}
      />

      <SectionCard title="Tournament links">
        <p>
          <Link to={viewerTournamentsPath(runId)}>Back to tournaments</Link>
          {calendarEvent ? (
            <>
              {' · '}
              <Link to={viewerPlannedEventPath(runId, eventId)}>Open calendar event</Link>
            </>
          ) : null}
          {week != null ? (
            <>
              {' · '}
              <Link to={viewerWeekDetailPath(runId, week)}>Open week detail</Link>
            </>
          ) : null}
          {' · '}
          <Link to={viewerSeasonCalendarPath(runId)}>Season calendar</Link>
        </p>
      </SectionCard>

      {!eventId ? (
        <SectionCard title="Tournament lookup">
          <EmptyState message="No event ID was provided in the URL." />
        </SectionCard>
      ) : null}

      {eventId ? (
        <>
          <SectionCard title="Tournament metadata">
            {calendarQuery.isLoading || historyQuery.isLoading ? <p className="status">Loading canonical tournament metadata…</p> : null}
            {canonicalError && !isApiNotFound(canonicalError) ? (
              <p className="error">Failed to load canonical tournament metadata: {formatApiError(canonicalError)}</p>
            ) : null}
            {!calendarQuery.isLoading && !historyQuery.isLoading && !canonicalError && !canonicalEventAvailable ? (
              <EmptyState message={`Event ${eventId} is not present in the canonical Saved Calendar or Tournament History.`} />
            ) : null}
            {canonicalEventAvailable ? (
              <>
                <SummaryPills
                  items={[
                    { label: 'Calendar status', value: calendarEvent?.status ?? 'No Saved Calendar match' },
                    { label: 'Result publication', value: resultQuery.data || historyEvent?.result_published ? 'Published' : 'Not published' },
                    { label: 'Ranking status', value: historyEvent?.ranking_status ?? '—' }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: 'Event ID', value: eventId },
                    { label: 'Event name', value: calendarEvent?.event_name ?? historyEvent?.event_name ?? eventId },
                    { label: 'Season', value: season ?? '—' },
                    { label: 'Week', value: displayWeekDetailLink(runId, week) },
                    { label: 'Tour', value: (calendarEvent?.tour_level ?? historyEvent?.tour_level)?.replace(/_/g, ' ') ?? '—' },
                    { label: 'Category', value: calendarEvent?.category ?? historyEvent?.category ?? '—' },
                    { label: 'Template', value: calendarEvent?.template_id ?? historyEvent?.template_id ?? '—' },
                    {
                      label: 'Host',
                      value:
                        calendarEvent
                          ? [calendarEvent.host_city, calendarEvent.host_country].filter(Boolean).join(', ')
                          : historyEvent
                            ? [historyEvent.host_city, historyEvent.host_country].filter(Boolean).join(', ')
                            : '—'
                    }
                  ]}
                />
                {calendarEvent ? (
                  <MetadataList
                    items={[
                      { label: 'Main draw', value: calendarEvent.main_draw_size },
                      { label: 'Qualification draw', value: calendarEvent.qualification_draw_size },
                      { label: 'Seeds', value: calendarEvent.seeds_count },
                      { label: 'Qualifier spots', value: calendarEvent.qualifier_spots },
                      { label: 'Wild Cards', value: calendarEvent.wild_cards },
                      { label: 'BYEs', value: calendarEvent.byes },
                      { label: 'Prestige', value: calendarEvent.prestige }
                    ]}
                  />
                ) : null}
              </>
            ) : null}
          </SectionCard>

          {canonicalEventAvailable ? (
            <SectionCard title="Canonical Entry Field">
              {entryFieldQuery.isLoading ? <p className="status">Loading canonical Entry Field…</p> : null}
              {entryFieldQuery.error && !isApiNotFound(entryFieldQuery.error) ? (
                <p className="error">Failed to load canonical Entry Field: {formatApiError(entryFieldQuery.error)}</p>
              ) : null}
              {isApiNotFound(entryFieldQuery.error) ? (
                <EmptyState message="Canonical Entry Field is not available for this tournament yet." />
              ) : null}
              {entryFieldQuery.data ? (
                <>
                  <MetadataList
                    items={[
                      { label: 'Viewer Branch', value: entryFieldQuery.data.viewer_branch_id },
                      { label: 'Field version', value: entryFieldQuery.data.field_sequence },
                      { label: 'Field mode', value: entryFieldQuery.data.mode === 'initial' ? 'Initial field' : 'Rebalanced field' },
                      { label: 'Main capacity', value: entryFieldQuery.data.main_draw_capacity },
                      { label: 'Active Main entrants', value: entryFieldQuery.data.active_main_entrant_count },
                      { label: 'Effective Main BYEs', value: entryFieldQuery.data.effective_main_bye_count }
                    ]}
                  />
                  <MetadataList
                    items={[
                      { label: 'Direct Main', value: entryFieldQuery.data.direct_main_player_ids.length ? entryFieldQuery.data.direct_main_player_ids.join(', ') : 'None' },
                      { label: 'Qualification', value: entryFieldQuery.data.qualification_player_ids.length ? entryFieldQuery.data.qualification_player_ids.join(', ') : 'None' },
                      { label: 'Alternates', value: entryFieldQuery.data.alternate_player_ids.length ? entryFieldQuery.data.alternate_player_ids.join(', ') : 'None' },
                      { label: 'Withdrawn', value: entryFieldQuery.data.withdrawn_player_ids.length ? entryFieldQuery.data.withdrawn_player_ids.join(', ') : 'None' }
                    ]}
                  />
                </>
              ) : null}
            </SectionCard>
          ) : null}

          {canonicalEventAvailable ? (
            <SectionCard title="Definitive Wild Cards">
              {wildCardsQuery.isLoading ? <p className="status">Loading definitive Wild Cards…</p> : null}
              {wildCardsQuery.error ? (
                <p className="error">Failed to load definitive Wild Cards: {formatApiError(wildCardsQuery.error)}</p>
              ) : null}
              {wildCardsQuery.data?.assignment_count === 0 ? (
                <EmptyState message="No definitive Wild Card assignments are recorded for this tournament." />
              ) : null}
              {wildCardsQuery.data && wildCardsQuery.data.assignments.length > 0 ? (
                <>
                  <MetadataList
                    items={[
                      { label: 'Viewer Branch', value: wildCardsQuery.data.viewer_branch_id },
                      { label: 'Definitive assignments', value: wildCardsQuery.data.assignment_count }
                    ]}
                  />
                  <ul className="item-list" aria-label="Definitive Wild Card assignments">
                    {wildCardsQuery.data.assignments.map((assignment) => (
                      <li key={assignment.wildcard_index}>
                        {assignment.source === 'reserve_wc'
                          ? `WC #${assignment.wildcard_index} · ${assignment.player_id} · Reserve WC #${assignment.reserve_ordinal}`
                          : `WC #${assignment.wildcard_index} · ${assignment.player_id} · Original WC`}
                      </li>
                    ))}
                  </ul>
                </>
              ) : null}
            </SectionCard>
          ) : null}

          {canonicalEventAvailable ? (
            <SectionCard title="Canonical Draw">
              {drawQuery.isLoading ? <p className="status">Loading canonical Draw…</p> : null}
              {drawQuery.error && !isApiNotFound(drawQuery.error) ? (
                <p className="error">Failed to load canonical Draw: {formatApiError(drawQuery.error)}</p>
              ) : null}
              {isApiNotFound(drawQuery.error) ? (
                <EmptyState message="Canonical Draw is not available for this tournament yet." />
              ) : null}
              {drawQuery.data ? (
                <>
                  <MetadataList
                    items={[
                      { label: 'Viewer Branch', value: drawQuery.data.viewer_branch_id },
                      { label: 'Draw revisions', value: drawQuery.data.revision_count },
                      { label: 'Main bracket size', value: drawQuery.data.main.bracket_size },
                      { label: 'Qualification sections', value: drawQuery.data.qualification_sections.length }
                    ]}
                  />
                  <div>
                    <strong>Main slots</strong>
                    <ul className="item-list" aria-label="Canonical Main draw slots">
                      {drawQuery.data.main.slots.map((slot) => (
                        <li key={slot.slot_index}>{drawSlotLabel(slot)}</li>
                      ))}
                    </ul>
                  </div>
                  {drawQuery.data.qualification_sections.map((section, index) => (
                    <div key={section.section_id ?? `qualification-${index + 1}`}>
                      <strong>{section.section_id ? `Qualification ${section.section_id}` : 'Qualification'}</strong>
                      <ul className="item-list" aria-label={section.section_id ? `Canonical Qualification ${section.section_id} slots` : 'Canonical Qualification slots'}>
                        {section.slots.map((slot) => (
                          <li key={slot.slot_index}>{drawSlotLabel(slot)}</li>
                        ))}
                      </ul>
                    </div>
                  ))}
                </>
              ) : null}
            </SectionCard>
          ) : null}

          {canonicalEventAvailable ? (
            <SectionCard title="Canonical publication context">
              {rankingHistoryQuery.error ? <p className="error">Failed to load Official Ranking history: {formatApiError(rankingHistoryQuery.error)}</p> : null}
              {finalsRaceQuery.error ? <p className="error">Failed to load Finals Race history: {formatApiError(finalsRaceQuery.error)}</p> : null}
              <MetadataList
                items={[
                  { label: 'Official Ranking publications this event week', value: rankingPublications.length },
                  { label: 'Finals Race publications at this cutoff week', value: finalsRacePublications.length },
                  {
                    label: 'Canonical links',
                    value: (
                      <ul className="item-list">
                        <li><Link to={viewerRankingsPath(runId)}>Official Ranking history</Link></li>
                        <li><Link to={viewerRacePath(runId)}>Finals Race</Link></li>
                        {rankingPublications.map((publication) => (
                          <li key={publication.week_ordinal}>
                            <Link to={viewerRankingSnapshotPath(runId, publication.week_ordinal)}>
                              Ranking publication #{publication.week_ordinal}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )
                  }
                ]}
              />
            </SectionCard>
          ) : null}

          <SectionCard title="Canonical Tournament Result">
            {resultQuery.isLoading ? <p className="status">Loading canonical Tournament Result…</p> : null}
            {resultQuery.error && !isApiNotFound(resultQuery.error) ? (
              <p className="error">Failed to load canonical Tournament Result: {formatApiError(resultQuery.error)}</p>
            ) : null}
            {isApiNotFound(resultQuery.error) ? (
              <EmptyState message="Canonical Tournament Result is not available for this tournament yet." />
            ) : null}
            {resultQuery.data ? (
              <>
                <MetadataList
                  items={[
                    { label: 'Viewer Branch', value: resultQuery.data.viewer_branch_id },
                    { label: 'Completed season', value: resultQuery.data.completed_season_index },
                    { label: 'Completed week', value: resultQuery.data.completed_week },
                    { label: 'Champion', value: resultQuery.data.champion_player_id },
                    { label: 'Finalist', value: resultQuery.data.finalist_player_id },
                    { label: 'Qualification winners', value: resultQuery.data.qualification_winner_ids.length ? resultQuery.data.qualification_winner_ids.join(', ') : 'None' },
                    { label: 'Players', value: resultQuery.data.players.length },
                    { label: 'Matches', value: resultQuery.data.matches.length }
                  ]}
                />
                <div>
                  <strong>Player results</strong>
                  <ul className="item-list" aria-label="Canonical Tournament player results">
                    {resultQuery.data.players.map((player) => (
                      <li key={player.player_id}>
                        {player.player_id} · {player.reached_stage.replace(/_/g, ' ')} · {player.wins}W–{player.losses}L
                        {player.seed_number == null ? '' : ` · seed ${player.seed_number}`}
                        {player.qualifier ? ' · qualifier' : ''}
                        {player.group_position == null ? '' : ` · group #${player.group_index ?? '?'} position ${player.group_position}`}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <strong>Match results</strong>
                  <ul className="item-list" aria-label="Canonical Tournament match results">
                    {resultQuery.data.matches.map((match) => (
                      <li key={match.match_id}>
                        {match.match_id} · {match.draw_type} R{match.round_number} · {match.winner_player_id}
                        {match.loser_player_id ? ` def. ${match.loser_player_id}` : ''} · {match.scoreline}
                      </li>
                    ))}
                  </ul>
                </div>
              </>
            ) : null}
          </SectionCard>

          {canonicalEventAvailable ? (
            <SectionCard title="Read-only data">
              <details>
                <summary>Show canonical source data</summary>
                <p className="status">Read-only Saved-Revision tournament metadata for audit/debugging.</p>
                <JsonPayloadBlock
                  title="Canonical tournament source"
                  emptyText="No canonical tournament source data is available."
                  payload={{ calendar: calendarEvent, history: historyEvent }}
                />
              </details>
            </SectionCard>
          ) : null}
        </>
      ) : null}
    </section>
  )
}

