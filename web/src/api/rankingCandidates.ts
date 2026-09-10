export type CandidateWeek = { season_index: number; week: number }
export type RankingCandidateHistory = {
  run_id: string; branch_id: string; publication_status: 'candidate_only'
  candidates: {
    publication_status: 'candidate_only'; fingerprint: string; command_ids: string[]
    snapshot: {
      run_id: string; branch_id: string; week: CandidateWeek
      policy: { policy_id: string; best_n: number }
      rows: { rank: number; player_id: string; points: number; counted_results: {
        edition_id: string; qualification_points: number; main_points: number
        completed_week: CandidateWeek; first_publication_week: CandidateWeek; validity_weeks: number
      }[] }[]
    }
  }[]
}

export type RankingCandidateSources = {
  run_id: string; branch_id: string; week: CandidateWeek
  candidate_fingerprint: string; publication_status: 'candidate_only'
  sources: { fingerprint: string; counted: boolean; version: {
    run_id: string; branch_id: string; effective_week: CandidateWeek; previous_fingerprint: string | null
    result: { edition_id: string; player_id: string; source_fingerprint: string; qualification_points: number; main_points: number; first_publication_week: CandidateWeek; validity_weeks: number; ranked: boolean }
  } }[]
}

export type RankingCandidateInputs = {
  run_id: string; branch_id: string; week: CandidateWeek
  candidate_fingerprint: string; publication_status: 'candidate_only'
  verification_status: 'complete_manifest' | 'legacy_without_manifest'
  manifest: null | {
    players: { player_id: string; tie_break_token: string; tour_entry_week: CandidateWeek; retired: boolean }[]
    results: RankingCandidateSources['sources'][number]['version']['result'][]
  }
}
