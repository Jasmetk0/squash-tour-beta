import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getViewerFinals } from '../api/client'
import type {
  ViewerFinalsParticipant,
  ViewerFinalsSeason,
  ViewerTournamentResult
} from '../api/types'
import {
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'
import { useViewerProductRunRouteContext } from '../viewer/ViewerProductRunRouteContext'
import {
  viewerFinalsPath,
  viewerFinalsQualificationPath,
  viewerFinalsResultPath,
  viewerPlayerProfilePath,
  viewerRacePath,
  viewerRankingsPath,
  viewerSeasonCalendarPath,
  viewerTournamentDetailPath,
  viewerTournamentsPath
} from '../viewer/viewerRoutes'

function seasonLabel(index: number): string {
  const start = 2000 + index
  return `${start}/${String((start + 1) % 100).padStart(2, '0')}`
}

function qualificationLabel(player: ViewerFinalsParticipant): string {
  if (player.qualification_source === 'direct_entry') {
    const sources = player.direct_entry_event_ids.length
      ? ` · ${player.direct_entry_event_ids.join(', ')}`
      : ''
    return `Direct entry${sources}`
  }
  return 'Race'
}

function FinalsParticipantsTable({
  runId,
  season
}: {
  runId: string
  season: ViewerFinalsSeason
}): JSX.Element {
  return (
    <div className="table-wrap">
      <table aria-label="Canonical Finals participants">
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
          {season.participants.map((player) => (
            <tr key={player.player_id}>
              <td>{player.seed}</td>
              <td>
                <Link to={viewerPlayerProfilePath(runId, player.player_id)}>
                  {player.player_id}
                </Link>
              </td>
              <td>#{player.race_rank}</td>
              <td>{player.race_points}</td>
              <td>{qualificationLabel(player)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function FinalsResultSummary({
  runId,
  season
}: {
  runId: string
  season: ViewerFinalsSeason
}): JSX.Element {
  const result = season.result
  if (!result) {
    return <EmptyState message="Canonical Finals Result has not been published for this saved season yet." />
  }

  return (
    <>
      <MetadataList
        items={[
          { label: 'Finals event', value: <Link to={viewerTournamentDetailPath(runId, result.event_id)}>{result.event_id}</Link> },
          { label: 'Completed week', value: `W${result.completed_week}` },
          { label: 'Champion', value: <Link to={viewerPlayerProfilePath(runId, result.champion_player_id)}>{result.champion_player_id}</Link> },
          { label: 'Finalist', value: <Link to={viewerPlayerProfilePath(runId, result.finalist_player_id)}>{result.finalist_player_id}</Link> },
          { label: 'Qualification winners', value: result.qualification_winner_ids.length ? result.qualification_winner_ids.join(', ') : 'None' },
          { label: 'Completed matches', value: result.matches.length }
        ]}
      />
    </>
  )
}

function FinalsResultDetails({
  runId,
  result
}: {
  runId: string
  result: ViewerTournamentResult
}): JSX.Element {
  return (
    <>
      <SectionCard title="Final standings / player outcomes">
        <ul className="item-list" aria-label="Canonical Finals player outcomes">
          {result.players.map((player) => (
            <li key={player.player_id}>
              <Link to={viewerPlayerProfilePath(runId, player.player_id)}>{player.player_id}</Link>
              {' · '}
              {player.reached_stage.replace(/_/g, ' ')}
              {' · '}
              {player.wins}W–{player.losses}L
              {player.seed_number == null ? '' : ` · seed ${player.seed_number}`}
              {player.group_position == null ? '' : ` · group position ${player.group_position}`}
            </li>
          ))}
        </ul>
      </SectionCard>

      <SectionCard title="Completed Finals matches">
        <ul className="item-list" aria-label="Canonical Finals match results">
          {result.matches.map((match) => (
            <li key={match.match_id}>
              {match.match_id} · {match.draw_type} R{match.round_number} · {match.winner_player_id}
              {match.loser_player_id ? ` def. ${match.loser_player_id}` : ''} · {match.scoreline}
            </li>
          ))}
        </ul>
      </SectionCard>
    </>
  )
}

function useCanonicalFinals(runId: string) {
  return useQuery({
    queryKey: ['viewer-canonical-finals', runId],
    queryFn: () => getViewerFinals(runId),
    enabled: Boolean(runId),
    retry: false
  })
}

function latestSeason(queryData: Awaited<ReturnType<typeof getViewerFinals>> | undefined): ViewerFinalsSeason | null {
  if (!queryData?.seasons.length) return null
  return queryData.seasons[queryData.seasons.length - 1]
}

export function ViewerRunFinalsPage(): JSX.Element {
  const { productRunId: runId } = useViewerProductRunRouteContext()
  const query = useCanonicalFinals(runId)
  const season = latestSeason(query.data)

  return (
    <section className="panel">
      <RunScopedHeader
        title="World Tour Finals"
        runId={runId}
        subtitle="Canonical saved Finals qualification and result for the selected Viewer Branch."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Viewer Branch', value: query.data?.viewer_branch_id ?? '—' },
          { label: 'Latest Finals season', value: season ? seasonLabel(season.target_season_index) : '—' },
          { label: 'Qualification', value: season?.selection_published ? 'Published' : 'Pending' },
          { label: 'Result', value: season?.result_published ? 'Published' : 'Pending' }
        ]}
      />

      <SectionCard title="Finals Summary">
        {query.isLoading ? <p className="status">Loading canonical Finals history…</p> : null}
        {query.error ? <p className="error">Failed to load canonical Finals history: {formatApiError(query.error)}</p> : null}
        {query.data && !season ? <EmptyState message="No canonical World Tour Finals season has been published for this Viewer Branch yet." /> : null}
        {season ? (
          <MetadataList
            items={[
              { label: 'Season', value: seasonLabel(season.target_season_index) },
              { label: 'Race cutoff', value: `${seasonLabel(season.race_cutoff_season_index)} · W${season.race_cutoff_week}` },
              { label: 'Finals event', value: season.finals_event_id ?? 'Selection pending' },
              { label: 'Participant capacity', value: season.participant_capacity ?? 'Pending' },
              { label: 'Current participants', value: season.participants.length },
              { label: 'Result publication', value: season.result_published ? 'Published' : 'Not published' }
            ]}
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Qualification">
        {season?.selection_published ? (
          <FinalsParticipantsTable runId={runId} season={season} />
        ) : season ? (
          <EmptyState message="Finals participant selection has not been published for this saved season yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Result">
        {season ? <FinalsResultSummary runId={runId} season={season} /> : null}
      </SectionCard>

      <SectionCard title="Saved Finals history">
        {query.data && query.data.seasons.length ? (
          <ul className="item-list" aria-label="Canonical Finals season history">
            {[...query.data.seasons].reverse().map((item) => (
              <li key={item.target_season_index}>
                <strong>{seasonLabel(item.target_season_index)}</strong>
                {' · '}
                {item.selection_published ? `${item.participants.length} participants` : 'selection pending'}
                {' · '}
                {item.result_published ? `champion ${item.result?.champion_player_id ?? '—'}` : 'result pending'}
              </li>
            ))}
          </ul>
        ) : null}
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
  const query = useCanonicalFinals(runId)
  const season = latestSeason(query.data)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Finals Qualification"
        runId={runId}
        subtitle="Canonical effective Finals participant field from the selected Viewer Branch Saved Revision."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Season', value: season ? seasonLabel(season.target_season_index) : '—' },
          { label: 'Race cutoff', value: season ? `W${season.race_cutoff_week}` : '—' },
          { label: 'Qualification', value: season?.selection_published ? 'Published' : 'Pending' }
        ]}
      />

      <SectionCard title="Qualification Summary">
        {query.isLoading ? <p className="status">Loading canonical Finals qualification…</p> : null}
        {query.error ? <p className="error">Failed to load canonical Finals qualification: {formatApiError(query.error)}</p> : null}
        {query.data && !season ? <EmptyState message="No canonical World Tour Finals season has been published for this Viewer Branch yet." /> : null}
        {season ? (
          <MetadataList
            items={[
              { label: 'Season', value: seasonLabel(season.target_season_index) },
              { label: 'Finals event', value: season.finals_event_id ?? 'Selection pending' },
              { label: 'Participant capacity', value: season.participant_capacity ?? 'Pending' },
              { label: 'Current participant count', value: season.participants.length }
            ]}
          />
        ) : null}
      </SectionCard>

      <SectionCard title="Qualified / confirmed participants">
        {season?.selection_published ? (
          <FinalsParticipantsTable runId={runId} season={season} />
        ) : season ? (
          <EmptyState message="Finals participant selection has not been published for this saved season yet." />
        ) : null}
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
  const query = useCanonicalFinals(runId)
  const season = latestSeason(query.data)
  const result = season?.result ?? null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Finals Result"
        runId={runId}
        subtitle="Canonical World Tour Finals sporting result from the selected Viewer Branch Saved Revision."
      />
      <CurrentContextStrip
        items={[
          { label: 'Active run', value: runId || 'unknown' },
          { label: 'Season', value: season ? seasonLabel(season.target_season_index) : '—' },
          { label: 'Finals event', value: season?.finals_event_id ?? '—' },
          { label: 'Result', value: result ? 'Published' : 'Pending' }
        ]}
      />

      <SectionCard title="Finals Result Summary">
        {query.isLoading ? <p className="status">Loading canonical Finals result…</p> : null}
        {query.error ? <p className="error">Failed to load canonical Finals result: {formatApiError(query.error)}</p> : null}
        {query.data && !season ? <EmptyState message="No canonical World Tour Finals season has been published for this Viewer Branch yet." /> : null}
        {season ? <FinalsResultSummary runId={runId} season={season} /> : null}
      </SectionCard>

      {result ? <FinalsResultDetails runId={runId} result={result} /> : null}

      <SectionCard title="Source Links">
        {season?.finals_event_id ? (
          <ul className="item-list" aria-label="Canonical Finals source links">
            <li><Link to={viewerTournamentDetailPath(runId, season.finals_event_id)}>Tournament detail {season.finals_event_id}</Link></li>
            <li><Link to={viewerRacePath(runId)}>Race to Finals</Link></li>
          </ul>
        ) : (
          <EmptyState message="Finals event identity has not been published for this saved season yet." />
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
