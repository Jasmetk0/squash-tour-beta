import type { ReactNode } from 'react'

import {
  ViewerActiveRunLinks,
  ViewerEmptyState,
  type ViewerLandingLink,
} from '../../../components/viewer/ViewerLandingComponents'
import {
  renderSourceMetadataList,
  type DeferredSourceMetadataItem,
} from './ViewerDeferredSourceMetadata'

type ViewerDeferredSourceCardProps = {
  title: string
  subtitle: ReactNode
  isLoadingMetadata: boolean
  hasMetadataError: boolean
  hasAnySourceMetadata: boolean
  metadataItems: DeferredSourceMetadataItem[]
  deferredCopy: ReactNode
  sourceLinks: ViewerLandingLink[]
  sourceLinksAriaLabel: string
}

export function ViewerDeferredSourceCard({
  title,
  subtitle,
  isLoadingMetadata,
  hasMetadataError,
  hasAnySourceMetadata,
  metadataItems,
  deferredCopy,
  sourceLinks,
  sourceLinksAriaLabel,
}: ViewerDeferredSourceCardProps): JSX.Element {
  return (
    <article
      className="viewer-active-run-card viewer-deferred-source-card"
      aria-label={`${title} active run metadata summary`}
    >
      <span className="eyebrow">Active Viewer run</span>
      <h3>{title} sources</h3>
      <p className="subtitle">{subtitle}</p>
      {isLoadingMetadata ? (
        <p className="status viewer-status-message viewer-status-message--loading">Loading active run metadata…</p>
      ) : null}
      {hasMetadataError ? (
        <ViewerEmptyState>
          Some active run metadata is temporarily unavailable.
        </ViewerEmptyState>
      ) : null}
      <section aria-label={`${title} source metadata`}>
        <h3>Available source metadata</h3>
        {renderSourceMetadataList(metadataItems)}
        {!isLoadingMetadata && !hasMetadataError && !hasAnySourceMetadata ? (
          <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>
        ) : null}
      </section>
      <section aria-label={`${title} deferred output explanation`}>
        <h3>Deferred output</h3>
        <p className="status viewer-status-message">{deferredCopy}</p>
      </section>
      <section aria-label={sourceLinksAriaLabel}>
        <h3>Source links</h3>
        <ViewerActiveRunLinks links={sourceLinks} />
      </section>
    </article>
  )
}
