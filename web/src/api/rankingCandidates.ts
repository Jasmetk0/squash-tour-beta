export type RankingDisciplinaryZero = {
  zero_id: string; run_id: string; branch_id: string; player_id: string; source_fingerprint: string
  effective_week: CandidateWeek; duration_weeks: number
}
export type CandidateWeek = { season_index: number; week: number }
export type RankingCandidateHistory = {
  run_id: string; branch_id: string; publication_status: 'candidate_only'
  candidates: {
    publication_status: 'candidate_only'; fingerprint: string; command_ids: string[]
    snapshot: {
      run_id: string; branch_id: string; week: CandidateWeek
      policy: { policy_id: string; best_n: number }
      rows: { rank: number; player_id: string; points: number; disciplinary_zeros?: RankingDisciplinaryZero[]; counted_results: {
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
  zero_history_status?: 'verified_stored_history' | 'caller_resolved' | 'legacy_without_manifest'
  zero_sources?: {
    fingerprint: string
    impact: 'superseded' | 'expired' | 'reserves_slot' | 'player_not_classified'
    version: { effective_week: CandidateWeek; previous_fingerprint: string | null; zero: RankingDisciplinaryZero }
  }[]
  tie_explanations?: {
    higher_player_id: string; lower_player_id: string; higher_rank: number; lower_rank: number; points: number
    reason: 'result_profile' | 'completion_age' | 'previous_position' | 'stored_token'
    result_slot: number | null; higher_value: number | string | null; lower_value: number | string | null
  }[]
  verification_status: 'complete_manifest' | 'legacy_without_manifest'
  manifest: null | {
    disciplinary_zeros?: RankingDisciplinaryZero[]
    zeros_from_history?: boolean
    players: { player_id: string; tie_break_token: string; tour_entry_week: CandidateWeek; retired: boolean }[]
    results: RankingCandidateSources['sources'][number]['version']['result'][]
  }
}
