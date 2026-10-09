import type {
  AuthoritativeWeekSchedulePreflight,
  CanonicalTournamentPreparationState
} from '../api/types'

type Props = {
  runId: string
  branchId: string
  preflight?: AuthoritativeWeekSchedulePreflight
  enabled: boolean
}

const actions: Record<CanonicalTournamentPreparationState['next_required_action'], string> = {
  adopt_ranking_snapshot: 'Review the published Ranking Snapshot and adopt it explicitly.',
  build_entry_field: 'Review eligible applications or the frozen Finals selection, then build the Entry Field.',
  review_finals_replacement: 'Review the Finals participant replacement decision.',
  review_wild_cards: 'Review Wild Card and replacement Wild Card authority.',
  review_pre_draw_or_commit_draw_input: 'Review qualification and the pre-draw field before confirming Draw Input.',
  configure_tournament_format: 'Tournament Format authority is required; check which controls are implemented on the Event page.',
  generate_tournament_topology: 'Tournament Topology is required; check which controls are implemented on the Event page.',
  prepare_group_match_schedule: 'Generate the frozen group-match schedule from verified Tournament Topology.',
  generate_draw: 'Review and generate the canonical Draw from verified inputs.',
  none: 'No supported next preparation action is reported.'
}

function verifiedSnapshot(
  value: AuthoritativeWeekSchedulePreflight | undefined,
  runId: string,
  branchId: string
): value is AuthoritativeWeekSchedulePreflight {
  if (!value || value.schema_version !== 'authoritative_week_schedule_preflight.v1' ||
      value.run_id !== runId || value.branch_id !== branchId || value.read_only !== true ||
      !Number.isInteger(value.week?.season_index) ||
      value.week.season_index < 0 || value.week.season_index > 49 ||
      !Number.isInteger(value.week?.week) || value.week.week < 1 || value.week.week > 61 ||
      !/^[0-9a-f]{64}$/.test(value.preflight_fingerprint) ||
      !Array.isArray(value.event_ids) || !Array.isArray(value.blockers)) return false

  const state = value.canonical_preparation
  if (!state || state.schema_version !== 'canonical_week_schedule_preparation_state.v1' ||
      state.run_id !== runId || state.branch_id !== branchId ||
      state.authority_source !== 'run_owned_db_authorities.v1' ||
      !/^[0-9a-f]{64}$/.test(state.preparation_fingerprint) ||
      !Array.isArray(state.event_ids) || !Array.isArray(state.tournaments) ||
      !Array.isArray(state.blockers) ||
      state.event_ids.length !== value.event_ids.length ||
      state.tournaments.length !== value.event_ids.length ||
      new Set(value.event_ids).size !== value.event_ids.length ||
      !value.event_ids.every((id, i) => typeof id === 'string' && id.length > 0 && state.event_ids[i] === id)) return false

  return state.tournaments.every(t =>
    t && t.schema_version === 'canonical_tournament_preparation_state.v1' &&
    t.run_id === runId && t.branch_id === branchId &&
    state.event_ids.includes(t.event_id) &&
    t.authority_source === 'run_owned_db_authorities.v1' &&
    typeof t.ready_for_match_schedule === 'boolean' &&
    Array.isArray(t.blockers) &&
    t.blockers.every(code => typeof code === 'string') &&
    Object.prototype.hasOwnProperty.call(actions, t.next_required_action)
  ) && new Set(state.tournaments.map(t => t.event_id)).size === state.tournaments.length &&
  state.ready_for_week_schedule === state.tournaments.every(t => t.ready_for_match_schedule)
}

export function TournamentPreparationGuide({
  runId, branchId, preflight, enabled
}: Props): JSX.Element {
  const verified = enabled && verifiedSnapshot(preflight, runId, branchId)
  const tournaments = verified ? preflight.canonical_preparation!.tournaments : []

  return (
    <section aria-label="Tournament preparation guide">
      <h4>Tournament preparation — current Week</h4>
      <p className="status">
        Read-only, Run/Branch-scoped Week Schedule preflight. Event links carry the
        required Branch identity; the detail page must verify it before showing controls.
        This guide never validates applications, picks qualifiers or creates a Draw.
      </p>
      {!enabled ? (
        <p role="status">Not verified: an active Branch and Saved Revision are required.</p>
      ) : !verified ? (
        <p role="status">
          Not verified: canonical tournament preparation is absent, loading or has inconsistent
          Run/Branch/Event identity. No event action is offered.
        </p>
      ) : tournaments.length === 0 ? (
        <p role="status">No tournament preparation is listed for this Week.</p>
      ) : (
        <>
          <p className="status">
            {tournaments.filter(t => t.ready_for_match_schedule).length} of {tournaments.length}
            {' '}tournaments report readiness for Week scheduling. This does not authorize a simulation command.
          </p>
          <ul aria-label="Tournament preparation next steps">
            {tournaments.map(t => {
              const action = actions[t.next_required_action]
              const canHandoff = t.ready_for_match_schedule ||
                (t.next_required_action !== 'none' && !t.ready_for_match_schedule)
              return (
                <li key={t.event_id}>
                  <strong>{t.event_id}</strong>{' — '}
                  {t.ready_for_match_schedule ? 'Schedule-ready' : 'Preparation needed'}
                  {' · '}<code>{t.phase}</code>
                  <p>{t.ready_for_match_schedule
                    ? 'Canonical preparation reports a schedule-ready tournament; the Week Schedule still requires its own review.'
                    : action}</p>
                  {t.blockers.length ? (
                    <p>Engine blockers: {t.blockers.map((code, i) => (
                      <span key={i}><code>{code}</code>{i < t.blockers.length - 1 ? ', ' : ''}</span>
                    ))}</p>
                  ) : null}
                  {canHandoff ? (
                    <a href={`/admin/runs/${encodeURIComponent(runId)}/calendar/${encodeURIComponent(t.event_id)}?branch=${encodeURIComponent(branchId)}`}>
                      Open Branch-scoped planned event review
                    </a>
                  ) : (
                    <p className="status">No verified action available here. Inspect the reported engine limitation.</p>
                  )}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}
