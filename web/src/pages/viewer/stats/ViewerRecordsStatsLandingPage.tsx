import { useQuery } from '@tanstack/react-query'
import { getFinalsSummary, getRunStatusSummary, listEvents, listRaceSnapshots, listRankingSnapshots } from '../../../api/client'
import { ViewerActiveRunLinks, ViewerDeferredFeatureList, ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerRunId } from '../../../viewer/useActiveViewerRunId'
import {
  viewerFinalsPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTournamentsPath
} from '../../../viewer/viewerRoutes'
import {
  buildDeferredSourceMetadata,
  commonDeferredSourceMetadataItems,
  hasAnyDeferredSourceMetadata,
  renderSourceMetadataList
} from '../deferred'
import {
  buildStatsRecordsSourceLinks,
  getStatsRecordsDeferredGroups,
  getStatsRecordsLandingConfig,
  type ViewerRecordsLandingKind
} from './viewerStatsRecordsDisplay'

export function ViewerRecordsStatsLandingPage({ kind }: { kind: ViewerRecordsLandingKind }): JSX.Element {
  const activeRunId = useActiveViewerRunId()
  const statusQuery = useQuery({ queryKey: ['viewer-records-status', kind, activeRunId], queryFn: () => getRunStatusSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const eventsQuery = useQuery({ queryKey: ['viewer-records-events', kind, activeRunId], queryFn: () => listEvents(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const rankingSnapshotsQuery = useQuery({ queryKey: ['viewer-records-ranking-snapshots', kind, activeRunId], queryFn: () => listRankingSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const raceSnapshotsQuery = useQuery({ queryKey: ['viewer-records-race-snapshots', kind, activeRunId], queryFn: () => listRaceSnapshots(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const finalsQuery = useQuery({ queryKey: ['viewer-records-finals', kind, activeRunId], queryFn: () => getFinalsSummary(activeRunId ?? ''), enabled: Boolean(activeRunId), retry: false })
  const config = getStatsRecordsLandingConfig(kind)

  if (!activeRunId) {
    return (
      <ViewerShellPage title={config.title} description={config.shellDescription}>
        <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const metadata = buildDeferredSourceMetadata({
    events: eventsQuery.data?.events,
    rankingSnapshots: rankingSnapshotsQuery.data?.snapshots,
    raceSnapshots: raceSnapshotsQuery.data?.snapshots,
    status: statusQuery.data,
    finals: finalsQuery.data
  })
  const hasAnySourceMetadata = hasAnyDeferredSourceMetadata(metadata)
  const deferredGroups = getStatsRecordsDeferredGroups(kind)

  return (
    <ViewerShellPage title={config.title} description={config.activeShellDescription}>
      <article className="viewer-active-run-card" aria-label={`${config.title} active run metadata summary`}>
        <span className="eyebrow">Active Viewer run</span>
        <h3>{config.overviewTitle}</h3>
        <p className="subtitle">{config.overviewDescription}</p>
        {statusQuery.isLoading || eventsQuery.isLoading || rankingSnapshotsQuery.isLoading || raceSnapshotsQuery.isLoading || finalsQuery.isLoading ? <p className="status">Loading active run metadata…</p> : null}
        {statusQuery.isError || eventsQuery.isError || rankingSnapshotsQuery.isError || raceSnapshotsQuery.isError || finalsQuery.isError ? <ViewerEmptyState>Some active run metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={`${config.title} source metadata`}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList(commonDeferredSourceMetadataItems({
            activeRunId,
            metadata,
            eventsLoading: eventsQuery.isLoading,
            rankingSnapshotsLoading: rankingSnapshotsQuery.isLoading,
            raceSnapshotsLoading: raceSnapshotsQuery.isLoading,
            finalsLoading: finalsQuery.isLoading
          }))}
          {!statusQuery.isLoading && !eventsQuery.isLoading && !rankingSnapshotsQuery.isLoading && !raceSnapshotsQuery.isLoading && !finalsQuery.isLoading && !hasAnySourceMetadata ? (
            <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={`${config.title} deferred groups`}>
          <ViewerDeferredFeatureList
            title={config.deferredGroupsTitle}
            label={config.deferredGroupsLabel}
            features={deferredGroups}
          />
        </section>
        <section aria-label={`${config.title} links`}>
          <h3>Links</h3>
          <ViewerActiveRunLinks
            links={buildStatsRecordsSourceLinks({
              activeRunId,
              viewerRunsPath,
              viewerTournamentsPath,
              viewerRankingsPath,
              viewerRacePath,
              viewerFinalsPath
            })}
          />
        </section>
      </article>
    </ViewerShellPage>
  )
}
