import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import {
  ApiError,
  getFinalsQualification,
  getFinalsResult,
  getFinalsSummary,
  simulateWorldTourFinals
} from '../api/client'

function extractReadableError(error: unknown): string {
  if (error instanceof ApiError) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: string }
      if (parsed.detail) return parsed.detail
    } catch {
      // Fallback to raw API error message when body is not JSON
    }
    return error.message
  }

  if (error instanceof Error) return error.message
  return String(error)
}

export function FinalsPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()

  const summaryQuery = useQuery({ queryKey: ['finals-summary', runId], queryFn: () => getFinalsSummary(runId), enabled: Boolean(runId) })
  const qualificationQuery = useQuery({
    queryKey: ['finals-qualification', runId],
    queryFn: () => getFinalsQualification(runId),
    enabled: Boolean(runId)
  })
  const resultQuery = useQuery({
    queryKey: ['finals-result', runId],
    queryFn: () => getFinalsResult(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const finalsSimulator = useMutation({
    mutationFn: () => simulateWorldTourFinals(runId),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['events', runId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-snapshots', runId] }),
        queryClient.invalidateQueries({ queryKey: ['race-snapshots', runId] }),
        queryClient.invalidateQueries({ queryKey: ['finals-summary', runId] }),
        queryClient.invalidateQueries({ queryKey: ['finals-qualification', runId] }),
        queryClient.invalidateQueries({ queryKey: ['finals-result', runId] })
      ])
    }
  })

  const isLoading = summaryQuery.isLoading || qualificationQuery.isLoading

  return (
    <section className="panel">
      <h2>World Tour Finals</h2>
      <p className="status">Run: {runId || 'unknown'}</p>

      <div className="actions">
        <button onClick={() => finalsSimulator.mutate()} disabled={!runId || finalsSimulator.isPending}>
          {finalsSimulator.isPending ? 'Simulating Finals...' : 'Simulate World Tour Finals'}
        </button>
      </div>
      {finalsSimulator.error && (
        <p className="error">Could not simulate Finals: {extractReadableError(finalsSimulator.error)}</p>
      )}
      {finalsSimulator.data && (
        <p className="status">
          Finals simulation complete{finalsSimulator.data.finals.already_simulated ? ' (already simulated)' : ''}.
        </p>
      )}

      {isLoading && <p>Loading Finals data...</p>}
      {summaryQuery.error && <p className="error">Failed to load Finals summary: {extractReadableError(summaryQuery.error)}</p>}
      {qualificationQuery.error && (
        <p className="error">Failed to load Finals qualification: {extractReadableError(qualificationQuery.error)}</p>
      )}

      {summaryQuery.data && (
        <article className="panel nested-panel">
          <h3>Finals summary</h3>
          <dl className="kv-grid">
            <div>
              <dt>Run ID</dt>
              <dd>{summaryQuery.data.run_id}</dd>
            </div>
            <div>
              <dt>Season</dt>
              <dd>{summaryQuery.data.season}</dd>
            </div>
            <div>
              <dt>Qualification status</dt>
              <dd>{summaryQuery.data.qualification ? 'Available' : 'Unavailable'}</dd>
            </div>
            <div>
              <dt>Result status</dt>
              <dd>{summaryQuery.data.result ? 'Available' : 'Not simulated yet'}</dd>
            </div>
          </dl>
        </article>
      )}

      <article className="panel nested-panel">
        <h3>Finals qualification</h3>
        {qualificationQuery.data ? (
          <>
            <p className="status">
              As of S{qualificationQuery.data.source_as_of_season}, W{qualificationQuery.data.source_as_of_week}
            </p>
            <pre className="json-block">{JSON.stringify(qualificationQuery.data.qualification, null, 2)}</pre>
          </>
        ) : (
          !qualificationQuery.isLoading && <p className="status">No qualification data available.</p>
        )}
      </article>

      <article className="panel nested-panel">
        <h3>Finals result</h3>
        {resultQuery.error && <p className="status">Finals result not available yet.</p>}
        {resultQuery.data ? (
          <>
            <p className="status">
              Event: {resultQuery.data.event_id} · As of S{resultQuery.data.source_as_of_season}, W
              {resultQuery.data.source_as_of_week}
            </p>
            <pre className="json-block">{JSON.stringify(resultQuery.data.result, null, 2)}</pre>
          </>
        ) : null}
      </article>
    </section>
  )
}
