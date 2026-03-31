import { useQuery } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createRun, getHealth, getRun } from '../api/client'
import { EmptyState, PageIntro } from '../components/RunScopedUi'
import { SUPPORTED_CALENDAR_SEASON } from '../config'
import { formatApiError } from '../utils/apiErrors'

type CreateInputState = {
  run_id: string
  seed: number
  season: number
}

const LAST_RUN_ID_STORAGE_KEY = 'beta_engine:last_run_id'

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate()
  const [createInput, setCreateInput] = useState<CreateInputState>({
    run_id: 'mvp-run',
    seed: 42,
    season: SUPPORTED_CALENDAR_SEASON
  })
  const [loadRunId, setLoadRunId] = useState('')
  const [lastRunId, setLastRunId] = useState(() => localStorage.getItem(LAST_RUN_ID_STORAGE_KEY))
  const [isCreating, setIsCreating] = useState(false)
  const [openingTarget, setOpeningTarget] = useState<'manual' | 'resume' | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)
  const [resumeError, setResumeError] = useState<string | null>(null)

  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: false })
  const rememberedRunQuery = useQuery({
    queryKey: ['dashboard-remembered-run', lastRunId],
    queryFn: () => getRun(lastRunId ?? ''),
    enabled: Boolean(lastRunId),
    retry: false
  })

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCreateError(null)
    setIsCreating(true)
    try {
      const run = await createRun(createInput)
      localStorage.setItem(LAST_RUN_ID_STORAGE_KEY, run.run_id)
      setLastRunId(run.run_id)
      navigate(`/runs/${run.run_id}`)
    } catch (err) {
      setCreateError(`Could not create run: ${formatApiError(err)}`)
    } finally {
      setIsCreating(false)
    }
  }

  const openRunById = async (runId: string, target: 'manual' | 'resume') => {
    const setError = target === 'manual' ? setOpenError : setResumeError
    setError(null)
    setOpeningTarget(target)
    try {
      const run = await getRun(runId)
      localStorage.setItem(LAST_RUN_ID_STORAGE_KEY, run.run.run_id)
      setLastRunId(run.run.run_id)
      navigate(`/runs/${run.run.run_id}`)
    } catch (err) {
      setError(`Could not open run: ${formatApiError(err)}`)
    } finally {
      setOpeningTarget(null)
    }
  }

  const onLoad = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await openRunById(loadRunId, 'manual')
  }

  return (
    <section className="panel">
      <PageIntro title="Dashboard" subtitle="Launch a deterministic simulation run or open an existing run from the API." />

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

        <section className="panel" aria-labelledby="dashboard-resume-heading">
          <h3 id="dashboard-resume-heading">Resume remembered run</h3>
          {lastRunId ? (
            <>
              <p className="status">Remembered run ID: {lastRunId}</p>
              {rememberedRunQuery.isLoading && <p className="status">Loading remembered run summary...</p>}
              {rememberedRunQuery.data && (
                <dl className="kv-grid">
                  <div>
                    <dt>Season</dt>
                    <dd>{rememberedRunQuery.data.run.season}</dd>
                  </div>
                  <div>
                    <dt>Seed</dt>
                    <dd>{rememberedRunQuery.data.run.seed}</dd>
                  </div>
                  <div>
                    <dt>Progress</dt>
                    <dd>
                      {rememberedRunQuery.data.run.next_event_index} / {rememberedRunQuery.data.run.total_events}
                    </dd>
                  </div>
                </dl>
              )}
              {rememberedRunQuery.isError && <p className="status">Summary unavailable until this run is opened again.</p>}
              <div className="dashboard-actions-row">
                <button
                  type="button"
                  disabled={openingTarget !== null}
                  onClick={() => {
                    void openRunById(lastRunId, 'resume')
                  }}
                >
                  {openingTarget === 'resume' ? 'Resuming...' : 'Resume Run'}
                </button>
                <button
                  type="button"
                  disabled={openingTarget !== null}
                  onClick={() => {
                    localStorage.removeItem(LAST_RUN_ID_STORAGE_KEY)
                    setLastRunId(null)
                    setResumeError(null)
                  }}
                >
                  Clear remembered run
                </button>
              </div>
              <p className="status">
                Quick links:{' '}
                <Link to={`/runs/${lastRunId}`}>Run Detail</Link> · <Link to={`/runs/${lastRunId}/events`}>Events</Link> ·{' '}
                <Link to={`/runs/${lastRunId}/finals`}>Finals</Link>
              </p>
            </>
          ) : (
            <EmptyState message="No remembered run yet. Create or open a run to enable quick resume." />
          )}
          {resumeError && <p className="error">{resumeError}</p>}
        </section>

        <form className="panel" aria-labelledby="dashboard-create-heading" onSubmit={onCreate}>
          <h3 id="dashboard-create-heading">Create run</h3>
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
            {isCreating ? 'Creating...' : 'Create and open run'}
          </button>
          {createError && <p className="error">{createError}</p>}
        </form>

        <form className="panel" aria-labelledby="dashboard-open-heading" onSubmit={onLoad}>
          <h3 id="dashboard-open-heading">Open run by ID</h3>
          <label>
            Existing run ID
            <input value={loadRunId} onChange={(e) => setLoadRunId(e.target.value)} required />
          </label>
          <button type="submit" disabled={openingTarget !== null}>
            {openingTarget === 'manual' ? 'Opening...' : 'Open and continue'}
          </button>
          {openError && <p className="error">{openError}</p>}
        </form>
      </div>
    </section>
  )
}
