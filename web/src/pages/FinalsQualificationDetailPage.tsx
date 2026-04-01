import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getFinalsQualification, getFinalsSummary } from '../api/client'
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

function readArrayFieldLength(payload: Record<string, unknown> | null | undefined, key: string): number | null {
  const value = payload?.[key]
  return Array.isArray(value) ? value.length : null
}

export function FinalsQualificationDetailPage(): JSX.Element {
  const { runId = '' } = useParams()
  const summaryQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const qualificationQuery = useQuery({
    queryKey: ['finals-qualification', runId],
    queryFn: () => getFinalsQualification(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const qualificationNotFound = isApiNotFound(qualificationQuery.error)
  const hasSummaryError = summaryQuery.error && !isApiNotFound(summaryQuery.error)
  const hasQualificationError = qualificationQuery.error && !qualificationNotFound

  const qualifiedPlayersCount = readArrayFieldLength(qualificationQuery.data?.qualification, 'qualified_player_ids')
  const groupCount = readArrayFieldLength(qualificationQuery.data?.qualification, 'groups')

  return (
    <section className="panel">
      <RunScopedHeader
        title="Finals qualification detail"
        runId={runId}
        subtitle="Summary-first inspection for World Tour Finals qualification."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          {
            label: 'Season',
            value: qualificationQuery.data?.season ?? summaryQuery.data?.season ?? summaryQuery.data?.qualification?.season ?? '—'
          },
          { label: 'Qualification', value: qualificationQuery.data ? 'Available' : qualificationNotFound ? 'Missing' : 'Loading' },
          { label: 'Result', value: summaryQuery.data?.result ? 'Recorded' : 'Not simulated' }
        ]}
      />

      <SectionCard title="Summary">
        {qualificationQuery.isLoading ? <p className="status">Loading Finals qualification detail...</p> : null}
        {hasSummaryError ? <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p> : null}
        {hasQualificationError ? (
          <p className="error">Failed to load Finals qualification: {formatApiError(qualificationQuery.error)}</p>
        ) : null}
        {qualificationNotFound ? <EmptyState message="No Finals qualification is available for this run yet." /> : null}
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
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: qualificationQuery.data.run_id },
                { label: 'Season', value: qualificationQuery.data.season }
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
              label: 'Result detail',
              value: summaryQuery.data?.result ? (
                <Link to={`/runs/${runId}/finals/result`}>Open Finals result detail</Link>
              ) : (
                'Result not available yet'
              )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title="Qualification payload">
        {qualificationQuery.data ? (
          <JsonPayloadBlock
            title="Raw qualification payload"
            payload={qualificationQuery.data.qualification}
            emptyText="No qualification payload available."
          />
        ) : qualificationNotFound ? (
          <EmptyState message="No qualification payload is available yet." />
        ) : !qualificationQuery.isLoading && !hasQualificationError ? (
          <EmptyState message="No qualification data available." />
        ) : null}
      </SectionCard>
    </section>
  )
}
