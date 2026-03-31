import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import {
  getFinalsQualification,
  getFinalsResult,
  getFinalsSummary,
  simulateWorldTourFinals
} from '../api/client'
import {
  ActionStatusBlock,
  EmptyState,
  JsonPayloadBlock,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

function readArrayFieldLength(payload: Record<string, unknown> | null | undefined, key: string): number | null {
  const value = payload?.[key]
  return Array.isArray(value) ? value.length : null
}

function readStringField(payload: Record<string, unknown> | null | undefined, key: string): string | null {
  const value = payload?.[key]
  return typeof value === 'string' ? value : null
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
  const qualificationNotFound = isApiNotFound(qualificationQuery.error)
  const resultNotFound = isApiNotFound(resultQuery.error)
  const hasResultError = resultQuery.error && !resultNotFound

  const qualifiedPlayersCount = readArrayFieldLength(qualificationQuery.data?.qualification, 'qualified_player_ids')
  const groupCount = readArrayFieldLength(qualificationQuery.data?.qualification, 'groups')
  const championPlayerId = readStringField(resultQuery.data?.result, 'champion_player_id')
  const runnerUpPlayerId = readStringField(resultQuery.data?.result, 'runner_up_player_id')

  return (
    <section className="panel">
      <RunScopedHeader
        title="World Tour Finals"
        runId={runId}
        subtitle="Inspect Finals qualification/results and run the Finals simulation action."
      />

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
          <MetadataList
            items={[
              { label: 'Run ID', value: summaryQuery.data.run_id },
              { label: 'Season', value: summaryQuery.data.season },
              { label: 'Qualification status', value: summaryQuery.data.qualification ? 'Available' : 'Unavailable' },
              { label: 'Result status', value: summaryQuery.data.result ? 'Available' : 'Not simulated yet' }
            ]}
          />
        </SectionCard>
      )}

      <SectionCard title="Finals qualification">
        {qualificationQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'As of season', value: qualificationQuery.data.source_as_of_season },
                { label: 'As of week', value: qualificationQuery.data.source_as_of_week },
                { label: 'Qualified players', value: qualifiedPlayersCount ?? 'Unknown' },
                { label: 'Groups', value: groupCount ?? 'Unknown' }
              ]}
            />
            <JsonPayloadBlock
              title="Qualification payload"
              payload={qualificationQuery.data.qualification}
              emptyText="No qualification payload available."
            />
          </>
        ) : qualificationNotFound ? (
          <EmptyState message="No Finals qualification is available for this run yet." />
        ) : (
          !qualificationQuery.isLoading && <EmptyState message="No qualification data available." />
        )}
      </SectionCard>

      <SectionCard title="Finals result">
        {resultNotFound && <EmptyState message="Finals result has not been recorded for this run yet." />}
        {hasResultError && <p className="error">Failed to load Finals result: {formatApiError(resultQuery.error)}</p>}
        {resultQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Event', value: resultQuery.data.event_id },
                { label: 'As of season', value: resultQuery.data.source_as_of_season },
                { label: 'As of week', value: resultQuery.data.source_as_of_week },
                { label: 'Champion', value: championPlayerId ?? 'Unknown' },
                { label: 'Runner-up', value: runnerUpPlayerId ?? 'Unknown' }
              ]}
            />
            <JsonPayloadBlock title="Result payload" payload={resultQuery.data.result} emptyText="No result payload available." />
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}
