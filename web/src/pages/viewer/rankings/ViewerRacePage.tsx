import { findViewerTopLevelHubLink } from '../../../viewer/viewerHubLinks'
import { viewerRacePath, viewerRaceSnapshotPath } from '../../../viewer/viewerRoutes'
import { ViewerSnapshotLandingPage } from './ViewerSnapshotLandingPage'

const VIEWER_RACE_HUB_LINK = findViewerTopLevelHubLink('Race to Finals')

export function ViewerRacePage(): JSX.Element {
  return (
    <ViewerSnapshotLandingPage
      config={{
        mode: 'race',
        title: VIEWER_RACE_HUB_LINK.label,
        description: VIEWER_RACE_HUB_LINK.description ?? '',
        emptyMessage: 'No data is available for this run yet.',
        noSnapshotsMessage: 'No data is available for this run yet.',
        countLabel: 'Race snapshot count',
        openLabel: 'Open active run race',
        latestLabel: 'View latest race snapshot',
        runScopedPath: (runId) => viewerRacePath(runId),
        detailPath: (runId, snapshotSequence) => viewerRaceSnapshotPath(runId, snapshotSequence)
      }}
    />
  )
}
