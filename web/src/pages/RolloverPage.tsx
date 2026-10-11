import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import {
  getLatestRollover,
  getNextSeasonPlayers,
  getPlayerTransitions,
  getRolloverBySeason,
  getRunStatusSummary,
  rolloverNextSeason
} from '../api/client'
import {
  ActionStatusBlock,
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

function RunBridgeLinks({ runId }: { runId: string }): JSX.Element {
  return (
    <p>
      <Link to={`/runs/${runId}`}>Run Detail</Link> · <Link to={`/runs/${runId}/diagnostics`}>Diagnostics</Link> ·{' '}
      <Link to={`/runs/${runId}/season-chain`}>Season Chain</Link>
    </p>
  )
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

  const statusSummaryQuery = useQuery({
    queryKey: ['run-status-summary', runId],
    queryFn: () => getRunStatusSummary(runId),
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
    enabled: Boolean(runId && selectedSeason !== null),
    retry: false
  })

  const playersQuery = useQuery({
    queryKey: ['rollover-next-season-players', runId, selectedSeason],
    queryFn: () => getNextSeasonPlayers(runId, selectedSeason ?? 0),
    enabled: Boolean(runId && selectedSeason !== null),
    retry: false
  })

  const rolloverAction = useMutation({
    mutationFn: () => rolloverNextSeason(runId),
    onSuccess: async (response) => {
      const toSeason = response.rollover.to_season
      setSelectedSeason(toSeason)
      setSeasonInput(String(toSeason))

      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-status-summary', runId] }),
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
  const transitionsNotFound = isApiNotFound(transitionsQuery.error)
  const playersNotFound = isApiNotFound(playersQuery.error)

  const transitionCount = transitionsQuery.data?.transitions.length ?? 0
  const nextSeasonPlayerCount = playersQuery.data?.players.length ?? 0
  const contextSeason = selectedSeason ?? latestQuery.data?.rollover.to_season ?? '—'

  const latestToSeason = latestQuery.data?.rollover.to_season ?? null
  const latestDetailHref = latestToSeason ? `/runs/${runId}/rollover/${latestToSeason}` : null

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Rollover"
        runId={runId}
        subtitle="Rollover overview/browser with compact season-level inspection and rollover execution access."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Latest rollover', value: latestToSeason ? `S${latestToSeason}` : 'None yet' },
          { label: 'Inspected season', value: contextSeason },
          {
            label: 'Season progress',
            value: statusSummaryQuery.data
              ? `${statusSummaryQuery.data.progress.next_event_index} / ${statusSummaryQuery.data.progress.total_events}`
              : '—'
          }
        ]}
      />

      <SectionCard title="Current run bridge navigation">
        <RunBridgeLinks runId={runId} />
      </SectionCard>

      <SectionCard title="Latest rollover summary">
        {latestQuery.isLoading && <p className="status">Loading latest rollover...</p>}
        {latestNotFound && <EmptyState message="No rollover has been executed for this run yet." />}
        {latestQuery.error && !latestNotFound && (
          <p className="error">Failed to load latest rollover: {formatApiError(latestQuery.error)}</p>
        )}
        {latestQuery.data && (
          <>
            <SummaryPills
              items={[
                { label: 'From season', value: latestQuery.data.rollover.from_season },
                { label: 'To season', value: latestQuery.data.rollover.to_season },
                { label: 'Transitioned players', value: latestQuery.data.rollover.transitioned_players },
                { label: 'Transition records', value: transitionsQuery.isLoading ? 'Loading...' : transitionCount },
                { label: 'Next-season players', value: playersQuery.isLoading ? 'Loading...' : nextSeasonPlayerCount }
              ]}
            />
            <MetadataList
              items={[
                { label: 'Run ID', value: latestQuery.data.rollover.run_id },
                {
                  label: 'Open rollover season detail',
                  value: <Link to={`/runs/${runId}/rollover/${latestQuery.data.rollover.to_season}`}>Open rollover season detail</Link>
                }
              ]}
            />
          </>
        )}
      </SectionCard>

      <SectionCard title="Inspect target rollover season">
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
        {selectedSeason === null && <EmptyState message="No rollover yet. Enter a target season to inspect if persisted." />}
        {selectedSeason !== null ? (
          <p>
            <Link to={`/runs/${runId}/rollover/${selectedSeason}`}>Open rollover season detail</Link>
          </p>
        ) : null}
      </SectionCard>

      {selectedSeason !== null && (
        <>
          <SectionCard title={`Rollover season summary (S${selectedSeason})`}>
            {seasonSummaryQuery.isLoading && <p className="status">Loading rollover summary...</p>}
            {seasonNotFound && <EmptyState message={`No rollover summary found for season ${selectedSeason}.`} />}
            {seasonSummaryQuery.error && !seasonNotFound && (
              <p className="error">Failed to load rollover summary: {formatApiError(seasonSummaryQuery.error)}</p>
            )}
            {seasonSummaryQuery.data && (
              <CompactSummaryCard
                items={[
                  { label: 'Run ID', value: seasonSummaryQuery.data.rollover.run_id },
                  { label: 'From season', value: seasonSummaryQuery.data.rollover.from_season },
                  { label: 'To season', value: seasonSummaryQuery.data.rollover.to_season },
                  { label: 'Transitioned players', value: seasonSummaryQuery.data.rollover.transitioned_players }
                ]}
              />
            )}
          </SectionCard>

          <SectionCard title="Transitions summary">
            {transitionsQuery.isLoading && <p className="status">Loading transitions...</p>}
            {transitionsNotFound && <EmptyState message={`No transitions payload found for season ${selectedSeason}.`} />}
            {transitionsQuery.error && !transitionsNotFound && (
              <p className="error">Failed to load transitions: {formatApiError(transitionsQuery.error)}</p>
            )}
            {transitionsQuery.data && (
              <>
                {transitionsQuery.data.transitions.length === 0 ? (
                  <EmptyState message="No transition records are available for this target season." />
                ) : (
                  <MetadataList
                    items={[
                      { label: 'Run ID', value: transitionsQuery.data.run_id },
                      { label: 'To season', value: transitionsQuery.data.to_season },
                      { label: 'Transition records', value: transitionsQuery.data.transitions.length }
                    ]}
                  />
                )}
              </>
            )}
          </SectionCard>

          <SectionCard title="Next-season players summary">
            {playersQuery.isLoading && <p className="status">Loading next-season players...</p>}
            {playersNotFound && <EmptyState message={`No next-season players payload found for season ${selectedSeason}.`} />}
            {playersQuery.error && !playersNotFound && (
              <p className="error">Failed to load next-season players: {formatApiError(playersQuery.error)}</p>
            )}
            {playersQuery.data && (
              <>
                {playersQuery.data.players.length === 0 ? (
                  <EmptyState message="No next-season players are available for this target season." />
                ) : (
                  <MetadataList
                    items={[
                      { label: 'Run ID', value: playersQuery.data.run_id },
                      { label: 'To season', value: playersQuery.data.to_season },
                      { label: 'Player records', value: playersQuery.data.players.length }
                    ]}
                  />
                )}
              </>
            )}
          </SectionCard>
        </>
      )}

      <SectionCard title="Most relevant next inspections">
        <ul className="item-list" aria-label="Most relevant next inspections">
          {latestDetailHref ? (
            <li>
              <Link to={latestDetailHref}>Inspect latest rollover season detail</Link>
            </li>
          ) : (
            <li>
              <Link to={`/runs/${runId}/bootstrap-lineage`}>Inspect bootstrap / lineage (no rollover yet)</Link>
            </li>
          )}
          <li>
            <Link to={`/runs/${runId}/season-chain`}>Inspect season chain</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/diagnostics`}>Inspect run diagnostics</Link>
          </li>
        </ul>
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
    </section>
  )
}
