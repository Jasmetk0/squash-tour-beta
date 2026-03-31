import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { bootstrapNextSeason, getRunLineage, getRunSource } from '../api/client'
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

export function BootstrapLineagePage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const [childRunId, setChildRunId] = useState('')
  const [childSeedInput, setChildSeedInput] = useState('')

  const sourceQuery = useQuery({
    queryKey: ['run-source', runId],
    queryFn: () => getRunSource(runId),
    enabled: Boolean(runId)
  })

  const lineageQuery = useQuery({
    queryKey: ['run-lineage', runId],
    queryFn: () => getRunLineage(runId),
    enabled: Boolean(runId)
  })

  const bootstrapMutation = useMutation({
    mutationFn: () => {
      const childSeed = childSeedInput.trim() === '' ? undefined : Number(childSeedInput)
      return bootstrapNextSeason(runId, {
        child_run_id: childRunId,
        ...(childSeed !== undefined ? { child_seed: childSeed } : {})
      })
    },
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-source', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-lineage', runId] })
      ])
    }
  })

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!childRunId.trim()) return
    bootstrapMutation.mutate()
  }

  const source = sourceQuery.data?.source
  const lineage = lineageQuery.data?.lineage
  const sourceNotFound = isApiNotFound(sourceQuery.error)
  const lineageNotFound = isApiNotFound(lineageQuery.error)

  return (
    <section className="panel">
      <RunScopedHeader
        title="Bootstrap / Lineage"
        runId={runId}
        subtitle="Review source/lineage metadata and bootstrap the next-season child run."
      />

      <SectionCard title="Run source summary">
        {sourceQuery.isLoading && <p className="status">Loading source metadata...</p>}
        {sourceNotFound && <EmptyState message="No source metadata is available for this run." />}
        {sourceQuery.error && !sourceNotFound && <p className="error">Failed to load run source: {formatApiError(sourceQuery.error)}</p>}
        {source && (
          <>
            <SummaryPills
              items={[
                { label: 'Source type', value: source.source_type },
                { label: 'Parent linked', value: source.parent_run_id ? 'Yes' : 'No' },
                { label: 'Rollover source linked', value: source.source_rollover_run_id ? 'Yes' : 'No' }
              ]}
            />
            <MetadataList
              items={[
                { label: 'Parent run ID', value: source.parent_run_id ?? 'None' },
                { label: 'Rollover source run', value: source.source_rollover_run_id ?? 'None' },
                { label: 'Rollover from season', value: source.source_rollover_from_season ?? 'None' },
                { label: 'Rollover to season', value: source.source_rollover_to_season ?? 'None' }
              ]}
            />
          </>
        )}
      </SectionCard>

      <SectionCard title="Lineage summary and navigation">
        {lineageQuery.isLoading && <p className="status">Loading lineage metadata...</p>}
        {lineageNotFound && <EmptyState message="No lineage record is available for this run yet." />}
        {lineageQuery.error && !lineageNotFound && (
          <p className="error">Failed to load run lineage: {formatApiError(lineageQuery.error)}</p>
        )}
        {lineage && (
          <>
            <SummaryPills
              items={[
                { label: 'Current run', value: lineage.run_id },
                { label: 'Parent runs', value: lineage.source.parent_run_id ? 1 : 0 },
                { label: 'Child runs', value: lineage.children.length }
              ]}
            />

            <h4>Parent run</h4>
            {lineage.source.parent_run_id ? (
              <p>
                <Link to={`/runs/${lineage.source.parent_run_id}`}>{lineage.source.parent_run_id}</Link>
              </p>
            ) : (
              <EmptyState message="No parent run linked for this run." />
            )}

            <h4>Child runs</h4>
            {lineage.children.length === 0 ? (
              <EmptyState message="No child runs yet." />
            ) : (
              <ul className="item-list">
                {lineage.children.map((child) => (
                  <li key={child}>
                    <Link to={`/runs/${child}`}>{child}</Link>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </SectionCard>

      <SectionCard title="Bootstrap next season child run">
        <form onSubmit={handleSubmit}>
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

        {bootstrapMutation.data && (
          <div>
            <SummaryPills
              items={[
                { label: 'Child run', value: bootstrapMutation.data.bootstrap.child_run_id },
                { label: 'To season', value: bootstrapMutation.data.bootstrap.to_season },
                { label: 'Transitioned players', value: bootstrapMutation.data.bootstrap.transitioned_players },
                { label: 'Status', value: bootstrapMutation.data.bootstrap.already_bootstrapped ? 'Already bootstrapped' : 'Created' }
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
          </div>
        )}
      </SectionCard>
    </section>
  )
}
