import { useQuery } from '@tanstack/react-query'
import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { createRun, getHealth, getRun, getRunLineage, getRunSource, getRunStatusSummary, listRuns, listWorldPackages } from '../api/client'
import { CompactSummaryCard, EmptyState, MetadataList, PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'
import {
  MSA_SEASON_WEEK_COUNT,
  MSA_TIMELINE_END_LABEL,
  MSA_TIMELINE_SEASON_COUNT,
  MSA_TIMELINE_START_LABEL,
  MSA_TIMELINE_START_YEAR
} from '../config'
import { formatApiError } from '../utils/apiErrors'
import { clearLastRunId, readLastRunId, writeLastRunId } from '../viewer/activeRun'

type CreateInputState = {
  run_id: string
  seed: number
  season: number
}


function formatProgress(nextEventIndex: number, totalEvents: number): string {
  return `${nextEventIndex} / ${totalEvents}`
}

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate()
  const [createInput, setCreateInput] = useState<CreateInputState>({
    run_id: 'mvp-run',
    seed: 42,
    season: MSA_TIMELINE_START_YEAR
  })
  const [worldId, setWorldId] = useState('official_fax_world')
  const [loadRunId, setLoadRunId] = useState('')
  const [lastRunId, setLastRunId] = useState(() => readLastRunId())
  const [isCreating, setIsCreating] = useState(false)
  const [openingTarget, setOpeningTarget] = useState<'manual' | 'resume' | null>(null)
  const [createError, setCreateError] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)
  const [resumeError, setResumeError] = useState<string | null>(null)
  const [runsFilter, setRunsFilter] = useState('')

  const health = useQuery({ queryKey: ['health'], queryFn: getHealth, retry: false })
  const rememberedRunQuery = useQuery({
    queryKey: ['dashboard-remembered-run', lastRunId],
    queryFn: () => getRunStatusSummary(lastRunId ?? ''),
    enabled: Boolean(lastRunId),
    retry: false
  })
  const rememberedRunSourceQuery = useQuery({
    queryKey: ['dashboard-remembered-run-source', lastRunId],
    queryFn: () => getRunSource(lastRunId ?? ''),
    enabled: Boolean(lastRunId),
    retry: false
  })
  const rememberedRunLineageQuery = useQuery({
    queryKey: ['dashboard-remembered-run-lineage', lastRunId],
    queryFn: () => getRunLineage(lastRunId ?? ''),
    enabled: Boolean(lastRunId),
    retry: false
  })
  const runsQuery = useQuery({
    queryKey: ['dashboard-runs-index'],
    queryFn: listRuns,
    retry: false
  })
  const worldPackagesQuery = useQuery({
    queryKey: ['dashboard-world-packages'],
    queryFn: listWorldPackages,
    retry: false
  })

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setCreateError(null)
    setIsCreating(true)
    try {
      const run = await createRun(worldId === 'official_fax_world' ? createInput : { ...createInput, world_id: worldId })
      writeLastRunId(run.run_id)
      setLastRunId(run.run_id)
      navigate(`/admin/runs/${run.run_id}`)
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
      writeLastRunId(run.run.run_id)
      setLastRunId(run.run.run_id)
      navigate(`/admin/runs/${run.run.run_id}`)
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

  const rememberedRunSource = rememberedRunSourceQuery.data?.source
  const rememberedRunLineage = rememberedRunLineageQuery.data?.lineage
  const rememberedRunChildren = rememberedRunLineage?.children ?? []
  const hasLineageSignal = Boolean(rememberedRunSource?.parent_run_id) || rememberedRunChildren.length > 0

  const nextInspectionLinks =
    lastRunId && rememberedRunQuery.data
      ? [
          { label: 'Run Detail', href: `/admin/runs/${lastRunId}` },
          { label: 'Diagnostics', href: `/admin/runs/${lastRunId}/diagnostics` },
          ...(hasLineageSignal ? [{ label: 'Season Chain', href: `/admin/runs/${lastRunId}/season-chain` }] : []),
          ...(rememberedRunQuery.data.finals.qualification_available && !rememberedRunQuery.data.finals.result_available
            ? [{ label: 'Finals', href: `/admin/runs/${lastRunId}/finals` }]
            : []),
          ...(rememberedRunQuery.data.rollover ? [{ label: 'Rollover', href: `/admin/runs/${lastRunId}/rollover` }] : []),
          ...(rememberedRunSource ? [{ label: 'Bootstrap / Lineage', href: `/admin/runs/${lastRunId}/bootstrap-lineage` }] : [])
        ]
      : []
  const filteredRuns =
    runsQuery.data?.runs.filter((run) => run.run_id.toLowerCase().includes(runsFilter.trim().toLowerCase())) ?? []

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
            <li>Create a root run with a unique run ID and seed.</li>
            <li>Open any existing run using its run ID.</li>
            <li>After launch/open, continue from Run Detail and its linked views.</li>
            <li>Inspect Official FAX World countries in the <Link to="/admin/world/library/official_fax_world/countries">World Package library</Link>.</li>
          </ul>
          <p className="status">New root runs start at {MSA_TIMELINE_START_LABEL}; later seasons continue through rollover/bootstrap child runs.</p>
        </section>

        <section className="panel" aria-labelledby="dashboard-resume-heading">
          <h3 id="dashboard-resume-heading">Resume remembered run</h3>
          {lastRunId ? (
            <>
              <p className="status">Remembered run ID: {lastRunId}</p>
              {rememberedRunQuery.isLoading && <p className="status">Loading remembered run summary...</p>}
              {rememberedRunQuery.data && (
                <>
                  <CompactSummaryCard
                    items={[
                      { label: 'Run ID', value: rememberedRunQuery.data.run_id },
                      { label: 'Season', value: rememberedRunQuery.data.season },
                      { label: 'Seed', value: rememberedRunQuery.data.seed },
                      {
                        label: 'Progress',
                        value: formatProgress(
                          rememberedRunQuery.data.progress.next_event_index,
                          rememberedRunQuery.data.progress.total_events
                        )
                      }
                    ]}
                  />
                  <SummaryPills
                    items={[
                      { label: 'Completed events', value: rememberedRunQuery.data.progress.completed_event_count },
                      { label: 'History events', value: rememberedRunQuery.data.history_counts.events },
                      { label: 'Ranking snapshots', value: rememberedRunQuery.data.history_counts.ranking_snapshots },
                      { label: 'Race snapshots', value: rememberedRunQuery.data.history_counts.race_snapshots },
                      {
                        label: 'Finals',
                        value: rememberedRunQuery.data.finals.qualification_available
                          ? rememberedRunQuery.data.finals.result_available
                            ? 'Completed'
                            : 'Ready'
                          : 'Not qualified yet'
                      },
                      {
                        label: 'Rollover',
                        value: rememberedRunQuery.data.rollover
                          ? `Latest: ${rememberedRunQuery.data.rollover.latest_to_season}`
                          : 'None'
                      }
                    ]}
                  />
                  <MetadataList
                    items={[
                      {
                        label: 'Source type',
                        value: rememberedRunSource?.source_type ?? rememberedRunQuery.data.source?.source_type ?? 'N/A'
                      },
                      {
                        label: 'Parent run',
                        value: rememberedRunSource?.parent_run_id ?? rememberedRunQuery.data.source?.parent_run_id ?? 'None'
                      },
                      {
                        label: 'Children',
                        value: rememberedRunChildren.length > 0 ? rememberedRunChildren.length : rememberedRunQuery.data.lineage.child_run_count
                      }
                    ]}
                  />
                  {hasLineageSignal ? (
                    <p className="status">
                      Chain signal:{' '}
                      {rememberedRunSource?.parent_run_id ? (
                        <>
                          Parent <Link to={`/admin/runs/${rememberedRunSource.parent_run_id}`}>{rememberedRunSource.parent_run_id}</Link>
                        </>
                      ) : (
                        'No parent'
                      )}
                      {rememberedRunChildren.length > 0 ? (
                        <>
                          {' '}
                          · {rememberedRunChildren.length} child run{rememberedRunChildren.length === 1 ? '' : 's'}:{' '}
                          {rememberedRunChildren.slice(0, 3).map((childRunId, index) => (
                            <span key={childRunId}>
                              {index > 0 ? ', ' : ''}
                              <Link to={`/admin/runs/${childRunId}`}>{childRunId}</Link>
                            </span>
                          ))}
                          {rememberedRunChildren.length > 3 ? '…' : ''}
                        </>
                      ) : null}
                    </p>
                  ) : null}
                  {nextInspectionLinks.length > 0 ? (
                    <>
                      <h4>Most relevant next inspections</h4>
                      <p className="status">
                        {nextInspectionLinks.map((item, index) => (
                          <span key={item.label}>
                            {index > 0 ? ' · ' : ''}
                            <Link to={item.href}>{item.label}</Link>
                          </span>
                        ))}
                      </p>
                    </>
                  ) : null}
                </>
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
                    clearLastRunId()
                    setLastRunId(null)
                    setResumeError(null)
                  }}
                >
                  Clear remembered run
                </button>
              </div>
              <p className="status">
                Quick links: <Link to={`/admin/runs/${lastRunId}`}>Run Detail</Link> · <Link to={`/admin/runs/${lastRunId}/events`}>Events</Link>
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
            World Package
            <select value={worldId} onChange={(e) => setWorldId(e.target.value)}>
              {(worldPackagesQuery.data?.packages ?? []).filter((pkg) => pkg.type === 'official' && pkg.status === 'active').map((pkg) => (
                <option key={pkg.world_id} value={pkg.world_id}>{pkg.name}</option>
              ))}
              {!worldPackagesQuery.data?.packages.some((pkg) => pkg.world_id === 'official_fax_world') ? (
                <option value="official_fax_world">Official FAX World</option>
              ) : null}
            </select>
          </label>
          {worldPackagesQuery.isError ? <p className="status">World Package list unavailable; Official FAX World will be used.</p> : null}
          <div className="status" role="note" aria-label="Fixed MSA timeline">
            New root runs start at {MSA_TIMELINE_START_LABEL}. The intended MSA timeline runs through {MSA_TIMELINE_END_LABEL}: {MSA_TIMELINE_SEASON_COUNT} seasons, {MSA_SEASON_WEEK_COUNT} Season Weeks per season. Later seasons continue through rollover/bootstrap child runs.
          </div>
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

        <section className="panel" aria-labelledby="dashboard-runs-index-heading">
          <h3 id="dashboard-runs-index-heading">Browse existing runs</h3>
          <p className="status">
            For full browsing and filtering, use the dedicated <Link to="/admin/runs">Runs browser</Link>.
          </p>
          <label>
            Filter by run ID
            <input
              value={runsFilter}
              onChange={(e) => setRunsFilter(e.target.value)}
              placeholder="Search run_id"
              aria-label="Filter runs by ID"
            />
          </label>
          {runsQuery.isLoading ? <p className="status">Loading existing runs...</p> : null}
          {runsQuery.isError ? <p className="error">Runs list unavailable: {formatApiError(runsQuery.error)}</p> : null}
          {!runsQuery.isLoading && !runsQuery.isError && runsQuery.data?.runs.length === 0 ? (
            <EmptyState message="No runs exist yet. Create a run to populate this browser." />
          ) : null}
          {!runsQuery.isLoading && !runsQuery.isError && runsQuery.data && filteredRuns.length === 0 && runsQuery.data.runs.length > 0 ? (
            <EmptyState message="No runs match the current filter." />
          ) : null}
          {!runsQuery.isLoading && !runsQuery.isError && filteredRuns.length > 0 ? (
            <div className="stack">
              {filteredRuns.map((run) => {
                const isRemembered = lastRunId === run.run_id
                return (
                  <SectionCard key={run.run_id} title={run.run_id}>
                    {isRemembered ? <p className="status">Remembered run</p> : null}
                    <MetadataList
                      items={[
                        { label: 'Season', value: run.season },
                        { label: 'Seed', value: run.seed },
                        { label: 'Progress', value: formatProgress(run.progress.next_event_index, run.progress.total_events) },
                        { label: 'Completed events', value: run.progress.completed_event_count },
                        { label: 'Source type', value: run.source_type ?? 'N/A' },
                        { label: 'Parent run', value: run.parent_run_id ?? 'None' },
                        { label: 'Child runs', value: run.child_run_count }
                      ]}
                    />
                    <p className="status">
                      <Link to={`/admin/runs/${run.run_id}`}>Run Detail</Link> ·{' '}
                      <Link to={`/admin/runs/${run.run_id}/diagnostics`}>Diagnostics</Link> ·{' '}
                      {run.parent_run_id || run.child_run_count > 0 ? (
                        <>
                          <Link to={`/admin/runs/${run.run_id}/season-chain`}>Season Chain</Link> ·{' '}
                        </>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => {
                          void openRunById(run.run_id, 'manual')
                        }}
                        disabled={openingTarget !== null}
                      >
                        Open / continue
                      </button>
                    </p>
                  </SectionCard>
                )
              })}
            </div>
          ) : null}
        </section>
      </div>
    </section>
  )
}
