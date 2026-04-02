import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { getRun, getRunStatusSummary, listRuns } from '../api/client'
import { CompactSummaryCard, EmptyState, MetadataList, PageIntro, SectionCard, SummaryPills } from '../components/RunScopedUi'
import { formatApiError } from '../utils/apiErrors'

const LAST_RUN_ID_STORAGE_KEY = 'beta_engine:last_run_id'

function formatProgress(nextEventIndex: number, totalEvents: number): string {
  return `${nextEventIndex} / ${totalEvents}`
}

type ChildrenFilter = 'any' | 'with-children' | 'without-children'

export function RunsPage(): JSX.Element {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [runIdFilter, setRunIdFilter] = useState('')
  const [seasonFilter, setSeasonFilter] = useState('')
  const [sourceTypeFilter, setSourceTypeFilter] = useState('')
  const [childrenFilter, setChildrenFilter] = useState<ChildrenFilter>('any')
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
        if (normalizedRunFilter && !run.run_id.toLowerCase().includes(normalizedRunFilter)) return false
        if (normalizedSeasonFilter && String(run.season) !== normalizedSeasonFilter) return false
        if (normalizedSourceFilter) {
          const sourceType = (run.source_type ?? '').toLowerCase()
          if (!sourceType.includes(normalizedSourceFilter)) return false
        }
        if (childrenFilter === 'with-children' && run.child_run_count === 0) return false
        if (childrenFilter === 'without-children' && run.child_run_count > 0) return false
        return true
      }) ?? []
    )
  }, [childrenFilter, runIdFilter, runsQuery.data?.runs, seasonFilter, sourceTypeFilter])

  const selectedRunParam = searchParams.get('selected')
  const selectedRun = useMemo(() => {
    if (filteredRuns.length === 0) return null
    if (!selectedRunParam) return filteredRuns[0]
    return filteredRuns.find((run) => run.run_id === selectedRunParam) ?? filteredRuns[0]
  }, [filteredRuns, selectedRunParam])

  useEffect(() => {
    if (!runsQuery.data) return

    if (!selectedRun && selectedRunParam) {
      setSearchParams((current) => {
        const next = new URLSearchParams(current)
        next.delete('selected')
        return next
      })
      return
    }

    if (selectedRun && selectedRunParam !== selectedRun.run_id) {
      setSearchParams((current) => {
        const next = new URLSearchParams(current)
        next.set('selected', selectedRun.run_id)
        return next
      })
    }
  }, [runsQuery.data, selectedRun, selectedRunParam, setSearchParams])

  const selectedRunStatusQuery = useQuery({
    queryKey: ['run-status-summary', selectedRun?.run_id],
    queryFn: () => getRunStatusSummary(selectedRun?.run_id ?? ''),
    enabled: Boolean(selectedRun?.run_id),
    retry: false
  })

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

  const onSelectRun = (runId: string) => {
    setSearchParams((current) => {
      const next = new URLSearchParams(current)
      next.set('selected', runId)
      return next
    })
  }

  return (
    <section className="panel">
      <PageIntro
        title="Runs browser"
        subtitle="Browse deterministic run summaries, select a run for compact inspection, and bridge directly into run-level surfaces."
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
          <label>
            Child runs
            <select value={childrenFilter} onChange={(e) => setChildrenFilter(e.target.value as ChildrenFilter)}>
              <option value="any">Any</option>
              <option value="with-children">Has children</option>
              <option value="without-children">No children</option>
            </select>
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
        <div className="grid">
          <SectionCard title="Matching runs">
            <p className="status">{filteredRuns.length} matching run(s), preserving API order.</p>
            <ul className="item-list" aria-label="Matching runs">
              {filteredRuns.map((run) => {
                const isSelected = selectedRun?.run_id === run.run_id
                const isRememberedRun = rememberedRunId === run.run_id
                return (
                  <li key={run.run_id}>
                    <button type="button" onClick={() => onSelectRun(run.run_id)}>
                      {isSelected ? 'Selected' : 'Inspect'} {run.run_id}
                    </button>{' '}
                    <span className="status">S{run.season} · {formatProgress(run.progress.next_event_index, run.progress.total_events)}</span>{' '}
                    {isRememberedRun ? <span className="status">Remembered</span> : null}
                  </li>
                )
              })}
            </ul>
          </SectionCard>

          {selectedRun ? (
            <SectionCard title="Selected run detail">
              {rememberedRunId === selectedRun.run_id ? <p className="status">Remembered run</p> : null}
              <SummaryPills
                items={[
                  { label: 'Run ID', value: selectedRun.run_id },
                  { label: 'Season', value: selectedRun.season },
                  { label: 'Source type', value: selectedRun.source_type ?? 'N/A' },
                  { label: 'Progress', value: formatProgress(selectedRun.progress.next_event_index, selectedRun.progress.total_events) }
                ]}
              />
              <CompactSummaryCard
                items={[
                  { label: 'Seed', value: selectedRun.seed },
                  { label: 'Completed events', value: selectedRun.progress.completed_event_count },
                  { label: 'Parent run', value: selectedRun.parent_run_id ?? 'None' },
                  { label: 'Child runs', value: selectedRun.child_run_count }
                ]}
              />

              {selectedRunStatusQuery.isLoading ? <p className="status">Loading selected run status summary…</p> : null}
              {selectedRunStatusQuery.isError ? (
                <p className="error">Status summary unavailable: {formatApiError(selectedRunStatusQuery.error)}</p>
              ) : null}
              {selectedRunStatusQuery.data ? (
                <MetadataList
                  items={[
                    { label: 'History events', value: selectedRunStatusQuery.data.history_counts.events },
                    { label: 'Ranking snapshots', value: selectedRunStatusQuery.data.history_counts.ranking_snapshots },
                    { label: 'Race snapshots', value: selectedRunStatusQuery.data.history_counts.race_snapshots },
                    {
                      label: 'Finals signal',
                      value: selectedRunStatusQuery.data.finals.result_available
                        ? 'Qualification + result available'
                        : selectedRunStatusQuery.data.finals.qualification_available
                          ? 'Qualification available'
                          : 'None yet'
                    },
                    {
                      label: 'Rollover signal',
                      value: selectedRunStatusQuery.data.rollover
                        ? `To S${selectedRunStatusQuery.data.rollover.latest_to_season}`
                        : 'None yet'
                    }
                  ]}
                />
              ) : null}

              <p className="status">
                <Link to={`/runs/${selectedRun.run_id}`}>Run Detail</Link> ·{' '}
                <Link to={`/runs/${selectedRun.run_id}/diagnostics`}>Diagnostics</Link> ·{' '}
                <Link to={`/runs/${selectedRun.run_id}/activity`}>Activity</Link> ·{' '}
                <Link to={`/runs/${selectedRun.run_id}/calendar`}>Season Calendar</Link>
                {(selectedRun.parent_run_id || selectedRun.child_run_count > 0) ? (
                  <>
                    {' '}
                    · <Link to={`/runs/${selectedRun.run_id}/season-chain`}>Season Chain</Link>
                  </>
                ) : null}
                {selectedRunStatusQuery.data?.finals.qualification_available || selectedRunStatusQuery.data?.finals.result_available ? (
                  <>
                    {' '}
                    · <Link to={`/runs/${selectedRun.run_id}/finals`}>World Tour Finals</Link>
                  </>
                ) : null}
                {selectedRunStatusQuery.data?.rollover ? (
                  <>
                    {' '}
                    · <Link to={`/runs/${selectedRun.run_id}/rollover`}>Season Rollover</Link>
                  </>
                ) : null}
                {(selectedRun.parent_run_id || selectedRun.child_run_count > 0 || selectedRun.source_type) ? (
                  <>
                    {' '}
                    · <Link to={`/runs/${selectedRun.run_id}/bootstrap-lineage`}>Bootstrap / Lineage</Link>
                  </>
                ) : null}
              </p>

              <button type="button" onClick={() => void onOpenRun(selectedRun.run_id)} disabled={openingRunId !== null}>
                {openingRunId === selectedRun.run_id ? 'Opening...' : 'Open / continue'}
              </button>
            </SectionCard>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
