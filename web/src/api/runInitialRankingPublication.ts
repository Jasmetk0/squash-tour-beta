import type { RankingCandidateDetail } from './rankingCandidates'
import type { ViewerOfficialRanking } from './types'

export type InitialRankingPublication = {
  schema_version: 'initial_official_ranking_publication.v1'
  run_id: string
  branch_id: string
  week: { season_index: number; week: number }
  ranking_fingerprint: string
  exact_retry: boolean
}

const sha = (value: unknown): value is string =>
  typeof value === 'string' && /^[a-f0-9]{64}$/.test(value)

export function validWeekOnePublicationCandidate(
  candidate: RankingCandidateDetail | null | undefined,
  runId: string,
  branchId: string
): candidate is RankingCandidateDetail {
  return Boolean(candidate &&
    candidate.publication_status === 'candidate_only' &&
    sha(candidate.fingerprint) &&
    candidate.snapshot.run_id === runId &&
    candidate.snapshot.branch_id === branchId &&
    candidate.snapshot.week.season_index === 0 &&
    candidate.snapshot.week.week === 1 &&
    candidate.snapshot.policy.best_n >= 1 &&
    Array.isArray(candidate.snapshot.rows))
}

export function verifiedInitialRankingPublication(
  data: InitialRankingPublication,
  runId: string, branchId: string, fingerprint: string
): boolean {
  return data?.schema_version === 'initial_official_ranking_publication.v1' &&
    data.run_id === runId && data.branch_id === branchId &&
    data.week?.season_index === 0 && data.week.week === 1 &&
    sha(data.ranking_fingerprint) && data.ranking_fingerprint === fingerprint &&
    typeof data.exact_retry === 'boolean'
}

export function verifiedViewerInitialRanking(
  viewer: ViewerOfficialRanking | null | undefined,
  runId: string, viewerBranchId: string, fingerprint: string
): boolean {
  return Boolean(viewer && viewer.schema_version === 'viewer_official_ranking.v1' &&
    viewer.product_run_id === runId && viewer.viewer_branch_id === viewerBranchId &&
    viewer.season_index === 0 && viewer.week === 1 && viewer.week_ordinal === 0 &&
    viewer.snapshot_fingerprint === fingerprint &&
    viewer.row_count === viewer.rows.length)
}
