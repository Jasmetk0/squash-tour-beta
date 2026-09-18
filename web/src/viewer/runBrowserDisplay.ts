import type { RunContainer } from '../api/types'
import { viewerCountriesPath, viewerFinalsPath, viewerHistoryPath, viewerPlayersPath, viewerRacePath, viewerRankingsPath, viewerSeasonCalendarPath, viewerTournamentsPath } from './viewerRoutes'

export type ViewerRunBrowserListItem = RunContainer | Record<string, unknown>
export type ViewerRunBrowserMetadataField = { label: string; value: string | number }
export type ViewerRunBrowserLink = { label: string; to: string }

const MISSING = '—'

export function hasSafeRunMetadataValue(
  value: unknown,
): value is string | number | boolean {
  if (typeof value === 'string') return Boolean(value.trim())
  return typeof value === 'number' || typeof value === 'boolean'
}

export function optionalRunField(
  run: ViewerRunBrowserListItem,
  key: string,
): unknown {
  return (run as Record<string, unknown>)[key]
}

function scalar(value: unknown): string | number {
  if (!hasSafeRunMetadataValue(value)) return MISSING
  return typeof value === 'number' ? value : String(value)
}

function timelineValue(run: ViewerRunBrowserListItem): string {
  const start = optionalRunField(run, 'timeline_start_season')
  const end = optionalRunField(run, 'timeline_end_season')
  if (typeof start !== 'number' || typeof end !== 'number') return MISSING
  return `${start}–${end}`
}

export function formatRunSourceLabel(
  run: ViewerRunBrowserListItem,
): string {
  return String(scalar(optionalRunField(run, 'source_type')))
}

export function normalizeRunBrowserRuns(runs: unknown): RunContainer[] {
  if (!Array.isArray(runs)) return []
  return runs
    .filter(
      (run): run is RunContainer =>
        typeof run === 'object' &&
        run !== null &&
        typeof (run as RunContainer).run_id === 'string' &&
        Boolean((run as RunContainer).run_id.trim()),
    )
    .map((run) => ({ ...run, run_id: run.run_id.trim() }))
}

export function buildRunBrowserMetadataItems(
  run: ViewerRunBrowserListItem,
): ViewerRunBrowserMetadataField[] {
  return [
    { label: 'Product Run ID', value: scalar(optionalRunField(run, 'run_id')) },
    { label: 'Status', value: scalar(optionalRunField(run, 'status')) },
    { label: 'Storage kind', value: scalar(optionalRunField(run, 'storage_kind')) },
    { label: 'Read-only', value: scalar(optionalRunField(run, 'read_only')) },
    { label: 'World ID', value: scalar(optionalRunField(run, 'world_id')) },
    { label: 'Timeline', value: timelineValue(run) },
    {
      label: 'Official Branch ID',
      value: scalar(optionalRunField(run, 'official_branch_id')),
    },
    {
      label: 'Mapped SimulationRuns',
      value: scalar(optionalRunField(run, 'mapped_simulation_run_count')),
    },
  ]
}

export function buildRunBrowserPrimaryLinks(
  productRunId: string,
): ViewerRunBrowserLink[] {
  return [
    { label: 'Season calendar', to: viewerSeasonCalendarPath(productRunId) },
    { label: 'Tournaments', to: viewerTournamentsPath(productRunId) },
    { label: 'Rankings', to: viewerRankingsPath(productRunId) },
    { label: 'Race', to: viewerRacePath(productRunId) },
  ]
}

export function buildRunBrowserContextLinks(
  productRunId: string,
): ViewerRunBrowserLink[] {
  return [
    { label: 'Players', to: viewerPlayersPath(productRunId) },
    { label: 'Countries', to: viewerCountriesPath(productRunId) },
    { label: 'History', to: viewerHistoryPath(productRunId) },
    { label: 'Finals', to: viewerFinalsPath(productRunId) },
  ]
}

export function buildViewerRunBrowserLinks(
  productRunId: string,
): ViewerRunBrowserLink[] {
  return [
    ...buildRunBrowserPrimaryLinks(productRunId),
    ...buildRunBrowserContextLinks(productRunId),
  ]
}

export function viewerRunMetadataFields(
  run: ViewerRunBrowserListItem,
): ViewerRunBrowserMetadataField[] {
  return buildRunBrowserMetadataItems(run)
}
