import type { CanonicalTournamentPreparationState } from '../api/types'

export type TournamentSectionId =
  | 'canonical-entry-timing'
  | 'canonical-preparation'
  | 'canonical-entry-review'
  | 'canonical-reviewed-entry-field'
  | 'canonical-main-draw-preflight'
  | 'canonical-wc-review'
  | 'canonical-draw-authority'
  | 'canonical-first-match'
  | 'finals-race-replacement'

export type TournamentNavigationSections = Partial<Record<TournamentSectionId, boolean>>
type Action = CanonicalTournamentPreparationState['next_required_action']

const actions: Record<Exclude<Action, 'none'>, {
  section: TournamentSectionId
  cs: string
  en: string
}> = {
  adopt_ranking_snapshot: {
    section: 'canonical-preparation', cs: 'Zvolit publikovaný Official Ranking',
    en: 'Select a published Official Ranking'
  },
  build_entry_field: {
    section: 'canonical-preparation', cs: 'Sestavit turnajové pole z ověřených přihlášek',
    en: 'Build the field from reviewed applications'
  },
  review_finals_replacement: {
    section: 'finals-race-replacement', cs: 'Posoudit náhradu pro World Tour Finals',
    en: 'Review World Tour Finals replacement'
  },
  review_wild_cards: {
    section: 'canonical-wc-review', cs: 'Prověřit divoké karty a náhradníky',
    en: 'Review Wild Cards and replacements'
  },
  review_pre_draw_or_commit_draw_input: {
    section: 'canonical-main-draw-preflight', cs: 'Prověřit předlosovací podmínky',
    en: 'Review pre-draw requirements'
  },
  configure_tournament_format: {
    section: 'canonical-preparation', cs: 'Nastavit formát turnaje',
    en: 'Configure the tournament format'
  },
  generate_tournament_topology: {
    section: 'canonical-preparation', cs: 'Připravit topologii turnaje',
    en: 'Prepare the tournament topology'
  },
  prepare_group_match_schedule: {
    section: 'canonical-preparation', cs: 'Připravit rozpis skupinových zápasů',
    en: 'Prepare group match schedule'
  },
  generate_draw: {
    section: 'canonical-draw-authority', cs: 'Vygenerovat potvrzený turnajový pavouk',
    en: 'Generate the authoritative tournament draw'
  }
}

export type VerifiedTournamentNavigation = {
  action: Action
  next: { label: string; target: TournamentSectionId } | null
  sourceBlockers: string[]
  scheduleReady: boolean
  rankingPublished: boolean
  entryFieldStored: boolean
  drawStored: boolean
}

export function verifiedTournamentNavigation(
  source: CanonicalTournamentPreparationState | null | undefined,
  runId: string,
  branchId: string,
  eventId: string,
  sections: TournamentNavigationSections,
  language: 'cs' | 'en'
): VerifiedTournamentNavigation | null {
  if (!source || !runId || !branchId || !eventId ||
      source.schema_version !== 'canonical_tournament_preparation_state.v1' ||
      source.authority_source !== 'run_owned_db_authorities.v1' ||
      source.run_id !== runId || source.branch_id !== branchId || source.event_id !== eventId ||
      !Array.isArray(source.blockers) ||
      source.blockers.some(x => typeof x !== 'string' || !x.trim()) ||
      typeof source.ready_for_match_schedule !== 'boolean' ||
      typeof source.next_required_action !== 'string' ||
      (source.next_required_action !== 'none' && !Object.prototype.hasOwnProperty.call(actions, source.next_required_action)) ||
      (source.preparation_fingerprint !== undefined &&
        !/^[0-9a-f]{64}$/.test(source.preparation_fingerprint))) return null

  const action = source.next_required_action as Action
  const plan = action === 'none' ? null : actions[action]
  // A backend action is *not* permission to show a link to an unmounted
  // section. More importantly, "none" is not itself proof of readiness.
  const terminalReady = action === 'none' &&
    source.ready_for_match_schedule && source.blockers.length === 0
  const target = plan?.section ?? (terminalReady ? 'canonical-first-match' : null)
  const targetAvailable = target !== null && sections[target] === true
  return {
    action,
    next: targetAvailable && target ? {
      label: plan ? plan[language] : language === 'cs'
        ? 'Otevřít přípravu zápasů' : 'Open match preparation',
      target
    } : null,
    sourceBlockers: source.blockers,
    scheduleReady: terminalReady,
    rankingPublished: source.ranking_snapshot_ready === true,
    entryFieldStored: source.entry_field_ready === true,
    drawStored: source.draw_ready === true
  }
}
