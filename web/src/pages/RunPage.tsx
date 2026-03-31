import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getFinalsSummary,
  getLatestRollover,
  getRun,
  getRunLineage,
  getRunSource,
  simulateFullSeason,
  simulateNextTournament,
  simulateNextWeek
} from '../api/client'
import { SectionCard } from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

export function RunPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()

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

  const simulator = useMutation({
    mutationFn: async (mode: 'next-tournament' | 'next-week' | 'full-season') => {
      if (mode === 'next-tournament') return simulateNextTournament(runId)
      if (mode === 'next-week') return simulateNextWeek(runId)
      return simulateFullSeason(runId)
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['events', runId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-snapshots', runId] }),
        queryClient.invalidateQueries({ queryKey: ['race-snapshots', runId] }),
        queryClient.invalidateQueries({ queryKey: ['finals-summary', runId] }),
        queryClient.invalidateQueries({ queryKey: ['rollover-latest', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-source', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-lineage', runId] })
      ])
    }
  })

  return (
    <section className="panel">
      <h2>Run detail</h2>
      {runQuery.isLoading && <p>Loading run...</p>}
      {runQuery.error && <p className="error">Failed to load run: {String(runQuery.error)}</p>}
      {runQuery.data && (
        <>
          <dl className="kv-grid">
            <div>
              <dt>Run ID</dt>
              <dd>{runQuery.data.run.run_id}</dd>
            </div>
            <div>
              <dt>Season</dt>
              <dd>{runQuery.data.run.season}</dd>
            </div>
            <div>
              <dt>Seed</dt>
              <dd>{runQuery.data.run.seed}</dd>
            </div>
            <div>
              <dt>Progress</dt>
              <dd>
                {runQuery.data.run.next_event_index} / {runQuery.data.run.total_events}
              </dd>
            </div>
            <div>
              <dt>Completed event IDs</dt>
              <dd>{runQuery.data.run.completed_event_ids.length}</dd>
            </div>
          </dl>

          <SectionCard title="World Tour Finals overview">
            {finalsSummaryQuery.isLoading && <p className="status">Loading Finals status...</p>}
            {finalsSummaryQuery.error && (
              <p className="error">Failed to load Finals summary: {formatApiError(finalsSummaryQuery.error)}</p>
            )}
            {finalsSummaryQuery.data && (
              <dl className="kv-grid">
                <div>
                  <dt>Qualification</dt>
                  <dd>{finalsSummaryQuery.data.qualification ? 'Available' : 'Not generated yet'}</dd>
                </div>
                <div>
                  <dt>Finals result</dt>
                  <dd>{finalsSummaryQuery.data.result ? 'Available' : 'Not simulated yet'}</dd>
                </div>
              </dl>
            )}
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
              <dl className="kv-grid">
                <div>
                  <dt>From season</dt>
                  <dd>{latestRolloverQuery.data.rollover.from_season}</dd>
                </div>
                <div>
                  <dt>To season</dt>
                  <dd>{latestRolloverQuery.data.rollover.to_season}</dd>
                </div>
                <div>
                  <dt>Transitioned players</dt>
                  <dd>{latestRolloverQuery.data.rollover.transitioned_players}</dd>
                </div>
              </dl>
            )}
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
              <dl className="kv-grid">
                <div>
                  <dt>Source type</dt>
                  <dd>{sourceQuery.data.source.source_type || 'Unknown'}</dd>
                </div>
                <div>
                  <dt>Parent run</dt>
                  <dd>
                    {sourceQuery.data.source.parent_run_id ? (
                      <Link to={`/runs/${sourceQuery.data.source.parent_run_id}`}>
                        {sourceQuery.data.source.parent_run_id}
                      </Link>
                    ) : (
                      'No parent run'
                    )}
                  </dd>
                </div>
              </dl>
            )}
            {!sourceQuery.data && isApiNotFound(sourceQuery.error) && (
              <p className="status">No source metadata available for this run.</p>
            )}
            {lineageQuery.data && (
              <>
                <p className="status">Child runs: {lineageQuery.data.lineage.children.length}</p>
                {lineageQuery.data.lineage.children.length > 0 ? (
                  <ul>
                    {lineageQuery.data.lineage.children.map((childRunId) => (
                      <li key={childRunId}>
                        <Link to={`/runs/${childRunId}`}>{childRunId}</Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="status">No child runs created yet.</p>
                )}
              </>
            )}
            {!lineageQuery.data && isApiNotFound(lineageQuery.error) && (
              <p className="status">No lineage metadata available for this run.</p>
            )}
            <p>
              <Link to={`/runs/${runId}/bootstrap-lineage`}>View bootstrap and lineage</Link>
            </p>
          </SectionCard>

          <h3>Simulation controls</h3>
          <div className="actions">
            <button onClick={() => simulator.mutate('next-tournament')}>Simulate next tournament</button>
            <button onClick={() => simulator.mutate('next-week')}>Simulate next week</button>
            <button onClick={() => simulator.mutate('full-season')}>Simulate full season</button>
          </div>
          {simulator.error && <p className="error">Simulation failed: {String(simulator.error)}</p>}
          {simulator.data && (
            <pre className="json-block" aria-label="simulation-result">
              {JSON.stringify(simulator.data.step, null, 2)}
            </pre>
          )}
        </>
      )}
    </section>
  )
}
