import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { commonDeferredSourceMetadataItems } from './ViewerDeferredSourceMetadataRender'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'
import { buildPredictionDeferredSourceLinks } from './viewerDeferredLinks'
import {
  type ViewerPredictionDeferredKind,
  viewerPredictionDeferredConfigs,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerPredictionDeferredPage({
  kind,
}: {
  kind: ViewerPredictionDeferredKind
}): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const config = viewerPredictionDeferredConfigs[kind]
  const {
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    productRunId,
    kind,
    scope: 'prediction',
  })

  if (!productRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only predictions destination requiring a selected Viewer Product Run."
      >
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only predictions page using canonical Saved-Revision source metadata only."
    >
      <ViewerDeferredSourceCard
        title={config.title}
        subtitle={
          <>
            Outputs remain deferred. This page only shows safe canonical source
            availability from the selected Product Run.
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
        sourceLinks={buildPredictionDeferredSourceLinks(productRunId)}
        sourceLinksAriaLabel={config.title + ' links'}
      />
    </ViewerShellPage>
  )
}
