import { ViewerActiveRunLinks, ViewerDeferredFeatureList, ViewerEmptyState } from '../../../components/viewer/ViewerLandingComponents'
import { ViewerShellPage } from '../../../components/viewer/ViewerShellPage'
import { useActiveViewerProductRunId } from '../../../viewer/useActiveViewerProductRunId'
import {
  viewerFinalsPath,
  viewerRacePath,
  viewerRankingsPath,
  viewerRunsPath,
  viewerTournamentsPath
} from '../../../viewer/viewerRoutes'
import {
  commonDeferredSourceMetadataItems,
  renderSourceMetadataList,
  useViewerDeferredSourceQueries
} from '../deferred'
import {
  buildStatsRecordsSourceLinks,
  getStatsRecordsDeferredGroups,
  getStatsRecordsLandingConfig,
  type ViewerRecordsLandingKind
} from './viewerStatsRecordsDisplay'

export function ViewerRecordsStatsLandingPage({ kind }: { kind: ViewerRecordsLandingKind }): JSX.Element {
  const productRunId = useActiveViewerProductRunId()
  const config = getStatsRecordsLandingConfig(kind)
  const {
    metadata,
    isLoadingMetadata,
    hasMetadataError,
    hasAnySourceMetadata,
  } = useViewerDeferredSourceQueries({
    productRunId,
    kind,
    scope: 'records-stats',
  })

  if (!productRunId) {
    return (
      <ViewerShellPage title={config.title} description={config.shellDescription}>
        <ViewerEmptyState>No Product Run is selected yet.</ViewerEmptyState>
      </ViewerShellPage>
    )
  }

  const deferredGroups = getStatsRecordsDeferredGroups(kind)

  return (
    <ViewerShellPage title={config.title} description={config.activeShellDescription}>
      <article className="viewer-active-run-card" aria-label={config.title + ' canonical Product Run metadata summary'}>
        <span className="eyebrow">Selected Product Run</span>
        <h3>{config.overviewTitle}</h3>
        <p className="subtitle">{config.overviewDescription}</p>
        {isLoadingMetadata ? <p className="status">Loading canonical Saved-Revision metadata…</p> : null}
        {hasMetadataError ? <ViewerEmptyState>Some canonical Saved-Revision metadata is temporarily unavailable.</ViewerEmptyState> : null}
        <section aria-label={config.title + ' source metadata'}>
          <h3>Available source metadata</h3>
          {renderSourceMetadataList(commonDeferredSourceMetadataItems({
            productRunId,
            metadata,
            isLoading: isLoadingMetadata
          }))}
          {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? (
            <ViewerEmptyState>No canonical source data is available for this Product Run yet.</ViewerEmptyState>
          ) : null}
        </section>
        <section aria-label={config.title + ' deferred groups'}>
          <ViewerDeferredFeatureList
            title={config.deferredGroupsTitle}
            label={config.deferredGroupsLabel}
            features={deferredGroups}
          />
        </section>
        <section aria-label={config.title + ' links'}>
          <h3>Links</h3>
          <ViewerActiveRunLinks
            links={buildStatsRecordsSourceLinks({
              activeRunId: productRunId,
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
