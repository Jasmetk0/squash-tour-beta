import { useQuery } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createRun, getHealth, getRun } from '../api/client'
import { SUPPORTED_CALENDAR_SEASON } from '../config'

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate()
  const [createInput, setCreateInput] = useState({ run_id: 'mvp-run', seed: 42, season: SUPPORTED_CALENDAR_SEASON })
  const [loadRunId, setLoadRunId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const health = useQuery({ queryKey: ['health'], queryFn: getHealth })

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    try {
      const run = await createRun(createInput)
      localStorage.setItem('beta_engine:last_run_id', run.run_id)
      navigate(`/runs/${run.run_id}`)
    } catch (err) {
      setError(`Could not create run: ${String(err)}`)
    }
  }

  const onLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    try {
      const run = await getRun(loadRunId)
      localStorage.setItem('beta_engine:last_run_id', run.run.run_id)
      navigate(`/runs/${run.run.run_id}`)
    } catch (err) {
      setError(`Could not load run: ${String(err)}`)
    }
  }

  return (
    <section className="panel">
      <h2>Dashboard</h2>
      <p>Use this MVP UI to create or load a deterministic simulation run from the API.</p>
      <p className="status">Health: {health.data?.status ?? (health.isLoading ? 'checking...' : 'unavailable')}</p>
      {error && <p className="error">{error}</p>}

      <div className="grid">
        <form className="panel" onSubmit={onCreate}>
          <h3>Create run</h3>
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
          <button type="submit">Initialize Simulation Run</button>
        </form>

        <form className="panel" onSubmit={onLoad}>
          <h3>Load existing run</h3>
          <label>
            Run ID
            <input value={loadRunId} onChange={(e) => setLoadRunId(e.target.value)} required />
          </label>
          <button type="submit">Load Run Summary</button>
        </form>
      </div>
    </section>
  )
}
