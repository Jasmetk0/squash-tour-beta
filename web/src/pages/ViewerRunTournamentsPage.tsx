import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'
import type { ReactNode } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getEvent, getRun, getViewerCompletedTournaments, getViewerTournamentDraw, getViewerTournamentEntryField, getViewerTournamentResult, getViewerTournamentWildCards, listEvents, listRaceSnapshots, listRankingSnapshots } from '../api/client'
import type { EventRecord, SeasonStateResponse, ViewerCompletedTournamentSummary } from '../api/types'
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
  viewerTournamentsPath,
  viewerTournamentDetailPath,
  viewerWeekDetailPath
} from '../viewer/viewerRoutes'
import {
  buildEventDetailLinks,
  snapshotsForSourceEvent
} from './viewer/tour/viewerEventDetailDisplay'
import { getPlannedEventStatus } from './plannedEventUtils'

type PlannedEvent = SeasonStateResponse['season_state']['ordered_events'][number]

type PlannedTournamentContext = PlannedEvent & {
  planPosition: number
}

function buildPlannedContext(runData: SeasonStateResponse | undefined): Map<string, PlannedTournamentContext> {
  const plannedContext = new Map<string, PlannedTournamentContext>()
  const orderedEvents = runData?.season_state?.ordered_events

  if (!Array.isArray(orderedEvents)) return plannedContext

  orderedEvents.forEach((event, index) => {
    if (event && typeof event === 'object' && typeof event.event_id === 'string') {
      plannedContext.set(event.event_id, { ...event, planPosition: index })
    }
  })
  return plannedContext
}

function isScalar(value: unknown): value is string | number {
  return typeof value === 'string' || typeof value === 'number'
}

function safeText(value: unknown, fallback: string | number = '—'): string | number {
  return isScalar(value) ? value : fallback
}

function safeNumber(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function safeEventRecords(events: EventRecord[] | undefined): EventRecord[] {
  if (!Array.isArray(events)) return []
  return events.filter((event) => event && typeof event === 'object' && typeof event.event_id === 'string')
}

function safeCompletedEventIds(data: SeasonStateResponse | undefined): string[] {
  const completedEventIds = data?.season_state?.completed_event_ids
  return Array.isArray(completedEventIds) ? completedEventIds.filter((eventId) => typeof eventId === 'string') : []
}

function safeSnapshotRecords<T extends { snapshot_sequence: number }>(snapshots: T[] | undefined): T[] {
  if (!Array.isArray(snapshots)) return []
  return snapshots.filter((snapshot) => snapshot && typeof snapshot === 'object' && typeof snapshot.snapshot_sequence === 'number')
}

function eventWeek(event: EventRecord | null | undefined, planned: PlannedTournamentContext | undefined): number | null {
  return safeNumber(event?.week) ?? safeNumber(planned?.week) ?? null
}

function eventSeason(event: EventRecord | null | undefined, planned: PlannedTournamentContext | undefined): number | null {
  return safeNumber(event?.season) ?? safeNumber(planned?.season) ?? null
}

function canonicalCompletionStatus(
  eventId: string,
  canonicalResult: ViewerCompletedTournamentSummary | undefined,
  completedEventIds: Set<string>
): string {
  if (canonicalResult) return 'Canonical Saved Revision result'
  if (completedEventIds.has(eventId)) return 'Completed in season plan; result not published canonically'
  return 'Not completed in season plan'
}

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
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()

  const eventsQuery = useQuery({ queryKey: ['events', runId, legacySimulationRunId], queryFn: () => listEvents(legacySimulationRunId), enabled: Boolean(runId) })
  const runQuery = useQuery({ queryKey: ['run', runId, legacySimulationRunId], queryFn: () => getRun(legacySimulationRunId), enabled: Boolean(runId), retry: false })
  const completedQuery = useQuery({
    queryKey: ['viewer-completed-tournaments', runId],
    queryFn: () => getViewerCompletedTournaments(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const events = safeEventRecords(eventsQuery.data?.events)
  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const completedEventIds = useMemo(
    () => new Set(safeCompletedEventIds(runQuery.data)),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const eventsById = useMemo(
    () => new Map(events.map((event) => [event.event_id, event])),
    [events]
  )
  const canonicalCompleted = completedQuery.data?.tournaments ?? []
  const canonicalCompletedById = useMemo(
    () => new Map(canonicalCompleted.map((item) => [item.event_id, item])),
    [canonicalCompleted]
  )
  const tournamentIds = useMemo(() => {
    const ids = events.map((event) => event.event_id)
    for (const item of canonicalCompleted) {
      if (!ids.includes(item.event_id)) ids.push(item.event_id)
    }
    return ids
  }, [events, canonicalCompleted])

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournaments"
        runId={runId}
        subtitle="Read-only tournament schedule plus canonical Saved-Revision results for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Tournament records', value: tournamentIds.length },
          { label: 'Canonical completed results', value: canonicalCompleted.length },
          { label: 'Season-plan completed IDs', value: completedEventIds.size }
        ]}
      />

      <SectionCard title="Tournament publications">
        {eventsQuery.isLoading && <p className="status">Loading schedule compatibility records...</p>}
        {eventsQuery.error && <p className="error">Legacy schedule records could not be loaded: {formatApiError(eventsQuery.error)}</p>}
        {completedQuery.isLoading && <p className="status">Loading canonical completed tournaments...</p>}
        {completedQuery.error && !isApiNotFound(completedQuery.error) ? (
          <p className="error">Failed to load canonical completed tournaments: {formatApiError(completedQuery.error)}</p>
        ) : null}
        {runQuery.error && <p className="error">Failed to load ordered calendar context: {formatApiError(runQuery.error)}</p>}
        {!eventsQuery.isLoading && !completedQuery.isLoading && tournamentIds.length === 0 ? (
          <EmptyState message="No tournament schedule or canonical completed result is available for this run yet." />
        ) : null}
        {tournamentIds.length > 0 ? (
          <ul className="item-list" aria-label="Tournament event list">
            {tournamentIds.map((eventId) => {
              const event = eventsById.get(eventId)
              const planned = plannedContext.get(eventId)
              const canonicalResult = canonicalCompletedById.get(eventId)
              const week = canonicalResult?.completed_week ?? eventWeek(event, planned)
              const season = canonicalResult?.completed_season_index ?? eventSeason(event, planned)

              return (
                <li key={eventId} id={`event-${eventId}`}>
                  <strong>{eventId}</strong>
                  <MetadataList
                    items={[
                      { label: 'Sequence', value: event ? safeText(event.event_sequence) : '—' },
                      { label: 'Season', value: season ?? '—' },
                      { label: 'Week', value: displayWeekDetailLink(runId, week) },
                      { label: 'Template', value: safeText(planned?.template_id ?? event?.template_id, 'No saved calendar metadata') },
                      { label: 'Category', value: safeText(planned?.category, 'No ordered-calendar category') },
                      { label: 'Tour', value: safeText(planned?.tour, 'No ordered-calendar tour') },
                      { label: 'Completion', value: canonicalCompletionStatus(eventId, canonicalResult, completedEventIds) },
                      { label: 'Result availability', value: canonicalResult ? 'Canonical Saved Revision result available' : 'No canonical saved result' }
                    ]}
                  />
                  {canonicalResult ? (
                    <SummaryPills
                      items={[
                        { label: 'Champion', value: canonicalResult.champion_player_id },
                        { label: 'Finalist', value: canonicalResult.finalist_player_id },
                        { label: 'Players', value: canonicalResult.player_count },
                        { label: 'Matches', value: canonicalResult.match_count }
                      ]}
                    />
                  ) : null}
                  <p>
                    <Link to={viewerTournamentDetailPath(runId, eventId)}>Open tournament detail</Link>
                  </p>
                </li>
              )
            })}
          </ul>
        ) : null}
      </SectionCard>
    </section>
  )
}

export function ViewerRunTournamentDetailPage(): JSX.Element {
  const { eventId = '' } = useParams()
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()

  const eventQuery = useQuery({
    queryKey: ['event', runId, eventId],
    queryFn: () => getEvent(legacySimulationRunId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const runQuery = useQuery({ queryKey: ['run', runId, legacySimulationRunId], queryFn: () => getRun(legacySimulationRunId), enabled: Boolean(runId && eventId), retry: false })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-tournament-ranking-snapshots', runId, eventId],
    queryFn: () => listRankingSnapshots(legacySimulationRunId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-tournament-race-snapshots', runId, eventId],
    queryFn: () => listRaceSnapshots(legacySimulationRunId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const entryFieldQuery = useQuery({
    queryKey: ['viewer-tournament-entry-field', runId, eventId],
    queryFn: () => getViewerTournamentEntryField(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const drawQuery = useQuery({
    queryKey: ['viewer-tournament-draw', runId, eventId],
    queryFn: () => getViewerTournamentDraw(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const wildCardsQuery = useQuery({
    queryKey: ['viewer-tournament-wild-cards', runId, eventId],
    queryFn: () => getViewerTournamentWildCards(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const resultQuery = useQuery({
    queryKey: ['viewer-tournament-result', runId, eventId],
    queryFn: () => getViewerTournamentResult(runId, eventId),
    enabled: Boolean(runId && eventId),
    retry: false
  })
  const canonicalResultAvailability = resultQuery.data
    ? 'Canonical Saved Revision result available'
    : resultQuery.isLoading
      ? 'Loading canonical saved result'
      : isApiNotFound(resultQuery.error)
        ? 'No canonical saved result yet'
        : 'Canonical result unavailable'

  const plannedContext = useMemo(() => buildPlannedContext(runQuery.data), [runQuery.data])
  const planned = plannedContext.get(eventId)
  const orderedEvents = Array.isArray(runQuery.data?.season_state?.ordered_events) ? runQuery.data.season_state.ordered_events : []
  const completedEventIds = useMemo(
    () => new Set(safeCompletedEventIds(runQuery.data)),
    [runQuery.data?.season_state.completed_event_ids]
  )
  const plannedStatus = planned
    ? getPlannedEventStatus({
        index: planned.planPosition,
        nextEventIndex: runQuery.data?.season_state.next_event_index ?? 0,
        completedEventIds,
        eventId: planned.event_id
      })
    : null
  const event = eventQuery.data
  const week = eventWeek(event, planned)
  const season = eventSeason(event, planned)
  const templateId = planned?.template_id ?? event?.template_id ?? null
  const rankingPublications = snapshotsForSourceEvent(safeSnapshotRecords(rankingSnapshotsQuery.data?.snapshots), eventId)
  const racePublications = snapshotsForSourceEvent(safeSnapshotRecords(raceSnapshotsQuery.data?.snapshots), eventId)
  const sourceLinks = buildEventDetailLinks({
    runId,
    eventId,
    week,
    hasPlanned: Boolean(planned),
    hasPersisted: Boolean(event),
    rankingSnapshotSequences: rankingPublications.map((snapshot) => snapshot.snapshot_sequence),
    raceSnapshotSequences: racePublications.map((snapshot) => snapshot.snapshot_sequence)
  })

  return (
    <section className="panel">
      <RunScopedHeader
        title="Tournament Detail"
        runId={runId}
        subtitle="Read-only tournament detail for the selected run."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Event', value: eventId || 'unknown' },
          { label: 'Result availability', value: canonicalResultAvailability }
        ]}
      />

      <SectionCard title="Tournament links">
        <p>
          <Link to={viewerTournamentsPath(runId)}>Back to tournaments</Link>
          {planned ? (
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
        </p>
      </SectionCard>

      {!eventId && (
        <SectionCard title="Tournament lookup">
          <EmptyState message="No event ID was provided in the URL." />
        </SectionCard>
      )}

      {eventId && (
        <>
          <SectionCard title="Tournament metadata">
            {eventQuery.isLoading && <p className="status">Loading tournament detail...</p>}
            {eventQuery.error && !isApiNotFound(eventQuery.error) && (
              <p className="error">Failed to load tournament detail: {formatApiError(eventQuery.error)}</p>
            )}
            {isApiNotFound(eventQuery.error) && <EmptyState message={`Event ${eventId} was not found for this run.`} />}
            {runQuery.error && <p className="error">Failed to load ordered calendar context: {formatApiError(runQuery.error)}</p>}
            {event ? (
              <>
                <SummaryPills
                  items={[
                    { label: 'Status', value: plannedStatus ?? canonicalCompletionStatus(event.event_id, resultQuery.data ? {
                      event_id: resultQuery.data.event_id,
                      completed_season_index: resultQuery.data.completed_season_index,
                      completed_week: resultQuery.data.completed_week,
                      champion_player_id: resultQuery.data.champion_player_id,
                      finalist_player_id: resultQuery.data.finalist_player_id,
                      qualification_winner_ids: resultQuery.data.qualification_winner_ids,
                      player_count: resultQuery.data.players.length,
                      match_count: resultQuery.data.matches.length
                    } : undefined, completedEventIds) },
                    { label: 'Result availability', value: canonicalResultAvailability },
                    { label: 'Ordered-calendar match', value: planned ? 'Available' : 'Not available' }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: 'Event ID', value: event.event_id },
                    { label: 'Run ID', value: runId || 'unknown' },
                    { label: 'Sequence', value: safeText(event.event_sequence) },
                    { label: 'Season', value: season ?? '—' },
                    { label: 'Week', value: displayWeekDetailLink(runId, week) },
                    { label: 'Tour', value: safeText(planned?.tour, 'No ordered-calendar tour') },
                    { label: 'Category', value: safeText(planned?.category, 'No ordered-calendar category') },
                    { label: 'Template', value: safeText(templateId) }
                  ]}
                />
                {planned ? (
                  <MetadataList
                    items={[
                      { label: 'Plan position', value: `${planned.planPosition + 1} of ${orderedEvents.length}` },
                      { label: 'Plan index', value: planned.planPosition },
                      { label: 'Current next event index', value: runQuery.data?.season_state.next_event_index ?? '—' }
                    ]}
                  />
                ) : null}
              </>
            ) : null}
          </SectionCard>

          {event ? (
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

          {event ? (
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

          {event ? (
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

          {event ? (
            <SectionCard title="Source context links">
              {rankingSnapshotsQuery.error ? <p className="error">Failed to load ranking publications: {formatApiError(rankingSnapshotsQuery.error)}</p> : null}
              {raceSnapshotsQuery.error ? <p className="error">Failed to load race publications: {formatApiError(raceSnapshotsQuery.error)}</p> : null}
              <MetadataList
                items={[
                  { label: 'Ranking publications from event', value: rankingPublications.length },
                  { label: 'Race publications from event', value: racePublications.length },
                  {
                    label: 'Safe links',
                    value: (
                      <ul className="item-list">
                        {sourceLinks.map((link) => (
                          <li key={`${link.label}-${link.href}`}>
                            <Link to={link.href}>{link.label}</Link>
                          </li>
                        ))}
                      </ul>
                    )
                  }
                ]}
              />
            </SectionCard>
          ) : null}

          {eventId ? (
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
          ) : null}

          {event ? (
            <SectionCard title="Read-only data">
              <details>
                <summary>Show technical event data</summary>
                <p className="status">Read-only technical event/result data for audit/debugging. Viewer tournament detail pages do not mutate run state.</p>
                <JsonPayloadBlock title="Technical event record" emptyText="No technical event data is available for this event." payload={event} />
              </details>
            </SectionCard>
          ) : null}
        </>
      )}
    </section>
  )
}
