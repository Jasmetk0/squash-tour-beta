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

  const summaryMismatch = Boolean(summaryQuery.data && (
    summaryQuery.data.run_id !== runId ||
    (summaryQuery.data.qualification && (
      summaryQuery.data.qualification.run_id !== runId ||
      (summaryQuery.data.qualification.season != null && summaryQuery.data.qualification.season !== summaryQuery.data.season)
    )) ||
    (summaryQuery.data.result && (
      summaryQuery.data.result.run_id !== runId ||
      (summaryQuery.data.result.season != null && summaryQuery.data.result.season !== summaryQuery.data.season)
    ))
  ))
  const safeSummary = summaryMismatch ? null : summaryQuery.data
  // The result summary and detail are separate reads. An explicit event
  // identity or as-of snapshot disagreement cannot prove the same result.
  const summaryResult = safeSummary?.result
  const resultMismatch = Boolean(resultQuery.data && (
    resultQuery.data.run_id !== runId ||
    (safeSummary && resultQuery.data.season !== safeSummary.season) ||
    (summaryResult && (
      (summaryResult.event_id != null && resultQuery.data.event_id !== summaryResult.event_id) ||
      (summaryResult.source_as_of_season != null &&
        resultQuery.data.source_as_of_season !== summaryResult.source_as_of_season) ||
      (summaryResult.source_as_of_week != null &&
        resultQuery.data.source_as_of_week !== summaryResult.source_as_of_week)
    ))
  ))
  const safeResult = resultMismatch ? null : resultQuery.data

  const resultNotFound = isApiNotFound(resultQuery.error)
  const hasSummaryError = summaryQuery.error && !isApiNotFound(summaryQuery.error)
  const hasResultError = resultQuery.error && !resultNotFound
  const qualificationStatus = summaryQuery.isLoading ? t('Loading')
    : summaryQuery.error || !safeSummary ? t('Unknown')
    : safeSummary.qualification ? t('Available') : t('Not generated')
  const resultStatus = safeResult ? t('Recorded')
    : resultQuery.isLoading ? t('Loading')
    : resultNotFound ? t('Missing')
    : resultQuery.error ? t('Failed') : t('Unavailable')

  const championPlayerId = readStringField(safeResult?.result, 'champion_player_id')
  const runnerUpPlayerId = readStringField(safeResult?.result, 'runner_up_player_id')

  return (
    <section className="panel">
      <RunScopedHeader title={t('Finals result detail')} runId={runId} subtitle={t('Summary-first inspection for World Tour Finals result.')} />
      <p className="status">{t('Stored legacy SimulationRun history. This view does not verify Product Run Saved Revision authority.')}</p>
      <button type="button" onClick={() => { void resultQuery.refetch(); void summaryQuery.refetch() }}>{t('Refresh read-only data')}</button>
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          { label: t('Season'), value: safeResult?.season ?? safeSummary?.season ?? safeSummary?.result?.season ?? '—' },
          { label: t('Qualification'), value: qualificationStatus },
          { label: t('Result'), value: resultStatus }
        ]}
      />

      <SectionCard title={t('Summary')}>
        {resultMismatch && <p role="alert" className="error">{t('Finals result detail conflicts with the stored summary or selected Run.')}</p>}
        {summaryMismatch && <p role="alert" className="error">{t('Finals result detail conflicts with the stored summary or selected Run.')}</p>}
        {resultQuery.isLoading ? <p className="status">{t('Loading Finals result detail...')}</p> : null}
        {hasSummaryError ? <p className="error">{t('Failed to load Finals summary')}: {formatApiError(summaryQuery.error)}</p> : null}
        {hasResultError ? <p className="error">{t('Failed to load Finals result')}: {formatApiError(resultQuery.error)}</p> : null}
        {resultNotFound ? <EmptyState message={t('Finals result has not been recorded for this run yet.')} /> : null}
        {safeResult ? (
          <>
            <SummaryPills
              items={[
                { label: t('Event'), value: safeResult.event_id },
                { label: t('As of season'), value: safeResult.source_as_of_season },
                { label: t('As of week'), value: safeResult.source_as_of_week },
                { label: t('Champion'), value: championPlayerId ?? t('Unknown') },
                { label: t('Runner-up'), value: runnerUpPlayerId ?? t('Unknown') }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: t('Run ID'), value: safeResult.run_id },
                { label: t('Season'), value: safeResult.season }
              ]}
            />
          </>
        ) : null}
      </SectionCard>

      <SectionCard title={t('Inspection context')}>
        <MetadataList
          items={[
            { label: t('Overview'), value: <Link to={`/runs/${encodeURIComponent(runId)}/finals`}>{t('Open Finals overview page')}</Link> },
            {
              label: t('Qualification detail'),
              value: safeSummary?.qualification ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/finals/qualification`}>{t('Open Finals qualification detail')}</Link>
              ) : (
                summaryQuery.isLoading ? t('Waiting for Finals summary') :
                  !safeSummary ? t('Qualification cannot be verified without a valid Finals summary') : t('Qualification not available')
              )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title={t('Result payload')}>
        {safeResult ? (
          <JsonPayloadBlock title={t('Raw result payload')} payload={safeResult.result} emptyText={t('No result payload available.')} />
        ) : resultNotFound ? (
          <EmptyState message={t('No Finals result payload is available yet.')} />
        ) : !resultQuery.isLoading && !hasResultError && !resultMismatch ? (
          <EmptyState message={t('No result data available.')} />
        ) : null}
      </SectionCard>
    </section>
  )
}
