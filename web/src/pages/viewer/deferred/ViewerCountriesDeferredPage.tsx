import { useQuery } from '@tanstack/react-query'

import {
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
  listRunNations,
} from '../../../api/client'
import {
  ViewerActiveRunLinks,
  ViewerEmptyState,
  ViewerSampleList,
} from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import { buildCountriesDeferredSourceLinks } from './viewerDeferredLinks'
import { renderCountrySampleMetadata } from '../people'
import {
  type ViewerCountriesDeferredKind,
  viewerCountriesDeferredConfigs,
} from './viewerDeferredConfigs'

export function ViewerCountriesDeferredPage({
  kind,
}: {
  kind: ViewerCountriesDeferredKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerCountriesDeferredConfigs[kind]
  const nationsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-run-nations', activeRunId],
    queryFn: () => listRunNations(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const statusQuery = useQuery({
    queryKey: ['viewer-countries-deferred-status', activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-events', activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-ranking-snapshots', activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-countries-deferred-race-snapshots', activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only Countries destination requiring an active Viewer run."
      >
        <ViewerEmptyState>
          No data is available for this run yet.
        </ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const nations = nationsQuery.data?.nations ?? []
  const sampleNations = nations.slice(0, 5)
  const completedEventCount =
    eventsQuery.data?.events.length ??
    statusQuery.data?.history_counts.events ??
    null
  const rankingSnapshotCount =
    rankingSnapshotsQuery.data?.snapshots.length ??
    statusQuery.data?.history_counts.ranking_snapshots ??
    null
  const raceSnapshotCount =
    raceSnapshotsQuery.data?.snapshots.length ??
    statusQuery.data?.history_counts.race_snapshots ??
    null
  const isLoadingMetadata =
    nationsQuery.isLoading ||
    statusQuery.isLoading ||
    eventsQuery.isLoading ||
    rankingSnapshotsQuery.isLoading ||
    raceSnapshotsQuery.isLoading
  const hasMetadataError =
    nationsQuery.isError ||
    statusQuery.isError ||
    eventsQuery.isError ||
    rankingSnapshotsQuery.isError ||
    raceSnapshotsQuery.isError

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only Countries page using existing active-run country metadata only."
    >
      <article
        className="viewer-active-run-card"
        aria-label={`${config.title} active run country metadata summary`}
      >
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">
          No real read model exists yet. This page only shows safe country and
          source metadata from the active Viewer run.
        </p>
        {isLoadingMetadata ? (
          <p className="status">Loading active run country metadata…</p>
        ) : null}
        {hasMetadataError ? (
          <ViewerEmptyState>
            Some active run country metadata is temporarily unavailable.
          </ViewerEmptyState>
        ) : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          <dl className="metadata-list">
            <div>
              <dt>Active run ID</dt>
              <dd>{activeRunId}</dd>
            </div>
            <div>
              <dt>Total country/nation count</dt>
              <dd>
                {nationsQuery.isLoading
                  ? 'Loading…'
                  : (nationsQuery.data?.total ?? '—')}
              </dd>
            </div>
            <div>
              <dt>Returned/sample country count</dt>
              <dd>
                {nationsQuery.isLoading
                  ? 'Loading…'
                  : `${nations.length}/${sampleNations.length}`}
              </dd>
            </div>
            <div>
              <dt>Completed/persisted event count</dt>
              <dd>
                {eventsQuery.isLoading && completedEventCount == null
                  ? 'Loading…'
                  : (completedEventCount ?? '—')}
              </dd>
            </div>
            <div>
              <dt>Ranking snapshot count</dt>
              <dd>
                {rankingSnapshotsQuery.isLoading && rankingSnapshotCount == null
                  ? 'Loading…'
                  : (rankingSnapshotCount ?? '—')}
              </dd>
            </div>
            <div>
              <dt>Race snapshot count</dt>
              <dd>
                {raceSnapshotsQuery.isLoading && raceSnapshotCount == null
                  ? 'Loading…'
                  : (raceSnapshotCount ?? '—')}
              </dd>
            </div>
          </dl>
          {!isLoadingMetadata &&
          !hasMetadataError &&
          nations.length === 0 &&
          completedEventCount === 0 &&
          rankingSnapshotCount === 0 &&
          raceSnapshotCount === 0 ? (
            <ViewerEmptyState>
              No data is available for this run yet.
            </ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={`${config.title} sample countries`}>
          <h3>Sample countries</h3>
          <p className="status">
            Read-only sample from the active run nations endpoint using
            identifiers and metadata fields already returned by the API.
          </p>
          <ViewerSampleList
            title="Sample active run countries"
            label={`${config.title} safe sample countries`}
            items={sampleNations}
            getKey={(nation) =>
              nation.country_code || nation.country_name || 'unknown-country'
            }
            renderItem={(nation) =>
              renderCountrySampleMetadata(nation, activeRunId)
            }
          />
        </section>
        <section aria-label={`${config.title} deferred output explanation`}>
          <h3>Deferred output</h3>
          <p className="status">{config.deferredCopy}</p>
        </section>
        <section aria-label={`${config.title} source links`}>
          <h3>Source links</h3>
          <ViewerActiveRunLinks
            links={buildCountriesDeferredSourceLinks(activeRunId)}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}
