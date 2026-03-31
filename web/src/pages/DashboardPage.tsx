import { useQuery } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createRun, getHealth, getRun } from '../api/client'
import { SUPPORTED_CALENDAR_SEASON } from '../config'
import { formatApiError } from '../utils/apiErrors'

type CreateInputState = {
  run_id: string
  seed: number
  season: number
}

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate()
  const [createInput, setCreateInput] = useState<CreateInputState>({
    run_id: 'mvp-run',
    seed: 42,
    season: SUPPORTED_CALENDAR_SEASON
  })
  const [loadRunId, setLoadRunId] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isOpening, setIsOpening] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)

  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: false })

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCreateError(null)
    setIsCreating(true)
    try {
      const run = await createRun(createInput)
      localStorage.setItem('beta_engine:last_run_id', run.run_id)
      navigate(`/runs/${run.run_id}`)
    } catch (err) {
      setCreateError(`Could not create run: ${formatApiError(err)}`)
    } finally {
      setIsCreating(false)
    }
  }

  const onLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setOpenError(null)
    setIsOpening(true)
    try {
      const run = await getRun(loadRunId)
      localStorage.setItem('beta_engine:last_run_id', run.run.run_id)
      navigate(`/runs/${run.run.run_id}`)
    } catch (err) {
      setOpenError(`Could not open run: ${formatApiError(err)}`)
    } finally {
      setIsOpening(false)
    }
  }

  return (
    <section className="panel">
      <h2>Dashboard</h2>
      <p className="subtitle">Launch a deterministic simulation run or open an existing run from the API.</p>

      <div className="grid">
        <section className="panel" aria-labelledby="dashboard-health-heading">
          <h3 id="dashboard-health-heading">System / API health</h3>
          {health.isLoading && <p className="status">Checking API health…</p>}
          {health.data && <p className="status">API status: {health.data.status}</p>}
          {health.isError && <p className="error">Health check unavailable: {formatApiError(health.error)}</p>}
        </section>

        <section className="panel" aria-labelledby="dashboard-help-heading">
          <h3 id="dashboard-help-heading">How to use this MVP</h3>
          <ul className="dashboard-help-list">
            <li>Create a run with a unique run ID, seed, and season.</li>
            <li>Open any existing run using its run ID.</li>
            <li>After launch/open, continue from Run Detail and its linked views.</li>
          </ul>
          <p className="status">Supported season default: {SUPPORTED_CALENDAR_SEASON}.</p>
        </section>

        <form className="panel" aria-labelledby="dashboard-create-heading" onSubmit={onCreate}>
          <h3 id="dashboard-create-heading">Create new simulation run</h3>
          <label>
            Run ID
            <input
              value={createInput.run_id}
              onChange={(e) => setCreateInput((v) => ({ ...v, run_id: e.target.value }))}
              required
            />
          </label>
          <label>
            Seed
            <input
              type="number"
              value={createInput.seed}
              onChange={(e) => setCreateInput((v) => ({ ...v, seed: Number(e.target.value) }))}
              required
            />
          </label>
          <label>
            Season
            <input
              type="number"
              value={createInput.season}
              onChange={(e) => setCreateInput((v) => ({ ...v, season: Number(e.target.value) }))}
              required
            />
          </label>
          <button type="submit" disabled={isCreating}>
            {isCreating ? 'Initializing...' : 'Initialize Simulation Run'}
          </button>
          {createError && <p className="error">{createError}</p>}
        </form>

        <form className="panel" aria-labelledby="dashboard-open-heading" onSubmit={onLoad}>
          <h3 id="dashboard-open-heading">Open existing run</h3>
          <label>
            Existing run ID
            <input value={loadRunId} onChange={(e) => setLoadRunId(e.target.value)} required />
          </label>
          <button type="submit" disabled={isOpening}>
            {isOpening ? 'Opening...' : 'Open Run'}
          </button>
          {openError && <p className="error">{openError}</p>}
        </form>
      </div>
    </section>
  )
}
