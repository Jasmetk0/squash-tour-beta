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

import { useHistoryText } from './runHistoryText'
export function RunDiagnosticsPage(): JSX.Element {
  const t = useHistoryText()
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
  const safeRun = !runQuery.error && runQuery.data?.run.run_id === runId ? runQuery.data : null
  const safeStatus = !statusSummaryQuery.error && statusSummaryQuery.data?.run_id === runId ? statusSummaryQuery.data : null

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
  const safeFinals = !finalsMismatch && !finalsSummaryQuery.error && finalsSummaryQuery.data?.run_id === runId ? finalsSummaryQuery.data : null
  const safeRollover = !latestRolloverQuery.error && latestRolloverQuery.data?.rollover.run_id === runId ? latestRolloverQuery.data : null
  const safeLineage = !lineageQuery.error && lineageQuery.data?.lineage.run_id === runId ? lineageQuery.data : null
  const safeSource = !sourceQuery.error ? sourceQuery.data : null

  // Every history response has a Run ID; never display another Run's artifacts.
  const eventsMismatch = Boolean(eventsQuery.data && eventsQuery.data.run_id !== runId)
  const rankingsMismatch = Boolean(rankingSnapshotsQuery.data && rankingSnapshotsQuery.data.run_id !== runId)
  const racesMismatch = Boolean(raceSnapshotsQuery.data && raceSnapshotsQuery.data.run_id !== runId)
  const safeEvents = !eventsQuery.error && eventsQuery.data?.run_id === runId ? eventsQuery.data.events : []
  const safeRankingSnapshots = !rankingSnapshotsQuery.error && rankingSnapshotsQuery.data?.run_id === runId ? rankingSnapshotsQuery.data.snapshots : []
  const safeRaceSnapshots = !raceSnapshotsQuery.error && raceSnapshotsQuery.data?.run_id === runId ? raceSnapshotsQuery.data.snapshots : []

  // History endpoints return ascending sequences; the first item is the oldest.
  // Select by persisted sequence rather than relying on response array order.
  const latestCompletedEvent = safeEvents
    .filter((event) => Boolean(event.tournament_result))
    .sort((a, b) => b.event_sequence - a.event_sequence)[0]
  const latestRankingSnapshot = safeRankingSnapshots
    .slice().sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0]
  const latestRaceSnapshot = safeRaceSnapshots
    .slice().sort((a, b) => b.snapshot_sequence - a.snapshot_sequence)[0]
  // The Run endpoint builds its summary and season state from separate reads.
  // If a concurrent update made them inconsistent, do not link to an obsolete week.
  const seasonStateMismatch = Boolean(safeRun && (
    safeRun.season_state.season !== safeRun.run.season ||
    safeRun.season_state.next_event_index !== safeRun.run.next_event_index
  ))
  const candidateNextEvent = safeRun?.season_state.ordered_events[safeRun.season_state.next_event_index] ?? null
  const nextEventSeasonMismatch = Boolean(candidateNextEvent && candidateNextEvent.season !== safeRun?.run.season)
  // Different read times can leave the detail and status-summary endpoints at
  // different seasons or progress cursors, even though their Run IDs match.
  const runStatusProgressMismatch = Boolean(safeRun && safeStatus && (
    safeRun.run.season !== safeStatus.season ||
    safeRun.run.next_event_index !== safeStatus.progress.next_event_index ||
    safeRun.run.total_events !== safeStatus.progress.total_events
  ))
  const nextPlannedEvent = seasonStateMismatch || nextEventSeasonMismatch || runStatusProgressMismatch
    ? null : candidateNextEvent
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
        title={t('Run diagnostics')}
        runId={runId}
        subtitle={t('Read-only run health, progress, and structure summary.')}
      />
      <p>
        <Link to={`/runs/${encodeURIComponent(runId)}/world-generation`}>{t('Open world generation diagnostics')}</Link>
      </p>
      <p className="status">{t('Stored legacy SimulationRun history. This view does not verify Product Run Saved Revision authority.')}</p>
      <button type="button" onClick={() => {
        void runQuery.refetch(); void statusSummaryQuery.refetch(); void finalsSummaryQuery.refetch()
        void latestRolloverQuery.refetch(); void sourceQuery.refetch(); void lineageQuery.refetch()
        void eventsQuery.refetch(); void rankingSnapshotsQuery.refetch(); void raceSnapshotsQuery.refetch()
      }}>{t('Refresh read-only data')}</button>
      <CurrentContextStrip
        items={[
          { label: t('Season'), value: safeStatus?.season ?? safeRun?.run.season ?? '—' },
          {
            label: t('Progress'),
            value: safeStatus
              ? `${safeStatus.progress.next_event_index}/${safeStatus.progress.total_events}`
              : safeRun
                ? `${safeRun.run.next_event_index}/${safeRun.run.total_events}`
                : '—'
          },
          {
            label: t('Completed events'),
            value: safeStatus?.progress.completed_event_count ?? safeRun?.run.completed_event_ids.length ?? '—'
          }
        ]}
      />

      <SectionCard title={t('Run diagnostics summary')}>
        {runQuery.isLoading && <p className="status">{t('Loading run diagnostics...')}</p>}
        {runQuery.error && <p className="error">{t('Failed to load run details')}: {formatApiError(runQuery.error)}</p>}
        {runMismatch && <p role="alert" className="error">{t('Run details belong to another Run. Its progress and planned week are hidden.')}</p>}
        {(seasonStateMismatch || nextEventSeasonMismatch) && (
          <p role="alert" className="error">{t('Run calendar and progress disagree. Current-week links are hidden.')}</p>
        )}
        {runStatusProgressMismatch && (
          <p role="alert" className="error">{t('Run detail and status summary disagree on season or progress. Current-week links are hidden.')}</p>
        )}
        {statusSummaryQuery.error && (
          <p className="error">{t('Failed to load status summary')}: {formatApiError(statusSummaryQuery.error)}</p>
        )}
        {statusMismatch && <p role="alert" className="error">{t('Status summary belongs to another Run. Its progress and counts are hidden.')}</p>}
        {(safeRun || safeStatus) && (
          <>
            <CompactSummaryCard
              items={[
                { label: t('Run ID'), value: safeRun?.run.run_id ?? safeStatus?.run_id ?? '—' },
                { label: t('Season'), value: safeStatus?.season ?? safeRun?.run.season ?? '—' },
                { label: t('Seed'), value: safeStatus?.seed ?? safeRun?.run.seed ?? '—' },
                {
                  label: t('Progress'),
                  value: safeStatus
                    ? `${safeStatus.progress.next_event_index} / ${safeStatus.progress.total_events}`
                    : safeRun
                      ? `${safeRun.run.next_event_index} / ${safeRun.run.total_events}`
                      : '—'
                },
                {
                  label: t('Completed events'),
                  value: safeStatus?.progress.completed_event_count ?? safeRun?.run.completed_event_ids.length ?? '—'
                }
              ]}
            />
            <SummaryPills
              items={[
                { label: t('Events'), value: safeStatus?.history_counts.events ?? (!eventsQuery.error && eventsQuery.data?.run_id === runId ? safeEvents.length : '—') },
                {
                  label: t('Ranking snapshots'),
                  value:
                    safeStatus?.history_counts.ranking_snapshots ?? (!rankingSnapshotsQuery.error && rankingSnapshotsQuery.data?.run_id === runId ? safeRankingSnapshots.length : '—')
                },
                {
                  label: t('Race snapshots'),
                  value: safeStatus?.history_counts.race_snapshots ?? (!raceSnapshotsQuery.error && raceSnapshotsQuery.data?.run_id === runId ? safeRaceSnapshots.length : '—')
                }
              ]}
            />
          </>
        )}
      </SectionCard>

      <SectionCard title={t('Finals and rollover')}>
        {(finalsSummaryQuery.isLoading || latestRolloverQuery.isLoading) && <p className="status">{t('Loading finals and rollover...')}</p>}
        {finalsSummaryQuery.error && !isApiNotFound(finalsSummaryQuery.error) && (
          <p className="error">{t('Failed to load Finals summary')}: {formatApiError(finalsSummaryQuery.error)}</p>
        )}
        {finalsMismatch && <p role="alert" className="error">{t('Finals summary contains mismatched Run or season data. Its status and inspection links are hidden.')}</p>}
        {rolloverMismatch && <p role="alert" className="error">{t('Rollover summary belongs to another Run. Its result and inspection link are hidden.')}</p>}
        {safeFinals && (
          <MetadataList
            items={[
              {
                label: t('Finals qualification'),
                value: safeFinals.qualification ? t('Available') : t('Not generated yet')
              },
              { label: t('Finals result'), value: safeFinals.result ? t('Available') : t('Not simulated yet') }
            ]}
          />
        )}
        {!safeFinals && isApiNotFound(finalsSummaryQuery.error) && (
          <EmptyState message={t('No Finals summary available for this run.')} />
        )}

        {safeRollover && (
          <MetadataList
            items={[
              { label: t('Latest rollover to season'), value: safeRollover.rollover.to_season },
              { label: t('Transitioned players'), value: safeRollover.rollover.transitioned_players }
            ]}
          />
        )}
        {!safeRollover && isApiNotFound(latestRolloverQuery.error) && (
          <EmptyState message={t('No rollover has been executed for this run yet.')} />
        )}
        {latestRolloverQuery.error && !isApiNotFound(latestRolloverQuery.error) && (
          <p className="error">{t('Failed to load latest rollover')}: {formatApiError(latestRolloverQuery.error)}</p>
        )}
      </SectionCard>

      <SectionCard title={t('Source and lineage')}>
        {(sourceQuery.isLoading || lineageQuery.isLoading) && <p className="status">{t('Loading source and lineage...')}</p>}
        {sourceQuery.error && !isApiNotFound(sourceQuery.error) && (
          <p className="error">{t('Failed to load run source')}: {formatApiError(sourceQuery.error)}</p>
        )}
        {lineageQuery.error && !isApiNotFound(lineageQuery.error) && (
          <p className="error">{t('Failed to load run lineage')}: {formatApiError(lineageQuery.error)}</p>
        )}
        {lineageMismatch && <p role="alert" className="error">{t('Lineage belongs to another Run. Child count and season-chain inspection link are hidden.')}</p>}
        {safeSource && (
          <CompactSummaryCard
            items={[
              { label: t('Source type'), value: safeSource.source.source_type || t('Unknown') },
              {
                label: t('Parent run'),
                value: safeSource.source.parent_run_id ? (
                  <Link to={`/runs/${encodeURIComponent(safeSource.source.parent_run_id)}`}>{safeSource.source.parent_run_id}</Link>
                ) : (
                  t('No parent run')
                )
              },
              { label: t('Child run count'), value: safeLineage?.lineage.children.length ?? '—' }
            ]}
          />
        )}
        {!safeSource && isApiNotFound(sourceQuery.error) && <EmptyState message={t('No source metadata available.')} />}
        {!safeLineage && isApiNotFound(lineageQuery.error) && <EmptyState message={t('No lineage metadata available.')} />}
      </SectionCard>

      <SectionCard title={t('Recent activity')}>
        {(eventsMismatch || rankingsMismatch || racesMismatch) && (
          <p role="alert" className="error">
            {t('History response belongs to another Run. Unrelated artifacts and inspection links are hidden.')}
          </p>
        )}
        <p>
          <Link to={`/runs/${encodeURIComponent(runId)}/activity`}>{t('Open aggregated run activity feed')}</Link>
        </p>
        <MetadataList
          items={[
            {
              label: t('Latest completed event'),
              value: eventsQuery.isLoading
                ? t('Loading...')
                : eventsQuery.error
                  ? `${t('Error')}: ${formatApiError(eventsQuery.error)}`
                  : eventsMismatch
                    ? t('Run mismatch')
                    : latestCompletedEvent
                    ? (
                        <>
                          {t('Available')} —{' '}
                          <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
                            {latestCompletedEvent.event_id} ({t('Seq')} {latestCompletedEvent.event_sequence})
                          </Link>
                        </>
                      )
                    : t('None yet')
            },
            {
              label: t('Latest ranking snapshot'),
              value: rankingSnapshotsQuery.isLoading
                ? t('Loading...')
                : rankingSnapshotsQuery.error
                  ? `${t('Error')}: ${formatApiError(rankingSnapshotsQuery.error)}`
                  : rankingsMismatch
                    ? t('Run mismatch')
                    : latestRankingSnapshot
                    ? (
                        <>
                          {t('Available')} —{' '}
                          <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
                            {t('Seq')} {latestRankingSnapshot.snapshot_sequence}
                          </Link>
                        </>
                      )
                    : t('None yet')
            },
            {
              label: t('Latest race snapshot'),
              value: raceSnapshotsQuery.isLoading
                ? t('Loading...')
                : raceSnapshotsQuery.error
                  ? `${t('Error')}: ${formatApiError(raceSnapshotsQuery.error)}`
                  : racesMismatch
                    ? t('Run mismatch')
                    : latestRaceSnapshot
                    ? (
                        <>
                          {t('Available')} —{' '}
                          <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
                            {t('Seq')} {latestRaceSnapshot.snapshot_sequence}
                          </Link>
                        </>
                      )
                    : t('None yet')
            }
          ]}
        />
        <PreviewListCard
          title={t('Recent events')}
          subtitle={t('Shows the three newest persisted events by sequence.')}
          isLoading={eventsQuery.isLoading}
          loadingText={t('Loading recent events...')}
          errorText={eventsMismatch ? t('Event history belongs to a different Run.') :
            eventsQuery.error ? `${t('Failed to load events')}: ${formatApiError(eventsQuery.error)}` : undefined}
          items={safeEvents.slice().sort((a, b) => b.event_sequence - a.event_sequence).slice(0, 3)}
          emptyText={t('No events are available yet.')}
          listAriaLabel={t('Diagnostics recent events')}
          getKey={(event) => event.event_id}
          renderItem={(event) => (
            <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(event.event_id)}`}>
              <strong>{event.event_id}</strong> <span className="status">• Seq {event.event_sequence}</span>
            </Link>
          )}
          viewAllLink={<Link to={`/runs/${encodeURIComponent(runId)}/events`}>{t('View all events')}</Link>}
        />
      </SectionCard>

      <SectionCard title={t('Availability / artifact state')}>
        <SummaryPills
          items={[
            {
              label: t('Finals qualification'),
              value: finalsSummaryQuery.isLoading
                ? t('Loading...')
                : finalsSummaryQuery.error || finalsMismatch
                  ? finalsMismatch ? t('Error') : isApiNotFound(finalsSummaryQuery.error)
                    ? t('Missing')
                    : t('Error')
                  : safeFinals?.qualification
                    ? t('Available')
                    : t('None yet')
            },
            {
              label: t('Finals result'),
              value: finalsSummaryQuery.isLoading
                ? t('Loading...')
                : finalsSummaryQuery.error || finalsMismatch
                  ? finalsMismatch ? t('Error') : isApiNotFound(finalsSummaryQuery.error)
                    ? t('Missing')
                    : t('Error')
                  : safeFinals?.result
                    ? t('Available')
                    : t('None yet')
            },
            {
              label: t('Latest rollover'),
              value: latestRolloverQuery.isLoading
                ? t('Loading...')
                : latestRolloverQuery.error || rolloverMismatch
                  ? rolloverMismatch ? t('Error') : isApiNotFound(latestRolloverQuery.error)
                    ? t('Missing')
                    : t('Error')
                  : safeRollover?.rollover
                    ? t('Available')
                    : t('None yet')
            },
            { label: t('Source metadata'), value: t(artifactAvailability({ isLoading: sourceQuery.isLoading, error: sourceQuery.error, availableLabel: sourceQuery.data ? t('Available') : '', noneLabel: 'None yet' })) },
            { label: t('Lineage metadata'), value: t(artifactAvailability({ isLoading: lineageQuery.isLoading, error: lineageMismatch ? new Error('Run mismatch') : lineageQuery.error, availableLabel: safeLineage ? t('Available') : '', noneLabel: 'None yet' })) },
            {
              label: t('Events'),
              value: eventsQuery.isLoading
                ? t('Loading...')
                : eventsQuery.error || eventsMismatch
                  ? t('Error')
                  : safeEvents.length > 0
                    ? t('Available')
                    : t('None yet')
            },
            {
              label: t('Ranking snapshots'),
              value: rankingSnapshotsQuery.isLoading
                ? t('Loading...')
                : rankingSnapshotsQuery.error || rankingsMismatch
                  ? t('Error')
                  : safeRankingSnapshots.length > 0
                    ? t('Available')
                    : t('None yet')
            },
            {
              label: t('Race snapshots'),
              value: raceSnapshotsQuery.isLoading
                ? t('Loading...')
                : raceSnapshotsQuery.error || racesMismatch
                  ? t('Error')
                  : safeRaceSnapshots.length > 0
                    ? t('Available')
                    : t('None yet')
            }
          ]}
        />
      </SectionCard>

      <SectionCard title={t('Most relevant next inspection links')}>
        <ul className="item-list" aria-label={t('Diagnostics next inspection links')}>
          {latestCompletedEvent ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/events/${encodeURIComponent(latestCompletedEvent.event_id)}`}>
                {t('Inspect latest completed event')} ({latestCompletedEvent.event_id})
              </Link>
            </li>
          ) : null}
          {latestRankingSnapshot ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/ranking/${latestRankingSnapshot.snapshot_sequence}`}>
                {t('Inspect latest ranking snapshot')} ({t('Seq')} {latestRankingSnapshot.snapshot_sequence})
              </Link>
            </li>
          ) : null}
          {latestRaceSnapshot ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/race/${latestRaceSnapshot.snapshot_sequence}`}>
                {t('Inspect latest race snapshot')} ({t('Seq')} {latestRaceSnapshot.snapshot_sequence})
              </Link>
            </li>
          ) : null}
          {nextPlannedEvent && nextPlannedWeek !== null ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${nextPlannedWeek}`}>
                {t('Inspect current week detail')} (W{nextPlannedWeek} {t('from')} {nextPlannedEvent.event_id})
              </Link>
            </li>
          ) : null}
          {safeFinals?.qualification || safeFinals?.result ? (
            <li>
              <Link to={finalsInspectionRoute}>
                {safeFinals?.result
                  ? t('Inspect Finals result detail (result available)')
                  : t('Inspect Finals qualification detail (qualification available, result pending)')}
              </Link>
            </li>
          ) : null}
          {safeRollover?.rollover ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/rollover`}>{t('Inspect latest rollover details')}</Link>
            </li>
          ) : null}
          {hasLineageChildren ? (
            <li>
              <Link to={`/runs/${encodeURIComponent(runId)}/season-chain`}>{t('Inspect season chain')} ({safeLineage?.lineage.children.length} {t('child run(s)')})</Link>
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
              <span className="status">{t('No targeted inspection links yet. Use quick navigation below.')}</span>
            </li>
          ) : null}
        </ul>
      </SectionCard>

      <SectionCard title={t('Quick navigation')}>
        <ul className="item-list" aria-label={t('Diagnostics quick navigation')}>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}`}>{t('Run Detail')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/events`}>{t('Events')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/calendar`}>{t('Season Calendar')}</Link>
          </li>
          <li>
            {nextPlannedWeek !== null ? (
              <Link to={`/runs/${encodeURIComponent(runId)}/weeks/${nextPlannedWeek}`}>{t('Week Detail (current week)')}</Link>
            ) : (
              <span>{t('Week Detail (current week unavailable)')}</span>
            )}
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/activity`}>{t('Activity')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/finals`}>{t('World Tour Finals')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/rollover`}>{t('Season Rollover')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/bootstrap-lineage`}>{t('Bootstrap / Lineage')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/season-chain`}>{t('Season Chain')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/ranking`}>{t('Ranking snapshots')}</Link>
          </li>
          <li>
            <Link to={`/runs/${encodeURIComponent(runId)}/snapshots/race`}>{t('Race snapshots')}</Link>
          </li>
        </ul>
      </SectionCard>
    </section>
  )
}
