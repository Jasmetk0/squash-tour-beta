import { useQuery } from '@tanstack/react-query'
import { ChangeEvent, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { getNextSeasonPlayers, getPlayerTransitions, getRolloverBySeason } from '../api/client'
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

function parseToSeasonParam(toSeasonParam: string | undefined): number | null {
  if (!toSeasonParam) return null
  const parsed = Number(toSeasonParam)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export function RolloverSeasonDetailPage(): JSX.Element {
  const { runId = '', toSeason: toSeasonParam } = useParams()
  const [playerIdFilter, setPlayerIdFilter] = useState('')

  const toSeason = parseToSeasonParam(toSeasonParam)

  const seasonSummaryQuery = useQuery({
    queryKey: ['rollover-by-season', runId, toSeason],
    queryFn: () => getRolloverBySeason(runId, toSeason ?? 0),
    enabled: Boolean(runId && toSeason !== null),
    retry: false
  })

  const transitionsQuery = useQuery({
    queryKey: ['rollover-transitions', runId, toSeason],
    queryFn: () => getPlayerTransitions(runId, toSeason ?? 0),
    enabled: Boolean(runId && toSeason !== null),
    retry: false
  })

  const playersQuery = useQuery({
    queryKey: ['rollover-next-season-players', runId, toSeason],
    queryFn: () => getNextSeasonPlayers(runId, toSeason ?? 0),
    enabled: Boolean(runId && toSeason !== null),
    retry: false
  })

  const normalizedFilter = playerIdFilter.trim().toLowerCase()

  const filteredTransitions = useMemo(() => {
    const transitions = transitionsQuery.data?.transitions ?? []
    if (!normalizedFilter) return transitions
    return transitions.filter((item) => item.player_id.toLowerCase().includes(normalizedFilter))
  }, [normalizedFilter, transitionsQuery.data])

  const filteredPlayers = useMemo(() => {
    const players = playersQuery.data?.players ?? []
    if (!normalizedFilter) return players
    return players.filter((item) => item.player_id.toLowerCase().includes(normalizedFilter))
  }, [normalizedFilter, playersQuery.data])

  const invalidSeasonParam = toSeason === null
  const seasonNotFound = isApiNotFound(seasonSummaryQuery.error)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Rollover season detail"
        runId={runId}
        subtitle="Read-only inspection for one rollover target season."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Target season', value: toSeason ?? 'Invalid' },
          { label: 'Filter', value: normalizedFilter || 'None' }
        ]}
      />

      <SectionCard title="Rollover season context">
        <MetadataList
          items={[
            { label: 'Overview', value: <Link to={`/runs/${runId}/rollover`}>Back to rollover overview</Link> },
            { label: 'Run', value: runId || 'unknown' },
            { label: 'To season parameter', value: toSeasonParam ?? 'missing' }
          ]}
        />
        {invalidSeasonParam ? <EmptyState message="Invalid or missing target season in URL. Use a positive integer season." /> : null}
      </SectionCard>

      {!invalidSeasonParam ? (
        <>
          <SectionCard title={`Rollover summary (S${toSeason})`}>
            {seasonSummaryQuery.isLoading && <p className="status">Loading rollover summary...</p>}
            {seasonNotFound && <EmptyState message={`No rollover summary found for season ${toSeason}.`} />}
            {seasonSummaryQuery.error && !seasonNotFound && (
              <p className="error">Failed to load rollover summary: {formatApiError(seasonSummaryQuery.error)}</p>
            )}
            {seasonSummaryQuery.data ? (
              <>
                <SummaryPills
                  items={[
                    { label: 'From season', value: seasonSummaryQuery.data.rollover.from_season },
                    { label: 'To season', value: seasonSummaryQuery.data.rollover.to_season },
                    { label: 'Transitioned players', value: seasonSummaryQuery.data.rollover.transitioned_players }
                  ]}
                />
                <CompactSummaryCard
                  items={[
                    { label: 'Run ID', value: seasonSummaryQuery.data.rollover.run_id },
                    {
                      label: 'Metadata keys',
                      value: Object.keys(seasonSummaryQuery.data.rollover.metadata ?? {}).length
                    }
                  ]}
                />
              </>
            ) : null}
          </SectionCard>

          <SectionCard title="Inspection summary">
            <SummaryPills
              items={[
                { label: 'Target season', value: toSeason },
                { label: 'Transition records', value: transitionsQuery.isLoading ? 'Loading...' : filteredTransitions.length },
                { label: 'Next-season players', value: playersQuery.isLoading ? 'Loading...' : filteredPlayers.length }
              ]}
            />
            <label>
              player_id filter
              <input
                type="text"
                value={playerIdFilter}
                onChange={(event: ChangeEvent<HTMLInputElement>) => setPlayerIdFilter(event.target.value)}
                placeholder="Filter by player_id"
                aria-label="player_id filter"
              />
            </label>
          </SectionCard>

          <SectionCard title="Player transitions">
            {transitionsQuery.isLoading && <p className="status">Loading transitions...</p>}
            {transitionsQuery.error && <p className="error">Failed to load transitions: {formatApiError(transitionsQuery.error)}</p>}
            {transitionsQuery.data ? (
              filteredTransitions.length === 0 ? (
                <EmptyState
                  message={normalizedFilter ? 'No transition records match the active player_id filter.' : 'No transition records are available for this season.'}
                />
              ) : (
                <JsonPayloadBlock title="Transitions payload" payload={filteredTransitions} emptyText="No transition payload available." />
              )
            ) : null}
          </SectionCard>

          <SectionCard title="Next-season players">
            {playersQuery.isLoading && <p className="status">Loading next-season players...</p>}
            {playersQuery.error && <p className="error">Failed to load next-season players: {formatApiError(playersQuery.error)}</p>}
            {playersQuery.data ? (
              filteredPlayers.length === 0 ? (
                <EmptyState
                  message={normalizedFilter ? 'No next-season players match the active player_id filter.' : 'No next-season players are available for this season.'}
                />
              ) : (
                <JsonPayloadBlock title="Next-season players payload" payload={filteredPlayers} emptyText="No player payload available." />
              )
            ) : null}
          </SectionCard>
        </>
      ) : null}
    </section>
  )
}
