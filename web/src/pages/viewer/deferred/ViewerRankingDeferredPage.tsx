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
import { buildRankingDeferredSourceLinks } from './viewerDeferredLinks'
import {
  viewerRankingDeferredConfigs,
  type ViewerRankingDeferredKind,
} from './viewerDeferredConfigs'
import { useViewerDeferredSourceQueries } from './useViewerDeferredSourceQueries'

export function ViewerRankingDeferredPage({
  kind,
}: {
  kind: ViewerRankingDeferredKind
}): JSX.Element {
  const config = viewerRankingDeferredConfigs[kind]
  const productRunId = useActiveViewerProductRunId()
  const {
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    productRunId,
    kind,
    scope: 'ranking',
  })

  if (!productRunId) {
    return (
      <ViewerShellPage
        title={config.title}
        description="Read-only rankings destination requiring a selected Viewer Product Run."
      >
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  return (
    <ViewerShellPage
      title={config.title}
      description="Conservative read-only rankings page using canonical Saved-Revision source metadata only."
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
        sourceLinks={buildRankingDeferredSourceLinks(productRunId)}
        sourceLinksAriaLabel={config.title + ' source links'}
      />
    </ViewerShellPage>
  )
}
