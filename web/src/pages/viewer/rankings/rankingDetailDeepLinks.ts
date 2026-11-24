// This page exposes the legacy saved viewer_official_ranking.v1 publication
// (50 W61 seasons). A page/filter URL must match the exact Product Run,
// Saved Viewer Branch, published ordinal and publication fingerprint.
// Do not turn a URL for a replaced publication into a different result.
const ownedKeys = [
  'rankDetailRun', 'rankDetailBranch', 'rankDetailOrdinal',
  'rankDetailFingerprint', 'rankDetailPlayer', 'rankDetailPage',
] as const

export type RankingDetailDeepLink =
  | { kind: 'valid'; player: string; page: number }
  | { kind: 'invalid' }

export function readRankingDetailDeepLink(
  params: URLSearchParams,
  runId: string, branchId: string, ordinal: number, fingerprint: string | null,
): RankingDetailDeepLink {
  if (!ownedKeys.some(key => params.has(key))) return { kind: 'valid', player: '', page: 1 }
  if (
    ownedKeys.some(key => params.getAll(key).length > 1) ||
    !runId.trim() || !branchId.trim() ||
    fingerprint === null ||
    params.get('rankDetailRun') !== runId ||
    params.get('rankDetailBranch') !== branchId ||
    params.get('rankDetailOrdinal') !== String(ordinal) ||
    params.get('rankDetailFingerprint') !== fingerprint
  ) return { kind: 'invalid' }

  const player = params.get('rankDetailPlayer') ?? ''
  const rawPage = params.get('rankDetailPage')
  const page = rawPage === null ? 1 : Number(rawPage)
  if (player.length > 256 ||
    (rawPage !== null && !/^[1-9][0-9]*$/.test(rawPage)) ||
    !Number.isSafeInteger(page) || page < 1) return { kind: 'invalid' }

  return { kind: 'valid', player, page }
}

export function clearRankingDetailDeepLink(previous: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(previous)
  for (const key of ownedKeys) next.delete(key)
  return next
}

export function writeRankingDetailDeepLink(
  previous: URLSearchParams,
  runId: string, branchId: string, ordinal: number, fingerprint: string,
  player: string, page: number,
): URLSearchParams {
  const next = clearRankingDetailDeepLink(previous)
  next.set('rankDetailRun', runId)
  next.set('rankDetailBranch', branchId)
  next.set('rankDetailOrdinal', String(ordinal))
  next.set('rankDetailFingerprint', fingerprint)
  if (player) next.set('rankDetailPlayer', player)
  if (page > 1) next.set('rankDetailPage', String(page))
  return next
}
