import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getFinalsResult, getFinalsSummary } from '../api/client'
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

function readStringField(payload: Record<string, unknown> | null | undefined, key: string): string | null {
  const value = payload?.[key]
  return typeof value === 'string' ? value : null
}

export function FinalsResultDetailPage(): JSX.Element {
  const { runId = '' } = useParams()
  const summaryQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const resultQuery = useQuery({
    queryKey: ['finals-result', runId],
    queryFn: () => getFinalsResult(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const resultNotFound = isApiNotFound(resultQuery.error)
  const hasSummaryError = summaryQuery.error && !isApiNotFound(summaryQuery.error)
  const hasResultError = resultQuery.error && !resultNotFound
  const championPlayerId = readStringField(resultQuery.data?.result, 'champion_player_id')
  const runnerUpPlayerId = readStringField(resultQuery.data?.result, 'runner_up_player_id')

  return (
    <section className="panel">
      <RunScopedHeader title="Finals result detail" runId={runId} subtitle="Summary-first inspection for World Tour Finals result." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Season', value: resultQuery.data?.season ?? summaryQuery.data?.season ?? summaryQuery.data?.result?.season ?? '—' },
          { label: 'Qualification', value: summaryQuery.data?.qualification ? 'Available' : 'Not generated' },
          { label: 'Result', value: resultQuery.data ? 'Recorded' : resultNotFound ? 'Missing' : 'Loading' }
        ]}
      />

      <SectionCard title="Summary">
        {resultQuery.isLoading ? <p className="status">Loading Finals result detail...</p> : null}
        {hasSummaryError ? <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p> : null}
        {hasResultError ? <p className="error">Failed to load Finals result: {formatApiError(resultQuery.error)}</p> : null}
        {resultNotFound ? <EmptyState message="Finals result has not been recorded for this run yet." /> : null}
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
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: resultQuery.data.run_id },
                { label: 'Season', value: resultQuery.data.season }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title="Inspection context">
        <MetadataList
          items={[
            { label: 'Overview', value: <Link to={`/runs/${runId}/finals`}>Open Finals overview page</Link> },
            {
              label: 'Qualification detail',
              value: summaryQuery.data?.qualification ? (
                <Link to={`/runs/${runId}/finals/qualification`}>Open Finals qualification detail</Link>
              ) : (
                'Qualification not available'
              )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title="Result payload">
        {resultQuery.data ? (
          <JsonPayloadBlock title="Raw result payload" payload={resultQuery.data.result} emptyText="No result payload available." />
        ) : resultNotFound ? (
          <EmptyState message="No Finals result payload is available yet." />
        ) : !resultQuery.isLoading && !hasResultError ? (
          <EmptyState message="No result data available." />
        ) : null}
      </SectionCard>
    </section>
  )
}
