import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import {
  getFinalsQualification,
  getFinalsResult,
  getFinalsSummary,
  simulateWorldTourFinals
} from '../api/client'
import { ActionStatusBlock, JsonPayloadBlock, RunScopedHeader, SectionCard } from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

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
  const qualificationNotFound = isApiNotFound(qualificationQuery.error)
  const resultNotFound = isApiNotFound(resultQuery.error)
  const hasResultError = resultQuery.error && !resultNotFound

  return (
    <section className="panel">
      <RunScopedHeader title="World Tour Finals" runId={runId} />

      <div className="actions">
        <button onClick={() => finalsSimulator.mutate()} disabled={!runId || finalsSimulator.isPending}>
          {finalsSimulator.isPending ? 'Simulating Finals...' : 'Simulate World Tour Finals'}
        </button>
      </div>
      <ActionStatusBlock
        errorText={finalsSimulator.error ? `Could not simulate Finals: ${formatApiError(finalsSimulator.error)}` : undefined}
        successText={
          finalsSimulator.data
            ? `Finals simulation complete${finalsSimulator.data.finals.already_simulated ? ' (already simulated)' : ''}.`
            : undefined
        }
      />

      {isLoading && <p>Loading Finals data...</p>}
      {summaryQuery.error && <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p>}
      {qualificationQuery.error && !qualificationNotFound && (
        <p className="error">Failed to load Finals qualification: {formatApiError(qualificationQuery.error)}</p>
      )}

      {summaryQuery.data && (
        <SectionCard title="Finals summary">
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
        </SectionCard>
      )}

      <SectionCard title="Finals qualification">
        {qualificationQuery.data ? (
          <>
            <p className="status">
              As of S{qualificationQuery.data.source_as_of_season}, W{qualificationQuery.data.source_as_of_week}
            </p>
            <JsonPayloadBlock
              title="Qualification payload"
              payload={qualificationQuery.data.qualification}
              emptyText="No qualification payload available."
            />
          </>
        ) : qualificationNotFound ? (
          <p className="status">No Finals qualification is available for this run yet.</p>
        ) : (
          !qualificationQuery.isLoading && <p className="status">No qualification data available.</p>
        )}
      </SectionCard>

      <SectionCard title="Finals result">
        {resultNotFound && <p className="status">Finals result has not been recorded for this run yet.</p>}
        {hasResultError && <p className="error">Failed to load Finals result: {formatApiError(resultQuery.error)}</p>}
        {resultQuery.data ? (
          <>
            <p className="status">
              Event: {resultQuery.data.event_id} · As of S{resultQuery.data.source_as_of_season}, W
              {resultQuery.data.source_as_of_week}
            </p>
            <JsonPayloadBlock title="Result payload" payload={resultQuery.data.result} emptyText="No result payload available." />
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}
