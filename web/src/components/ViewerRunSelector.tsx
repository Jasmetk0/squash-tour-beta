import { useQuery } from '@tanstack/react-query'
import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { listRuns } from '../api/client'
import {
  LAST_RUN_ID_STORAGE_KEY,
  VIEWER_ACTIVE_RUN_STORAGE_KEY,
  VIEWER_ACTIVE_RUN_CHANGED_EVENT,
  readLastRunId,
  readViewerActiveRunId,
  writeViewerActiveRunId
} from '../viewer/activeRun'
import { viewerRunsPath } from '../viewer/viewerRoutes'

type ViewerRunSelectorProps = {
  compact?: boolean
}

function useViewerRunSelection() {
  const [activeRunId, setActiveRunId] = useState(() => readViewerActiveRunId())
  const [selectedRunId, setSelectedRunId] = useState(() => readViewerActiveRunId() ?? '')

  const runsQuery = useQuery({
    queryKey: ['viewer-run-selector-runs'],
    queryFn: listRuns,
    retry: false
  })

  const runs = runsQuery.data?.runs ?? []

  useEffect(() => {
    function handleActiveRunChange(): void {
      const nextActiveRunId = readViewerActiveRunId()
      setActiveRunId(nextActiveRunId)
      if (nextActiveRunId) setSelectedRunId(nextActiveRunId)
    }

    window.addEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, handleActiveRunChange)
    window.addEventListener('storage', handleActiveRunChange)
    return () => {
      window.removeEventListener(VIEWER_ACTIVE_RUN_CHANGED_EVENT, handleActiveRunChange)
      window.removeEventListener('storage', handleActiveRunChange)
    }
  }, [])

  useEffect(() => {
    if (runs.length === 0) return
    if (selectedRunId && runs.some((run) => run.run_id === selectedRunId)) return
    const preferredRunId = activeRunId ?? readLastRunId()
    const preferredRun = runs.find((run) => run.run_id === preferredRunId)
    setSelectedRunId((preferredRun ?? runs[0]).run_id)
  }, [activeRunId, runs, selectedRunId])

  function applyRunSelection(runId: string): void {
    const normalizedRunId = runId.trim()
    if (!normalizedRunId) return
    window.localStorage.setItem(LAST_RUN_ID_STORAGE_KEY, normalizedRunId)
    writeViewerActiveRunId(normalizedRunId)
    setActiveRunId(normalizedRunId)
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    applyRunSelection(selectedRunId)
  }

  return { activeRunId, selectedRunId, setSelectedRunId, applyRunSelection, runsQuery, runs, handleSubmit }
}

export function ViewerActiveRunCompact(): JSX.Element {
  const { activeRunId, selectedRunId, setSelectedRunId, applyRunSelection, runsQuery, runs } = useViewerRunSelection()

  return (
    <form className="viewer-active-run-compact" aria-label="Viewer topbar active run">
      <span className="viewer-active-run-compact__status">
        Active run: <strong>{activeRunId ?? 'None'}</strong>
      </span>
      <label className="viewer-active-run-compact__field">
        <span className="sr-only">Viewer active run</span>
        <select
          aria-label="Viewer active run"
          value={selectedRunId}
          onChange={(event) => {
            setSelectedRunId(event.target.value)
            applyRunSelection(event.target.value)
          }}
          disabled={runsQuery.isLoading || runs.length === 0}
        >
          {runs.length === 0 ? <option value="">No runs available</option> : null}
          {runs.map((run) => (
            <option key={run.run_id} value={run.run_id}>
              {run.run_id} · S{run.season} · seed {run.seed}
            </option>
          ))}
        </select>
      </label>
      {runsQuery.isError ? <span className="error">Runs unavailable</span> : null}
    </form>
  )
}

export function ViewerRunSelector({ compact = false }: ViewerRunSelectorProps): JSX.Element {
  const { activeRunId, selectedRunId, setSelectedRunId, runsQuery, runs, handleSubmit } = useViewerRunSelection()

  return (
    <section className={compact ? 'viewer-run-selector viewer-run-selector--compact' : 'panel nested-panel viewer-run-selector'} aria-label="Active run picker">
      <div className="page-intro">
        <span className="eyebrow">Active run</span>
        <h3>Active Run</h3>
        <p className="subtitle">Select which existing run Viewer / MSA Website Mode should browse. This only changes local Viewer context.</p>
      </div>

      <p className="status">
        Current active run id: <strong>{activeRunId ?? 'No active run selected'}</strong>
      </p>
      <p className="metadata-note">
        Viewer selection is stored locally in <code>{VIEWER_ACTIVE_RUN_STORAGE_KEY}</code>; no backend run state is changed.
      </p>
      <p className="viewer-active-run-actions">
        <Link className="viewer-active-run-link" to={viewerRunsPath()}>Browse all runs</Link>
      </p>

      <form className="stacked-form" onSubmit={handleSubmit}>
        <label>
          Available runs
          <select
            value={selectedRunId}
            onChange={(event) => setSelectedRunId(event.target.value)}
            disabled={runsQuery.isLoading || runs.length === 0}
          >
            {runs.length === 0 ? <option value="">No runs available</option> : null}
            {runs.map((run) => (
              <option key={run.run_id} value={run.run_id}>
                {run.run_id} — season {run.season}, seed {run.seed}
              </option>
            ))}
          </select>
        </label>
        <div className="actions">
          <button type="submit" disabled={!selectedRunId.trim()}>
            Set active run
          </button>
        </div>
      </form>

      {runsQuery.isLoading ? <p className="status">Loading available runs…</p> : null}
      {runsQuery.isError ? <p className="error">Run list is unavailable.</p> : null}
      {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? <p className="status">No runs are available yet.</p> : null}
    </section>
  )
}
