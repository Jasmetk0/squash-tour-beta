import { Link } from 'react-router-dom'

import { ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import { viewerPlannedEventPath } from '../../../viewer/viewerRoutes'
import {
  commonDeferredSourceMetadataItems,
  renderLoadingValue,
} from './ViewerDeferredSourceMetadataRender'
import { ViewerDeferredSourceCard } from './ViewerDeferredSourceCard'
import { buildTourDeferredSourceLinks } from './viewerDeferredLinks'
import {
  type ViewerTourDeferredKind,
  viewerTourDeferredConfigs,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerTourDeferredPage({
  kind,
}: {
  kind: ViewerTourDeferredKind
}): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const config = viewerTourDeferredConfigs[kind]
  const {
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    productRunId,
    kind,
    scope: 'tour',
  })

  if (!productRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only Tour destination requiring a selected Viewer Product Run."
      >
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only Tour page using canonical Saved-Revision source metadata only."
    >
      <ViewerDeferredSourceCard
        title={config.title}
        subtitle={
          <>
            No dedicated read model exists yet. This page only shows safe canonical
            source availability from the selected Product Run.
          </>
        }
        isLoadingMetadata={isLoadingMetadata}
        hasMetadataError={hasMetadataError}
        hasAnySourceMetadata={hasAnySourceMetadata}
        metadataItems={[
          ...commonDeferredSourceMetadataItems({
            productRunId,
            metadata,
            isLoading: isLoadingMetadata,
          }),
          {
            label: 'Next Saved Calendar event',
            value: isLoadingMetadata
              ? renderLoadingValue(true, null)
              : metadata.nextCalendarEvent
                ? (
                  <Link to={viewerPlannedEventPath(productRunId, metadata.nextCalendarEvent.event_id)}>
                    {metadata.nextCalendarEvent.event_name || metadata.nextCalendarEvent.event_id}
                  </Link>
                )
                : '—',
          },
        ]}
        deferredCopy={config.deferredCopy}
        sourceLinks={buildTourDeferredSourceLinks(productRunId)}
        sourceLinksAriaLabel={config.title + ' source links'}
      />
    </ViewerShellPage>
  )
}
