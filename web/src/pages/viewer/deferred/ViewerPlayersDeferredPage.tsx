import type { ViewerPlayersDeferredKind } from './viewerDeferredConfigs'
import { ViewerSavedPlayerDirectoriesPage } from './ViewerSavedPlayerDirectoriesPage'

// All three legacy placeholders now consume the same verified public Saved
// player projection; no Admin/current-run sample data is read in Viewer.
export function ViewerPlayersDeferredPage({ kind }: {
  kind: ViewerPlayersDeferredKind
}): JSX.Element {
  return <ViewerSavedPlayerDirectoriesPage kind={kind} />
}
