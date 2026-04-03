import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  getFinalsSummary,
  getLatestRollover,
  getRun,
  getRunLineage,
  getRunSource,
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots
} from '../api/client'
import {
  CompactSummaryCard,
  CurrentContextStrip,
  EmptyState,
  MetadataList,
  PreviewListCard,
  RunScopedHeader,
  SectionCard,
  SummaryPills
} from '../components/RunScopedUi'
import { getFinalsInspectionRoute } from './finalsDetailRoutes'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'

function artifactAvailability({
  isLoading,
  error,
  availableLabel,
  noneLabel
}: {
  isLoading: boolean
  error: unknown
  availableLabel: string
  noneLabel: string
}): string {
  if (isLoading) return 'Loading...'
  if (error) return isApiNotFound(error) ? 'Missing' : 'Error'
  return availableLabel || noneLabel
}

export function RunDiagnosticsPage(): JSX.Element {
  const { runId = '' } = useParams()

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
  const eventsQuery = useQuery({ queryKey: ['events', runId], queryFn: () => listEvents(runId), enabled: Boolean(runId) })
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

  const latestCompletedEvent = eventsQuery.data?.events.find((event) => event.tournament_result)
  const latestRankingSnapshot = rankingSnapshotsQuery.data?.snapshots[0]
  const latestRaceSnapshot = raceSnapshotsQuery.data?.snapshots[0]
  const nextPlannedEvent = runQuery.data?.season_state.ordered_events[runQuery.data.season_state.next_event_index] ?? null
  const nextPlannedWeek = nextPlannedEvent?.week ?? null
  const hasLineageChildren = (lineageQuery.data?.lineage.children.length ?? 0) > 0
  const finalsInspectionRoute = getFinalsInspectionRoute({
    runId,
    hasQualification: Boolean(finalsSummaryQuery.data?.qualification),
    hasResult: Boolean(finalsSummaryQuery.data?.result)
  })

  return (
    <section className="panel">
      <RunScopedHeader
        title="Run diagnostics"
        runId={runId}
        subtitle="Read-only run health, progress, and structure summary."
      />
      <p>
        <Link to={`/runs/${runId}/world-generation`}>Open world generation diagnostics</Link>
      </p>
      <CurrentContextStrip
        items={[
          { label: 'Season', value: statusSummaryQuery.data?.season ?? runQuery.data?.run.season ?? '—' },
          {
            label: 'Progress',
            value: statusSummaryQuery.data
              ? `${statusSummaryQuery.data.progress.next_event_index}/${statusSummaryQuery.data.progress.total_events}`
              : runQuery.data
                ? `${runQuery.data.run.next_event_index}/${runQuery.data.run.total_events}`
                : '—'
          },
          {
            label: 'Completed events',
            value: statusSummaryQuery.data?.progress.completed_event_count ?? runQuery.data?.run.completed_event_ids.length ?? '—'
          }
        ]}
      />

      <SectionCard title="Run diagnostics summary">
        {runQuery.isLoading && <p className="status">Loading run diagnostics...</p>}
        {runQuery.error && <p className="error">Failed to load run details: {formatApiError(runQuery.error)}</p>}
        {statusSummaryQuery.error && (
          <p className="error">Failed to load status summary: {formatApiError(statusSummaryQuery.error)}</p>
        )}
        {runQuery.data && (
          <>
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: runQuery.data.run.run_id },
                { label: 'Season', value: statusSummaryQuery.data?.season ?? runQuery.data.run.season },
                { label: 'Seed', value: statusSummaryQuery.data?.seed ?? runQuery.data.run.seed },
                {
                  label: 'Progress',
                  value: statusSummaryQuery.data
                    ? `${statusSummaryQuery.data.progress.next_event_index} / ${statusSummaryQuery.data.progress.total_events}`
                    : `${runQuery.data.run.next_event_index} / ${runQuery.data.run.total_events}`
                },
                {
                  label: 'Completed events',
                  value: statusSummaryQuery.data?.progress.completed_event_count ?? runQuery.data.run.completed_event_ids.length
                }
              ]}
            />
            <SummaryPills
              items={[
                { label: 'Events', value: statusSummaryQuery.data?.history_counts.events ?? eventsQuery.data?.events.length ?? '—' },
                {
                  label: 'Ranking snapshots',
                  value:
                    statusSummaryQuery.data?.history_counts.ranking_snapshots ?? rankingSnapshotsQuery.data?.snapshots.length ?? '—'
                },
                {
                  label: 'Race snapshots',
                  value: statusSummaryQuery.data?.history_counts.race_snapshots ?? raceSnapshotsQuery.data?.snapshots.length ?? '—'
                }
              ]}
            />
          </>
        )}
      </SectionCard>

      <SectionCard title="Finals and rollover">
        {(finalsSummaryQuery.isLoading || latestRolloverQuery.isLoading) && <p className="status">Loading finals and rollover...</p>}
        {finalsSummaryQuery.error && !isApiNotFound(finalsSummaryQuery.error) && (
          <p className="error">Failed to load Finals summary: {formatApiError(finalsSummaryQuery.error)}</p>
        )}
        {finalsSummaryQuery.data && (
          <MetadataList
            items={[
              {
                label: 'Finals qualification',
                value: finalsSummaryQuery.data.qualification ? 'Available' : 'Not generated yet'
              },
              { label: 'Finals result', value: finalsSummaryQuery.data.result ? 'Available' : 'Not simulated yet' }
            ]}
          />
        )}
        {!finalsSummaryQuery.data && isApiNotFound(finalsSummaryQuery.error) && (
          <EmptyState message="No Finals summary available for this run." />
        )}

        {latestRolloverQuery.data && (
          <MetadataList
            items={[
              { label: 'Latest rollover to season', value: latestRolloverQuery.data.rollover.to_season },
              { label: 'Transitioned players', value: latestRolloverQuery.data.rollover.transitioned_players }
            ]}
          />
        )}
        {!latestRolloverQuery.data && isApiNotFound(latestRolloverQuery.error) && (
          <EmptyState message="No rollover has been executed for this run yet." />
        )}
        {latestRolloverQuery.error && !isApiNotFound(latestRolloverQuery.error) && (
          <p className="error">Failed to load latest rollover: {formatApiError(latestRolloverQuery.error)}</p>
        )}
      </SectionCard>

      <SectionCard title="Source and lineage">
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
        {!sourceQuery.data && isApiNotFound(sourceQuery.error) && <EmptyState message="No source metadata available." />}
        {!lineageQuery.data && isApiNotFound(lineageQuery.error) && <EmptyState message="No lineage metadata available." />}
      </SectionCard>

      <SectionCard title="Recent activity">
        <p>
          <Link to={`/runs/${runId}/activity`}>Open aggregated run activity feed</Link>
        </p>
        <MetadataList
          items={[
            {
              label: 'Latest completed event',
              value: eventsQuery.isLoading
                ? 'Loading...'
                : eventsQuery.error
                  ? `Error: ${formatApiError(eventsQuery.error)}`
                  : latestCompletedEvent
                    ? (
                        <>
                          Available —{' '}
                          <Link to={`/runs/${runId}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
                            {latestCompletedEvent.event_id} (Seq {latestCompletedEvent.event_sequence})
                          </Link>
                        </>
                      )
                    : 'None yet'
            },
            {
              label: 'Latest ranking snapshot',
              value: rankingSnapshotsQuery.isLoading
                ? 'Loading...'
                : rankingSnapshotsQuery.error
                  ? `Error: ${formatApiError(rankingSnapshotsQuery.error)}`
                  : latestRankingSnapshot
                    ? (
                        <>
                          Available —{' '}
                          <Link to={`/runs/${runId}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
                            Seq {latestRankingSnapshot.snapshot_sequence}
                          </Link>
                        </>
                      )
                    : 'None yet'
            },
            {
              label: 'Latest race snapshot',
              value: raceSnapshotsQuery.isLoading
                ? 'Loading...'
                : raceSnapshotsQuery.error
                  ? `Error: ${formatApiError(raceSnapshotsQuery.error)}`
                  : latestRaceSnapshot
                    ? (
                        <>
                          Available —{' '}
                          <Link to={`/runs/${runId}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
                            Seq {latestRaceSnapshot.snapshot_sequence}
                          </Link>
                        </>
                      )
                    : 'None yet'
            }
          ]}
        />
        <PreviewListCard
          title="Recent events"
          subtitle="Shows latest events in API order."
          isLoading={eventsQuery.isLoading}
          loadingText="Loading recent events..."
          errorText={eventsQuery.error ? `Failed to load events: ${formatApiError(eventsQuery.error)}` : undefined}
          items={(eventsQuery.data?.events ?? []).slice(0, 3)}
          emptyText="No events are available yet."
          listAriaLabel="Diagnostics recent events"
          getKey={(event) => event.event_id}
          renderItem={(event) => (
            <Link to={`/runs/${runId}/events/${encodeURIComponent(event.event_id)}`}>
              <strong>{event.event_id}</strong> <span className="status">• Seq {event.event_sequence}</span>
            </Link>
          )}
          viewAllLink={<Link to={`/runs/${runId}/events`}>View all events</Link>}
        />
      </SectionCard>

      <SectionCard title="Availability / artifact state">
        <SummaryPills
          items={[
            {
              label: 'Finals qualification',
              value: finalsSummaryQuery.isLoading
                ? 'Loading...'
                : finalsSummaryQuery.error
                  ? isApiNotFound(finalsSummaryQuery.error)
                    ? 'Missing'
                    : 'Error'
                  : finalsSummaryQuery.data?.qualification
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Finals result',
              value: finalsSummaryQuery.isLoading
                ? 'Loading...'
                : finalsSummaryQuery.error
                  ? isApiNotFound(finalsSummaryQuery.error)
                    ? 'Missing'
                    : 'Error'
                  : finalsSummaryQuery.data?.result
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Latest rollover',
              value: latestRolloverQuery.isLoading
                ? 'Loading...'
                : latestRolloverQuery.error
                  ? isApiNotFound(latestRolloverQuery.error)
                    ? 'Missing'
                    : 'Error'
                  : latestRolloverQuery.data?.rollover
                    ? 'Available'
                    : 'None yet'
            },
            { label: 'Source metadata', value: artifactAvailability({ isLoading: sourceQuery.isLoading, error: sourceQuery.error, availableLabel: sourceQuery.data ? 'Available' : '', noneLabel: 'None yet' }) },
            { label: 'Lineage metadata', value: artifactAvailability({ isLoading: lineageQuery.isLoading, error: lineageQuery.error, availableLabel: lineageQuery.data ? 'Available' : '', noneLabel: 'None yet' }) },
            {
              label: 'Events',
              value: eventsQuery.isLoading
                ? 'Loading...'
                : eventsQuery.error
                  ? 'Error'
                  : (eventsQuery.data?.events.length ?? 0) > 0
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Ranking snapshots',
              value: rankingSnapshotsQuery.isLoading
                ? 'Loading...'
                : rankingSnapshotsQuery.error
                  ? 'Error'
                  : (rankingSnapshotsQuery.data?.snapshots.length ?? 0) > 0
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Race snapshots',
              value: raceSnapshotsQuery.isLoading
                ? 'Loading...'
                : raceSnapshotsQuery.error
                  ? 'Error'
                  : (raceSnapshotsQuery.data?.snapshots.length ?? 0) > 0
                    ? 'Available'
                    : 'None yet'
            }
          ]}
        />
      </SectionCard>

      <SectionCard title="Most relevant next inspection links">
        <ul className="item-list" aria-label="Diagnostics next inspection links">
          {latestCompletedEvent ? (
            <li>
              <Link to={`/runs/${runId}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
                Inspect latest completed event ({latestCompletedEvent.event_id})
              </Link>
            </li>
          ) : null}
          {latestRankingSnapshot ? (
            <li>
              <Link to={`/runs/${runId}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
                Inspect latest ranking snapshot (Seq {latestRankingSnapshot.snapshot_sequence})
              </Link>
            </li>
          ) : null}
          {latestRaceSnapshot ? (
            <li>
              <Link to={`/runs/${runId}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
                Inspect latest race snapshot (Seq {latestRaceSnapshot.snapshot_sequence})
              </Link>
            </li>
          ) : null}
          {nextPlannedEvent && nextPlannedWeek !== null ? (
            <li>
              <Link to={`/runs/${runId}/weeks/${nextPlannedWeek}`}>
                Inspect current week detail (W{nextPlannedWeek} from {nextPlannedEvent.event_id})
              </Link>
            </li>
          ) : null}
          {finalsSummaryQuery.data?.qualification || finalsSummaryQuery.data?.result ? (
            <li>
              <Link to={finalsInspectionRoute}>
                {finalsSummaryQuery.data?.result
                  ? 'Inspect Finals result detail (result available)'
                  : 'Inspect Finals qualification detail (qualification available, result pending)'}
              </Link>
            </li>
          ) : null}
          {latestRolloverQuery.data?.rollover ? (
            <li>
              <Link to={`/runs/${runId}/rollover`}>Inspect latest rollover details</Link>
            </li>
          ) : null}
          {hasLineageChildren ? (
            <li>
              <Link to={`/runs/${runId}/season-chain`}>Inspect season chain ({lineageQuery.data?.lineage.children.length} child run(s))</Link>
            </li>
          ) : null}
          {!latestCompletedEvent &&
          !latestRankingSnapshot &&
          !latestRaceSnapshot &&
          !(nextPlannedEvent && nextPlannedWeek !== null) &&
          !latestRolloverQuery.data?.rollover &&
          !hasLineageChildren &&
          !(finalsSummaryQuery.data?.qualification || finalsSummaryQuery.data?.result) ? (
            <li>
              <span className="status">No targeted inspection links yet. Use quick navigation below.</span>
            </li>
          ) : null}
        </ul>
      </SectionCard>

      <SectionCard title="Quick navigation">
        <ul className="item-list" aria-label="Diagnostics quick navigation">
          <li>
            <Link to={`/runs/${runId}`}>Run Detail</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/events`}>Events</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/calendar`}>Season Calendar</Link>
          </li>
          <li>
            {nextPlannedWeek !== null ? (
              <Link to={`/runs/${runId}/weeks/${nextPlannedWeek}`}>Week Detail (current week)</Link>
            ) : (
              <span>Week Detail (current week unavailable)</span>
            )}
          </li>
          <li>
            <Link to={`/runs/${runId}/activity`}>Activity</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/finals`}>World Tour Finals</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/rollover`}>Season Rollover</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/bootstrap-lineage`}>Bootstrap / Lineage</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/season-chain`}>Season Chain</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/snapshots/ranking`}>Ranking snapshots</Link>
          </li>
          <li>
            <Link to={`/runs/${runId}/snapshots/race`}>Race snapshots</Link>
          </li>
        </ul>
      </SectionCard>
    </section>
  )
}
