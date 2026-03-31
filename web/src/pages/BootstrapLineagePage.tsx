import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { ApiError, bootstrapNextSeason, getRunLineage, getRunSource } from '../api/client'

function extractReadableError(error: unknown): string {
  if (error instanceof ApiError) {
    try {
      const parsed = JSON.parse(error.message) as { detail?: string }
      if (parsed.detail) return parsed.detail
    } catch {
      // Fallback to raw response body when error payload is not JSON.
    }
    return error.message
  }

  if (error instanceof Error) return error.message
  return String(error)
}

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

  return (
    <section className="panel">
      <h2>Bootstrap / Lineage</h2>
      <p className="status">Run: {runId || 'unknown'}</p>

      <article className="panel nested-panel">
        <h3>Run source summary</h3>
        {sourceQuery.isLoading && <p className="status">Loading source metadata...</p>}
        {sourceQuery.error && <p className="error">Failed to load run source: {extractReadableError(sourceQuery.error)}</p>}
        {source && (
          <dl className="kv-grid">
            <div>
              <dt>Source type</dt>
              <dd>{source.source_type}</dd>
            </div>
            <div>
              <dt>Parent run ID</dt>
              <dd>{source.parent_run_id ?? 'None'}</dd>
            </div>
            <div>
              <dt>Rollover source run</dt>
              <dd>{source.source_rollover_run_id ?? 'None'}</dd>
            </div>
            <div>
              <dt>Rollover from season</dt>
              <dd>{source.source_rollover_from_season ?? 'None'}</dd>
            </div>
            <div>
              <dt>Rollover to season</dt>
              <dd>{source.source_rollover_to_season ?? 'None'}</dd>
            </div>
          </dl>
        )}
      </article>

      <article className="panel nested-panel">
        <h3>Lineage summary</h3>
        {lineageQuery.isLoading && <p className="status">Loading lineage metadata...</p>}
        {lineageQuery.error && <p className="error">Failed to load run lineage: {extractReadableError(lineageQuery.error)}</p>}
        {lineage && (
          <>
            <dl className="kv-grid">
              <div>
                <dt>Lineage run ID</dt>
                <dd>{lineage.run_id}</dd>
              </div>
              <div>
                <dt>Child runs</dt>
                <dd>{lineage.children.length}</dd>
              </div>
            </dl>

            <h4>Parent run</h4>
            {lineage.source.parent_run_id ? (
              <p>
                <Link to={`/runs/${lineage.source.parent_run_id}`}>{lineage.source.parent_run_id}</Link>
              </p>
            ) : (
              <p className="status">No parent run linked for this run.</p>
            )}

            <h4>Child runs</h4>
            {lineage.children.length === 0 ? (
              <p className="status">No child runs yet.</p>
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
      </article>

      <article className="panel nested-panel">
        <h3>Bootstrap next season child run</h3>
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

        {bootstrapMutation.error && (
          <p className="error">Could not bootstrap next season: {extractReadableError(bootstrapMutation.error)}</p>
        )}

        {bootstrapMutation.data && (
          <div>
            <p className="status">
              Bootstrap complete for child run <strong>{bootstrapMutation.data.bootstrap.child_run_id}</strong>
              {bootstrapMutation.data.bootstrap.already_bootstrapped ? ' (already bootstrapped).' : '.'}
            </p>
            <p>
              <Link to={`/runs/${bootstrapMutation.data.bootstrap.child_run_id}`}>Open child run</Link>
            </p>
            <pre className="json-block">{JSON.stringify(bootstrapMutation.data.bootstrap, null, 2)}</pre>
          </div>
        )}
      </article>
    </section>
  )
}
