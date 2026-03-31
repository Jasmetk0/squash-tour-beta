import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import {
  getLatestRollover,
  getNextSeasonPlayers,
  getPlayerTransitions,
  getRolloverBySeason,
  rolloverNextSeason
} from '../api/client'
import { ActionStatusBlock, JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

export function RolloverPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const [seasonInput, setSeasonInput] = useState('')
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null)

  const latestQuery = useQuery({
    queryKey: ['rollover-latest', runId],
    queryFn: () => getLatestRollover(runId),
    enabled: Boolean(runId),
    retry: false
  })

  useEffect(() => {
    const latestSeason = latestQuery.data?.rollover.to_season
    if (latestSeason !== undefined && selectedSeason === null) {
      setSelectedSeason(latestSeason)
      setSeasonInput(String(latestSeason))
    }
  }, [latestQuery.data, selectedSeason])

  const seasonSummaryQuery = useQuery({
    queryKey: ['rollover-by-season', runId, selectedSeason],
    queryFn: () => getRolloverBySeason(runId, selectedSeason ?? 0),
    enabled: Boolean(runId && selectedSeason !== null),
    retry: false
  })

  const transitionsQuery = useQuery({
    queryKey: ['rollover-transitions', runId, selectedSeason],
    queryFn: () => getPlayerTransitions(runId, selectedSeason ?? 0),
    enabled: Boolean(runId && selectedSeason !== null)
  })

  const playersQuery = useQuery({
    queryKey: ['rollover-next-season-players', runId, selectedSeason],
    queryFn: () => getNextSeasonPlayers(runId, selectedSeason ?? 0),
    enabled: Boolean(runId && selectedSeason !== null)
  })

  const rolloverAction = useMutation({
    mutationFn: () => rolloverNextSeason(runId),
    onSuccess: async (response) => {
      const toSeason = response.rollover.to_season
      setSelectedSeason(toSeason)
      setSeasonInput(String(toSeason))

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['rollover-latest', runId] }),
        queryClient.invalidateQueries({ queryKey: ['rollover-by-season', runId] }),
        queryClient.invalidateQueries({ queryKey: ['rollover-transitions', runId] }),
        queryClient.invalidateQueries({ queryKey: ['rollover-next-season-players', runId] })
      ])
    }
  })

  const submitSeason = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const parsed = Number(seasonInput)
    if (Number.isInteger(parsed) && parsed > 0) {
      setSelectedSeason(parsed)
    }
  }

  const latestNotFound = isApiNotFound(latestQuery.error)
  const seasonNotFound = isApiNotFound(seasonSummaryQuery.error)

  return (
    <section className="panel">
      <RunScopedHeader title="Season Rollover" runId={runId} />

      <SectionCard title="Latest rollover summary">
        {latestQuery.isLoading && <p className="status">Loading latest rollover...</p>}
        {latestNotFound && <p className="status">No rollover has been executed for this run yet.</p>}
        {latestQuery.error && !latestNotFound && (
          <p className="error">Failed to load latest rollover: {formatApiError(latestQuery.error)}</p>
        )}
        {latestQuery.data && (
          <dl className="kv-grid">
            <div>
              <dt>From season</dt>
              <dd>{latestQuery.data.rollover.from_season}</dd>
            </div>
            <div>
              <dt>To season</dt>
              <dd>{latestQuery.data.rollover.to_season}</dd>
            </div>
            <div>
              <dt>Transitioned players</dt>
              <dd>{latestQuery.data.rollover.transitioned_players}</dd>
            </div>
          </dl>
        )}
      </SectionCard>

      <SectionCard title="Rollover actions">
        <div className="actions">
          <button onClick={() => rolloverAction.mutate()} disabled={!runId || rolloverAction.isPending}>
            {rolloverAction.isPending ? 'Rolling over...' : 'Roll over to next season'}
          </button>
        </div>
        <ActionStatusBlock
          errorText={rolloverAction.error ? `Could not execute rollover: ${formatApiError(rolloverAction.error)}` : undefined}
          successText={
            rolloverAction.data
              ? `Rollover complete for season ${rolloverAction.data.rollover.to_season}${
                  rolloverAction.data.rollover.already_persisted ? ' (already persisted)' : ''
                }.`
              : undefined
          }
        />
      </SectionCard>

      <SectionCard title="Inspect target season">
        <form className="actions" onSubmit={submitSeason}>
          <label>
            To season
            <input
              type="number"
              value={seasonInput}
              onChange={(event) => setSeasonInput(event.target.value)}
              placeholder="Enter target season"
              aria-label="To season"
            />
          </label>
          <button type="submit">Load season data</button>
        </form>
        {selectedSeason === null && <p className="status">Select a season to inspect rollover payloads.</p>}
      </SectionCard>

      {selectedSeason !== null && (
        <>
          <SectionCard title={`Season summary (S${selectedSeason})`}>
            {seasonSummaryQuery.isLoading && <p className="status">Loading rollover summary...</p>}
            {seasonNotFound && <p className="status">No rollover summary found for season {selectedSeason}.</p>}
            {seasonSummaryQuery.error && !seasonNotFound && (
              <p className="error">Failed to load rollover summary: {formatApiError(seasonSummaryQuery.error)}</p>
            )}
            {seasonSummaryQuery.data && (
              <dl className="kv-grid">
                <div>
                  <dt>From season</dt>
                  <dd>{seasonSummaryQuery.data.rollover.from_season}</dd>
                </div>
                <div>
                  <dt>To season</dt>
                  <dd>{seasonSummaryQuery.data.rollover.to_season}</dd>
                </div>
                <div>
                  <dt>Transitioned players</dt>
                  <dd>{seasonSummaryQuery.data.rollover.transitioned_players}</dd>
                </div>
              </dl>
            )}
          </SectionCard>

          <SectionCard title="Transition metadata and payload">
            {transitionsQuery.isLoading && <p className="status">Loading transitions...</p>}
            {transitionsQuery.error && <p className="error">Failed to load transitions: {formatApiError(transitionsQuery.error)}</p>}
            {transitionsQuery.data && (
              <>
                <p className="status">Transition records: {transitionsQuery.data.transitions.length}</p>
                <JsonPayloadBlock
                  title="Transition payload"
                  payload={transitionsQuery.data.transitions}
                  emptyText="No transition payload available."
                />
              </>
            )}
          </SectionCard>

          <SectionCard title="Next-season players payload">
            {playersQuery.isLoading && <p className="status">Loading next-season players...</p>}
            {playersQuery.error && <p className="error">Failed to load next-season players: {formatApiError(playersQuery.error)}</p>}
            {playersQuery.data && (
              <>
                <p className="status">Player records: {playersQuery.data.players.length}</p>
                <JsonPayloadBlock
                  title="Players payload"
                  payload={playersQuery.data.players}
                  emptyText="No next-season player payload available."
                />
              </>
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}
