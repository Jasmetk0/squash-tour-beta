import { useQuery } from '@tanstack/react-query'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { listRuns } from '../api/client'
import { formatApiError } from '../utils/apiErrors'
import {
  LAST_RUN_ID_STORAGE_KEY,
  VIEWER_ACTIVE_RUN_STORAGE_KEY,
  clearViewerActiveRunId,
  readLastRunId,
  readViewerActiveRunId,
  writeViewerActiveRunId
} from '../viewer/activeRun'

type ViewerRunSelectorProps = {
  compact?: boolean
}

export function ViewerRunSelector({ compact = false }: ViewerRunSelectorProps): JSX.Element {
  const [activeRunId, setActiveRunId] = useState(() => readViewerActiveRunId())
  const [manualRunId, setManualRunId] = useState(() => readViewerActiveRunId() ?? readLastRunId() ?? '')
  const [selectedRunId, setSelectedRunId] = useState(() => readViewerActiveRunId() ?? readLastRunId() ?? '')

  const runsQuery = useQuery({
    queryKey: ['viewer-run-selector-runs'],
    queryFn: listRuns,
    retry: false
  })

  const runs = runsQuery.data?.runs ?? []
  const lastRunId = readLastRunId()
  const suggestedRunId = activeRunId ? null : lastRunId
  const effectiveInputRunId = manualRunId.trim() || selectedRunId.trim()

  useEffect(() => {
    if (runs.length === 0) return
    if (selectedRunId && runs.some((run) => run.run_id === selectedRunId)) return
    const preferredRunId = activeRunId ?? lastRunId
    const preferredRun = runs.find((run) => run.run_id === preferredRunId)
    setSelectedRunId((preferredRun ?? runs[0]).run_id)
  }, [activeRunId, lastRunId, runs, selectedRunId])

  const activeRunLinks = useMemo(() => {
    if (!activeRunId) return []
    return [
      { label: 'Rankings', to: `/viewer/runs/${activeRunId}/rankings` },
      { label: 'Tournaments', to: `/viewer/runs/${activeRunId}/tournaments` },
      { label: 'Players', to: `/viewer/runs/${activeRunId}/players` },
      { label: 'Countries', to: `/viewer/runs/${activeRunId}/countries` },
      { label: 'History', to: `/viewer/runs/${activeRunId}/history` }
    ]
  }, [activeRunId])

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (!effectiveInputRunId) return
    writeViewerActiveRunId(effectiveInputRunId)
    window.localStorage.setItem(LAST_RUN_ID_STORAGE_KEY, effectiveInputRunId)
    setActiveRunId(effectiveInputRunId)
    setManualRunId(effectiveInputRunId)
    setSelectedRunId(effectiveInputRunId)
  }

  function handleClear(): void {
    clearViewerActiveRunId()
    setActiveRunId(null)
  }

  return (
    <section className={compact ? 'viewer-run-selector viewer-run-selector--compact' : 'panel nested-panel viewer-run-selector'}>
      <div className="page-intro">
        <h3>Viewer active run</h3>
        <p className="subtitle">Choose the generated world/run that Viewer / MSA Website Mode should browse.</p>
      </div>

      <p className="status">
        Current selected run: <strong>{activeRunId ?? 'No Viewer run selected'}</strong>
      </p>
      {suggestedRunId ? <p className="status">Suggested from last Admin run: {suggestedRunId}</p> : null}
      <p className="metadata-note">
        Viewer selection is stored in <code>{VIEWER_ACTIVE_RUN_STORAGE_KEY}</code>. Admin resume flows can still use{' '}
        <code>{LAST_RUN_ID_STORAGE_KEY}</code>.
      </p>

      <form className="stacked-form" onSubmit={handleSubmit}>
        <label>
          Select existing run
          <select
            value={selectedRunId}
            onChange={(event) => {
              setSelectedRunId(event.target.value)
              setManualRunId(event.target.value)
            }}
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
        <label>
          Or enter run ID manually
          <input value={manualRunId} onChange={(event) => setManualRunId(event.target.value)} placeholder="run-id" />
        </label>
        <div className="actions">
          <button type="submit" disabled={!effectiveInputRunId}>
            Set as Viewer Run
          </button>
          <button type="button" onClick={handleClear} disabled={!activeRunId}>
            Clear Viewer Run
          </button>
          {activeRunId ? <Link to={`/admin/runs/${activeRunId}`}>Open Admin Run Detail</Link> : <Link to="/admin/runs">Open Admin Runs</Link>}
        </div>
      </form>

      {runsQuery.isLoading ? <p className="status">Loading available runs…</p> : null}
      {runsQuery.isError ? <p className="error">Could not load runs: {formatApiError(runsQuery.error)}</p> : null}
      {!runsQuery.isLoading && !runsQuery.isError && runs.length === 0 ? (
        <p className="status">No runs were returned by the API. You can still enter a run ID manually.</p>
      ) : null}

      {activeRunLinks.length > 0 ? (
        <div className="actions" aria-label="Viewer active run quick links">
          {activeRunLinks.map((link) => (
            <Link key={link.to} to={link.to}>
              {link.label}
            </Link>
          ))}
        </div>
      ) : null}
    </section>
  )
}
