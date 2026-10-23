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

  // Run and status summaries must belong to the currently selected route.
  // Other independently valid diagnostics remain available if either is wrong.
  const runMismatch = Boolean(runQuery.data && runQuery.data.run.run_id !== runId)
  const statusMismatch = Boolean(statusSummaryQuery.data && statusSummaryQuery.data.run_id !== runId)
  const safeRun = runQuery.data?.run.run_id === runId ? runQuery.data : null
  const safeStatus = statusSummaryQuery.data?.run_id === runId ? statusSummaryQuery.data : null

  // Finals include independently identified qualification and result records.
  // A matching outer summary must not conceal a foreign or cross-season artifact.
  const finalsMismatch = Boolean(finalsSummaryQuery.data && (
    finalsSummaryQuery.data.run_id !== runId ||
    (finalsSummaryQuery.data.qualification && (
      finalsSummaryQuery.data.qualification.run_id !== runId ||
      finalsSummaryQuery.data.qualification.season !== finalsSummaryQuery.data.season
    )) ||
    (finalsSummaryQuery.data.result && (
      finalsSummaryQuery.data.result.run_id !== runId ||
      finalsSummaryQuery.data.result.season !== finalsSummaryQuery.data.season
    ))
  ))
  const rolloverMismatch = Boolean(latestRolloverQuery.data && latestRolloverQuery.data.rollover.run_id !== runId)
  const lineageMismatch = Boolean(lineageQuery.data && lineageQuery.data.lineage.run_id !== runId)
  const safeFinals = finalsSummaryQuery.data?.run_id === runId ? finalsSummaryQuery.data : null
  const safeRollover = latestRolloverQuery.data?.rollover.run_id === runId ? latestRolloverQuery.data : null
  const safeLineage = lineageQuery.data?.lineage.run_id === runId ? lineageQuery.data : null

  // Every history response has a Run ID; never display another Run's artifacts.
  const eventsMismatch = Boolean(eventsQuery.data && eventsQuery.data.run_id !== runId)
  const rankingsMismatch = Boolean(rankingSnapshotsQuery.data && rankingSnapshotsQuery.data.run_id !== runId)
  const racesMismatch = Boolean(raceSnapshotsQuery.data && raceSnapshotsQuery.data.run_id !== runId)
  const safeEvents = eventsQuery.data?.run_id === runId ? eventsQuery.data.events : []
  const safeRankingSnapshots = rankingSnapshotsQuery.data?.run_id === runId ? rankingSnapshotsQuery.data.snapshots : []
  const safeRaceSnapshots = raceSnapshotsQuery.data?.run_id === runId ? raceSnapshotsQuery.data.snapshots : []

  // History endpoints return ascending sequences; the first item is the oldest.
  // Select by persisted sequence rather than relying on response array order.
  const latestCompletedEvent = safeEvents
    .filter((event) => Boolean(event.tournament_result))
    .sort((a, b) => b.event_sequence - a.event_sequence)[0]
  const latestRankingSnapshot = safeRankingSnapshots
    .slice().sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0]
  const latestRaceSnapshot = safeRaceSnapshots
    .slice().sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0]
  const nextPlannedEvent = safeRun?.season_state.ordered_events[safeRun.season_state.next_event_index] ?? null
  const nextPlannedWeek = nextPlannedEvent?.week ?? null
  const hasLineageChildren = (safeLineage?.lineage.children.length ?? 0) > 0
  const finalsInspectionRoute = getFinalsInspectionRoute({
    runId,
    hasQualification: Boolean(safeFinals?.qualification),
    hasResult: Boolean(safeFinals?.result)
  })

  return (
    <section className="panel">
      <RunScopedHeader
        title="Run diagnostics"
        runId={runId}
        subtitle="Read-only run health, progress, and structure summary."
      />
      <p>
        <Link to={`/runs/${encodeURIComponent(runId)}/world-generation`}>Open world generation diagnostics</Link>
      </p>
      <CurrentContextStrip
        items={[
          { label: 'Season', value: safeStatus?.season ?? safeRun?.run.season ?? '—' },
          {
            label: 'Progress',
            value: safeStatus
              ? `${safeStatus.progress.next_event_index}/${safeStatus.progress.total_events}`
              : safeRun
                ? `${safeRun.run.next_event_index}/${safeRun.run.total_events}`
                : '—'
          },
          {
            label: 'Completed events',
            value: safeStatus?.progress.completed_event_count ?? safeRun?.run.completed_event_ids.length ?? '—'
          }
        ]}
      />

      <SectionCard title="Run diagnostics summary">
        {runQuery.isLoading && <p className="status">Loading run diagnostics...</p>}
        {runQuery.error && <p className="error">Failed to load run details: {formatApiError(runQuery.error)}</p>}
        {runMismatch && <p role="alert" className="error">Run details belong to another Run. Its progress and planned week are hidden.</p>}
        {statusSummaryQuery.error && (
          <p className="error">Failed to load status summary: {formatApiError(statusSummaryQuery.error)}</p>
        )}
        {statusMismatch && <p role="alert" className="error">Status summary belongs to another Run. Its progress and counts are hidden.</p>}
        {safeRun && (
          <>
            <CompactSummaryCard
              items={[
                { label: 'Run ID', value: safeRun.run.run_id },
                { label: 'Season', value: safeStatus?.season ?? safeRun.run.season },
                { label: 'Seed', value: safeStatus?.seed ?? safeRun.run.seed },
                {
                  label: 'Progress',
                  value: safeStatus
                    ? `${safeStatus.progress.next_event_index} / ${safeStatus.progress.total_events}`
                    : `${safeRun.run.next_event_index} / ${safeRun.run.total_events}`
                },
                {
                  label: 'Completed events',
                  value: safeStatus?.progress.completed_event_count ?? safeRun.run.completed_event_ids.length
                }
              ]}
            />
            <SummaryPills
              items={[
                { label: 'Events', value: safeStatus?.history_counts.events ?? (eventsQuery.data?.run_id === runId ? safeEvents.length : '—') },
                {
                  label: 'Ranking snapshots',
                  value:
                    safeStatus?.history_counts.ranking_snapshots ?? (rankingSnapshotsQuery.data?.run_id === runId ? safeRankingSnapshots.length : '—')
                },
                {
                  label: 'Race snapshots',
                  value: safeStatus?.history_counts.race_snapshots ?? (raceSnapshotsQuery.data?.run_id === runId ? safeRaceSnapshots.length : '—')
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
        {finalsMismatch && <p role="alert" className="error">Finals summary contains mismatched Run or season data. Its status and inspection links are hidden.</p>}
        {rolloverMismatch && <p role="alert" className="error">Rollover summary belongs to another Run. Its result and inspection link are hidden.</p>}
        {safeFinals && (
          <MetadataList
            items={[
              {
                label: 'Finals qualification',
                value: safeFinals.qualification ? 'Available' : 'Not generated yet'
              },
              { label: 'Finals result', value: safeFinals.result ? 'Available' : 'Not simulated yet' }
            ]}
          />
        )}
        {!safeFinals && isApiNotFound(finalsSummaryQuery.error) && (
          <EmptyState message="No Finals summary available for this run." />
        )}

        {safeRollover && (
          <MetadataList
            items={[
              { label: 'Latest rollover to season', value: safeRollover.rollover.to_season },
              { label: 'Transitioned players', value: safeRollover.rollover.transitioned_players }
            ]}
          />
        )}
        {!safeRollover && isApiNotFound(latestRolloverQuery.error) && (
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
        {lineageMismatch && <p role="alert" className="error">Lineage belongs to another Run. Child count and season-chain inspection link are hidden.</p>}
        {sourceQuery.data && (
          <CompactSummaryCard
            items={[
              { label: 'Source type', value: sourceQuery.data.source.source_type || 'Unknown' },
              {
                label: 'Parent run',
                value: sourceQuery.data.source.parent_run_id ? (
                  <Link to={`/runs/${encodeURIComponent(sourceQuery.data.source.parent_run_id)}`}>{sourceQuery.data.source.parent_run_id}</Link>
                ) : (
                  'No parent run'
                )
              },
              { label: 'Child run count', value: safeLineage?.lineage.children.length ?? '—' }
            ]}
          />
        )}
        {!sourceQuery.data && isApiNotFound(sourceQuery.error) && <EmptyState message="No source metadata available." />}
        {!safeLineage && isApiNotFound(lineageQuery.error) && <EmptyState message="No lineage metadata available." />}
      </SectionCard>

      <SectionCard title="Recent activity">
        {(eventsMismatch || rankingsMismatch || racesMismatch) && (
          <p role="alert" className="error">
            History response belongs to another Run. Unrelated artifacts and inspection links are hidden.
          </p>
        )}
        <p>
          <Link to={`/runs/${encodeURIComponent(runId)}/activity`}>Open aggregated run activity feed</Link>
        </p>
        <MetadataList
          items={[
            {
              label: 'Latest completed event',
              value: eventsQuery.isLoading
                ? 'Loading...'
                : eventsQuery.error
                  ? `Error: ${formatApiError(eventsQuery.error)}`
                  : eventsMismatch
                    ? 'Run mismatch'
                    : latestCompletedEvent
                    ? (
                        <>
                          Available —{' '}
                          <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
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
                  : rankingsMismatch
                    ? 'Run mismatch'
                    : latestRankingSnapshot
                    ? (
                        <>
                          Available —{' '}
                          <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
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
                  : racesMismatch
                    ? 'Run mismatch'
                    : latestRaceSnapshot
                    ? (
                        <>
                          Available —{' '}
                          <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
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
          subtitle="Shows the three newest persisted events by sequence."
          isLoading={eventsQuery.isLoading}
          loadingText="Loading recent events..."
          errorText={eventsMismatch ? 'Event history belongs to a different Run.' :
            eventsQuery.error ? `Failed to load events: ${formatApiError(eventsQuery.error)}` : undefined}
          items={safeEvents.slice().sort((a, b) => b.event_sequence - a.event_sequence).slice(0, 3)}
          emptyText="No events are available yet."
          listAriaLabel="Diagnostics recent events"
          getKey={(event) => event.event_id}
          renderItem={(event) => (
            <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(event.event_id)}`}>
              <strong>{event.event_id}</strong> <span className="status">• Seq {event.event_sequence}</span>
            </Link>
          )}
          viewAllLink={<Link to={`/runs/${encodeURIComponent(runId)}/events`}>View all events</Link>}
        />
      </SectionCard>

      <SectionCard title="Availability / artifact state">
        <SummaryPills
          items={[
            {
              label: 'Finals qualification',
              value: finalsSummaryQuery.isLoading
                ? 'Loading...'
                : finalsSummaryQuery.error || finalsMismatch
                  ? finalsMismatch ? 'Error' : isApiNotFound(finalsSummaryQuery.error)
                    ? 'Missing'
                    : 'Error'
                  : safeFinals?.qualification
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Finals result',
              value: finalsSummaryQuery.isLoading
                ? 'Loading...'
                : finalsSummaryQuery.error || finalsMismatch
                  ? finalsMismatch ? 'Error' : isApiNotFound(finalsSummaryQuery.error)
                    ? 'Missing'
                    : 'Error'
                  : safeFinals?.result
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Latest rollover',
              value: latestRolloverQuery.isLoading
                ? 'Loading...'
                : latestRolloverQuery.error || rolloverMismatch
                  ? rolloverMismatch ? 'Error' : isApiNotFound(latestRolloverQuery.error)
                    ? 'Missing'
                    : 'Error'
                  : safeRollover?.rollover
                    ? 'Available'
                    : 'None yet'
            },
            { label: 'Source metadata', value: artifactAvailability({ isLoading: sourceQuery.isLoading, error: sourceQuery.error, availableLabel: sourceQuery.data ? 'Available' : '', noneLabel: 'None yet' }) },
            { label: 'Lineage metadata', value: artifactAvailability({ isLoading: lineageQuery.isLoading, error: lineageMismatch ? new Error('Run mismatch') : lineageQuery.error, availableLabel: safeLineage ? 'Available' : '', noneLabel: 'None yet' }) },
            {
              label: 'Events',
              value: eventsQuery.isLoading
                ? 'Loading...'
                : eventsQuery.error || eventsMismatch
                  ? 'Error'
                  : safeEvents.length > 0
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Ranking snapshots',
              value: rankingSnapshotsQuery.isLoading
                ? 'Loading...'
                : rankingSnapshotsQuery.error || rankingsMismatch
                  ? 'Error'
                  : safeRankingSnapshots.length > 0
                    ? 'Available'
                    : 'None yet'
            },
            {
              label: 'Race snapshots',
              value: raceSnapshotsQuery.isLoading
                ? 'Loading...'
                : raceSnapshotsQuery.error || racesMismatch
                  ? 'Error'
                  : safeRaceSnapshots.length > 0
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
              <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
                Inspect latest completed event ({latestCompletedEvent.event_id})
              </Link>
            </li>
          ) : null}
          {latestRankingSnapshot ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
                Inspect latest ranking snapshot (Seq {latestRankingSnapshot.snapshot_sequence})
              </Link>
            </li>
          ) : null}
          {latestRaceSnapshot ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
                Inspect latest race snapshot (Seq {latestRaceSnapshot.snapshot_sequence})
              </Link>
            </li>
          ) : null}
          {nextPlannedEvent && nextPlannedWeek !== null ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${nextPlannedWeek}`}>
                Inspect current week detail (W{nextPlannedWeek} from {nextPlannedEvent.event_id})
              </Link>
            </li>
          ) : null}
          {safeFinals?.qualification || safeFinals?.result ? (
            <li>
              <Link to={finalsInspectionRoute}>
                {safeFinals?.result
                  ? 'Inspect Finals result detail (result available)'
                  : 'Inspect Finals qualification detail (qualification available, result pending)'}
              </Link>
            </li>
          ) : null}
          {safeRollover?.rollover ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/rollover`}>Inspect latest rollover details</Link>
            </li>
          ) : null}
          {hasLineageChildren ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/season-chain`}>Inspect season chain ({safeLineage?.lineage.children.length} child run(s))</Link>
            </li>
          ) : null}
          {!latestCompletedEvent &&
          !latestRankingSnapshot &&
          !latestRaceSnapshot &&
          !(nextPlannedEvent && nextPlannedWeek !== null) &&
          !safeRollover?.rollover &&
          !hasLineageChildren &&
          !(safeFinals?.qualification || safeFinals?.result) ? (
            <li>
              <span className="status">No targeted inspection links yet. Use quick navigation below.</span>
            </li>
          ) : null}
        </ul>
      </SectionCard>

      <SectionCard title="Quick navigation">
        <ul className="item-list" aria-label="Diagnostics quick navigation">
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}`}>Run Detail</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/events`}>Events</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/calendar`}>Season Calendar</Link>
          </li>
          <li>
            {nextPlannedWeek !== null ? (
              <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${nextPlannedWeek}`}>Week Detail (current week)</Link>
            ) : (
              <span>Week Detail (current week unavailable)</span>
            )}
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/activity`}>Activity</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/finals`}>World Tour Finals</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/rollover`}>Season Rollover</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/bootstrap-lineage`}>Bootstrap / Lineage</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/season-chain`}>Season Chain</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/ranking`}>Ranking snapshots</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/race`}>Race snapshots</Link>
          </li>
        </ul>
      </SectionCard>
    </section>
  )
}
