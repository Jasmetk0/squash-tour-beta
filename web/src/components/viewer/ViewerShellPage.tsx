import type { ReactNode } from 'react'

import { useViewerContext } from '../../viewer/ViewerContext'
import { ViewerEmptyState, ViewerStatusMessage } from './ViewerLandingComponents'

export type ViewerShellPageProps = {
  title: string
  kicker?: string
  description?: string
  children?: ReactNode
}

function ViewerContextLine(): JSX.Element {
  const context = useViewerContext()
  return (
    <ViewerStatusMessage>
      Viewer context: Season {context.selectedSeason} · W{context.selectedWeek}. This section is ready for read-only tour data once the Viewer read model is connected.
    </ViewerStatusMessage>
  )
}

export function ViewerShellPage({ title, kicker = 'Read-only Viewer section', description, children }: ViewerShellPageProps): JSX.Element {
  return (
    <section className="panel viewer-shell-page">
      <div className="page-intro">
        <span className="eyebrow">{kicker}</span>
        <h2>{title}</h2>
        <p className="subtitle">
          {description ?? 'This Viewer section is ready for read-only data. Future tour information will appear here once the read model is connected.'}
        </p>
      </div>
      <ViewerContextLine />
      {children ?? <ViewerEmptyState>No data is available for this run yet.</ViewerEmptyState>}
    </section>
  )
}
