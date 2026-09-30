import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { commonDeferredSourceMetadataItems } from './ViewerDeferredSourceMetadataRender'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'
import { buildStatsDeferredSourceLinks } from './viewerDeferredLinks'
import {
  type ViewerStatsDeferredKind,
  viewerStatsDeferredConfigs,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerStatsDeferredPage({
  kind,
}: {
  kind: ViewerStatsDeferredKind
}): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const config = viewerStatsDeferredConfigs[kind]
  const {
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    productRunId,
    kind,
    scope: 'stats',
  })

  if (!productRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only stats and records destination requiring a selected Viewer Product Run."
      >
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only stats and records page using canonical Saved-Revision source metadata only."
    >
      <ViewerDeferredSourceCard
        title={config.title}
        subtitle={
          <>
            No records or statistics are calculated here yet. This page only
            shows safe canonical source availability from the selected Product Run.
          </>
        }
        isLoadingMetadata={isLoadingMetadata}
        hasMetadataError={hasMetadataError}
        hasAnySourceMetadata={hasAnySourceMetadata}
        metadataItems={commonDeferredSourceMetadataItems({
          productRunId,
          metadata,
          isLoading: isLoadingMetadata,
        })}
        deferredCopy={config.deferredCopy}
        sourceLinks={buildStatsDeferredSourceLinks(productRunId)}
        sourceLinksAriaLabel={config.title + ' links'}
      />
    </ViewerShellPage>
  )
}
