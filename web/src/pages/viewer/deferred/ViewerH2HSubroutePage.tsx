import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getFinalsSummary,
  getRunStatusSummary,
  listEvents,
  listRaceSnapshots,
  listRankingSnapshots,
  listRunPlayers,
} from '../../../api/client'
import {
  ViewerActiveRunCard,
  ViewerActiveRunLinks,
  ViewerEmptyState,
  ViewerLandingGrid,
  ViewerMetadataList,
  ViewerSectionCard,
} from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerFinalsPath,
  viewerPlayersPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTopH2HPath,
  viewerTournamentsPath,
} from '../../../viewer/viewerRoutes'
import { ViewerSamplePlayersList } from '../explore/viewerComparisonRender'
import { formatFinalsAvailability } from '../tour/viewerTourDisplay'
import { hasAvailableFinals } from './viewerDeferredSourceMetadata'
import {
  type ViewerH2HSubrouteKind,
  viewerH2HSubrouteContent,
} from './viewerDeferredConfigs'

export function ViewerH2HSubroutePage({
  kind,
}: {
  kind: ViewerH2HSubrouteKind
}): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const content = viewerH2HSubrouteContent[kind]
  const queryEnabled = Boolean(activeRunId)
  const statusQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-status', kind, activeRunId],
    queryFn: () => getRunStatusSummary(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const playersQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-players', kind, activeRunId],
    queryFn: () => listRunPlayers(activeRunId ?? '', { limit: 50, offset: 0 }),
    enabled: queryEnabled,
    retry: false,
  })
  const eventsQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-events', kind, activeRunId],
    queryFn: () => listEvents(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const rankingSnapshotsQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-ranking-snapshots', kind, activeRunId],
    queryFn: () => listRankingSnapshots(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const raceSnapshotsQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-race-snapshots', kind, activeRunId],
    queryFn: () => listRaceSnapshots(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })
  const finalsQuery = useQuery({
    queryKey: ['viewer-h2h-subroute-finals', kind, activeRunId],
    queryFn: () => getFinalsSummary(activeRunId ?? ''),
    enabled: queryEnabled,
    retry: false,
  })

  if (!activeRunId) {
    return (
      <ViewerShellPage
        title={content.title}
        description="Read-only H2H Explorer that defers analytics until authoritative match history exists."
      >
        <ViewerEmptyState>
          No data is available for this run yet.
        </ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const samplePlayers = playersQuery.data?.players ?? []
  const playerTotal = playersQuery.data?.total
  const completedEventCount =
    eventsQuery.data?.events.length ??
    statusQuery.data?.history_counts.events ??
    statusQuery.data?.progress.completed_event_count
  const rankingSnapshotCount =
    rankingSnapshotsQuery.data?.snapshots.length ??
    statusQuery.data?.history_counts.ranking_snapshots
  const raceSnapshotCount =
    raceSnapshotsQuery.data?.snapshots.length ??
    statusQuery.data?.history_counts.race_snapshots
  const finalsAvailability = finalsQuery.data
    ? formatFinalsAvailability(finalsQuery.data)
    : statusQuery.data?.finals.result_available
      ? 'Finals result available'
      : statusQuery.data?.finals.qualification_available
        ? 'Finals qualification available'
        : 'Finals summary not available yet'
  const hasFinalsAvailability = hasAvailableFinals(finalsAvailability)

  return (
    <ViewerShellPage
      title={content.title}
      description="Read-only H2H Explorer that defers analytics until authoritative match history exists."
    >
      <ViewerLandingGrid>
        <ViewerActiveRunCard
          ariaLabel={`${content.title} source metadata`}
          kicker="Active Viewer run"
          title={`${content.title} source metadata`}
        >
          {statusQuery.isLoading ||
          playersQuery.isLoading ||
          eventsQuery.isLoading ||
          rankingSnapshotsQuery.isLoading ||
          raceSnapshotsQuery.isLoading ||
          finalsQuery.isLoading ? (
            <p className="status">Loading active-run metadata…</p>
          ) : null}
          <ViewerMetadataList
            ariaLabel={`${content.title} source metadata values`}
            items={[
              { label: 'Active run ID', value: activeRunId },
              {
                label: 'Total player count',
                value: playersQuery.isLoading
                  ? 'Loading…'
                  : (playerTotal ?? '—'),
              },
              {
                label: 'Returned/sample player count',
                value: playersQuery.isLoading
                  ? 'Loading…'
                  : samplePlayers.length,
              },
              {
                label: 'Completed/persisted event count',
                value: eventsQuery.isLoading
                  ? 'Loading…'
                  : (completedEventCount ?? '—'),
              },
              {
                label: 'Ranking snapshot count',
                value: rankingSnapshotsQuery.isLoading
                  ? 'Loading…'
                  : (rankingSnapshotCount ?? '—'),
              },
              {
                label: 'Race snapshot count',
                value: raceSnapshotsQuery.isLoading
                  ? 'Loading…'
                  : (raceSnapshotCount ?? '—'),
              },
              {
                label: 'Finals availability',
                value: finalsQuery.isLoading ? (
                  'Loading…'
                ) : hasFinalsAvailability ? (
                  <Link to={viewerFinalsPath(activeRunId)}>
                    {finalsAvailability}
                  </Link>
                ) : (
                  finalsAvailability
                ),
              },
            ]}
          />
          {!playersQuery.isLoading &&
          !playersQuery.isError &&
          samplePlayers.length === 0 ? (
            <ViewerEmptyState>
              No data is available for this run yet.
            </ViewerEmptyState>
          ) : null}
          <ViewerSamplePlayersList
            players={samplePlayers}
            label={`${content.title} sample players`}
            runId={activeRunId}
          />
        </ViewerActiveRunCard>
        <ViewerSectionCard
          title="Deferred H2H outputs"
          kicker="No authoritative match read model"
        >
          <ViewerEmptyState>
            This preview is not connected for this data shape yet.
          </ViewerEmptyState>
          <p className="status">{content.note}</p>
        </ViewerSectionCard>
        <ViewerSectionCard title="Source links" kicker="Read-only navigation">
          <ViewerActiveRunLinks
            links={[
              { label: 'Open H2H comparison', to: viewerTopH2HPath() },
              {
                label: 'Open active run players',
                to: viewerPlayersPath(activeRunId),
              },
              {
                label: 'Open active run tournaments',
                to: viewerTournamentsPath(activeRunId),
              },
              {
                label: 'Open active run rankings',
                to: viewerRankingsPath(activeRunId),
              },
              {
                label: 'Open active run race',
                to: viewerRacePath(activeRunId),
              },
              { label: 'Open run browser', to: viewerRunsPath() },
            ]}
          />
        </ViewerSectionCard>
      </ViewerLandingGrid>
    </ViewerShellPage>
  )
}
