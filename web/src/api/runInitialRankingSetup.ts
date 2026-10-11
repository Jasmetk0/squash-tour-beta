import type { RankingCandidateDetail, RankingPreparationPreview } from './rankingCandidates'

export type DerivedInitialRankingIntent = {
  command_id: string
  audit: { actor_label: string; reason: string }
}

export function verifyDerivedInitialCandidate(
  runId: string, branchId: string, commandId: string, bestN: number,
  candidate: RankingCandidateDetail
): boolean {
  return candidate?.publication_status === 'candidate_only' &&
    /^[0-9a-f]{64}$/.test(candidate.fingerprint) &&
    candidate.command_ids?.includes(commandId) === true &&
    candidate.snapshot?.run_id === runId &&
    candidate.snapshot?.branch_id === branchId &&
    candidate.snapshot.week?.season_index === 0 &&
    candidate.snapshot.week?.week === 1 &&
    candidate.snapshot.policy?.best_n === bestN &&
    Array.isArray(candidate.snapshot.rows)
}

export function verifyDerivedInitialPreview(
  runId: string, branchId: string, intent: DerivedInitialRankingIntent,
  bestN: number, preview: RankingPreparationPreview
): boolean {
  return preview?.preview_only === true &&
    /^[0-9a-f]{64}$/.test(preview.request_fingerprint) &&
    verifyDerivedInitialCandidate(runId, branchId, intent.command_id, bestN, preview.candidate)
}

export function initialRankingCandidate(
  candidates: RankingCandidateDetail[]
): RankingCandidateDetail | null {
  return candidates.find(item => item.snapshot.week.season_index === 0 && item.snapshot.week.week === 1) ?? null
}
