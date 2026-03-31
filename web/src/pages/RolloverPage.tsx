import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import {
  ApiError,
  getLatestRollover,
  getNextSeasonPlayers,
  getPlayerTransitions,
  getRolloverBySeason,
  rolloverNextSeason
} from '../api/client'

function extractReadableError(error: unknown): string {
  if (error instanceof ApiError) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: string }
      if (parsed.detail) return parsed.detail
    } catch {
      // Fall back to raw error text when body is not JSON
    }
    return error.message
  }

  if (error instanceof Error) return error.message
  return String(error)
}

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

  const latestNotFound = latestQuery.error instanceof ApiError && latestQuery.error.status === 404
  const seasonNotFound = seasonSummaryQuery.error instanceof ApiError && seasonSummaryQuery.error.status === 404

  return (
    <section className="panel">
      <h2>Season rollover</h2>
      <p className="status">Run: {runId || 'unknown'}</p>

      <article className="panel nested-panel">
        <h3>Latest rollover summary</h3>
        {latestQuery.isLoading && <p className="status">Loading latest rollover...</p>}
        {latestNotFound && <p className="status">No rollover has been executed for this run yet.</p>}
        {latestQuery.error && !latestNotFound && (
          <p className="error">Failed to load latest rollover: {extractReadableError(latestQuery.error)}</p>
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
      </article>

      <article className="panel nested-panel">
        <h3>Rollover actions</h3>
        <div className="actions">
          <button onClick={() => rolloverAction.mutate()} disabled={!runId || rolloverAction.isPending}>
            {rolloverAction.isPending ? 'Rolling over...' : 'Roll over to next season'}
          </button>
        </div>
        {rolloverAction.data && (
          <p className="status">
            Rollover complete for season {rolloverAction.data.rollover.to_season}
            {rolloverAction.data.rollover.already_persisted ? ' (already persisted)' : ''}.
          </p>
        )}
        {rolloverAction.error && (
          <p className="error">Could not execute rollover: {extractReadableError(rolloverAction.error)}</p>
        )}
      </article>

      <article className="panel nested-panel">
        <h3>Inspect target season</h3>
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
      </article>

      {selectedSeason !== null && (
        <>
          <article className="panel nested-panel">
            <h3>Season summary (S{selectedSeason})</h3>
            {seasonSummaryQuery.isLoading && <p className="status">Loading rollover summary...</p>}
            {seasonNotFound && <p className="status">No rollover summary found for season {selectedSeason}.</p>}
            {seasonSummaryQuery.error && !seasonNotFound && (
              <p className="error">Failed to load rollover summary: {extractReadableError(seasonSummaryQuery.error)}</p>
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
          </article>

          <article className="panel nested-panel">
            <h3>Transition metadata and payload</h3>
            {transitionsQuery.isLoading && <p className="status">Loading transitions...</p>}
            {transitionsQuery.error && (
              <p className="error">Failed to load transitions: {extractReadableError(transitionsQuery.error)}</p>
            )}
            {transitionsQuery.data && (
              <>
                <p className="status">Transition records: {transitionsQuery.data.transitions.length}</p>
                <pre className="json-block">{JSON.stringify(transitionsQuery.data.transitions, null, 2)}</pre>
              </>
            )}
          </article>

          <article className="panel nested-panel">
            <h3>Next-season players payload</h3>
            {playersQuery.isLoading && <p className="status">Loading next-season players...</p>}
            {playersQuery.error && (
              <p className="error">Failed to load next-season players: {extractReadableError(playersQuery.error)}</p>
            )}
            {playersQuery.data && (
              <>
                <p className="status">Player records: {playersQuery.data.players.length}</p>
                <pre className="json-block">{JSON.stringify(playersQuery.data.players, null, 2)}</pre>
              </>
            )}
          </article>
        </>
      )}
    </section>
  )
}
