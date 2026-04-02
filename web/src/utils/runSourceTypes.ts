import type { RunSourceSummary, RunSourceType, RunSourceTypeLike } from '../api/types'

const LEGACY_TO_CANONICAL_SOURCE_TYPE: Record<string, RunSourceType> = {
  new_run: 'fresh_seed',
  bootstrap: 'rollover_bootstrap',
  bootstrapped_rollover: 'rollover_bootstrap'
}

export function normalizeRunSourceType(sourceType: RunSourceTypeLike | null | undefined): RunSourceType | string | null {
  if (!sourceType) return null
  return LEGACY_TO_CANONICAL_SOURCE_TYPE[sourceType] ?? sourceType
}

export function classifyRunProvenance(source?: RunSourceSummary | null): 'fresh_seed' | 'rollover-derived' | 'bootstrap-derived' | 'unknown' {
  if (!source) return 'unknown'
  const sourceType = normalizeRunSourceType(source.source_type)
  if (sourceType === 'fresh_seed') return 'fresh_seed'
  if (source.source_rollover_run_id) return 'rollover-derived'
  if (source.parent_run_id) return 'bootstrap-derived'
  return 'unknown'
}

