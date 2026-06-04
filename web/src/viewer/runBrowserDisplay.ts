import type { RunsIndexResponse } from '../api/types'
import { buildViewerActiveRunQuickLinks, type ViewerActiveRunQuickLink } from './activeRunDisplay'

export type ViewerRunBrowserListItem = RunsIndexResponse['runs'][number] & Record<string, unknown>

export type ViewerRunBrowserMetadataField = {
  label: string
  value: string | number
}

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

function toRunMetadataValue(value: unknown): string | number | null {
  if (!isSafePrimitiveRunMetadataValue(value)) return null
  return typeof value === 'number' ? value : String(value)
}

function addRunMetadataField(fields: ViewerRunBrowserMetadataField[], label: string, value: unknown): void {
  const safeValue = toRunMetadataValue(value)
  if (safeValue !== null) fields.push({ label, value: safeValue })
}

export function viewerRunMetadataFields(run: ViewerRunBrowserListItem): ViewerRunBrowserMetadataField[] {
  const fields: ViewerRunBrowserMetadataField[] = []
  const progress = run.progress
  const parentRunId = optionalRunField(run, 'parent_run_id')
  const sourceType = optionalRunField(run, 'source_type')
  const createdAt = optionalRunField(run, 'created_at') ?? optionalRunField(run, 'created')
  const updatedAt = optionalRunField(run, 'updated_at') ?? optionalRunField(run, 'updated')

  addRunMetadataField(fields, 'Run id', run.run_id)
  addRunMetadataField(fields, 'Season', run.season)
  addRunMetadataField(fields, 'Seed', run.seed)
  addRunMetadataField(fields, 'Next event index', progress?.next_event_index)
  addRunMetadataField(fields, 'Total events', progress?.total_events)
  addRunMetadataField(fields, 'Completed event count', progress?.completed_event_count)
  addRunMetadataField(fields, 'Source', sourceType)
  addRunMetadataField(fields, 'Parent run', parentRunId)
  addRunMetadataField(fields, 'Created', createdAt)
  addRunMetadataField(fields, 'Updated', updatedAt)

  return fields
}

export function buildViewerRunBrowserLinks(runId: string): ViewerActiveRunQuickLink[] {
  return buildViewerActiveRunQuickLinks(runId)
}
