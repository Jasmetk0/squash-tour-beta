// The native signed-season APIs accept arbitrary nonnegative safe season indices,
// not the 50xW61 legacy RankingWeek calendar. Only actually returned completed
// seasons are selectable after the authoritative saved list GET succeeds.
const owned = ['signedRun', 'signedBranch', 'signedHead', 'signedSeason', 'compareSeason'] as const

export type SignedSeasonDeepLink =
  | { kind: 'none' }
  | { kind: 'invalid' }
  | { kind: 'selection'; savedHead: string; selected: number; comparison: number | null }

function nonnegativeIndex(value: string | null): number | null {
  if (value === null || !/^(0|[1-9][0-9]*)$/.test(value)) return null
  const number = Number(value)
  return Number.isSafeInteger(number) ? number : null
}

export function readSignedSeasonDeepLink(
  params: URLSearchParams, runId: string, branchId: string
): SignedSeasonDeepLink {
  if (!owned.some(key => params.has(key))) return { kind: 'none' }
  if (owned.some(key => params.getAll(key).length > 1) ||
      !runId.trim() || !branchId.trim() ||
      params.get('signedRun') !== runId ||
      params.get('signedBranch') !== branchId ||
      !params.get('signedHead')?.trim()) return { kind: 'invalid' }
  const selected = nonnegativeIndex(params.get('signedSeason'))
  const rawComparison = params.get('compareSeason')
  const comparison = rawComparison === null ? null : nonnegativeIndex(rawComparison)
  if (selected === null || (rawComparison !== null && comparison === null) ||
      (comparison !== null && comparison === selected)) return { kind: 'invalid' }
  return { kind: 'selection', savedHead: params.get('signedHead')!, selected, comparison }
}

export function writeSignedSeasonDeepLink(
  previous: URLSearchParams,
  runId: string, branchId: string, savedHead: string,
  selected: number, comparison: number | null
): URLSearchParams {
  const next = new URLSearchParams(previous)
  for (const key of owned) next.delete(key)
  next.set('signedRun', runId)
  next.set('signedBranch', branchId)
  next.set('signedHead', savedHead)
  next.set('signedSeason', String(selected))
  if (comparison !== null) next.set('compareSeason', String(comparison))
  return next
}
