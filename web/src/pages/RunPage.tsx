import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getFinalsSummary,
  getLatestRollover,
  getRun,
  getRunContainer,
  getRunLineage,
  getRunSource,
  getRunStatusSummary,
  getRunWorldStatus,
  listEvents,
  rebuildRunWorld
} from '../api/client'
import { useAdminBranch } from '../admin/AdminBranchContext'
import { useAdminTime } from '../admin/AdminTimeContext'
import {
  ActionStatusBlock,
  CompactSummaryCard,
  CurrentContextStrip,
  MetadataList,
  PageIntro,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { normalizeRunSourceType } from '../utils/runSourceTypes'

export function RunPage(): JSX.Element {
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()
  const { selectedBranch, selectedBranchId, viewerBranchId } = useAdminBranch()
  const time = useAdminTime()

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const containerQuery = useQuery({
    queryKey: ['run-container', runId],
    queryFn: () => getRunContainer(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const statusQuery = useQuery({
    queryKey: ['run-status-summary', runId],
    queryFn: () => getRunStatusSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const finalsQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const rolloverQuery = useQuery({
    queryKey: ['rollover-latest', runId],
    queryFn: () => getLatestRollover(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const sourceQuery = useQuery({
    queryKey: ['run-source', runId],
    queryFn: () => getRunSource(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const lineageQuery = useQuery({
    queryKey: ['run-lineage', runId],
    queryFn: () => getRunLineage(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const worldQuery = useQuery({
    queryKey: ['run-world-status', runId],
    queryFn: () => getRunWorldStatus(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })

  const invalidateHome = async (): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['run', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-status-summary', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-summary', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-latest', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-world-status', runId] }),
      queryClient.invalidateQueries({ queryKey: ['events', runId] })
    ])
  }

  const rebuildAction = useMutation({ mutationFn: () => rebuildRunWorld(runId), onSuccess: invalidateHome })

  const run = runQuery.data?.run
  const seasonState = runQuery.data?.season_state
  const progress = statusQuery.data?.progress
  const nextEvent = seasonState?.ordered_events[seasonState.next_event_index] ?? null
  const latestEvent = eventsQuery.data?.events[0] ?? null
  const seasonComplete = Boolean(run && (progress?.next_event_index ?? run.next_event_index) >= (progress?.total_events ?? run.total_events))
  const source = sourceQuery.data?.source
  const children = lineageQuery.data?.lineage.children ?? []
  const dataErrors = [containerQuery.error, statusQuery.error, finalsQuery.error, sourceQuery.error, lineageQuery.error, worldQuery.error, eventsQuery.error]
    .filter((error) => error && !isApiNotFound(error))

  return (
    <section className="panel">
      <PageIntro
        title="Home"
        subtitle="Run command center for branch position, Run-level operations, and admin workflows."
        meta={`Run: ${run?.run_id ?? runId ?? 'unknown'}`}
      />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: run?.run_id ?? runId ?? 'unknown' },
          { label: 'Branch', value: selectedBranch?.display_name ?? '—' },
          { label: 'Time', value: 'Present' },
          { label: 'Season', value: time.currentSeason ?? '—' },
          { label: 'Week', value: time.currentWeek != null ? `W${time.currentWeek}` : '—' },
          { label: 'Event', value: time.currentEventId ?? '—' }
        ]}
      />

      {selectedBranchId && time.isLoading && <p className="status">Loading Active Admin Branch position…</p>}
      {selectedBranchId && time.error && (
        <p role="alert" className="error">
          Active Admin Branch position unavailable{time.identityMismatch ? ': returned Branch State identity does not match this Run and Branch.' : '.'}
        </p>
      )}

      {runQuery.isLoading && <p className="status">Loading run...</p>}
      {runQuery.error && <p role="alert" className="error">Failed to load run: {formatApiError(runQuery.error)}</p>}
      {run && (
        <>
          <SectionCard title="Run overview">
            <SummaryPills
              items={[
                { label: 'Legacy simulation status', value: seasonComplete ? 'Regular season complete' : 'Active' },
                { label: 'Legacy completed events', value: progress?.completed_event_count ?? run.completed_event_ids.length },
                {
                  label: 'Legacy Finals',
                  value: finalsQuery.data?.result
                    ? 'Complete'
                    : finalsQuery.data?.qualification
                      ? 'Ready to simulate'
                      : 'Not yet qualified'
                },
                { label: 'World data', value: worldQuery.data?.is_stale ? 'Stale' : worldQuery.data ? 'Fresh' : 'Unavailable' }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: run.run_id },
                { label: 'Seed', value: statusQuery.data?.seed ?? run.seed },
                { label: 'World package', value: worldQuery.data?.world_id ?? '—' },
                { label: 'Source', value: normalizeRunSourceType(source?.source_type) ?? 'Unknown' }
              ]}
            />
          </SectionCard>

          <SectionCard title="Active Admin Branch">
            <MetadataList
              items={[
                { label: 'Name', value: selectedBranch?.display_name ?? 'Not available' },
                { label: 'Branch ID', value: selectedBranchId ?? 'Not available' },
                { label: 'Status', value: selectedBranch?.status ?? 'Not available' },
                { label: 'Viewing mode', value: selectedBranch?.read_only ? 'Read-only' : 'Writable' },
                { label: 'View time', value: 'Present' },
                { label: 'Head checkpoint', value: time.headCheckpointId ?? '—' },
                { label: 'Current season', value: time.currentSeason ?? '—' },
                { label: 'Current week', value: time.currentWeek ?? '—' },
                { label: 'Current event', value: time.currentEventId ?? '—' },
              ]}
            />
            {!selectedBranchId && <p className="status">No Active Admin Branch is available.</p>}
            {selectedBranchId && !time.isLoading && !time.isAvailable && (
              <p className="status">Branch position is unavailable. Legacy Run position is not used as a fallback.</p>
            )}
          </SectionCard>

          <SectionCard title="Viewer publication">
            <MetadataList
              items={[
                { label: 'Viewer Branch', value: viewerBranchId ?? 'Not available' },
                { label: 'Active Branch is Viewer Branch', value: selectedBranchId && viewerBranchId ? (selectedBranchId === viewerBranchId ? 'Yes' : 'No') : '—' },
                {
                  label: 'Parent run',
                  value: source?.parent_run_id ? <Link to={`/admin/runs/${source.parent_run_id}`}>{source.parent_run_id}</Link> : 'None'
                },
                { label: 'Child runs', value: children.length },
                { label: 'Product run status', value: containerQuery.data?.status ?? 'Legacy run' },
                { label: 'Branch controls', value: <Link to={`/admin/runs/${runId}/branches`}>Manage branches and Viewer Branch</Link> }
              ]}
            />
          </SectionCard>

          <SectionCard title="Legacy Run activity">
            <p className="status">Transitional Simulation Run scheduling and history; this is not the Active Admin Branch position.</p>
            <MetadataList
              items={[
                {
                  label: 'Next scheduled event',
                  value: nextEvent ? (
                    <Link to={`/admin/runs/${runId}/calendar/${encodeURIComponent(nextEvent.event_id)}`}>
                      {nextEvent.event_id} · W{nextEvent.week}
                    </Link>
                  ) : 'None — regular season complete'
                },
                {
                  label: 'Latest history event',
                  value: latestEvent ? (
                    <Link to={`/admin/runs/${runId}/events/${encodeURIComponent(latestEvent.event_id)}`}>{latestEvent.event_id}</Link>
                  ) : eventsQuery.isLoading ? 'Loading…' : 'None yet'
                },
                { label: 'Latest rollover', value: rolloverQuery.data ? `S${rolloverQuery.data.rollover.from_season} → S${rolloverQuery.data.rollover.to_season}` : 'None yet' }
              ]}
            />
          </SectionCard>

          <SectionCard title="Admin attention">
            {dataErrors.length === 0 && !worldQuery.data?.is_stale && !(seasonComplete && finalsQuery.data?.qualification && !finalsQuery.data.result) ? (
              <p className="status">No warnings require attention.</p>
            ) : (
              <ul aria-label="Admin warnings">
                {worldQuery.data?.is_stale && <li className="error">World inputs are stale. Review the fingerprint and rebuild support below.</li>}
                {seasonComplete && finalsQuery.data?.qualification && !finalsQuery.data.result && (
                  <li className="error">Regular season is complete and the World Tour Finals result is pending.</li>
                )}
                {dataErrors.length > 0 && <li className="error">{dataErrors.length} run overview request(s) failed. Refresh or inspect diagnostics.</li>}
              </ul>
            )}
            {worldQuery.data?.is_stale && <p>{worldQuery.data.message}</p>}
            <div className="actions">
              {seasonComplete && finalsQuery.data?.qualification && !finalsQuery.data.result && (
                <Link to={`/admin/runs/${runId}/finals`}>Review World Tour Finals</Link>
              )}
              {seasonComplete && finalsQuery.data?.result && (
                <Link to={`/admin/runs/${runId}/rollover`}>Continue to season rollover</Link>
              )}
              {worldQuery.data?.is_stale && worldQuery.data.rebuild_supported && (
                <button type="button" onClick={() => rebuildAction.mutate()} disabled={rebuildAction.isPending}>Rebuild Run from Current World Data</button>
              )}
            </div>
            <ActionStatusBlock
              isLoading={rebuildAction.isPending}
              loadingText="Executing maintenance command…"
              errorText={rebuildAction.error ? `Rebuild failed: ${formatApiError(rebuildAction.error)}` : undefined}
              successText={rebuildAction.data ? 'Run world rebuilt.' : undefined}
            />
          </SectionCard>

          <SectionCard title="Admin shortcuts">
            <div className="actions">
              <Link to={`/admin/runs/${runId}/simulate`}>Open Simulate</Link>
              <Link to={`/admin/runs/${runId}/calendar`}>Season calendar</Link>
              <Link to={`/admin/runs/${runId}/activity`}>Run activity</Link>
              <Link to={`/admin/runs/${runId}/diagnostics`}>Diagnostics</Link>
              <Link to={`/admin/runs/${runId}/finals`}>World Tour Finals</Link>
              <Link to={`/admin/runs/${runId}/rollover`}>Season rollover</Link>
              <Link to={`/admin/runs/${runId}/bootstrap-lineage`}>Source and lineage</Link>
            </div>
            <p className="status">Simulation commands remain in the dedicated Simulate and Branch workflows.</p>
          </SectionCard>
        </>
      )}
    </section>
  )
}
