import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'

import { getRunActivity, getViewerFinalsRace, getViewerTournamentResult } from '../api/client'
import type { RunActivityItem, ViewerFinalsRaceHistory, ViewerFinalsRacePublication, ViewerFinalsRaceRow } from '../api/types'
import {
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
  viewerFinalsPath,
  viewerFinalsQualificationPath,
  viewerFinalsResultPath,
  viewerPlannedEventPath,
  viewerPlayerProfilePath,
  viewerRacePath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath
} from '../viewer/viewerRoutes'


function isScalar(value: unknown): value is string | number | boolean {
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

function safeScalarValue(value: unknown, fallback: string | number = '—'): string | number {
  if (typeof value === 'string' || typeof value === 'number') return value
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return fallback
}

function formatWeek(week: number | null | undefined): string {
  return typeof week === 'number' ? `W${week}` : '—'
}

function formatSeason(season: number | null | undefined): string | number {
  return typeof season === 'number' ? season : '—'
}

function isPreviewableActivityItem(item: RunActivityItem | undefined): item is RunActivityItem {
  return Boolean(item && isScalar(item.label) && isScalar(item.kind))
}

function latestFinalsPublication(history: ViewerFinalsRaceHistory | undefined): ViewerFinalsRacePublication | null {
  if (!history || history.latest_target_season_index == null) return null
  return history.publications.find(
    (publication) => publication.target_season_index === history.latest_target_season_index
  ) ?? null
}

function confirmedFinalsParticipants(publication: ViewerFinalsRacePublication | null): ViewerFinalsRaceRow[] {
  if (!publication?.selection_published) return []
  return publication.rows
    .filter((row) => row.finals_selected === true)
    .sort((a, b) => (a.finals_seed ?? Number.MAX_SAFE_INTEGER) - (b.finals_seed ?? Number.MAX_SAFE_INTEGER))
}

function FinalsParticipantList({ runId, rows }: { runId: string; rows: ViewerFinalsRaceRow[] }): JSX.Element {
  if (!rows.length) return <EmptyState message="Confirmed World Tour Finals participants are not published yet." />
  return (
    <div className="table-wrap">
      <table aria-label="Canonical World Tour Finals participants">
        <thead>
          <tr>
            <th>Seed</th>
            <th>Player</th>
            <th>Race rank</th>
            <th>Race points</th>
            <th>Qualification</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.player_id}>
              <td>{row.finals_seed ?? '—'}</td>
              <td><Link to={viewerPlayerProfilePath(runId, row.player_id)}>{row.player_id}</Link></td>
              <td>#{row.rank}</td>
              <td>{row.race_points}</td>
              <td>{row.qualification_source === 'direct_entry' ? 'Direct entry' : row.qualification_source === 'race' ? 'Race' : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TechnicalData({ summary, title, payload, emptyText }: { summary: string; title: string; payload: unknown; emptyText: string }): JSX.Element {
  return (
    <details>
      <summary>{summary}</summary>
      <JsonPayloadBlock title={title} payload={payload} emptyText={emptyText} />
    </details>
  )
}

export function ViewerRunHistoryPage(): JSX.Element {
  const { productRunId: runId, legacySimulationRunId } = useViewerProductRunRouteContext()
  const activityQuery = useQuery({
    queryKey: ['run-activity', runId, legacySimulationRunId],
    queryFn: () => getRunActivity(legacySimulationRunId),
    enabled: Boolean(runId),
    retry: false
  })

  const items = Array.isArray(activityQuery.data?.items) ? activityQuery.data.items : []
  const latestItem = items[0]
  const canPreviewLatest = isPreviewableActivityItem(latestItem)

  return (
    <section className="panel">
      <RunScopedHeader title="History" runId={runId} subtitle="Read-only run activity and season timeline." />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Activity count', value: activityQuery.data ? items.length : '—' },
          { label: 'Latest activity', value: canPreviewLatest ? latestItem.label : items.length > 0 ? 'Preview deferred' : '—' }
        ]}
      />

      <SectionCard title="Season timeline">
        {activityQuery.isLoading ? <p className="status">Loading history…</p> : null}
        {activityQuery.error ? <p className="error">Failed to load run activity: {formatApiError(activityQuery.error)}</p> : null}
        {activityQuery.data && items.length === 0 ? <EmptyState message="No data is available for this run yet." /> : null}
        {activityQuery.data && items.length > 0 ? (
          canPreviewLatest ? (
            <>
              <SummaryPills
                items={[
                  { label: 'Activity count', value: items.length },
                  { label: 'Latest kind', value: safeScalarValue(latestItem.kind) },
                  { label: 'Latest season', value: formatSeason(latestItem.season) },
                  { label: 'Latest week', value: formatWeek(latestItem.week) }
                ]}
              />
              <MetadataList
                items={[
                  { label: 'Latest label', value: safeScalarValue(latestItem.label) },
                  { label: 'Sequence', value: safeScalarValue(latestItem.sequence) },
                  { label: 'Event ID', value: safeScalarValue(latestItem.event_id) },
                  { label: 'Snapshot sequence', value: safeScalarValue(latestItem.snapshot_sequence) },
                  { label: 'Source event', value: safeScalarValue(latestItem.source_event_id) },
                  { label: 'Related run', value: safeScalarValue(latestItem.related_run_id) }
                ]}
              />
            </>
          ) : (
            <EmptyState message="This preview is not connected for this data shape yet." />
          )
        ) : null}
      </SectionCard>

      {activityQuery.data ? (
        <SectionCard title="Read-only data">
          <TechnicalData
            summary="Show technical history data"
            title="Technical activity data"
            payload={activityQuery.data}
            emptyText="No technical history data is available."
          />
        </SectionCard>
      ) : null}
    </section>
  )
}

export function ViewerRunFinalsPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const raceQuery = useQuery({
    queryKey: ['viewer-finals-race', runId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const publication = latestFinalsPublication(raceQuery.data)
  const participants = confirmedFinalsParticipants(publication)

  return (
    <section className="panel">
      <RunScopedHeader
        title="World Tour Finals"
        runId={runId}
        subtitle="Canonical confirmed Finals field from the selected Viewer Branch's Saved Revision."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Qualification', value: publication?.selection_published ? 'Published' : publication ? 'Pending' : 'Unavailable' },
          { label: 'Target season index', value: publication?.target_season_index ?? '—' },
          { label: 'Confirmed players', value: participants.length }
        ]}
      />

      <SectionCard title="Finals Summary">
        {raceQuery.isLoading ? <p className="status">Loading canonical Finals publication…</p> : null}
        {raceQuery.error ? <p className="error">Failed to load canonical Finals publication: {formatApiError(raceQuery.error)}</p> : null}
        {publication ? (
          <MetadataList
            items={[
              { label: 'Viewer Branch', value: publication.viewer_branch_id },
              { label: 'Finals event ID', value: publication.finals_event_id ?? 'Not selected yet' },
              { label: 'Race cutoff', value: `season ${publication.cutoff_season_index}, W${publication.cutoff_week}` },
              { label: 'Best-N', value: publication.best_n },
              { label: 'Selection published', value: publication.selection_published ? 'Yes' : 'No' },
              { label: 'Confirmed participants', value: participants.length }
            ]}
          />
        ) : raceQuery.data ? (
          <EmptyState message="No canonical World Tour Finals Race publication exists yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Confirmed Finals Participants">
        <FinalsParticipantList runId={runId} rows={participants} />
      </SectionCard>

      <SectionCard title="Finals Result">
        <p className="status">
          Finals Result is published from the same Saved-Revision canonical Tournament Result authority used by Tournament Detail.
          It becomes visible only after the Finals event identity is published and the completed result is captured by Save.
        </p>
        <p><Link to={viewerFinalsResultPath(runId)}>Open Finals result</Link></p>
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerSeasonCalendarPath(runId)}>Back to Season Calendar</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsQualificationPath(runId)}>Open Finals qualification</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerFinalsResultPath(runId)}>Open Finals result</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>
    </section>
  )
}

export function ViewerRunFinalsQualificationPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const raceQuery = useQuery({
    queryKey: ['viewer-finals-race', runId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const publication = latestFinalsPublication(raceQuery.data)
  const participants = confirmedFinalsParticipants(publication)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Finals Qualification"
        runId={runId}
        subtitle="Canonical confirmed World Tour Finals participant field from Saved Revision authority."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Target season index', value: publication?.target_season_index ?? '—' },
          { label: 'Race cutoff', value: publication ? `W${publication.cutoff_week}` : '—' },
          { label: 'Qualification', value: publication?.selection_published ? 'Published' : publication ? 'Pending' : 'Unavailable' }
        ]}
      />

      <SectionCard title="Qualification Summary">
        {raceQuery.isLoading ? <p className="status">Loading canonical Finals qualification…</p> : null}
        {raceQuery.error ? <p className="error">Failed to load canonical Finals qualification: {formatApiError(raceQuery.error)}</p> : null}
        {publication ? (
          <MetadataList
            items={[
              { label: 'Viewer Branch', value: publication.viewer_branch_id },
              { label: 'Finals event ID', value: publication.finals_event_id ?? 'Not selected yet' },
              { label: 'Target season index', value: publication.target_season_index },
              { label: 'Cutoff season index', value: publication.cutoff_season_index },
              { label: 'Cutoff week', value: `W${publication.cutoff_week}` },
              { label: 'Best-N', value: publication.best_n },
              { label: 'Confirmed players', value: participants.length }
            ]}
          />
        ) : raceQuery.data ? (
          <EmptyState message="No canonical World Tour Finals Race publication exists yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Confirmed Participants">
        <FinalsParticipantList runId={runId} rows={participants} />
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>Back to Finals Summary</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>
    </section>
  )
}

export function ViewerRunFinalsResultPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const raceQuery = useQuery({
    queryKey: ['viewer-finals-race', runId],
    queryFn: () => getViewerFinalsRace(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const publication = latestFinalsPublication(raceQuery.data)
  const eventId = publication?.finals_event_id ?? null
  const resultQuery = useQuery({
    queryKey: ['viewer-finals-result', runId, eventId],
    queryFn: () => getViewerTournamentResult(runId, eventId ?? ''),
    enabled: Boolean(runId && eventId),
    retry: false
  })

  const resultNotFound = isApiNotFound(resultQuery.error)
  const result = resultQuery.data
  const resultStatus = result
    ? 'Published'
    : resultNotFound
      ? 'Not published'
      : eventId
        ? resultQuery.isLoading
          ? 'Loading'
          : 'Unavailable'
        : 'Unavailable'

  return (
    <section className="panel">
      <RunScopedHeader
        title="Finals Result"
        runId={runId}
        subtitle="Canonical World Tour Finals result from the selected Viewer Branch's Saved Revision."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Finals event', value: eventId ?? '—' },
          { label: 'Target season index', value: publication?.target_season_index ?? '—' },
          { label: 'Result', value: resultStatus }
        ]}
      />

      <SectionCard title="Canonical Finals Result">
        {raceQuery.isLoading ? <p className="status">Loading canonical Finals publication…</p> : null}
        {raceQuery.error ? <p className="error">Failed to load canonical Finals publication: {formatApiError(raceQuery.error)}</p> : null}
        {raceQuery.data && !publication ? (
          <EmptyState message="No canonical World Tour Finals Race publication exists yet." />
        ) : null}
        {publication && !eventId ? (
          <EmptyState message="The canonical Finals event identity is not published yet." />
        ) : null}

        {eventId && resultQuery.isLoading ? <p className="status">Loading canonical Finals Tournament Result…</p> : null}
        {eventId && resultQuery.error && !resultNotFound ? (
          <p className="error">Failed to load canonical Finals Tournament Result: {formatApiError(resultQuery.error)}</p>
        ) : null}
        {eventId && resultNotFound ? (
          <EmptyState message="Canonical Finals Tournament Result is not published yet." />
        ) : null}

        {result ? (
          <>
            <MetadataList
              items={[
                { label: 'Viewer Branch', value: result.viewer_branch_id },
                {
                  label: 'Finals event ID',
                  value: <Link to={viewerTournamentDetailPath(runId, result.event_id)}>{result.event_id}</Link>
                },
                { label: 'Completed season', value: result.completed_season_index },
                { label: 'Completed week', value: \`W\${result.completed_week}\` },
                {
                  label: 'Champion',
                  value: <Link to={viewerPlayerProfilePath(runId, result.champion_player_id)}>{result.champion_player_id}</Link>
                },
                {
                  label: 'Finalist',
                  value: <Link to={viewerPlayerProfilePath(runId, result.finalist_player_id)}>{result.finalist_player_id}</Link>
                },
                {
                  label: 'Qualification winners',
                  value: result.qualification_winner_ids.length ? (
                    <ul className="item-list" aria-label="Finals qualification winners">
                      {result.qualification_winner_ids.map((playerId) => (
                        <li key={playerId}>
                          <Link to={viewerPlayerProfilePath(runId, playerId)}>{playerId}</Link>
                        </li>
                      ))}
                    </ul>
                  ) : 'None'
                },
                { label: 'Players', value: result.players.length },
                { label: 'Matches', value: result.matches.length }
              ]}
            />

            <div>
              <strong>Player results</strong>
              <ul className="item-list" aria-label="Canonical Finals player results">
                {result.players.map((player) => (
                  <li key={player.player_id}>
                    <Link to={viewerPlayerProfilePath(runId, player.player_id)}>{player.player_id}</Link>
                    {\` · \${player.reached_stage.replace(/_/g, ' ')} · \${player.wins}W–\${player.losses}L\`}
                    {player.seed_number == null ? '' : \` · seed \${player.seed_number}\`}
                    {player.qualifier ? ' · qualifier' : ''}
                    {player.group_position == null ? '' : \` · group #\${player.group_index ?? '?'} position \${player.group_position}\`}
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <strong>Match results</strong>
              <ul className="item-list" aria-label="Canonical Finals match results">
                {result.matches.map((match) => (
                  <li key={match.match_id}>
                    {match.match_id} · {match.draw_type} R{match.round_number} ·{' '}
                    <Link to={viewerPlayerProfilePath(runId, match.winner_player_id)}>{match.winner_player_id}</Link>
                    {match.loser_player_id ? (
                      <>
                        {' '}def. <Link to={viewerPlayerProfilePath(runId, match.loser_player_id)}>{match.loser_player_id}</Link>
                      </>
                    ) : null}
                    {' '}· {match.scoreline}
                  </li>
                ))}
              </ul>
            </div>
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Source Links">
        {eventId ? (
          <ul className="item-list" aria-label="Finals source event links">
            <li><Link to={viewerPlannedEventPath(runId, eventId)}>Planned event {eventId}</Link></li>
            <li><Link to={viewerTournamentDetailPath(runId, eventId)}>Tournament detail {eventId}</Link></li>
          </ul>
        ) : (
          <EmptyState message="Finals source links become available after the event identity is published." />
        )}
      </SectionCard>

      <SectionCard title="Links">
        <p className="viewer-active-run-actions">
          <Link className="viewer-active-run-link" to={viewerFinalsPath(runId)}>Back to Finals Summary</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRankingsPath(runId)}>Open rankings</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerRacePath(runId)}>Open race</Link>{' '}
          <Link className="viewer-active-run-link" to={viewerTournamentsPath(runId)}>Open tournaments</Link>
        </p>
      </SectionCard>
    </section>
  )
}
