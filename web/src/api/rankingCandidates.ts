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
