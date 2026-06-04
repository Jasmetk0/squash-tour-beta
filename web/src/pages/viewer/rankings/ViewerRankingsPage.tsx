import { findViewerTopLevelHubLink } from '../../../viewer/viewerHubLinks'
import { viewerRankingSnapshotPath, viewerRankingsPath } from '../../../viewer/viewerRoutes'
import { ViewerSnapshotLandingPage } from './ViewerSnapshotLandingPage'

const VIEWER_RANKINGS_HUB_LINK = findViewerTopLevelHubLink('MSA Rankings')

export function ViewerRankingsPage(): JSX.Element {
  return (
    <ViewerSnapshotLandingPage
      config={{
        mode: 'ranking',
        title: VIEWER_RANKINGS_HUB_LINK.label,
        description: VIEWER_RANKINGS_HUB_LINK.description ?? '',
        emptyMessage: 'No data is available for this run yet.',
        noSnapshotsMessage: 'No data is available for this run yet.',
        countLabel: 'Ranking snapshot count',
        openLabel: 'Open active run rankings',
        latestLabel: 'View latest ranking snapshot',
        runScopedPath: (runId) => viewerRankingsPath(runId),
        detailPath: (runId, snapshotSequence) => viewerRankingSnapshotPath(runId, snapshotSequence)
      }}
    />
  )
}
