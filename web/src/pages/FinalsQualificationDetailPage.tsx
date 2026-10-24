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

import { useHistoryText } from './runHistoryText'
export function FinalsQualificationDetailPage(): JSX.Element {
  const t = useHistoryText()
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

  const qualificationStatus = qualificationQuery.data ? t('Available')
    : qualificationQuery.isLoading ? t('Loading')
    : qualificationNotFound ? t('Missing')
    : qualificationQuery.error ? t('Failed') : t('Unavailable')
  const resultStatus = summaryQuery.isLoading ? t('Loading')
    : summaryQuery.error || !summaryQuery.data ? t('Unknown')
    : summaryQuery.data.result ? t('Recorded') : t('Not simulated')

  const qualifiedPlayersCount = readArrayFieldLength(qualificationQuery.data?.qualification, 'qualified_player_ids')
  const groupCount = readArrayFieldLength(qualificationQuery.data?.qualification, 'groups')

  return (
    <section className="panel">
      <RunScopedHeader
        title={t('Finals qualification detail')}
        runId={runId}
        subtitle={t('Summary-first inspection for World Tour Finals qualification.')}
      />
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          {
            label: t('Season'),
            value: qualificationQuery.data?.season ?? summaryQuery.data?.season ?? summaryQuery.data?.qualification?.season ?? '—'
          },
          { label: t('Qualification'), value: qualificationStatus },
          { label: t('Result'), value: resultStatus }
        ]}
      />

      <SectionCard title={t('Summary')}>
        {qualificationQuery.isLoading ? <p className="status">{t('Loading Finals qualification detail...')}</p> : null}
        {hasSummaryError ? <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p> : null}
        {hasQualificationError ? (
          <p className="error">Failed to load Finals qualification: {formatApiError(qualificationQuery.error)}</p>
        ) : null}
        {qualificationNotFound ? <EmptyState message={t('No Finals qualification is available for this run yet.')} /> : null}
        {qualificationQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: t('As of season'), value: qualificationQuery.data.source_as_of_season },
                { label: t('As of week'), value: qualificationQuery.data.source_as_of_week },
                { label: t('Qualified players'), value: qualifiedPlayersCount ?? t('Unknown') },
                { label: t('Groups'), value: groupCount ?? t('Unknown') }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: t('Run ID'), value: qualificationQuery.data.run_id },
                { label: t('Season'), value: qualificationQuery.data.season }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title={t('Inspection context')}>
        <MetadataList
          items={[
            { label: t('Overview'), value: <Link to={`/runs/${runId}/finals`}>{t('Open Finals overview page')}</Link> },
            {
              label: t('Result detail'),
              value: summaryQuery.data?.result ? (
                <Link to={`/runs/${runId}/finals/result`}>{t('Open Finals result detail')}</Link>
              ) : (
                t('Result not available yet')
              )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title={t('Qualification payload')}>
        {qualificationQuery.data ? (
          <JsonPayloadBlock
            title={t('Raw qualification payload')}
            payload={qualificationQuery.data.qualification}
            emptyText={t('No qualification payload available.')}
          />
        ) : qualificationNotFound ? (
          <EmptyState message={t('No qualification payload is available yet.')} />
        ) : !qualificationQuery.isLoading && !hasQualificationError ? (
          <EmptyState message={t('No qualification data available.')} />
        ) : null}
      </SectionCard>
    </section>
  )
}
