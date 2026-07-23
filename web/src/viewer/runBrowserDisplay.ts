import type { RunContainer } from '../api/types'
import { viewerCountriesPath, viewerFinalsPath, viewerHistoryPath, viewerPlayersPath, viewerRacePath, viewerRankingsPath, viewerSeasonCalendarPath, viewerTournamentsPath } from './viewerRoutes'

export type ViewerRunBrowserListItem = RunContainer | Record<string, unknown>
export type ViewerRunBrowserMetadataField = { label: string; value: string | number }
export type ViewerRunBrowserLink = { label: string; to: string }
const MISSING = '—'
export function hasSafeRunMetadataValue(value: unknown): value is string | number | boolean { return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean' }
export function optionalRunField(run: ViewerRunBrowserListItem, key: string): unknown { return (run as Record<string, unknown>)[key] }
export function formatRunSourceLabel(run: ViewerRunBrowserListItem): string { return String(scalar(optionalRunField(run, 'source_type'))) }
function scalar(value: unknown): string | number { return typeof value === 'number' ? value : typeof value === 'string' || typeof value === 'boolean' ? String(value) : MISSING }
export function normalizeRunBrowserRuns(runs: unknown): RunContainer[] {
  if (!Array.isArray(runs)) return []
  return runs.filter((run): run is RunContainer => typeof run === 'object' && run !== null && typeof (run as RunContainer).run_id === 'string' && Boolean((run as RunContainer).run_id.trim()))
    .map((run) => ({ ...run, run_id: run.run_id.trim() }))
}
export function buildRunBrowserMetadataItems(run: ViewerRunBrowserListItem): ViewerRunBrowserMetadataField[] {
  const product = run as RunContainer
  return [
    { label: 'Product Run ID', value: product.run_id }, { label: 'Status', value: scalar(product.status) },
    { label: 'Storage kind', value: scalar(product.storage_kind) }, { label: 'Read-only', value: scalar(product.read_only) },
    { label: 'World ID', value: scalar(product.world_id) }, { label: 'Timeline', value: `${product.timeline_start_season}–${product.timeline_end_season}` },
    { label: 'Official Branch ID', value: scalar(product.official_branch_id) }, { label: 'Mapped SimulationRuns', value: scalar(product.mapped_simulation_run_count) }
  ]
}
export function buildRunBrowserPrimaryLinks(productRunId: string): ViewerRunBrowserLink[] { return [{ label: 'Season calendar', to: viewerSeasonCalendarPath(productRunId) }, { label: 'Tournaments', to: viewerTournamentsPath(productRunId) }, { label: 'Rankings', to: viewerRankingsPath(productRunId) }, { label: 'Race', to: viewerRacePath(productRunId) }] }
export function buildRunBrowserContextLinks(productRunId: string): ViewerRunBrowserLink[] { return [{ label: 'Players', to: viewerPlayersPath(productRunId) }, { label: 'Countries', to: viewerCountriesPath(productRunId) }, { label: 'History', to: viewerHistoryPath(productRunId) }, { label: 'Finals', to: viewerFinalsPath(productRunId) }] }
export function buildViewerRunBrowserLinks(productRunId: string): ViewerRunBrowserLink[] { return [...buildRunBrowserPrimaryLinks(productRunId), ...buildRunBrowserContextLinks(productRunId)] }

export function viewerRunMetadataFields(run: ViewerRunBrowserListItem): ViewerRunBrowserMetadataField[] { return buildRunBrowserMetadataItems(run) }
