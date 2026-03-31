import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getFinalsSummary,
  getLatestRollover,
  getRun,
  getRunLineage,
  getRunSource,
  rolloverNextSeason,
  simulateFullSeason,
  simulateNextTournament,
  simulateNextWeek,
  simulateWorldTourFinals
} from '../api/client'
import { ActionStatusBlock, EmptyState, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

export function RunPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()

  const invalidateRunDetailQueries = async (): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['run', runId] }),
      queryClient.invalidateQueries({ queryKey: ['events', runId] }),
      queryClient.invalidateQueries({ queryKey: ['ranking-snapshots', runId] }),
      queryClient.invalidateQueries({ queryKey: ['race-snapshots', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-summary', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-qualification', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-result', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-latest', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-by-season', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-transitions', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-next-season-players', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-source', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-lineage', runId] })
    ])
  }

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const finalsSummaryQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const latestRolloverQuery = useQuery({
    queryKey: ['rollover-latest', runId],
    queryFn: () => getLatestRollover(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const sourceQuery = useQuery({
    queryKey: ['run-source', runId],
    queryFn: () => getRunSource(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const lineageQuery = useQuery({
    queryKey: ['run-lineage', runId],
    queryFn: () => getRunLineage(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const finalsQuickAction = useMutation({
    mutationFn: () => simulateWorldTourFinals(runId),
    onSuccess: async () => {
      await invalidateRunDetailQueries()
    }
  })

  const rolloverQuickAction = useMutation({
    mutationFn: () => rolloverNextSeason(runId),
    onSuccess: async () => {
      await invalidateRunDetailQueries()
    }
  })

  const simulator = useMutation({
    mutationFn: async (mode: 'next-tournament' | 'next-week' | 'full-season') => {
      if (mode === 'next-tournament') return simulateNextTournament(runId)
      if (mode === 'next-week') return simulateNextWeek(runId)
      return simulateFullSeason(runId)
    },
    onSuccess: async () => {
      await invalidateRunDetailQueries()
    }
  })

  return (
    <section className="panel">
      <PageIntro title="Run detail" subtitle="Review run status, execute quick actions, and navigate to detailed run views." />
      {runQuery.isLoading && <p className="status">Loading run...</p>}
      {runQuery.error && <p className="error">Failed to load run: {String(runQuery.error)}</p>}
      {runQuery.data && (
        <>
          <MetadataList
            items={[
              { label: 'Run ID', value: runQuery.data.run.run_id },
              { label: 'Season', value: runQuery.data.run.season },
              { label: 'Seed', value: runQuery.data.run.seed },
              { label: 'Progress', value: `${runQuery.data.run.next_event_index} / ${runQuery.data.run.total_events}` },
              { label: 'Completed event IDs', value: runQuery.data.run.completed_event_ids.length }
            ]}
          />

          <SectionCard title="World Tour Finals overview">
            {finalsSummaryQuery.isLoading && <p className="status">Loading Finals status...</p>}
            {finalsSummaryQuery.error && (
              <p className="error">Failed to load Finals summary: {formatApiError(finalsSummaryQuery.error)}</p>
            )}
            {finalsSummaryQuery.data && (
              <MetadataList
                items={[
                  { label: 'Qualification', value: finalsSummaryQuery.data.qualification ? 'Available' : 'Not generated yet' },
                  { label: 'Finals result', value: finalsSummaryQuery.data.result ? 'Available' : 'Not simulated yet' }
                ]}
              />
            )}
            <div className="actions">
              <button onClick={() => finalsQuickAction.mutate()} disabled={!runId || finalsQuickAction.isPending}>
                {finalsQuickAction.isPending ? 'Simulating Finals...' : 'Simulate World Tour Finals'}
              </button>
            </div>
            <ActionStatusBlock
              isLoading={finalsQuickAction.isPending}
              loadingText="Simulating World Tour Finals..."
              errorText={
                finalsQuickAction.error ? `Could not simulate Finals: ${formatApiError(finalsQuickAction.error)}` : undefined
              }
              successText={
                finalsQuickAction.data
                  ? `Finals simulation complete${finalsQuickAction.data.finals.already_simulated ? ' (already simulated)' : ''}.`
                  : undefined
              }
            />
            <p>
              <Link to={`/runs/${runId}/finals`}>View World Tour Finals</Link>
            </p>
          </SectionCard>

          <SectionCard title="Latest rollover overview">
            {latestRolloverQuery.isLoading && <p className="status">Loading latest rollover...</p>}
            {isApiNotFound(latestRolloverQuery.error) && <p className="status">No rollover yet for this run.</p>}
            {latestRolloverQuery.error && !isApiNotFound(latestRolloverQuery.error) && (
              <p className="error">Failed to load latest rollover: {formatApiError(latestRolloverQuery.error)}</p>
            )}
            {latestRolloverQuery.data && (
              <MetadataList
                items={[
                  { label: 'From season', value: latestRolloverQuery.data.rollover.from_season },
                  { label: 'To season', value: latestRolloverQuery.data.rollover.to_season },
                  { label: 'Transitioned players', value: latestRolloverQuery.data.rollover.transitioned_players }
                ]}
              />
            )}
            <div className="actions">
              <button onClick={() => rolloverQuickAction.mutate()} disabled={!runId || rolloverQuickAction.isPending}>
                {rolloverQuickAction.isPending ? 'Rolling over...' : 'Roll over to next season'}
              </button>
            </div>
            <ActionStatusBlock
              isLoading={rolloverQuickAction.isPending}
              loadingText="Rolling over to next season..."
              errorText={
                rolloverQuickAction.error
                  ? `Could not execute rollover: ${formatApiError(rolloverQuickAction.error)}`
                  : undefined
              }
              successText={
                rolloverQuickAction.data
                  ? `Rollover complete for season ${rolloverQuickAction.data.rollover.to_season}${
                      rolloverQuickAction.data.rollover.already_persisted ? ' (already persisted)' : ''
                    }.`
                  : undefined
              }
            />
            <p>
              <Link to={`/runs/${runId}/rollover`}>View season rollover</Link>
            </p>
          </SectionCard>

          <SectionCard title="Run source and lineage overview">
            {(sourceQuery.isLoading || lineageQuery.isLoading) && <p className="status">Loading source and lineage...</p>}
            {sourceQuery.error && !isApiNotFound(sourceQuery.error) && (
              <p className="error">Failed to load run source: {formatApiError(sourceQuery.error)}</p>
            )}
            {lineageQuery.error && !isApiNotFound(lineageQuery.error) && (
              <p className="error">Failed to load run lineage: {formatApiError(lineageQuery.error)}</p>
            )}
            {sourceQuery.data && (
              <MetadataList
                items={[
                  { label: 'Source type', value: sourceQuery.data.source.source_type || 'Unknown' },
                  {
                    label: 'Parent run',
                    value: sourceQuery.data.source.parent_run_id ? (
                      <Link to={`/runs/${sourceQuery.data.source.parent_run_id}`}>{sourceQuery.data.source.parent_run_id}</Link>
                    ) : (
                      'No parent run'
                    )
                  },
                  { label: 'Child run count', value: lineageQuery.data?.lineage.children.length ?? 0 }
                ]}
              />
            )}
            {!sourceQuery.data && isApiNotFound(sourceQuery.error) && (
              <p className="status">No source metadata available for this run.</p>
            )}
            {lineageQuery.data && lineageQuery.data.lineage.children.length > 0 && (
              <ul>
                {lineageQuery.data.lineage.children.map((childRunId) => (
                  <li key={childRunId}>
                    <Link to={`/runs/${childRunId}`}>{childRunId}</Link>
                  </li>
                ))}
              </ul>
            )}
            {lineageQuery.data && lineageQuery.data.lineage.children.length === 0 && (
              <EmptyState message="No child runs created yet." />
            )}
            {!lineageQuery.data && isApiNotFound(lineageQuery.error) && (
              <EmptyState message="No lineage metadata available for this run." />
            )}
            <p>
              <Link to={`/runs/${runId}/bootstrap-lineage`}>View bootstrap and lineage</Link>
            </p>
          </SectionCard>

          <SectionCard title="Simulation controls">
            <div className="actions">
              <button onClick={() => simulator.mutate('next-tournament')}>Simulate next tournament</button>
              <button onClick={() => simulator.mutate('next-week')}>Simulate next week</button>
              <button onClick={() => simulator.mutate('full-season')}>Simulate full season</button>
            </div>
            <ActionStatusBlock
              errorText={simulator.error ? `Simulation failed: ${formatApiError(simulator.error)}` : undefined}
            />
            {simulator.data && (
              <pre className="json-block" aria-label="simulation-result">
                {JSON.stringify(simulator.data.step, null, 2)}
              </pre>
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}
