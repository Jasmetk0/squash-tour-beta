export type NativeTournamentClosedPlayer = {
  player_id: string; reached_stage: 'quarterfinal' | 'semifinal' | 'finalist' | 'champion'
  played_match_ids: string[]; wins: number; losses: number; prepared_points: number
}
export type NativeTournamentClosureSummary = {
  command_id: string; tournament_id: string; fingerprint: string
  champion_player_id: string; finalist_player_id: string
  source_tournament_fingerprint: string; saved: boolean
  scope: 'played_native_result_closed_not_official'
  players: NativeTournamentClosedPlayer[]
}
export type NativeTournamentClosureCommand = {
  command_id: string; tournament_id: string
  expected_saved_head: string; expected_checkpoint_fingerprint: string
  operator_label: string; audit_reason: string; explicit_result_confirmation: true
}
export type NativeTournamentClosureReceipt = {
  schema_version: 'calendar_native_tournament_closure_receipt.v1'
  closure: NativeTournamentClosureSummary & {
    source_saved_head: string; source_checkpoint_fingerprint: string
    source_week_event_count: number; source_prepared_awards_fingerprint: string
    request_fingerprint: string
  }
  fingerprint: string; checkpoint_fingerprint: string
  official_ranking_published: false
  publication_status: 'native_result_closed_not_official'
}

export type ContinuationView = {
  schema_version: 'calendar_continuation_inspection.v1'; run_id: string; branch_id: string
  saved_head_revision_id: string; draft_version: number; checkpoint_fingerprint: string | null
  player_ids: string[]; saved: boolean; can_play: boolean; limited_player_ids: string[]
  sporting_week?: { calendar: { weeks_per_year: number; season_start_year_week: number; start_year: number; season_count: number }; season_index: number; week: number } | null
  tournaments?: { tournament_id: string; command_id: string; fingerprint: string; week: number
    entrant_ids: string[]; entrant_count?: number; match_count?: number
    winner_player_id: string; match_ids: string[]; saved: boolean
    result_closed?: boolean; result_closure_saved?: boolean
    scope: 'sporting_exhibition_knockout_not_official'
    prepared_points_status?: 'not_prepared' | 'prepared_not_official'
    prepared_policy?: FollowupPointPolicy | FollowupEightPointPolicy | null
    prepared_awards?: FollowupPreparedAward[]
  }[]
  closures?: NativeTournamentClosureSummary[]
  weekly_advance_count?: number
  weekly_advances?: { command_id: string; fingerprint: string; completed_week: number; target_week: number; saved: boolean }[]
  health_numeric_effect_applied: false
  matches: { match_id: string; sequence: number; fingerprint: string; player_ids: [string, string]
    winner_player_id: string; rally_count: number; saved: boolean }[]
}
export type ContinuationCommand = {
  command_id: string; match_id: string; expected_saved_head: string; expected_checkpoint_fingerprint: string
  player_a_id: string; player_b_id: string; seed: number; operator_label: string; audit_reason: string
}
export type ContinuationReceipt = {
  fingerprint: string; checkpoint_fingerprint: string
  match: { match_id: string; sequence: number; source_saved_head: string; source_checkpoint_fingerprint: string
    result: { winner_player_id: string }; input_context: { player_a: { player: { player_id: string } }; player_b: { player: { player_id: string } } }
    canonical_projections: { player_id: string; current_form: number; match_sharpness: number; long_term_fatigue: number }[] }
}
export function verifyContinuation(v: ContinuationView, run: string, branch: string, head: string) {
  const hash = (s: unknown) => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s)
  if (!v || v.schema_version !== 'calendar_continuation_inspection.v1' || v.run_id !== run || v.branch_id !== branch
    || v.saved_head_revision_id !== head || !Number.isSafeInteger(v.draft_version) || v.draft_version < 0
    || !Array.isArray(v.player_ids) || new Set(v.player_ids).size !== v.player_ids.length
    || typeof v.saved !== 'boolean' || typeof v.can_play !== 'boolean' || (v.can_play && !v.saved)
    || (v.checkpoint_fingerprint !== null && !hash(v.checkpoint_fingerprint))
    || ((v.saved || v.can_play) && !v.checkpoint_fingerprint)
    || v.health_numeric_effect_applied !== false || !Array.isArray(v.limited_player_ids)
    || v.limited_player_ids.some(p => !v.player_ids.includes(p)) || !Array.isArray(v.matches)
    || new Set(v.matches.map(m => m.match_id)).size !== v.matches.length
    || v.matches.some((m, i) => m.sequence !== i + 1 || !hash(m.fingerprint)
      || m.player_ids.length !== 2 || new Set(m.player_ids).size !== 2
      || m.player_ids.some(p => !v.player_ids.includes(p)) || !m.player_ids.includes(m.winner_player_id)
      || !Number.isSafeInteger(m.rally_count) || m.rally_count < 1 || typeof m.saved !== 'boolean'
      || (v.saved && !m.saved))) throw Error('Continuation source/history changed')
  if (v.tournaments && (!Array.isArray(v.tournaments) || v.tournaments.some(t =>
    !hash(t.fingerprint) || t.scope !== 'sporting_exhibition_knockout_not_official'
    || ![4, 8].includes(t.entrant_ids.length)
    || new Set(t.entrant_ids).size !== t.entrant_ids.length
    || (t.entrant_count !== undefined && t.entrant_count !== t.entrant_ids.length)
    || (t.match_count !== undefined && t.match_count !== t.match_ids.length)
    || t.entrant_ids.some(p => !v.player_ids.includes(p))
    || t.match_ids.length !== t.entrant_ids.length - 1
    || t.match_ids.some(id => !v.matches.some(m => m.match_id === id))
    || !t.entrant_ids.includes(t.winner_player_id) || typeof t.saved !== 'boolean'
    || (v.saved && !t.saved)
  ))) throw Error('Later knockout source/history changed')
  if (v.tournaments?.some(t => {
    const prepared = t.prepared_points_status === 'prepared_not_official'
    if (!prepared) return !!t.prepared_policy || !!t.prepared_awards?.length
    const policy = t.prepared_policy, awards = t.prepared_awards
    const eight = t.entrant_ids.length === 8
    const qfPoints = 'quarterfinal' in (policy ?? {}) ? (policy as FollowupEightPointPolicy).quarterfinal : undefined
    const pointValues: Record<string, number> = policy
      ? {champion: policy.champion, finalist: policy.finalist,
         semifinal: policy.semifinal, ...(eight ? {quarterfinal: qfPoints ?? -1} : {})}
      : {}
    if (!policy || !awards || awards.length !== t.entrant_ids.length
      || (policy.schema_version !== undefined
        && policy.schema_version !== (eight ? 'calendar_followup_point_policy.v2' : 'calendar_followup_point_policy.v1'))
      || !Number.isSafeInteger(policy.validity_weeks) || policy.validity_weeks !== v.sporting_week?.calendar.weeks_per_year
      || !Number.isSafeInteger(policy.champion) || !Number.isSafeInteger(policy.finalist) || !Number.isSafeInteger(policy.semifinal)
      || policy.champion <= (eight ? (qfPoints ?? -1) : policy.semifinal)
      || policy.champion < policy.finalist || policy.finalist < policy.semifinal
      || (eight && (!Number.isSafeInteger(qfPoints) || qfPoints! < 0 || policy.semifinal < qfPoints!))
      || new Set(awards.map(a => a.player_id)).size !== t.entrant_ids.length
      || awards.some(a => !t.entrant_ids.includes(a.player_id) || !hash(a.source_policy_fingerprint)
        || !hash(a.source_tournament_fingerprint) || !(a.reached_stage in pointValues)
        || a.main_points !== pointValues[a.reached_stage])
      || awards.filter(a => a.reached_stage === 'champion').length !== 1
      || awards.filter(a => a.reached_stage === 'finalist').length !== 1
      || awards.filter(a => a.reached_stage === 'semifinal').length !== 2
      || awards.filter(a => a.reached_stage === 'quarterfinal').length !== (eight ? 4 : 0)
      || awards.find(a => a.reached_stage === 'champion')?.player_id !== t.winner_player_id
    ) return true
    return new Set(awards.map(a => a.source_tournament_fingerprint)).size !== 1
      || new Set(awards.map(a => a.source_policy_fingerprint)).size !== 1
  })) throw Error('Prepared knockout award history changed')
  const closures = v.closures ?? []
  if (!Array.isArray(closures)
    || new Set(closures.map(c => c.tournament_id)).size !== closures.length
    || new Set(closures.map(c => c.command_id)).size !== closures.length
    || closures.some(c => {
      const event = v.tournaments?.find(t => t.tournament_id === c.tournament_id)
      if (!event || event.entrant_ids.length !== 8 || event.match_ids.length !== 7
        || event.prepared_points_status !== 'prepared_not_official'
        || event.scope !== 'sporting_exhibition_knockout_not_official'
        || !hash(c.fingerprint) || c.source_tournament_fingerprint !== event.fingerprint
        || c.scope !== 'played_native_result_closed_not_official'
        || c.champion_player_id !== event.winner_player_id
        || (v.saved && !c.saved) || c.players.length !== 8) return true
      const results = event.match_ids.map(id => v.matches.find(m => m.match_id === id))
      if (results.some(m => !m)) return true
      const counters = new Map(event.entrant_ids.map(id => [id, {wins: 0, losses: 0, ids: [] as string[]}]))
      const rounds: Record<string, string> = {}
      results.forEach((m, i) => {
        if (!m) return
        const loser = m.player_ids.find(id => id !== m.winner_player_id)!
        counters.get(m.winner_player_id)?.ids.push(m.match_id)
        counters.get(loser)?.ids.push(m.match_id)
        counters.get(m.winner_player_id)!.wins++
        counters.get(loser)!.losses++
        rounds[loser] = i < 4 ? 'quarterfinal' : i < 6 ? 'semifinal' : 'finalist'
      })
      rounds[event.winner_player_id] = 'champion'
      const awarded = new Map(event.prepared_awards?.map(a => [a.player_id, a]) ?? [])
      const finishers = c.players.map(p => p.player_id)
      return finishers.join('|') !== [...finishers].sort().join('|')
        || new Set(finishers).size !== 8
        || c.players.some(p => {
          const counts = counters.get(p.player_id), a = awarded.get(p.player_id)
          return !counts || !a || p.reached_stage !== rounds[p.player_id]
            || p.reached_stage !== a.reached_stage || p.prepared_points !== a.main_points
            || p.wins !== counts.wins || p.losses !== counts.losses
            || p.played_match_ids.join('|') !== counts.ids.join('|')
        })
        || c.finalist_player_id !== results[6]!.player_ids.find(id => id !== results[6]!.winner_player_id)
    })
    || v.tournaments?.some(t => !!t.result_closed !== closures.some(c => c.tournament_id === t.tournament_id))
  ) throw Error('Native tournament closed-result history changed')
  if (v.sporting_week) {
    const w = v.sporting_week
    if (!Number.isSafeInteger(w.week) || w.week < 1 || w.week > w.calendar.weeks_per_year
      || w.season_index !== 0 || !Number.isSafeInteger(v.weekly_advance_count) || v.weekly_advance_count! < 0
      || !Array.isArray(v.weekly_advances) || v.weekly_advances.length !== v.weekly_advance_count
      || v.weekly_advances.length !== w.week - 1
      || v.weekly_advances.some((a, i) => !hash(a.fingerprint) || a.completed_week !== i + 1 || a.target_week !== i + 2
        || typeof a.saved !== 'boolean' || (v.saved && !a.saved))) throw Error('Sporting week source/history changed')
  }
  return v
}

export type SportingWeekCommand = { command_id: string; expected_saved_head: string; expected_checkpoint_fingerprint: string
  seed: number; operator_label: string; audit_reason: string }
export type SportingWeekPreview = { schema_version: 'calendar_sporting_week_preview.v1'; preview_fingerprint: string
  advance_fingerprint: string; checkpoint_fingerprint: string; player_count: number; changed_player_count: number; attribute_change_count: number
  changes: { player_id: string; changed_attributes: number; form_before: number; form_after: number; sharpness_before: number; sharpness_after: number; fatigue_before: number; fatigue_after: number }[]
  advance: { run_id: string; branch_id: string; command_id: string; source_saved_head: string; source_checkpoint_fingerprint: string
    completed_week: NonNullable<ContinuationView['sporting_week']>; target_week: NonNullable<ContinuationView['sporting_week']>
    policy: { policy_id: string }; scope: 'sporting_only_exhibition_timeline' } }
export function verifySportingWeek(v: SportingWeekPreview, command: SportingWeekCommand, source: ContinuationView) {
  const a = v?.advance, w = source.sporting_week
  const hash = (s: unknown) => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s)
  if (!v || v.schema_version !== 'calendar_sporting_week_preview.v1' || !a || !w
    || !hash(v.preview_fingerprint) || !hash(v.advance_fingerprint) || !hash(v.checkpoint_fingerprint)
    || a.run_id !== source.run_id || a.branch_id !== source.branch_id || a.command_id !== command.command_id
    || a.source_saved_head !== source.saved_head_revision_id || a.source_checkpoint_fingerprint !== source.checkpoint_fingerprint
    || a.scope !== 'sporting_only_exhibition_timeline' || a.policy.policy_id !== 'calendar-annual-development.provisional.v1'
    || a.completed_week.week !== w.week || a.target_week.week !== w.week + 1
    || a.completed_week.season_index !== w.season_index || a.target_week.season_index !== w.season_index
    || Object.entries(w.calendar).some(([k, n]) => a.completed_week.calendar[k as keyof typeof w.calendar] !== n || a.target_week.calendar[k as keyof typeof w.calendar] !== n)
    || !Number.isSafeInteger(v.changed_player_count) || v.changed_player_count < 0 || v.changed_player_count > source.player_ids.length
    || v.player_count !== source.player_ids.length || !Array.isArray(v.changes) || v.changes.length !== v.changed_player_count
    || new Set(v.changes.map(c => c.player_id)).size !== v.changes.length || v.changes.some(c => !source.player_ids.includes(c.player_id))
    || !Number.isSafeInteger(v.attribute_change_count) || v.attribute_change_count < 0) throw Error('Weekly preview source changed')
  return v
}

export type FollowupPointPolicy = {
  schema_version?: 'calendar_followup_point_policy.v1'
  source_kind?: 'admin_explicit_reviewed'
  category_label: string; champion: number; finalist: number; semifinal: number; validity_weeks: number
}
export type FollowupEightPointPolicy = {
  schema_version?: 'calendar_followup_point_policy.v2'
  source_kind?: 'admin_explicit_reviewed'
  category_label: string
  champion: number; finalist: number; semifinal: number; quarterfinal: number; validity_weeks: number
}
export type FollowupPreparedAward = {
  player_id: string; reached_stage: 'champion' | 'finalist' | 'semifinal' | 'quarterfinal'
  main_points: number; source_tournament_fingerprint: string; source_policy_fingerprint: string
}
export type FollowupKnockoutCommand = {
  command_id: string; tournament_id: string; expected_saved_head: string
  expected_checkpoint_fingerprint: string; entrant_ids: [string, string, string, string]
  seed: number; operator_label: string; audit_reason: string
}
export type FollowupScoredCommand = FollowupKnockoutCommand & {
  point_policy: FollowupPointPolicy; explicit_point_confirmation: true
}
export type FollowupKnockoutReceipt = {
  schema_version: 'calendar_followup_knockout_receipt.v1'; fingerprint: string
  checkpoint_fingerprint: string; winner_player_id: string; official_ranking_published: false
  scope: 'sporting_exhibition_knockout_not_official'
  publication_status?: 'prepared_not_official'
  prepared_awards?: FollowupPreparedAward[]
  prepared_policy_fingerprint?: string
  tournament: {
    schema_version?: 'calendar_followup_knockout.v1' | 'calendar_followup_knockout.v2' | 'calendar_followup_knockout.v3' | 'calendar_followup_knockout.v4'
    run_id: string; branch_id: string; command_id: string; tournament_id: string
    source_saved_head: string; source_checkpoint_fingerprint: string
    entrant_ids: string[]; matches: { match_id: string; sequence: number; fingerprint?: string
      result: { winner_player_id: string; player_a_id: string; player_b_id: string } }[]
  }
}
export function verifyFollowupKnockout(
  receipt: FollowupKnockoutReceipt, command: FollowupKnockoutCommand | FollowupScoredCommand, view: ContinuationView,
): FollowupKnockoutReceipt {
  const e = receipt?.tournament
  const fingerprint = (s: unknown) => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s)
  const matchIds = ['sf1', 'sf2', 'final'].map(s => command.tournament_id + ':' + s)
  if (!receipt || !e || receipt.schema_version !== 'calendar_followup_knockout_receipt.v1'
    || receipt.scope !== 'sporting_exhibition_knockout_not_official'
    || receipt.official_ranking_published !== false || !fingerprint(receipt.fingerprint)
    || !fingerprint(receipt.checkpoint_fingerprint) || e.run_id !== view.run_id
    || e.branch_id !== view.branch_id || e.source_saved_head !== view.saved_head_revision_id
    || e.source_checkpoint_fingerprint !== view.checkpoint_fingerprint
    || e.command_id !== command.command_id || e.tournament_id !== command.tournament_id
    || e.entrant_ids.length !== 4 || e.entrant_ids.some((p, i) => p !== command.entrant_ids[i])
    || !Array.isArray(e.matches) || e.matches.length !== 3
    || e.matches.some((m, i) => m.match_id !== matchIds[i] || m.sequence !== view.matches.length + i + 1)
    || e.matches[0].result.player_a_id !== command.entrant_ids[0]
    || e.matches[0].result.player_b_id !== command.entrant_ids[1]
    || e.matches[1].result.player_a_id !== command.entrant_ids[2]
    || e.matches[1].result.player_b_id !== command.entrant_ids[3]
    || e.matches[2].result.player_a_id !== e.matches[0].result.winner_player_id
    || e.matches[2].result.player_b_id !== e.matches[1].result.winner_player_id
    || receipt.winner_player_id !== e.matches[2].result.winner_player_id
  ) throw Error('Later knockout result differs from frozen Saved source or semifinal winners')
  if ('point_policy' in command) {
    const awards = receipt.prepared_awards
    const values = command.point_policy
    if (receipt.publication_status !== 'prepared_not_official'
      || !fingerprint(receipt.prepared_policy_fingerprint)
      || !Array.isArray(awards) || awards.length !== 4
      || awards.some(a => !fingerprint(a.source_tournament_fingerprint)
        || a.source_policy_fingerprint !== receipt.prepared_policy_fingerprint
        || !command.entrant_ids.includes(a.player_id)
        || a.reached_stage === 'quarterfinal'
        || a.main_points !== values[a.reached_stage as 'champion' | 'finalist' | 'semifinal'])
      || new Set(awards.map(a => a.player_id)).size !== 4
      || awards.filter(a => a.reached_stage === 'champion').length !== 1
      || awards.filter(a => a.reached_stage === 'finalist').length !== 1
      || awards.filter(a => a.reached_stage === 'semifinal').length !== 2
      || awards.find(a => a.reached_stage === 'champion')?.player_id !== receipt.winner_player_id
    ) throw Error('Prepared points disagree with the actual played knockout')
  } else if (receipt.prepared_awards?.length || receipt.publication_status) {
    throw Error('Unscored knockout cannot gain prepared awards')
  }
  return receipt
}

export type FollowupEightCommand = Omit<FollowupKnockoutCommand, 'entrant_ids'> & {
  entrant_ids: [string, string, string, string, string, string, string, string]
}
export type FollowupEightScoredCommand = FollowupEightCommand & {
  point_policy: FollowupEightPointPolicy; explicit_point_confirmation: true
}

/** Historical 4-player results use the separate v1/v2 verifier above. */
export function verifyEightFollowupKnockout(
  receipt: FollowupKnockoutReceipt, command: FollowupEightCommand | FollowupEightScoredCommand, view: ContinuationView,
): FollowupKnockoutReceipt {
  const e = receipt?.tournament, hash = (x: unknown) => typeof x === 'string' && /^[0-9a-f]{64}$/.test(x)
  const names = ['qf1', 'qf2', 'qf3', 'qf4', 'sf1', 'sf2', 'final']
  const scored = 'point_policy' in command
  if (!receipt || !e || receipt.schema_version !== 'calendar_followup_knockout_receipt.v1'
    || e.schema_version !== (scored ? 'calendar_followup_knockout.v4' : 'calendar_followup_knockout.v3')
    || receipt.official_ranking_published !== false
    || receipt.scope !== 'sporting_exhibition_knockout_not_official'
    || (!scored && (!!receipt.publication_status || !!receipt.prepared_awards?.length))
    || !hash(receipt.fingerprint) || !hash(receipt.checkpoint_fingerprint)
    || e.run_id !== view.run_id || e.branch_id !== view.branch_id
    || e.source_saved_head !== view.saved_head_revision_id
    || e.source_checkpoint_fingerprint !== view.checkpoint_fingerprint
    || e.tournament_id !== command.tournament_id || e.command_id !== command.command_id
    || e.entrant_ids.length !== 8 || new Set(e.entrant_ids).size !== 8
    || e.entrant_ids.some((p, i) => p !== command.entrant_ids[i])
    || !Array.isArray(e.matches) || e.matches.length !== 7
    || e.matches.some((m, i) => m.match_id !== command.tournament_id + ':' + names[i]
      || m.sequence !== view.matches.length + i + 1)
  ) throw Error('Eight-player tournament source changed')
  const pairs = e.matches.map(m => [m.result.player_a_id, m.result.player_b_id])
  const winners = e.matches.map(m => m.result.winner_player_id)
  for (let i=0; i<4; i++) {
    if (pairs[i][0] !== command.entrant_ids[2*i] || pairs[i][1] !== command.entrant_ids[2*i+1]) {
      throw Error('Eight-player quarterfinal draw changed')
    }
  }
  if (pairs[4][0] !== winners[0] || pairs[4][1] !== winners[1]
    || pairs[5][0] !== winners[2] || pairs[5][1] !== winners[3]
    || pairs[6][0] !== winners[4] || pairs[6][1] !== winners[5]
    || receipt.winner_player_id !== winners[6] || !command.entrant_ids.includes(winners[6])
  ) throw Error('Eight-player semifinal or final winner lineage changed')
  if (scored) {
    const policy = command.point_policy, awards = receipt.prepared_awards
    const expected: Record<string, number> = {
      champion: policy.champion, finalist: policy.finalist,
      semifinal: policy.semifinal, quarterfinal: policy.quarterfinal,
    }
    const placements = [
      ...e.matches.slice(0, 4).map(m => [m.result.player_a_id === m.result.winner_player_id
        ? m.result.player_b_id : m.result.player_a_id, 'quarterfinal']),
      ...e.matches.slice(4, 6).map(m => [m.result.player_a_id === m.result.winner_player_id
        ? m.result.player_b_id : m.result.player_a_id, 'semifinal']),
      [e.matches[6].result.player_a_id === winners[6]
        ? e.matches[6].result.player_b_id : e.matches[6].result.player_a_id, 'finalist'],
      [winners[6], 'champion'],
    ]
    if (receipt.publication_status !== 'prepared_not_official'
      || !hash(receipt.prepared_policy_fingerprint)
      || !awards || awards.length !== 8
      || !policy.category_label.trim()
      || !Number.isSafeInteger(policy.validity_weeks)
      || policy.validity_weeks !== view.sporting_week?.calendar.weeks_per_year
      || ![policy.champion, policy.finalist, policy.semifinal, policy.quarterfinal]
        .every(n => Number.isSafeInteger(n) && n >= 0 && n <= 1000000)
      || policy.champion <= policy.quarterfinal
      || policy.champion < policy.finalist || policy.finalist < policy.semifinal
      || policy.semifinal < policy.quarterfinal
      || placements.some(([playerId, stage]) => !awards.some(a => a.player_id === playerId
        && a.reached_stage === stage && a.main_points === expected[stage]))
      || new Set(awards.map(a => a.player_id)).size !== 8
      || new Set(awards.map(a => a.source_policy_fingerprint)).size !== 1
      || new Set(awards.map(a => a.source_tournament_fingerprint)).size !== 1
      || awards.some(a => !hash(a.source_tournament_fingerprint)
        || a.source_policy_fingerprint !== receipt.prepared_policy_fingerprint)
    ) throw Error('Eight-player prepared awards differ from the played knockout')
  }
  return receipt
}

export function verifyNativeTournamentClosure(
  receipt: NativeTournamentClosureReceipt,
  command: NativeTournamentClosureCommand, view: ContinuationView,
): NativeTournamentClosureReceipt {
  const closure = receipt?.closure, matches = view.tournaments?.find(t => t.tournament_id === command.tournament_id)
  const validHash = (s: unknown) => typeof s === 'string' && /^[0-9a-f]{64}$/.test(s)
  if (!receipt || receipt.schema_version !== 'calendar_native_tournament_closure_receipt.v1'
    || receipt.official_ranking_published !== false
    || receipt.publication_status !== 'native_result_closed_not_official'
    || !validHash(receipt.fingerprint) || !validHash(receipt.checkpoint_fingerprint)
    || !closure || closure.scope !== 'played_native_result_closed_not_official'
    || closure.command_id !== command.command_id || closure.tournament_id !== command.tournament_id
    || closure.source_saved_head !== command.expected_saved_head
    || closure.source_checkpoint_fingerprint !== command.expected_checkpoint_fingerprint
    || !matches || closure.source_tournament_fingerprint !== matches.fingerprint
    || closure.champion_player_id !== matches.winner_player_id
    || !Array.isArray(closure.players) || closure.players.length !== 8
    || !validHash(closure.source_prepared_awards_fingerprint)
    || !validHash(closure.request_fingerprint)
  ) throw Error('Native tournament result closure does not match Saved sporting evidence')
  return receipt
}
