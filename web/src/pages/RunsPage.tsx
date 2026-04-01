import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getRun, listRuns } from '../api/client'
import { EmptyState, MetadataList, PageIntro, SectionCard } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

const LAST_RUN_ID_STORAGE_KEY = 'beta_engine:last_run_id'

function formatProgress(nextEventIndex: number, totalEvents: number): string {
  return `${nextEventIndex} / ${totalEvents}`
}

export function RunsPage(): JSX.Element {
  const navigate = useNavigate()
  const [runIdFilter, setRunIdFilter] = useState('')
  const [seasonFilter, setSeasonFilter] = useState('')
  const [sourceTypeFilter, setSourceTypeFilter] = useState('')
  const [openingRunId, setOpeningRunId] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)
  const [rememberedRunId, setRememberedRunId] = useState(() => localStorage.getItem(LAST_RUN_ID_STORAGE_KEY))

  const runsQuery = useQuery({
    queryKey: ['runs-index-page'],
    queryFn: listRuns,
    retry: false
  })

  const filteredRuns = useMemo(() => {
    const normalizedRunFilter = runIdFilter.trim().toLowerCase()
    const normalizedSourceFilter = sourceTypeFilter.trim().toLowerCase()
    const normalizedSeasonFilter = seasonFilter.trim()

    return (
      runsQuery.data?.runs.filter((run) => {
        if (normalizedRunFilter && !run.run_id.toLowerCase().includes(normalizedRunFilter)) {
          return false
        }

        if (normalizedSeasonFilter && String(run.season) !== normalizedSeasonFilter) {
          return false
        }

        if (normalizedSourceFilter) {
          const sourceType = (run.source_type ?? '').toLowerCase()
          if (!sourceType.includes(normalizedSourceFilter)) {
            return false
          }
        }

        return true
      }) ?? []
    )
  }, [runIdFilter, runsQuery.data?.runs, seasonFilter, sourceTypeFilter])

  const onOpenRun = async (runId: string) => {
    setOpenError(null)
    setOpeningRunId(runId)
    try {
      const run = await getRun(runId)
      localStorage.setItem(LAST_RUN_ID_STORAGE_KEY, run.run.run_id)
      setRememberedRunId(run.run.run_id)
      navigate(`/runs/${run.run.run_id}`)
    } catch (err) {
      setOpenError(`Could not open run: ${formatApiError(err)}`)
    } finally {
      setOpeningRunId(null)
    }
  }

  return (
    <section className="panel">
      <PageIntro
        title="Runs browser"
        subtitle="Browse deterministic run summaries from the API index, then jump into detail and inspection views."
      />

      <SectionCard title="Filters">
        <div className="grid">
          <label>
            Filter by run ID
            <input value={runIdFilter} onChange={(e) => setRunIdFilter(e.target.value)} placeholder="Search run_id" />
          </label>
          <label>
            Filter by season
            <input value={seasonFilter} onChange={(e) => setSeasonFilter(e.target.value)} placeholder="e.g. 2027" />
          </label>
          <label>
            Filter by source type
            <input value={sourceTypeFilter} onChange={(e) => setSourceTypeFilter(e.target.value)} placeholder="bootstrap" />
          </label>
        </div>
      </SectionCard>

      {runsQuery.isLoading ? <p className="status">Loading runs index…</p> : null}
      {runsQuery.isError ? <p className="error">Runs list unavailable: {formatApiError(runsQuery.error)}</p> : null}
      {!runsQuery.isLoading && !runsQuery.isError && runsQuery.data?.runs.length === 0 ? (
        <EmptyState message="No runs exist yet. Create a run from Dashboard to populate this browser." />
      ) : null}
      {!runsQuery.isLoading && !runsQuery.isError && runsQuery.data && filteredRuns.length === 0 && runsQuery.data.runs.length > 0 ? (
        <EmptyState message="No runs match the current filters." />
      ) : null}
      {openError ? <p className="error">{openError}</p> : null}

      {!runsQuery.isLoading && !runsQuery.isError && filteredRuns.length > 0 ? (
        <div className="stack">
          {filteredRuns.map((run) => {
            const isRememberedRun = rememberedRunId === run.run_id
            const showSeasonChainLink = Boolean(run.parent_run_id) || run.child_run_count > 0
            return (
              <SectionCard key={run.run_id} title={run.run_id}>
                {isRememberedRun ? <p className="status">Remembered run</p> : null}
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
                  <Link to={`/runs/${run.run_id}`}>Run Detail</Link> · <Link to={`/runs/${run.run_id}/diagnostics`}>Diagnostics</Link> ·{' '}
                  <Link to={`/runs/${run.run_id}/activity`}>Activity</Link>
                  {showSeasonChainLink ? (
                    <>
                      {' '}
                      · <Link to={`/runs/${run.run_id}/season-chain`}>Season Chain</Link>
                    </>
                  ) : null}
                </p>
                <button type="button" onClick={() => void onOpenRun(run.run_id)} disabled={openingRunId !== null}>
                  {openingRunId === run.run_id ? 'Opening...' : 'Open / continue'}
                </button>
              </SectionCard>
            )
          })}
        </div>
      ) : null}
    </section>
  )
}
