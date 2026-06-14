import type { ViewerHubLink } from './viewerHubLinks'
import { buildActiveRunHubLinks, viewerTopLevelHubLinks } from './viewerHubLinks'

export function normalizeViewerHomeActiveRunId(activeRunId: string | null | undefined): string | null {
  const normalizedRunId = activeRunId?.trim()
  return normalizedRunId ? normalizedRunId : null
}

export function buildViewerHomeActiveRunLinks(activeRunId: string | null | undefined): ViewerHubLink[] {
  const normalizedRunId = normalizeViewerHomeActiveRunId(activeRunId)
  if (!normalizedRunId) return []
  return buildActiveRunHubLinks(normalizedRunId)
}

export function buildViewerHomePrimaryHubLinks(): ViewerHubLink[] {
  return viewerTopLevelHubLinks
}

export function buildViewerHomeReadOnlyNotes(): string[] {
  return [
    'Viewer Home is read-only and links to existing Viewer surfaces only.',
    'Active-run shortcuts appear only when an active Viewer run is selected.',
    'Unavailable previews stay empty instead of inventing progress, results, table rows, or schedule facts.'
  ]
}

export function getViewerHomeActiveRunLabel(activeRunId: string | null | undefined): string {
  const normalizedRunId = normalizeViewerHomeActiveRunId(activeRunId)
  return normalizedRunId ? `Active Viewer run: ${normalizedRunId}` : 'No active Viewer run selected'
}
