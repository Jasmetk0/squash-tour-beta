import type { RunsIndexResponse } from '../api/types'
import { viewerCountriesPath, viewerFinalsPath, viewerHistoryPath, viewerPlayersPath, viewerRacePath, viewerRankingsPath, viewerSeasonCalendarPath, viewerTournamentsPath } from './viewerRoutes'

export type ViewerRunBrowserListItem = RunsIndexResponse['runs'][number] & Record<string, unknown>

export type ViewerRunBrowserMetadataField = {
  label: string
  value: string | number
}

export type ViewerRunBrowserLink = {
  label: string
  to: string
}

const MISSING_RUN_METADATA_VALUE = '—'

function isSafePrimitiveRunMetadataValue(value: unknown): value is string | number | boolean {
  if (value === null || value === undefined || value === '') return false
  return typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
}

export function hasSafeRunMetadataValue(value: unknown): boolean {
  return isSafePrimitiveRunMetadataValue(value)
}

export function optionalRunField(run: ViewerRunBrowserListItem, key: string): unknown {
  return run[key]
}

function toRunMetadataValue(value: unknown, fallback = MISSING_RUN_METADATA_VALUE): string | number {
  if (!isSafePrimitiveRunMetadataValue(value)) return fallback
  return typeof value === 'number' ? value : String(value)
}

function runMetadataField(label: string, value: unknown): ViewerRunBrowserMetadataField {
  return { label, value: toRunMetadataValue(value) }
}

export function formatRunSourceLabel(run: ViewerRunBrowserListItem): string {
  return String(toRunMetadataValue(optionalRunField(run, 'source_type')))
}

export function buildRunBrowserMetadataItems(run: ViewerRunBrowserListItem): ViewerRunBrowserMetadataField[] {
  const progress = run.progress
  const parentRunId = optionalRunField(run, 'parent_run_id')
  const sourceType = optionalRunField(run, 'source_type')
  const childRunCount = optionalRunField(run, 'child_run_count')

  return [
    runMetadataField('Run id', run.run_id),
    runMetadataField('Season', run.season),
    runMetadataField('Seed', run.seed),
    runMetadataField('Source', sourceType),
    runMetadataField('Parent run', parentRunId),
    runMetadataField('Child runs', childRunCount),
    runMetadataField('Next event index', progress?.next_event_index),
    runMetadataField('Total events', progress?.total_events),
    runMetadataField('Completed event count', progress?.completed_event_count)
  ]
}

export function viewerRunMetadataFields(run: ViewerRunBrowserListItem): ViewerRunBrowserMetadataField[] {
  return buildRunBrowserMetadataItems(run)
}

export function buildRunBrowserPrimaryLinks(runId: string): ViewerRunBrowserLink[] {
  return [
    { label: 'Season calendar', to: viewerSeasonCalendarPath(runId) },
    { label: 'Tournaments', to: viewerTournamentsPath(runId) },
    { label: 'Rankings', to: viewerRankingsPath(runId) },
    { label: 'Race', to: viewerRacePath(runId) }
  ]
}

export function buildRunBrowserContextLinks(runId: string): ViewerRunBrowserLink[] {
  return [
    { label: 'Players', to: viewerPlayersPath(runId) },
    { label: 'Countries', to: viewerCountriesPath(runId) },
    { label: 'History', to: viewerHistoryPath(runId) },
    { label: 'Finals', to: viewerFinalsPath(runId) }
  ]
}

export function buildViewerRunBrowserLinks(runId: string): ViewerRunBrowserLink[] {
  return [...buildRunBrowserPrimaryLinks(runId), ...buildRunBrowserContextLinks(runId)]
}
