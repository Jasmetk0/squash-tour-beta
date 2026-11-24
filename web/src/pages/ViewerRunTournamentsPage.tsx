import { useQuery, type UseQueryResult } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'
import { ViewerRunTournamentArchive } from './viewer/tour/ViewerRunTournamentArchive'

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

function displayWeekDetailLink(runId: string, week: number | null, season: string | number | null): ReactNode {
  if (week == null) return '—'
  if (season == null || !String(season).trim()) return `W${week}`

  return <Link to={viewerWeekDetailPath(runId, week) + '?season=' + encodeURIComponent(String(season))}>{`W${week}`}</Link>
}


export function ViewerRunTournamentsPage(): JSX.Element {
  return <ViewerRunTournamentArchive detailPath={viewerTournamentDetailPath} />
}

// Each public endpoint is independently fetched. A run-only cache key cannot
// distinguish a changed saved Viewer Branch. Never render stale or foreign DTOs.
function matchesTournamentSource(value: unknown, runId: string, branchId: string, schema: string, eventId?: string): boolean {
  if (!value || typeof value !== 'object' || Array.isArray(value) || !branchId) return false
  const source = value as Record<string, unknown>
  return source.schema_version === schema && source.product_run_id === runId &&
    source.viewer_branch_id === branchId && (eventId === undefined || source.event_id === eventId)
}

function scopedRead<T>(query: UseQueryResult<T, Error>, runId: string, branchId: string, schema: string, eventId?: string) {
  const ready = !query.isFetching && !query.isPending && !query.isError
  const mismatch = ready && query.data !== undefined && !matchesTournamentSource(query.data, runId, branchId, schema, eventId)
  return { ...query, data: ready && !mismatch ? query.data : undefined, mismatch }
}

export function ViewerRunTournamentDetailPage(): JSX.Element {
  const { eventId = '' } = useParams()
  const { productRunId: runId, officialBranchId: branchId, officialContext, isLoading, isStale } = useViewerProductRunRouteContext()
  const validContext = Boolean(runId && branchId && officialContext.product_run_id === runId &&
    officialContext.official_branch_id === branchId && !isLoading && !isStale)
  const enabled = Boolean(validContext && eventId)

  const calendarQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-detail-calendar', runId, branchId, eventId],
    queryFn: () => getViewerRunCalendar(runId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_run_calendar.v1')
  const historyQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-detail-history', runId, branchId, eventId],
    queryFn: () => getViewerTournamentHistory(runId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_tournament_history.v1')
  const rankingHistoryQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-detail-ranking-history', runId, branchId, eventId],
    queryFn: () => listViewerOfficialRankingHistory(runId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_official_ranking_history.v1')
  const finalsRaceQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-detail-finals-race', runId, branchId, eventId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_finals_race_history.v1')
  const entryFieldQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-entry-field', runId, branchId, eventId],
    queryFn: () => getViewerTournamentEntryField(runId, eventId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_tournament_entry_field.v1', eventId)
  const drawQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-draw', runId, branchId, eventId],
    queryFn: () => getViewerTournamentDraw(runId, eventId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_tournament_draw.v1', eventId)
  const wildCardsQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-wild-cards', runId, branchId, eventId],
    queryFn: () => getViewerTournamentWildCards(runId, eventId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_tournament_wild_cards.v1', eventId)
  const resultQuery = scopedRead(useQuery({
    queryKey: ['viewer-tournament-result', runId, branchId, eventId],
    queryFn: () => getViewerTournamentResult(runId, eventId),
    enabled,
    retry: false
  }), runId, enabled ? branchId : '', 'viewer_tournament_result.v1', eventId)

  const calendarMatches = useMemo(
    () => (calendarQuery.data?.seasons ?? []).flatMap((season) => season.events).filter((event) => event.event_id === eventId),
    [calendarQuery.data?.seasons, eventId]
  )
  const historyMatches = useMemo(
    () => (historyQuery.data?.tournaments ?? []).filter((event) => event.event_id === eventId),
    [historyQuery.data?.tournaments, eventId]
  )
  const calendarCandidate = calendarMatches[0]
  const historyCandidate = historyMatches[0]
  const metadataConflict = calendarQuery.mismatch || historyQuery.mismatch ||
    calendarMatches.length > 1 || historyMatches.length > 1 ||
    Boolean(calendarCandidate && historyCandidate &&
      (String(calendarCandidate.season) !== historyCandidate.season ||
       calendarCandidate.season_week !== historyCandidate.season_week))
  const metadataReady = enabled && !metadataConflict &&
    !calendarQuery.isPending && !historyQuery.isPending && !calendarQuery.isFetching && !historyQuery.isFetching
  const calendarEvent = metadataReady ? calendarCandidate ?? null : null
  const historyEvent = metadataReady ? historyCandidate ?? null : null
  const week = calendarEvent?.season_week ?? historyEvent?.season_week ?? null
  const season = calendarEvent?.season ?? historyEvent?.season ?? null
  const seasonMatch = season == null ? null : /^(\d{4})(?:\/\d{2,4})?$/.exec(String(season))
  const seasonStart = seasonMatch ? Number(seasonMatch[1]) : null
  const seasonIndex = seasonStart !== null && seasonStart >= 2000 ? seasonStart - 2000 : null
  const canonicalEventAvailable = Boolean(calendarEvent || historyEvent)
  const resultAvailable = canonicalEventAvailable && Boolean(resultQuery.data)
  const publicationLabel = resultAvailable || historyEvent?.result_published === true ? 'Published' :
    canonicalEventAvailable && (historyEvent?.result_published === false || isApiNotFound(resultQuery.error)) ? 'Not published' : '—'

  const rankingPublications = useMemo(
    () => seasonIndex === null ? [] :
      (rankingHistoryQuery.data?.publications ?? []).filter(publication =>
        publication.week === week && publication.season_index === seasonIndex),
    [rankingHistoryQuery.data?.publications, seasonIndex, week]
  )
  const finalsRacePublications = useMemo(
    () => seasonIndex === null ? [] :
      (finalsRaceQuery.data?.publications ?? []).filter(publication =>
        matchesTournamentSource(publication, runId, branchId, 'viewer_finals_race_publication.v1') &&
        publication.cutoff_week === week && publication.cutoff_season_index === seasonIndex),
    [finalsRaceQuery.data?.publications, runId, branchId, seasonIndex, week]
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
          { label: 'Viewer Branch', value: validContext ? branchId : '—' },
          { label: 'Result availability', value: publicationLabel }
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
          {week != null && season != null && String(season).trim() ? (
            <>
              {' · '}
              <Link to={viewerWeekDetailPath(runId, week) + '?season=' + encodeURIComponent(String(season))}>Open week detail</Link>
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
            {!validContext ? <p role="alert">Viewer Branch context is not verified.</p> : null}
            {metadataConflict ? <p role="alert">Tournament metadata sources are inconsistent or belong to another Viewer context.</p> : null}
            {enabled && (calendarQuery.isFetching || historyQuery.isFetching) ? <p className="status">Loading canonical tournament metadata…</p> : null}
            {canonicalError && !isApiNotFound(canonicalError) ? (
              <p className="error">Failed to load canonical tournament metadata: {formatApiError(canonicalError)}</p>
            ) : null}
            {metadataReady && !canonicalError && !canonicalEventAvailable ? (
              <EmptyState message={`Event ${eventId} is not present in the canonical Saved Calendar or Tournament History.`} />
            ) : null}
            {canonicalEventAvailable ? (
              <>
                <SummaryPills
                  items={[
                    { label: 'Calendar status', value: calendarEvent?.status ?? 'No Saved Calendar match' },
                    { label: 'Result publication', value: publicationLabel },
                    { label: 'Ranking status', value: historyEvent?.ranking_status ?? '—' }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: 'Event ID', value: eventId },
                    { label: 'Event name', value: calendarEvent?.event_name ?? historyEvent?.event_name ?? eventId },
                    { label: 'Season', value: season ?? '—' },
                    { label: 'Week', value: displayWeekDetailLink(runId, week, season) },
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
              {entryFieldQuery.mismatch ? <p role="alert">Canonical Entry Field source does not match this tournament or Viewer Branch.</p> : null}
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
              {wildCardsQuery.mismatch ? <p role="alert">Definitive Wild Cards source does not match this tournament or Viewer Branch.</p> : null}
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
              {drawQuery.mismatch ? <p role="alert">Canonical Draw source does not match this tournament or Viewer Branch.</p> : null}
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
              {rankingHistoryQuery.mismatch ? <p role="alert">Official Ranking history source does not match this Viewer Branch.</p> : null}
              {finalsRaceQuery.mismatch ? <p role="alert">Finals Race history source does not match this Viewer Branch.</p> : null}
              {rankingHistoryQuery.error ? <p className="error">Failed to load Official Ranking history: {formatApiError(rankingHistoryQuery.error)}</p> : null}
              {finalsRaceQuery.error ? <p className="error">Failed to load Finals Race history: {formatApiError(finalsRaceQuery.error)}</p> : null}
              <MetadataList
                items={[
                  { label: 'Official Ranking publications this event week', value: rankingHistoryQuery.data && seasonIndex !== null ? rankingPublications.length : '—' },
                  { label: 'Finals Race publications at this cutoff week', value: finalsRaceQuery.data && seasonIndex !== null ? finalsRacePublications.length : '—' },
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
            {resultQuery.mismatch ? <p role="alert">Tournament Result source does not match this tournament or Viewer Branch.</p> : null}
            {!canonicalEventAvailable && resultQuery.data ? <p className="status">Tournament Result withheld until the event context is verified.</p> : null}
            {resultQuery.isLoading ? <p className="status">Loading canonical Tournament Result…</p> : null}
            {resultQuery.error && !isApiNotFound(resultQuery.error) ? (
              <p className="error">Failed to load canonical Tournament Result: {formatApiError(resultQuery.error)}</p>
            ) : null}
            {isApiNotFound(resultQuery.error) ? (
              <EmptyState message="Canonical Tournament Result is not available for this tournament yet." />
            ) : null}
            {canonicalEventAvailable && resultQuery.data ? (
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

