import { useQueries, useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRunLineage, getRunSource, getRunStatusSummary } from '../api/client'
import type { RunSourceApiResponse, RunStatusSummary } from '../api/types'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

function describeFinalsSignal(summary?: RunStatusSummary): string {
  if (!summary) return 'Unknown'
  if (summary.finals.result_available) return 'Qualification + result'
  if (summary.finals.qualification_available) return 'Qualification only'
  return 'Not available'
}

function describeRunOrigin(source?: RunSourceApiResponse['source'] | null): string {
  if (!source) return 'Unknown (no source metadata)'
  if (source.source_type === 'new_run') return 'Fresh seed/bootstrap run (new_run)'
  if (source.source_rollover_run_id || source.parent_run_id) return `Rollover-derived (${source.source_type})`
  return `${source.source_type} (source metadata available)`
}

function SeasonChainRunCard({
  title,
  runId,
  summary,
  isLoading,
  error,
  sourceType,
  parentRunId,
  childCount,
  isCurrent,
  seasonProgressNote
}: {
  title: string
  runId: string
  summary?: RunStatusSummary
  isLoading: boolean
  error: unknown
  sourceType?: string
  parentRunId?: string | null
  childCount?: number
  isCurrent?: boolean
  seasonProgressNote?: string
}): JSX.Element {
  return (
    <SectionCard title={title}>
      {isLoading ? <p className="status">Loading run summary...</p> : null}
      {error ? <p className="error">Failed to load {runId}: {formatApiError(error)}</p> : null}
      {!isLoading && !error && summary ? (
        <>
          <CompactSummaryCard
            items={[
              { label: 'Run ID', value: summary.run_id },
              { label: 'Season', value: summary.season },
              {
                label: 'Progress',
                value: `${summary.progress.next_event_index} / ${summary.progress.total_events}`
              },
              {
                label: 'Finals availability',
                value: describeFinalsSignal(summary)
              },
              {
                label: 'Latest rollover',
                value: summary.rollover
                  ? `To ${summary.rollover.latest_to_season} (${summary.rollover.transitioned_players} players)`
                  : 'None'
              },
              { label: 'Source type', value: sourceType ?? summary.source?.source_type ?? 'Unknown' },
              {
                label: 'Parent run',
                value: (parentRunId ?? summary.source?.parent_run_id) ? (
                  <Link to={`/runs/${parentRunId ?? summary.source?.parent_run_id}`}>{parentRunId ?? summary.source?.parent_run_id}</Link>
                ) : (
                  'None'
                )
              },
              { label: 'Child runs', value: childCount ?? summary.lineage.child_run_count }
            ]}
          />
          {seasonProgressNote ? <p className="status">{seasonProgressNote}</p> : null}
          <p>
            <Link to={`/runs/${runId}`}>Run Detail</Link> · <Link to={`/runs/${runId}/diagnostics`}>Diagnostics</Link> ·{' '}
            <Link to={`/runs/${runId}/bootstrap-lineage`}>Bootstrap / Lineage</Link>
            {summary.rollover ? (
              <>
                {' '}
                · <Link to={`/runs/${runId}/rollover`}>Rollover</Link>
              </>
            ) : null}
            {(summary.finals.qualification_available || summary.finals.result_available) ? (
              <>
                {' '}
                · <Link to={`/runs/${runId}/finals`}>World Tour Finals</Link>
              </>
            ) : null}
            {isCurrent ? (
              <>
                {' '}
                · <Link to={`/runs/${runId}/season-chain`}>Season Chain</Link>
              </>
            ) : null}
          </p>
        </>
      ) : null}
    </SectionCard>
  )
}

export function SeasonChainPage(): JSX.Element {
  const { runId = '' } = useParams()

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

  const currentStatusQuery = useQuery({
    queryKey: ['run-status-summary', runId],
    queryFn: () => getRunStatusSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })

  const parentRunId = sourceQuery.data?.source.parent_run_id ?? lineageQuery.data?.lineage.source.parent_run_id ?? null
  const childRunIds = lineageQuery.data?.lineage.children ?? []

  const [parentStatusQuery] = useQueries({
    queries: [
      {
        queryKey: ['run-status-summary', parentRunId],
        queryFn: () => getRunStatusSummary(parentRunId as string),
        enabled: Boolean(parentRunId),
        retry: false
      }
    ]
  })

  const childStatusQueries = useQueries({
    queries: childRunIds.map((childRunId) => ({
      queryKey: ['run-status-summary', childRunId],
      queryFn: () => getRunStatusSummary(childRunId),
      enabled: Boolean(childRunId),
      retry: false
    }))
  })

  const chainKnown = Boolean(sourceQuery.data || lineageQuery.data)
  const sourceMetadataExists = Boolean(sourceQuery.data?.source)
  const lineageMetadataExists = Boolean(lineageQuery.data?.lineage)
  const currentSource = sourceQuery.data?.source ?? currentStatusQuery.data?.source

  const nextInspectionLinks: Array<{ key: string; label: string; to: string }> = [
    { key: 'current-detail', label: 'Current run detail', to: `/runs/${runId}` },
    { key: 'current-diagnostics', label: 'Current diagnostics', to: `/runs/${runId}/diagnostics` },
    { key: 'current-chain', label: 'Current season chain', to: `/runs/${runId}/season-chain` }
  ]

  if (parentRunId) {
    nextInspectionLinks.push({ key: 'parent-diagnostics', label: 'Parent diagnostics', to: `/runs/${parentRunId}/diagnostics` })
    nextInspectionLinks.push({ key: 'parent-detail', label: 'Parent run detail', to: `/runs/${parentRunId}` })
  }

  if (currentStatusQuery.data?.rollover) {
    nextInspectionLinks.push({ key: 'current-rollover', label: 'Current rollover', to: `/runs/${runId}/rollover` })
  }

  if (currentStatusQuery.data?.finals.qualification_available && !currentStatusQuery.data.finals.result_available) {
    nextInspectionLinks.push({ key: 'current-finals', label: 'Current finals', to: `/runs/${runId}/finals` })
  }

  if (sourceMetadataExists) {
    nextInspectionLinks.push({ key: 'current-bootstrap-lineage', label: 'Current bootstrap / lineage', to: `/runs/${runId}/bootstrap-lineage` })
  }

  childRunIds.forEach((childRunId) => {
    nextInspectionLinks.push({ key: `child-diag-${childRunId}`, label: `Child diagnostics: ${childRunId}`, to: `/runs/${childRunId}/diagnostics` })
    nextInspectionLinks.push({ key: `child-detail-${childRunId}`, label: `Child run detail: ${childRunId}`, to: `/runs/${childRunId}` })
  })

  return (
    <section className="panel">
      <RunScopedHeader
        title="Season Chain"
        runId={runId}
        subtitle="Read-only parent/current/children run chain overview for this run context."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Source type', value: currentSource?.source_type ?? '—' },
          { label: 'Parent', value: parentRunId ?? 'None' },
          { label: 'Children', value: childRunIds.length },
          {
            label: 'Rollover',
            value: currentStatusQuery.data?.rollover ? `To ${currentStatusQuery.data.rollover.latest_to_season}` : 'None'
          }
        ]}
      />

      <SectionCard title="Chain summary">
        {(sourceQuery.isLoading || lineageQuery.isLoading || currentStatusQuery.isLoading) && (
          <p className="status">Loading chain summary...</p>
        )}
        {sourceQuery.error && !isApiNotFound(sourceQuery.error) && (
          <p className="error">Failed to load source metadata: {formatApiError(sourceQuery.error)}</p>
        )}
        {lineageQuery.error && !isApiNotFound(lineageQuery.error) && (
          <p className="error">Failed to load lineage metadata: {formatApiError(lineageQuery.error)}</p>
        )}
        {currentStatusQuery.error && (
          <p className="error">Failed to load current run summary: {formatApiError(currentStatusQuery.error)}</p>
        )}
        {chainKnown && currentStatusQuery.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Parent status', value: parentRunId ? 'Linked' : 'None' },
                { label: 'Current status', value: currentStatusQuery.data.run_id ? 'Loaded' : 'Unavailable' },
                { label: 'Children status', value: childRunIds.length > 0 ? `${childRunIds.length} linked` : 'None' },
                { label: 'Rollover exists', value: currentStatusQuery.data.rollover ? 'Yes' : 'No' },
                { label: 'Finals signal', value: describeFinalsSignal(currentStatusQuery.data) },
                { label: 'Source metadata', value: sourceMetadataExists ? 'Present' : 'Absent' },
                { label: 'Lineage metadata', value: lineageMetadataExists ? 'Present' : 'Absent' }
              ]}
            />
            <MetadataList
              items={[
                { label: 'Current season', value: currentStatusQuery.data.season },
                {
                  label: 'Season progression',
                  value: parentStatusQuery?.data
                    ? `${parentStatusQuery.data.season} → ${currentStatusQuery.data.season}`
                    : `Current season ${currentStatusQuery.data.season}`
                },
                {
                  label: 'Latest rollover',
                  value: currentStatusQuery.data.rollover
                    ? `To ${currentStatusQuery.data.rollover.latest_to_season} (${currentStatusQuery.data.rollover.transitioned_players} players)`
                    : 'None recorded'
                },
                { label: 'Finals availability', value: describeFinalsSignal(currentStatusQuery.data) }
              ]}
            />
          </>
        ) : null}
        {!chainKnown && isApiNotFound(sourceQuery.error) && isApiNotFound(lineageQuery.error) ? (
          <EmptyState message="No source/lineage metadata is available for this run yet." />
        ) : null}
      </SectionCard>

      <SectionCard title="Season-to-season signals">
        <MetadataList
          items={[
            {
              label: 'Parent vs current',
              value: parentStatusQuery?.data && currentStatusQuery.data
                ? `Parent season ${parentStatusQuery.data.season} → current season ${currentStatusQuery.data.season}`
                : parentRunId
                  ? 'Parent run linked but parent season summary is unavailable'
                  : 'No parent run linked'
            },
            {
              label: 'Current vs children',
              value: childRunIds.length === 0
                ? 'No child runs to compare'
                : childRunIds
                    .map((childRunId, index) => {
                      const childSeason = childStatusQueries[index]?.data?.season
                      return childSeason
                        ? `${currentStatusQuery.data?.season ?? 'Current ?'} → ${childSeason} (${childRunId})`
                        : `${currentStatusQuery.data?.season ?? 'Current ?'} → ? (${childRunId})`
                    })
                    .join('; ')
            },
            {
              label: 'Current rollover signal',
              value: currentStatusQuery.data?.rollover
                ? `Latest rollover to season ${currentStatusQuery.data.rollover.latest_to_season}`
                : 'No rollover recorded for current run'
            },
            {
              label: 'Current run origin signal',
              value: describeRunOrigin(sourceQuery.data?.source)
            }
          ]}
        />
      </SectionCard>

      <SectionCard title="Most relevant next inspection links">
        <ul className="item-list" aria-label="Season chain next inspection links">
          {nextInspectionLinks.map((item) => (
            <li key={item.key}>
              <Link to={item.to}>{item.label}</Link>
            </li>
          ))}
        </ul>
      </SectionCard>

      {parentRunId ? (
        <SeasonChainRunCard
          title="Parent run"
          runId={parentRunId}
          summary={parentStatusQuery?.data}
          isLoading={Boolean(parentStatusQuery?.isLoading)}
          error={parentStatusQuery?.error}
        />
      ) : (
        <SectionCard title="Parent run">
          <EmptyState message="No parent run is linked for this run." />
        </SectionCard>
      )}

      <SeasonChainRunCard
        title="Current run"
        runId={runId}
        summary={currentStatusQuery.data}
        isLoading={currentStatusQuery.isLoading}
        error={currentStatusQuery.error}
        sourceType={sourceQuery.data?.source.source_type}
        parentRunId={parentRunId}
        childCount={childRunIds.length}
        isCurrent
      />

      <SectionCard title="Child runs">
        {lineageQuery.isLoading ? <p className="status">Loading child runs...</p> : null}
        {lineageQuery.error && !isApiNotFound(lineageQuery.error) ? (
          <p className="error">Failed to load child runs: {formatApiError(lineageQuery.error)}</p>
        ) : null}
        {!lineageQuery.isLoading && childRunIds.length === 0 ? <EmptyState message="No child runs exist for this run yet." /> : null}
        {childRunIds.map((childRunId, index) => {
          const childQuery = childStatusQueries[index]
          const seasonProgressNote = childQuery?.data && currentStatusQuery.data
            ? `Season progression: ${currentStatusQuery.data.season} → ${childQuery.data.season}`
            : undefined
          return (
            <article key={childRunId} className="panel nested-panel">
              <h4>{childRunId}</h4>
              {childQuery?.isLoading ? <p className="status">Loading child run summary...</p> : null}
              {childQuery?.error ? <p className="error">Failed to load {childRunId}: {formatApiError(childQuery.error)}</p> : null}
              {childQuery?.data ? (
                <>
                  <CompactSummaryCard
                    items={[
                      { label: 'Run ID', value: childQuery.data.run_id },
                      { label: 'Season', value: childQuery.data.season },
                      {
                        label: 'Progress',
                        value: `${childQuery.data.progress.next_event_index} / ${childQuery.data.progress.total_events}`
                      },
                      {
                        label: 'Finals availability',
                        value: describeFinalsSignal(childQuery.data)
                      },
                      {
                        label: 'Latest rollover',
                        value: childQuery.data.rollover
                          ? `To ${childQuery.data.rollover.latest_to_season} (${childQuery.data.rollover.transitioned_players} players)`
                          : 'None'
                      },
                      { label: 'Source type', value: childQuery.data.source?.source_type ?? 'Unknown' },
                      {
                        label: 'Parent run',
                        value: childQuery.data.source?.parent_run_id ? (
                          <Link to={`/runs/${childQuery.data.source.parent_run_id}`}>{childQuery.data.source.parent_run_id}</Link>
                        ) : (
                          'None'
                        )
                      },
                      { label: 'Child runs', value: childQuery.data.lineage.child_run_count }
                    ]}
                  />
                  {seasonProgressNote ? <p className="status">{seasonProgressNote}</p> : null}
                  <p>
                    <Link to={`/runs/${childRunId}`}>Run Detail</Link> ·{' '}
                    <Link to={`/runs/${childRunId}/diagnostics`}>Diagnostics</Link> ·{' '}
                    <Link to={`/runs/${childRunId}/bootstrap-lineage`}>Bootstrap / Lineage</Link>
                  </p>
                </>
              ) : null}
            </article>
          )
        })}
      </SectionCard>
    </section>
  )
}
