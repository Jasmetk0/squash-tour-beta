import type { ViewerSignedRecordsFilters } from '../../../api/viewerSignedTourRecords'

// Never reuse a filter link for a newer Save (or a different Product Run/Branch).
// Only the completed-season inventory from the baseline authenticated GET decides
// if the numeric season indices exist. No legacy W61 calendar assumptions.
const owned = [
  'recordsRun', 'recordsBranch', 'recordsHead', 'recordsFingerprint',
  'recordsAsOf', 'recordsFrom', 'recordsCountry'
] as const

export type SignedRecordsDeepLink =
  | { kind: 'none' }
  | { kind: 'invalid' }
  | { kind: 'selection'; filters: ViewerSignedRecordsFilters }

function parseIndex(raw: string | null): number | null {
  if (raw === null || !/^(0|[1-9][0-9]*)$/.test(raw)) return null
  const value = Number(raw)
  return Number.isSafeInteger(value) ? value : null
}

export function readSignedRecordsDeepLink(
  params: URLSearchParams,
  runId: string, branchId: string,
  savedHead: string | null, fingerprint: string | null
): SignedRecordsDeepLink {
  if (!owned.some(key => params.has(key))) return { kind: 'none' }
  if (owned.some(key => params.getAll(key).length > 1) ||
      !savedHead || !fingerprint || !runId.trim() || !branchId.trim() ||
      params.get('recordsRun') !== runId ||
      params.get('recordsBranch') !== branchId ||
      params.get('recordsHead') !== savedHead ||
      params.get('recordsFingerprint') !== fingerprint) return { kind: 'invalid' }

  const asOfSeason = parseIndex(params.get('recordsAsOf'))
  const fromSeason = parseIndex(params.get('recordsFrom'))
  const countryCode = params.get('recordsCountry')
  if (asOfSeason === null || fromSeason === null || fromSeason > asOfSeason ||
      (countryCode !== null && !/^[A-Z]{3}$/.test(countryCode))) return { kind: 'invalid' }

  return { kind: 'selection', filters: {
    asOfSeason, fromSeason, countryCode
  } }
}

export function clearSignedRecordsDeepLink(previous: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(previous)
  for (const key of owned) next.delete(key)
  return next
}

export function writeSignedRecordsDeepLink(
  previous: URLSearchParams, runId: string, branchId: string,
  savedHead: string, fingerprint: string,
  filters: ViewerSignedRecordsFilters
): URLSearchParams {
  const next = clearSignedRecordsDeepLink(previous)
  next.set('recordsRun', runId)
  next.set('recordsBranch', branchId)
  next.set('recordsHead', savedHead)
  next.set('recordsFingerprint', fingerprint)
  next.set('recordsAsOf', String(filters.asOfSeason))
  next.set('recordsFrom', String(filters.fromSeason))
  if (filters.countryCode !== null) next.set('recordsCountry', filters.countryCode)
  return next
}
