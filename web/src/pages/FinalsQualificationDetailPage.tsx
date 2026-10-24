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
  const qualificationMismatch = Boolean(qualificationQuery.data && (
    qualificationQuery.data.run_id !== runId || (safeSummary && qualificationQuery.data.season !== safeSummary.season)
  ))
  const safeQualification = qualificationMismatch ? null : qualificationQuery.data

  const qualificationNotFound = isApiNotFound(qualificationQuery.error)
  const hasSummaryError = summaryQuery.error && !isApiNotFound(summaryQuery.error)
  const hasQualificationError = qualificationQuery.error && !qualificationNotFound

  const qualificationStatus = safeQualification ? t('Available')
    : qualificationQuery.isLoading ? t('Loading')
    : qualificationNotFound ? t('Missing')
    : qualificationQuery.error ? t('Failed') : t('Unavailable')
  const resultStatus = summaryQuery.isLoading ? t('Loading')
    : summaryQuery.error || !safeSummary ? t('Unknown')
    : safeSummary.result ? t('Recorded') : t('Not simulated')

  const qualifiedPlayersCount = readArrayFieldLength(safeQualification?.qualification, 'qualified_player_ids') ?? readArrayFieldLength(safeQualification?.qualification, 'qualified')
  const groupCount = readArrayFieldLength(safeQualification?.qualification, 'groups')

  return (
    <section className="panel">
      <RunScopedHeader
        title={t('Finals qualification detail')}
        runId={runId}
        subtitle={t('Summary-first inspection for World Tour Finals qualification.')}
      />
      <p className="status">{t('Stored legacy SimulationRun history. This view does not verify Product Run Saved Revision authority.')}</p>
      <button type="button" onClick={() => { void qualificationQuery.refetch(); void summaryQuery.refetch() }}>{t('Refresh read-only data')}</button>
      <CurrentContextStrip
        items={[
          { label: t('Run'), value: runId || 'unknown' },
          {
            label: t('Season'),
            value: safeQualification?.season ?? safeSummary?.season ?? safeSummary?.qualification?.season ?? '—'
          },
          { label: t('Qualification'), value: qualificationStatus },
          { label: t('Result'), value: resultStatus }
        ]}
      />

      <SectionCard title={t('Summary')}>
        {qualificationMismatch && <p role="alert" className="error">{t('Finals qualification identity differs from the selected Run or summary season.')}</p>}
        {summaryMismatch && <p role="alert" className="error">{t('Finals qualification identity differs from the selected Run or summary season.')}</p>}
        {qualificationQuery.isLoading ? <p className="status">{t('Loading Finals qualification detail...')}</p> : null}
        {hasSummaryError ? <p className="error">{t('Failed to load Finals summary')}: {formatApiError(summaryQuery.error)}</p> : null}
        {hasQualificationError ? (
          <p className="error">{t('Failed to load Finals qualification')}: {formatApiError(qualificationQuery.error)}</p>
        ) : null}
        {qualificationNotFound ? <EmptyState message={t('No Finals qualification is available for this run yet.')} /> : null}
        {safeQualification ? (
          <>
            <SummaryPills
              items={[
                { label: t('As of season'), value: safeQualification.source_as_of_season },
                { label: t('As of week'), value: safeQualification.source_as_of_week },
                { label: t('Qualified players'), value: qualifiedPlayersCount ?? t('Unknown') },
                { label: t('Groups'), value: groupCount ?? t('Unknown') }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: t('Run ID'), value: safeQualification.run_id },
                { label: t('Season'), value: safeQualification.season }
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
              label: t('Result detail'),
              value: safeSummary?.result ? (
                <Link to={`/runs/${encodeURIComponent(runId)}/finals/result`}>{t('Open Finals result detail')}</Link>
              ) : (
                t('Result not available yet')
              )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title={t('Qualification payload')}>
        {safeQualification ? (
          <JsonPayloadBlock
            title={t('Raw qualification payload')}
            payload={safeQualification.qualification}
            emptyText={t('No qualification payload available.')}
          />
        ) : qualificationNotFound ? (
          <EmptyState message={t('No qualification payload is available yet.')} />
        ) : !qualificationQuery.isLoading && !hasQualificationError && !qualificationMismatch ? (
          <EmptyState message={t('No qualification data available.')} />
        ) : null}
      </SectionCard>
    </section>
  )
}
