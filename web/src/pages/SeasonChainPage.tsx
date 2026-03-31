import { useQueries, useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getRunLineage, getRunSource, getRunStatusSummary } from '../api/client'
import type { RunStatusSummary } from '../api/types'
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

function SeasonChainRunCard({
  title,
  runId,
  summary,
  isLoading,
  error,
  sourceType,
  parentRunId,
  childCount,
  isCurrent
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
                value: summary.finals.result_available
                  ? 'Qualification + result'
                  : summary.finals.qualification_available
                    ? 'Qualification only'
                    : 'Not available'
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
          <p>
            <Link to={`/runs/${runId}`}>Run Detail</Link> · <Link to={`/runs/${runId}/diagnostics`}>Diagnostics</Link> ·{' '}
            <Link to={`/runs/${runId}/bootstrap-lineage`}>Bootstrap / Lineage</Link>
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
          { label: 'Source type', value: sourceQuery.data?.source.source_type ?? currentStatusQuery.data?.source?.source_type ?? '—' },
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
                { label: 'Source type', value: sourceQuery.data?.source.source_type ?? currentStatusQuery.data.source?.source_type ?? 'Unknown' },
                { label: 'Parent linked', value: parentRunId ? 'Yes' : 'No' },
                { label: 'Child runs', value: childRunIds.length },
                { label: 'Rollover exists', value: currentStatusQuery.data.rollover ? 'Yes' : 'No' }
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
                { label: 'Lineage child count', value: childRunIds.length }
              ]}
            />
          </>
        ) : null}
        {!chainKnown && isApiNotFound(sourceQuery.error) && isApiNotFound(lineageQuery.error) ? (
          <EmptyState message="No source/lineage metadata is available for this run yet." />
        ) : null}
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
                        value: childQuery.data.finals.result_available
                          ? 'Qualification + result'
                          : childQuery.data.finals.qualification_available
                            ? 'Qualification only'
                            : 'Not available'
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

      <SectionCard title="Relationship notes">
        <MetadataList
          items={[
            {
              label: 'Source relationship',
              value: sourceQuery.data?.source.source_type
                ? `${sourceQuery.data.source.source_type}${parentRunId ? ` (parent: ${parentRunId})` : ''}`
                : 'No source metadata available'
            },
            {
              label: 'Parent/current/children',
              value: parentRunId ? `Parent → Current (${runId}) → ${childRunIds.length} child run(s)` : `Current (${runId}) with ${childRunIds.length} child run(s)`
            },
            {
              label: 'Season progression visibility',
              value: parentStatusQuery?.data
                ? `${parentStatusQuery.data.season} → ${currentStatusQuery.data?.season ?? '—'}`
                : 'Only current run season is visible from available data'
            },
            {
              label: 'Current run rollover',
              value: currentStatusQuery.data?.rollover ? 'Latest rollover exists' : 'No rollover found for current run'
            }
          ]}
        />
      </SectionCard>

      <SectionCard title="Quick navigation">
        <ul className="item-list" aria-label="Season chain quick navigation">
          <li>
            <Link to={`/runs/${runId}`}>Current run detail</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/diagnostics`}>Current diagnostics</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/bootstrap-lineage`}>Current bootstrap / lineage</Link>
          </li>
          {parentRunId ? (
            <>
              <li>
                <Link to={`/runs/${parentRunId}`}>Parent run detail</Link>
              </li>
              <li>
                <Link to={`/runs/${parentRunId}/diagnostics`}>Parent diagnostics</Link>
              </li>
              <li>
                <Link to={`/runs/${parentRunId}/bootstrap-lineage`}>Parent bootstrap / lineage</Link>
              </li>
            </>
          ) : null}
          {childRunIds.map((childRunId) => (
            <li key={`quick-${childRunId}`}>
              <Link to={`/runs/${childRunId}`}>Child run detail: {childRunId}</Link>
            </li>
          ))}
          {childRunIds.map((childRunId) => (
            <li key={`quick-diag-${childRunId}`}>
              <Link to={`/runs/${childRunId}/diagnostics`}>Child diagnostics: {childRunId}</Link>
            </li>
          ))}
        </ul>
      </SectionCard>
    </section>
  )
}
