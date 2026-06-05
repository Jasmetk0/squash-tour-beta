import { useQuery } from '@tanstack/react-query'

import {
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
  listRunPlayers,
} from '../../../api/client'
import {
  ViewerActiveRunLinks,
  ViewerEmptyState,
  ViewerSampleList,
} from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerCountriesPath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTopH2HPath,
  viewerTopSearchPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'
import { renderPlayerSampleMetadata } from '../people'
import {
  type ViewerPlayersDeferredKind,
  viewerPlayersDeferredConfigs,
} from './viewerDeferredConfigs'

export function ViewerPlayersDeferredPage({
  kind,
}: {
  kind: ViewerPlayersDeferredKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const config = viewerPlayersDeferredConfigs[kind]
  const playersQuery = useQuery({
    queryKey: ['viewer-players-deferred-run-players', activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const statusQuery = useQuery({
    queryKey: ['viewer-players-deferred-status', activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-players-deferred-events', activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-players-deferred-ranking-snapshots', activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-players-deferred-race-snapshots', activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: Boolean(activeRunId),
    retry: false,
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only Players destination requiring an active Viewer run."
      >
        <ViewerEmptyState>
          No data is available for this run yet.
        </ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const players = playersQuery.data?.players ?? []
  const samplePlayers = players.slice(0, 5)
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
    playersQuery.isLoading ||
    statusQuery.isLoading ||
    eventsQuery.isLoading ||
    rankingSnapshotsQuery.isLoading ||
    raceSnapshotsQuery.isLoading
  const hasMetadataError =
    playersQuery.isError ||
    statusQuery.isError ||
    eventsQuery.isError ||
    rankingSnapshotsQuery.isError ||
    raceSnapshotsQuery.isError

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only Players page using existing active-run player metadata only."
    >
      <article
        className="viewer-active-run-card"
        aria-label={`${config.title} active run player metadata summary`}
      >
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.title} sources</h3>
        <p className="subtitle">
          No real read model exists yet. This page only shows safe player and
          source metadata from the active Viewer run.
        </p>
        {isLoadingMetadata ? (
          <p className="status">Loading active run player metadata…</p>
        ) : null}
        {hasMetadataError ? (
          <ViewerEmptyState>
            Some active run player metadata is temporarily unavailable.
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
              <dt>Total player count</dt>
              <dd>
                {playersQuery.isLoading
                  ? 'Loading…'
                  : (playersQuery.data?.total ?? '—')}
              </dd>
            </div>
            <div>
              <dt>Returned/sample player count</dt>
              <dd>
                {playersQuery.isLoading
                  ? 'Loading…'
                  : `${players.length}/${samplePlayers.length}`}
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
          players.length === 0 &&
          completedEventCount === 0 &&
          rankingSnapshotCount === 0 &&
          raceSnapshotCount === 0 ? (
            <ViewerEmptyState>
              No data is available for this run yet.
            </ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={`${config.title} sample players`}>
          <h3>Sample players</h3>
          <p className="status">
            Read-only sample from the active run player endpoint using
            identifiers and metadata fields already returned by the API.
          </p>
          <ViewerSampleList
            title="Sample active run players"
            label={`${config.title} safe sample players`}
            items={samplePlayers}
            getKey={(player) =>
              player.player_id || player.name || 'unknown-player'
            }
            renderItem={(player) =>
              renderPlayerSampleMetadata(player, activeRunId, {
                includeQualityBand: true,
              })
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
            links={[
              {
                label: 'Open active run players',
                to: viewerPlayersPath(activeRunId),
              },
              {
                label: 'Open active run countries',
                to: viewerCountriesPath(activeRunId),
              },
              {
                label: 'Open active run rankings',
                to: viewerRankingsPath(activeRunId),
              },
              {
                label: 'Open active run tournaments',
                to: viewerTournamentsPath(activeRunId),
              },
              { label: 'Open Viewer search', to: viewerTopSearchPath() },
              { label: 'Open run browser', to: viewerRunsPath() },
            ]}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}
