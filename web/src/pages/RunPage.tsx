import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getFinalsSummary,
  getLatestRollover,
  getRun,
  getRunLineage,
  getRunStatusSummary,
  getRunSource,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
  rolloverNextSeason,
  simulateFullSeason,
  simulateNextTournament,
  simulateNextWeek,
  simulateWorldTourFinals
} from '../api/client'
import {
  ActionStatusBlock,
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  PageIntro,
  PreviewListCard,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

export function RunPage(): JSX.Element {
  const previewLimit = 3
  const { runId = '' } = useParams()
  const queryClient = useQueryClient()

  const invalidateRunDetailQueries = async (): Promise<void> => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['run', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-status-summary', runId] }),
      queryClient.invalidateQueries({ queryKey: ['events', runId] }),
      queryClient.invalidateQueries({ queryKey: ['ranking-snapshots', runId] }),
      queryClient.invalidateQueries({ queryKey: ['race-snapshots', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-summary', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-qualification', runId] }),
      queryClient.invalidateQueries({ queryKey: ['finals-result', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-latest', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-by-season', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-transitions', runId] }),
      queryClient.invalidateQueries({ queryKey: ['rollover-next-season-players', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-source', runId] }),
      queryClient.invalidateQueries({ queryKey: ['run-lineage', runId] })
    ])
  }

  const runQuery = useQuery({ queryKey: ['run', runId], queryFn: () => getRun(runId), enabled: Boolean(runId) })
  const statusSummaryQuery = useQuery({
    queryKey: ['run-status-summary', runId],
    queryFn: () => getRunStatusSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const finalsSummaryQuery = useQuery({
    queryKey: ['finals-summary', runId],
    queryFn: () => getFinalsSummary(runId),
    enabled: Boolean(runId),
    retry: false
  })
  const latestRolloverQuery = useQuery({
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
  const eventsQuery = useQuery({
    queryKey: ['events', runId],
    queryFn: () => listEvents(runId),
    enabled: Boolean(runId)
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['ranking-snapshots', runId],
    queryFn: () => listRankingSnapshots(runId),
    enabled: Boolean(runId)
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['race-snapshots', runId],
    queryFn: () => listRaceSnapshots(runId),
    enabled: Boolean(runId)
  })

  const finalsQuickAction = useMutation({
    mutationFn: () => simulateWorldTourFinals(runId),
    onSuccess: async () => {
      await invalidateRunDetailQueries()
    }
  })

  const rolloverQuickAction = useMutation({
    mutationFn: () => rolloverNextSeason(runId),
    onSuccess: async () => {
      await invalidateRunDetailQueries()
    }
  })

  const simulator = useMutation({
    mutationFn: async (mode: 'next-tournament' | 'next-week' | 'full-season') => {
      if (mode === 'next-tournament') return simulateNextTournament(runId)
      if (mode === 'next-week') return simulateNextWeek(runId)
      return simulateFullSeason(runId)
    },
    onSuccess: async () => {
      await invalidateRunDetailQueries()
    }
  })

  const recentEvents = eventsQuery.data?.events.slice(0, previewLimit) ?? []
  const recentRankingSnapshots = rankingSnapshotsQuery.data?.snapshots.slice(0, previewLimit) ?? []
  const recentRaceSnapshots = raceSnapshotsQuery.data?.snapshots.slice(0, previewLimit) ?? []
  const latestCompletedEvent = eventsQuery.data?.events[0]
  const latestRankingSnapshot = rankingSnapshotsQuery.data?.snapshots[0]
  const latestRaceSnapshot = raceSnapshotsQuery.data?.snapshots[0]

  const artifactState = (
    query: { isLoading: boolean; error: unknown; data: unknown },
    availableLabel = 'Available',
    noneLabel = 'None yet'
  ): string => {
    if (query.isLoading) return 'Loading'
    if (query.error) return isApiNotFound(query.error) ? noneLabel : 'Error'
    if (query.data) return availableLabel
    return 'Missing'
  }

  const finalsInspectionNeeded = Boolean(finalsSummaryQuery.data?.qualification && !finalsSummaryQuery.data?.result)
  const hasLineageRelationships = Boolean(
    sourceQuery.data?.source.parent_run_id || (lineageQuery.data?.lineage.children.length ?? 0) > 0
  )

  return (
    <section className="panel">
      <PageIntro title="Run detail" subtitle="Review run status, execute quick actions, and navigate to detailed run views." />
      <CurrentContextStrip
        items={[
          { label: 'Run', value: runQuery.data?.run.run_id ?? runId ?? 'unknown' },
          { label: 'Season', value: statusSummaryQuery.data?.season ?? runQuery.data?.run.season ?? '—' },
          {
            label: 'Progress',
            value: statusSummaryQuery.data
              ? `${statusSummaryQuery.data.progress.next_event_index}/${statusSummaryQuery.data.progress.total_events}`
              : runQuery.data
                ? `${runQuery.data.run.next_event_index}/${runQuery.data.run.total_events}`
                : '—'
          }
        ]}
      />
      {runQuery.isLoading && <p className="status">Loading run...</p>}
      {runQuery.error && <p className="error">Failed to load run: {String(runQuery.error)}</p>}
      {runQuery.data && (
        <>
          <SectionCard title="Run landing summary">
            <SummaryPills
              items={[
                { label: 'Current season', value: statusSummaryQuery.data?.season ?? runQuery.data.run.season },
                {
                  label: 'Progress',
                  value: statusSummaryQuery.data
                    ? `${statusSummaryQuery.data.progress.next_event_index}/${statusSummaryQuery.data.progress.total_events}`
                    : `${runQuery.data.run.next_event_index}/${runQuery.data.run.total_events}`
                },
                {
                  label: 'Completed events',
                  value: statusSummaryQuery.data?.progress.completed_event_count ?? runQuery.data.run.completed_event_ids.length
                },
                {
                  label: 'Finals',
                  value: finalsSummaryQuery.data?.result
                    ? 'Result available'
                    : finalsSummaryQuery.data?.qualification
                      ? 'Qualification available'
                      : finalsSummaryQuery.isLoading
                        ? 'Loading'
                        : finalsSummaryQuery.error
                          ? 'Error'
                          : 'None yet'
                },
                {
                  label: 'Rollover',
                  value: latestRolloverQuery.data
                    ? `To S${latestRolloverQuery.data.rollover.to_season}`
                    : latestRolloverQuery.isLoading
                      ? 'Loading'
                      : latestRolloverQuery.error
                        ? isApiNotFound(latestRolloverQuery.error)
                          ? 'None yet'
                          : 'Error'
                        : 'Missing'
                },
                {
                  label: 'Source / lineage',
                  value: hasLineageRelationships ? 'Connected' : sourceQuery.data || lineageQuery.data ? 'Standalone' : 'None yet'
                }
              ]}
            />
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: runQuery.data.run.run_id },
                { label: 'Seed', value: statusSummaryQuery.data?.seed ?? runQuery.data.run.seed }
              ]}
            />
          </SectionCard>

          <SectionCard title="Most relevant next inspections">
            <MetadataList
              items={[
                {
                  label: 'Latest completed event',
                  value: latestCompletedEvent ? (
                    <Link to={`/runs/${runId}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
                      {latestCompletedEvent.event_id}
                    </Link>
                  ) : (
                    'None yet'
                  )
                },
                {
                  label: 'Latest ranking snapshot',
                  value: latestRankingSnapshot ? (
                    <Link to={`/runs/${runId}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
                      Seq {latestRankingSnapshot.snapshot_sequence}
                    </Link>
                  ) : (
                    'None yet'
                  )
                },
                {
                  label: 'Latest race snapshot',
                  value: latestRaceSnapshot ? (
                    <Link to={`/runs/${runId}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
                      Seq {latestRaceSnapshot.snapshot_sequence}
                    </Link>
                  ) : (
                    'None yet'
                  )
                },
                {
                  label: 'World Tour Finals',
                  value: finalsInspectionNeeded ? <Link to={`/runs/${runId}/finals`}>Inspect pending Finals result</Link> : 'None yet'
                },
                {
                  label: 'Latest rollover',
                  value: latestRolloverQuery.data ? (
                    <Link to={`/runs/${runId}/rollover/${latestRolloverQuery.data.rollover.to_season}`}>Inspect latest rollover</Link>
                  ) : 'None yet'
                },
                {
                  label: 'Season chain',
                  value: hasLineageRelationships ? <Link to={`/runs/${runId}/season-chain`}>Inspect season chain</Link> : 'None yet'
                },
                {
                  label: 'Run activity',
                  value: <Link to={`/runs/${runId}/activity`}>Inspect aggregated run activity</Link>
                },
                {
                  label: 'Bootstrap / lineage',
                  value: sourceQuery.data ? <Link to={`/runs/${runId}/bootstrap-lineage`}>Inspect source metadata</Link> : 'None yet'
                }
              ]}
            />
          </SectionCard>

          <SectionCard title="Current artifact state">
            <CompactSummaryCard
              items={[
                {
                  label: 'Finals qualification',
                  value: artifactState(
                    finalsSummaryQuery,
                    finalsSummaryQuery.data?.qualification ? 'Available' : 'None yet',
                    'None yet'
                  )
                },
                {
                  label: 'Finals result',
                  value: artifactState(finalsSummaryQuery, finalsSummaryQuery.data?.result ? 'Available' : 'None yet', 'None yet')
                },
                { label: 'Latest rollover', value: artifactState(latestRolloverQuery, 'Available', 'None yet') },
                { label: 'Source metadata', value: artifactState(sourceQuery, 'Available', 'None yet') },
                { label: 'Lineage metadata', value: artifactState(lineageQuery, 'Available', 'None yet') },
                {
                  label: 'Events',
                  value: artifactState(eventsQuery, eventsQuery.data?.events.length ? 'Available' : 'None yet', 'None yet')
                },
                {
                  label: 'Ranking snapshots',
                  value: artifactState(
                    rankingSnapshotsQuery,
                    rankingSnapshotsQuery.data?.snapshots.length ? 'Available' : 'None yet',
                    'None yet'
                  )
                },
                {
                  label: 'Race snapshots',
                  value: artifactState(raceSnapshotsQuery, raceSnapshotsQuery.data?.snapshots.length ? 'Available' : 'None yet', 'None yet')
                }
              ]}
            />
          </SectionCard>

          <SectionCard title="World Tour Finals overview">
            {finalsSummaryQuery.isLoading && <p className="status">Loading Finals status...</p>}
            {finalsSummaryQuery.error && (
              <p className="error">Failed to load Finals summary: {formatApiError(finalsSummaryQuery.error)}</p>
            )}
            {finalsSummaryQuery.data && (
              <MetadataList
                items={[
                  { label: 'Qualification', value: finalsSummaryQuery.data.qualification ? 'Available' : 'Not generated yet' },
                  { label: 'Finals result', value: finalsSummaryQuery.data.result ? 'Available' : 'Not simulated yet' }
                ]}
              />
            )}
            <div className="actions">
              <button onClick={() => finalsQuickAction.mutate()} disabled={!runId || finalsQuickAction.isPending}>
                {finalsQuickAction.isPending ? 'Simulating Finals...' : 'Simulate World Tour Finals'}
              </button>
            </div>
            <ActionStatusBlock
              isLoading={finalsQuickAction.isPending}
              loadingText="Simulating World Tour Finals..."
              errorText={
                finalsQuickAction.error ? `Could not simulate Finals: ${formatApiError(finalsQuickAction.error)}` : undefined
              }
              successText={
                finalsQuickAction.data
                  ? `Finals simulation complete${finalsQuickAction.data.finals.already_simulated ? ' (already simulated)' : ''}.`
                  : undefined
              }
            />
            <p>
              <Link to={`/runs/${runId}/finals`}>View World Tour Finals</Link>
            </p>
          </SectionCard>

          <SectionCard title="Latest rollover overview">
            {latestRolloverQuery.isLoading && <p className="status">Loading latest rollover...</p>}
            {isApiNotFound(latestRolloverQuery.error) && <p className="status">No rollover yet for this run.</p>}
            {latestRolloverQuery.error && !isApiNotFound(latestRolloverQuery.error) && (
              <p className="error">Failed to load latest rollover: {formatApiError(latestRolloverQuery.error)}</p>
            )}
            {latestRolloverQuery.data && (
              <MetadataList
                items={[
                  { label: 'From season', value: latestRolloverQuery.data.rollover.from_season },
                  { label: 'To season', value: latestRolloverQuery.data.rollover.to_season },
                  { label: 'Transitioned players', value: latestRolloverQuery.data.rollover.transitioned_players }
                ]}
              />
            )}
            <div className="actions">
              <button onClick={() => rolloverQuickAction.mutate()} disabled={!runId || rolloverQuickAction.isPending}>
                {rolloverQuickAction.isPending ? 'Rolling over...' : 'Roll over to next season'}
              </button>
            </div>
            <ActionStatusBlock
              isLoading={rolloverQuickAction.isPending}
              loadingText="Rolling over to next season..."
              errorText={
                rolloverQuickAction.error
                  ? `Could not execute rollover: ${formatApiError(rolloverQuickAction.error)}`
                  : undefined
              }
              successText={
                rolloverQuickAction.data
                  ? `Rollover complete for season ${rolloverQuickAction.data.rollover.to_season}${
                      rolloverQuickAction.data.rollover.already_persisted ? ' (already persisted)' : ''
                    }.`
                  : undefined
              }
            />
            <p>
              <Link to={`/runs/${runId}/rollover`}>View season rollover</Link>
            </p>
          </SectionCard>

          <SectionCard title="Run source and lineage overview">
            {(sourceQuery.isLoading || lineageQuery.isLoading) && <p className="status">Loading source and lineage...</p>}
            {sourceQuery.error && !isApiNotFound(sourceQuery.error) && (
              <p className="error">Failed to load run source: {formatApiError(sourceQuery.error)}</p>
            )}
            {lineageQuery.error && !isApiNotFound(lineageQuery.error) && (
              <p className="error">Failed to load run lineage: {formatApiError(lineageQuery.error)}</p>
            )}
            {sourceQuery.data && (
              <CompactSummaryCard
                items={[
                  { label: 'Source type', value: sourceQuery.data.source.source_type || 'Unknown' },
                  {
                    label: 'Parent run',
                    value: sourceQuery.data.source.parent_run_id ? (
                      <Link to={`/runs/${sourceQuery.data.source.parent_run_id}`}>{sourceQuery.data.source.parent_run_id}</Link>
                    ) : (
                      'No parent run'
                    )
                  },
                  { label: 'Child run count', value: lineageQuery.data?.lineage.children.length ?? 0 }
                ]}
              />
            )}
            {!sourceQuery.data && isApiNotFound(sourceQuery.error) && (
              <p className="status">No source metadata available for this run.</p>
            )}
            {lineageQuery.data && lineageQuery.data.lineage.children.length > 0 && (
              <ul>
                {lineageQuery.data.lineage.children.map((childRunId) => (
                  <li key={childRunId}>
                    <Link to={`/runs/${childRunId}`}>{childRunId}</Link>
                  </li>
                ))}
              </ul>
            )}
            {lineageQuery.data && lineageQuery.data.lineage.children.length === 0 && (
              <EmptyState message="No child runs created yet." />
            )}
            {!lineageQuery.data && isApiNotFound(lineageQuery.error) && (
              <EmptyState message="No lineage metadata available for this run." />
            )}
            <p>
              <Link to={`/runs/${runId}/bootstrap-lineage`}>View bootstrap and lineage</Link>
              {' · '}
              <Link to={`/runs/${runId}/season-chain`}>View season chain</Link>
            </p>
          </SectionCard>

          <SectionCard title="Recent history previews">
            <p className="subtitle">Recent entries are shown in API order to match the full history views.</p>
            <div className="grid">
              <PreviewListCard
                title="Recent events"
                isLoading={eventsQuery.isLoading}
                loadingText="Loading recent events..."
                errorText={eventsQuery.error ? `Failed to load recent events: ${formatApiError(eventsQuery.error)}` : undefined}
                items={recentEvents}
                emptyText="No events are available for this run yet."
                listAriaLabel="Recent events preview"
                getKey={(event) => event.event_id}
                renderItem={(event) => (
                  <Link to={`/runs/${runId}/events/${encodeURIComponent(event.event_id)}`}>
                    <strong>{event.event_id}</strong>{' '}
                    <span className="status">
                      • Seq {event.event_sequence}
                      {event.season != null ? ` • S${event.season}` : ''}
                      {event.week != null ? ` • W${event.week}` : ''}
                    </span>
                  </Link>
                )}
                viewAllLink={<Link to={`/runs/${runId}/events`}>View all events</Link>}
              />

              <PreviewListCard
                title="Recent ranking snapshots"
                isLoading={rankingSnapshotsQuery.isLoading}
                loadingText="Loading recent ranking snapshots..."
                errorText={
                  rankingSnapshotsQuery.error
                    ? `Failed to load recent ranking snapshots: ${formatApiError(rankingSnapshotsQuery.error)}`
                    : undefined
                }
                items={recentRankingSnapshots}
                emptyText="No ranking snapshots are available for this run yet."
                listAriaLabel="Recent ranking snapshots preview"
                getKey={(snapshot) => `${snapshot.snapshot_kind}-${snapshot.snapshot_sequence}`}
                renderItem={(snapshot) => (
                  <Link to={`/runs/${runId}/snapshots/ranking/${snapshot.snapshot_sequence}`}>
                    <strong>
                      Seq {snapshot.snapshot_sequence} • {snapshot.snapshot_kind}
                    </strong>{' '}
                    <span className="status">{snapshot.source_event_id ? `• Source ${snapshot.source_event_id}` : '• Source —'}</span>
                  </Link>
                )}
                viewAllLink={<Link to={`/runs/${runId}/snapshots/ranking`}>View all ranking snapshots</Link>}
              />

              <PreviewListCard
                title="Recent race snapshots"
                isLoading={raceSnapshotsQuery.isLoading}
                loadingText="Loading recent race snapshots..."
                errorText={
                  raceSnapshotsQuery.error ? `Failed to load recent race snapshots: ${formatApiError(raceSnapshotsQuery.error)}` : undefined
                }
                items={recentRaceSnapshots}
                emptyText="No race snapshots are available for this run yet."
                listAriaLabel="Recent race snapshots preview"
                getKey={(snapshot) => `${snapshot.snapshot_kind}-${snapshot.snapshot_sequence}`}
                renderItem={(snapshot) => (
                  <Link to={`/runs/${runId}/snapshots/race/${snapshot.snapshot_sequence}`}>
                    <strong>
                      Seq {snapshot.snapshot_sequence} • {snapshot.snapshot_kind}
                    </strong>{' '}
                    <span className="status">{snapshot.source_event_id ? `• Source ${snapshot.source_event_id}` : '• Source —'}</span>
                  </Link>
                )}
                viewAllLink={<Link to={`/runs/${runId}/snapshots/race`}>View all race snapshots</Link>}
              />
            </div>
          </SectionCard>

          <SectionCard title="Simulation controls">
            <div className="actions">
              <button onClick={() => simulator.mutate('next-tournament')}>Simulate next tournament</button>
              <button onClick={() => simulator.mutate('next-week')}>Simulate next week</button>
              <button onClick={() => simulator.mutate('full-season')}>Simulate full season</button>
            </div>
            <ActionStatusBlock
              errorText={simulator.error ? `Simulation failed: ${formatApiError(simulator.error)}` : undefined}
            />
            {simulator.data && (
              <pre className="json-block" aria-label="simulation-result">
                {JSON.stringify(simulator.data.step, null, 2)}
              </pre>
            )}
          </SectionCard>
        </>
      )}
    </section>
  )
}
