import { ViewerTourArchivePage } from './ViewerTourArchivePage'
import { ViewerSavedMatchCenterPage } from './ViewerSavedMatchCenterPage'
import type { ViewerTourDeferredKind } from './viewerDeferredConfigs'

// All three public Tour destinations now consume independently verified
// legacy Saved read models; no Admin/Working Draft fallbacks.
export function ViewerTourDeferredPage({ kind }: {
  kind: ViewerTourDeferredKind
}): JSX.Element {
  if (kind === 'matches') return <ViewerSavedMatchCenterPage />
  return <ViewerTourArchivePage kind={kind} />
}
