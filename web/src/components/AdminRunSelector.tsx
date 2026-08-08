import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { listRunContainers } from '../api/client'
import type { RunContainer } from '../api/types'
import { adminRunSwitchTarget } from '../navigation/adminRunSwitchTarget'
import { formatApiError } from '../utils/apiErrors'

type AdminRunSelectorProps = {
  pathname: string
  runId: string
}

function validRunContainers(value: unknown): RunContainer[] {
  return Array.isArray(value)
    ? value.filter((run): run is RunContainer => typeof run === 'object' && run !== null && typeof (run as RunContainer).run_id === 'string' && Boolean((run as RunContainer).run_id.trim()))
    : []
}

export function AdminRunSelector({ pathname, runId }: AdminRunSelectorProps): JSX.Element {
  const navigate = useNavigate()
  const query = useQuery({ queryKey: ['admin-run-containers'], queryFn: listRunContainers, retry: false })
  const runs = validRunContainers(query.data?.run_containers)
  const currentRun = runs.find(run => run.run_id === runId)
  const currentLabel = currentRun?.display_name?.trim() || runId
  const currentIsMissing = !runs.some(run => run.run_id === runId)

  return (
    <div className="admin-active-run-compact" aria-label="Admin Run context">
      <span className="admin-active-run-compact__status">Run <strong>{currentLabel}</strong></span>
      <label className="admin-active-run-compact__field">
        <span className="sr-only">Admin active Run</span>
        <select
          aria-label="Admin active Run"
          value={runId}
          onChange={event => navigate(adminRunSwitchTarget(pathname, event.target.value))}
          disabled={query.isLoading || runs.length === 0}
        >
          {currentIsMissing ? <option value={runId}>{runId}</option> : null}
          {runs.map(run => <option key={run.run_id} value={run.run_id}>{run.display_name?.trim() || run.run_id}</option>)}
        </select>
      </label>
      {query.isLoading ? <span className="sr-only">Loading available Runs</span> : null}
      {query.isError ? <span className="sr-only">Run metadata unavailable: {formatApiError(query.error)}</span> : null}
    </div>
  )
}
