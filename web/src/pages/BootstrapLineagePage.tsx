import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { bootstrapNextSeason, getRunLineage, getRunSource, getRunStatusSummary } from '../api/client'
import type { RunStatusSummary } from '../api/types'
import {
  ActionStatusBlock,
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
import { classifyRunProvenance, normalizeRunSourceType } from '../utils/runSourceTypes'

function statusProgress(summary?: RunStatusSummary): string {
  if (!summary) return 'Unknown'
  return `${summary.progress.next_event_index} / ${summary.progress.total_events}`
}

function LinkCluster({ runId }: { runId: string }): JSX.Element {
  return (
    <p>
      <Link to={`/runs/${runId}`}>Run Detail</Link> · <Link to={`/runs/${runId}/diagnostics`}>Diagnostics</Link> ·{' '}
      <Link to={`/runs/${runId}/season-chain`}>Season Chain</Link>
    </p>
  )
}

export function BootstrapLineagePage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const [childRunId, setChildRunId] = useState('')
  const [childSeedInput, setChildSeedInput] = useState('')

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

  const bootstrapMutation = useMutation({
    mutationFn: () => {
      const childSeed = childSeedInput.trim() === '' ? undefined : Number(childSeedInput)
      return bootstrapNextSeason(runId, {
        child_run_id: childRunId.trim(),
        ...(childSeed !== undefined ? { child_seed: childSeed } : {})
      })
    },
    onSuccess: async () => {
      setChildSeedInput('')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-source', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-lineage', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-status-summary', runId] })
      ])
    }
  })

  const handleBootstrapSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!childRunId.trim()) return
    bootstrapMutation.mutate()
  }

  const source = sourceQuery.data?.source
  const lineage = lineageQuery.data?.lineage
  const sourceNotFound = isApiNotFound(sourceQuery.error)
  const lineageNotFound = isApiNotFound(lineageQuery.error)
  const parentRunId = source?.parent_run_id ?? lineage?.source.parent_run_id ?? null
  const childRunIds = lineage?.children ?? []

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
    queries: childRunIds.map((childId) => ({
      queryKey: ['run-status-summary', childId],
      queryFn: () => getRunStatusSummary(childId),
      enabled: Boolean(childId),
      retry: false
    }))
  })

  const runClassification = classifyRunProvenance(source ?? lineage?.source)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Bootstrap / Lineage"
        runId={runId}
        subtitle="Read-only provenance and lineage inspection for this run context."
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runId || 'unknown' },
          { label: 'Source type', value: normalizeRunSourceType(source?.source_type ?? lineage?.source.source_type) ?? '—' },
          { label: 'Parent', value: parentRunId ?? 'None' },
          { label: 'Children', value: childRunIds.length }
        ]}
      />

      <SectionCard title="Current run provenance summary">
        {(sourceQuery.isLoading || lineageQuery.isLoading || currentStatusQuery.isLoading) && <p className="status">Loading provenance summary...</p>}
        {sourceNotFound && <EmptyState message="No source metadata is available for this run." />}
        {lineageNotFound && <EmptyState message="No lineage metadata is available for this run." />}
        {sourceQuery.error && !sourceNotFound && <p className="error">Failed to load run source: {formatApiError(sourceQuery.error)}</p>}
        {lineageQuery.error && !lineageNotFound && <p className="error">Failed to load run lineage: {formatApiError(lineageQuery.error)}</p>}
        {currentStatusQuery.error && <p className="error">Failed to load current run status: {formatApiError(currentStatusQuery.error)}</p>}

        {(source || lineage || currentStatusQuery.data) && (
          <>
            <SummaryPills
              items={[
                {
                  label: 'Source type',
                  value: normalizeRunSourceType(source?.source_type ?? lineage?.source.source_type) ?? 'Unknown'
                },
                { label: 'Classification', value: runClassification },
                { label: 'Parent linked', value: parentRunId ? 'Yes' : 'No' },
                {
                  label: 'Rollover provenance',
                  value: (source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id) ? 'Present' : 'None'
                }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: runId },
                { label: 'Season', value: currentStatusQuery.data?.season ?? 'Unknown' },
                { label: 'Progress', value: statusProgress(currentStatusQuery.data) },
                { label: 'Child runs', value: childRunIds.length }
              ]}
            />
            <MetadataList
              items={[
                { label: 'Parent run ID', value: parentRunId ?? 'None' },
                { label: 'Rollover source run', value: source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id ?? 'None' },
                {
                  label: 'Rollover from season',
                  value: source?.source_rollover_from_season ?? lineage?.source.source_rollover_from_season ?? 'None'
                },
                { label: 'Rollover to season', value: source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season ?? 'None' }
              ]}
            />
          </>
        )}
      </SectionCard>

      <SectionCard title="Current run bridge navigation">
        <LinkCluster runId={runId} />
      </SectionCard>

      <SectionCard title="Parent run inspection">
        {lineageQuery.isLoading && <p className="status">Loading parent run metadata...</p>}
        {parentRunId ? (
          <>
            {parentStatusQuery.isLoading && <p className="status">Loading parent status summary...</p>}
            {parentStatusQuery.error ? <p className="error">Failed to load parent status summary: {formatApiError(parentStatusQuery.error)}</p> : null}
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: parentRunId },
                { label: 'Season', value: parentStatusQuery.data?.season ?? 'Unknown' },
                { label: 'Progress', value: statusProgress(parentStatusQuery.data) },
                { label: 'Child count', value: parentStatusQuery.data?.lineage.child_run_count ?? 'Unknown' }
              ]}
            />
            <LinkCluster runId={parentRunId} />
          </>
        ) : (
          <EmptyState message="No parent run linked for this run." />
        )}
      </SectionCard>

      <SectionCard title="Child runs inspection">
        {lineageQuery.isLoading && <p className="status">Loading child runs...</p>}
        {!lineageQuery.isLoading && childRunIds.length === 0 ? <EmptyState message="No child runs linked for this run." /> : null}
        <ul className="item-list">
          {childRunIds.map((childId, index) => {
            const childStatusQuery = childStatusQueries[index]
            return (
              <li key={childId}>
                <h4>{childId}</h4>
                {childStatusQuery?.isLoading ? <p className="status">Loading child status summary...</p> : null}
                {childStatusQuery?.error ? <p className="error">Failed to load child status summary: {formatApiError(childStatusQuery.error)}</p> : null}
                <CompactSummaryCard
                  items={[
                    { label: 'Run ID', value: childId },
                    { label: 'Season', value: childStatusQuery?.data?.season ?? 'Unknown' },
                    { label: 'Progress', value: statusProgress(childStatusQuery?.data) },
                    { label: 'Child count', value: childStatusQuery?.data?.lineage.child_run_count ?? 'Unknown' }
                  ]}
                />
                <LinkCluster runId={childId} />
              </li>
            )
          })}
        </ul>
      </SectionCard>

      <SectionCard title="Rollover provenance">
        {(source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id) ? (
          <MetadataList
            items={[
              { label: 'Source rollover run', value: source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id ?? 'None' },
              {
                label: 'Source rollover season',
                value:
                  source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season
                    ? `Season ${source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season}`
                    : 'Unknown'
              }
            ]}
          />
        ) : (
          <EmptyState message="No rollover provenance is linked for this run." />
        )}

        {(source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id) &&
        (source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season) ? (
          <p>
            <Link
              to={`/runs/${source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id}/rollover/${
                source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season
              }`}
            >
              Open source rollover detail
            </Link>
          </p>
        ) : null}
      </SectionCard>

      <SectionCard title="Most relevant next inspections">
        <MetadataList
          items={[
            {
              label: 'Parent season chain',
              value: parentRunId ? <Link to={`/runs/${parentRunId}/season-chain`}>Inspect parent season chain</Link> : 'No parent run linked'
            },
            {
              label: 'First child diagnostics',
              value: childRunIds[0] ? <Link to={`/runs/${childRunIds[0]}/diagnostics`}>Inspect first child diagnostics</Link> : 'No child run linked'
            },
            {
              label: 'Source rollover',
              value:
                (source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id) &&
                (source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season) ? (
                  <Link
                    to={`/runs/${source?.source_rollover_run_id ?? lineage?.source.source_rollover_run_id}/rollover/${
                      source?.source_rollover_to_season ?? lineage?.source.source_rollover_to_season
                    }`}
                  >
                    Inspect source rollover detail
                  </Link>
                ) : (
                  'No source rollover linked'
                )
            }
          ]}
        />
      </SectionCard>

      <SectionCard title="Bootstrap next season child run">
        <form onSubmit={handleBootstrapSubmit}>
          <label>
            Child run ID
            <input
              aria-label="Child run ID"
              value={childRunId}
              onChange={(event) => setChildRunId(event.target.value)}
              placeholder="e.g. run-2029"
            />
          </label>

          <label>
            Child seed (optional)
            <input
              type="number"
              aria-label="Child seed"
              value={childSeedInput}
              onChange={(event) => setChildSeedInput(event.target.value)}
              placeholder="Leave empty to let backend decide"
            />
          </label>

          <div className="actions">
            <button type="submit" disabled={!runId || !childRunId.trim() || bootstrapMutation.isPending}>
              {bootstrapMutation.isPending ? 'Bootstrapping...' : 'Bootstrap next season'}
            </button>
          </div>
        </form>

        <ActionStatusBlock
          errorText={
            bootstrapMutation.error ? `Could not bootstrap next season: ${formatApiError(bootstrapMutation.error)}` : undefined
          }
        />

        {bootstrapMutation.data ? (
          <>
            <SummaryPills
              items={[
                { label: 'Child run', value: bootstrapMutation.data.bootstrap.child_run_id },
                { label: 'To season', value: bootstrapMutation.data.bootstrap.to_season },
                { label: 'Transitioned players', value: bootstrapMutation.data.bootstrap.transitioned_players },
                {
                  label: 'Status',
                  value: bootstrapMutation.data.bootstrap.already_bootstrapped ? 'Already bootstrapped' : 'Created'
                }
              ]}
            />
            <p>
              <Link to={`/runs/${bootstrapMutation.data.bootstrap.child_run_id}`}>Open child run</Link>
            </p>
            <JsonPayloadBlock
              title="Bootstrap payload"
              payload={bootstrapMutation.data.bootstrap}
              emptyText="No bootstrap payload available."
            />
          </>
        ) : null}
      </SectionCard>
    </section>
  )
}
