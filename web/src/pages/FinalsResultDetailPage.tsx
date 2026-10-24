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

import { useHistoryText } from './runHistoryText'
export function FinalsResultDetailPage(): JSX.Element {
  const t = useHistoryText()
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
  const qualificationStatus = summaryQuery.isLoading ? t('Loading')
    : summaryQuery.error || !summaryQuery.data ? t('Unknown')
    : summaryQuery.data.qualification ? t('Available') : t('Not generated')
  const resultStatus = resultQuery.data ? t('Recorded')
    : resultQuery.isLoading ? t('Loading')
    : resultNotFound ? t('Missing')
    : resultQuery.error ? t('Failed') : t('Unavailable')

  const championPlayerId = readStringField(resultQuery.data?.result, 'champion_player_id')
  const runnerUpPlayerId = readStringField(resultQuery.data?.result, 'runner_up_player_id')

  return (
    <section className="panel">
      <RunScopedHeader title={t('Finals result detail')} runId={runId} subtitle={t('Summary-first inspection for World Tour Finals result.')} />
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Season'), value: resultQuery.data?.season ?? summaryQuery.data?.season ?? summaryQuery.data?.result?.season ?? '—' },
          { label: t('Qualification'), value: qualificationStatus },
          { label: t('Result'), value: resultStatus }
        ]}
      />

      <SectionCard title={t('Summary')}>
        {resultQuery.isLoading ? <p className="status">{t('Loading Finals result detail...')}</p> : null}
        {hasSummaryError ? <p className="error">Failed to load Finals summary: {formatApiError(summaryQuery.error)}</p> : null}
        {hasResultError ? <p className="error">Failed to load Finals result: {formatApiError(resultQuery.error)}</p> : null}
        {resultNotFound ? <EmptyState message={t('Finals result has not been recorded for this run yet.')} /> : null}
        {resultQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Event', value: resultQuery.data.event_id },
                { label: t('As of season'), value: resultQuery.data.source_as_of_season },
                { label: t('As of week'), value: resultQuery.data.source_as_of_week },
                { label: t('Champion'), value: championPlayerId ?? t('Unknown') },
                { label: t('Runner-up'), value: runnerUpPlayerId ?? t('Unknown') }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: t('Run ID'), value: resultQuery.data.run_id },
                { label: t('Season'), value: resultQuery.data.season }
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
              label: t('Qualification detail'),
              value: summaryQuery.data?.qualification ? (
                <Link to={`/runs/${runId}/finals/qualification`}>{t('Open Finals qualification detail')}</Link>
              ) : (
                t('Qualification not available')
              )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title={t('Result payload')}>
        {resultQuery.data ? (
          <JsonPayloadBlock title={t('Raw result payload')} payload={resultQuery.data.result} emptyText={t('No result payload available.')} />
        ) : resultNotFound ? (
          <EmptyState message={t('No Finals result payload is available yet.')} />
        ) : !resultQuery.isLoading && !hasResultError ? (
          <EmptyState message={t('No result data available.')} />
        ) : null}
      </SectionCard>
    </section>
  )
}
