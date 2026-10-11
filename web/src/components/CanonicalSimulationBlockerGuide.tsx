import type {
  AuthoritativeSimulationPosition,
  AuthoritativeWeekSchedulePreflight
} from '../api/types'

type Props = {
  runId: string
  branchId: string
  available: boolean
  position?: AuthoritativeSimulationPosition
  schedulePreflight?: AuthoritativeWeekSchedulePreflight
  scheduleInspectionAvailable: boolean
}

type Guidance = {
  explanation: string
  target?: string
  action?: string
}

function validPosition(
  position: AuthoritativeSimulationPosition | undefined,
  runId: string,
  branchId: string
): position is AuthoritativeSimulationPosition {
  return Boolean(
    position &&
    position.run_id === runId &&
    position.branch_id === branchId &&
    Number.isInteger(position.current_week?.season_index) &&
    position.current_week.season_index >= 0 &&
    position.current_week.season_index < 50 &&
    Number.isInteger(position.current_week?.week) &&
    position.current_week.week >= 1 &&
    position.current_week.week <= 61 &&
    /^[a-f0-9]{64}$/.test(position.position_fingerprint) &&
    Array.isArray(position.transition_blockers) &&
    position.transition_blockers.every((code) => typeof code === 'string' && code.length > 0)
  )
}

/**
 * These are read-only navigation hints, NOT preflight decisions or auto-fixes.
 * Any unknown authority code deliberately has no executable shortcut.
 */
export function blockerGuidance(
  code: string,
  position: AuthoritativeSimulationPosition
): Guidance {
  switch (code) {
    case 'pending_authoritative_groups':
      return position.current_slot_kind === 'match' && position.unresolved_group_ids.length > 0
        ? {
            explanation: 'Competitive groups remain unresolved in the current Slot.',
            target: 'canonical-current-slot',
            action: 'Inspect current matches'
          }
        : { explanation: 'Current sporting Slot is not complete; inspect its authoritative state.' }
    case 'entry_validation_pending':
      return position.current_slot_kind === 'entry' && position.slot_ordinal != null
        ? {
            explanation: 'Frozen Entry decisions require explicit, audited Admin validation.',
            target: 'canonical-entry-validation',
            action: 'Inspect Entry review'
          }
        : { explanation: 'Entry validation is pending, but the matching Entry Slot is not verified.' }
    case 'working_draft_dirty':
      return {
        explanation: 'The Branch Working Draft must be saved explicitly before advancing.',
        target: 'canonical-simulation-save',
        action: 'Inspect Save preview'
      }
    case 'ranking_transition_authority_missing':
      return position.transition_blockers.length === 1
        ? {
            explanation: 'The target week needs a reviewed Ranking Transition Authority.',
            target: 'canonical-ranking-authority',
            action: 'Inspect Ranking Authority'
          }
        : {
            explanation: 'Ranking Transition Authority is missing. Resolve the other canonical blockers first.'
          }
    case 'season_transition_required':
      return position.current_week.week === 61
        ? {
            explanation: 'Week 61 requires a separate, reviewed Season Transition or final Run closure.',
            target: 'canonical-season-transition',
            action: 'Inspect season preflight'
          }
        : { explanation: 'Season boundary code conflicts with the current week; do not advance.' }
    case 'run_branch_not_writable':
    case 'run_branch_scope_missing':
      return { explanation: 'Run/Branch authority or write permissions are unavailable; inspect the selected Branch.' }
    case 'ranking_transition_authority_stale':
    case 'ranking_transition_authority_boundary_mismatch':
    case 'authoritative_world_head_mismatch':
      return { explanation: 'Persisted authority is inconsistent or stale. Reconcile the Saved Revision and authoritative state.' }
    default:
      return {
        explanation: 'No verified resolution is mapped for this engine blocker. Inspect the canonical preflights; do not bypass it.'
      }
  }
}

export function CanonicalSimulationBlockerGuide({
  runId,
  branchId,
  available,
  position,
  schedulePreflight,
  scheduleInspectionAvailable
}: Props): JSX.Element {
  const validSchedule = !schedulePreflight || (
    schedulePreflight.run_id === runId &&
    schedulePreflight.branch_id === branchId &&
    schedulePreflight.schema_version === 'authoritative_week_schedule_preflight.v1' &&
    schedulePreflight.read_only === true &&
    Number.isInteger(schedulePreflight.week?.season_index) &&
    Number.isInteger(schedulePreflight.week?.week)
  )
  const verified = validPosition(position, runId, branchId) && validSchedule && (
    !schedulePreflight ||
    (schedulePreflight.week.season_index === position.current_week.season_index &&
      schedulePreflight.week.week === position.current_week.week &&
      (!schedulePreflight.schedule_required || schedulePreflight.schedule_already_adopted))
  )
  const needsSchedule = available && validSchedule && schedulePreflight?.schedule_required &&
    !schedulePreflight.schedule_already_adopted

  return (
    <section aria-label="Canonical simulation blocker guide">
      <h4>What blocks this Branch?</h4>
      <p className="status">
        Read-only guidance for this exact Run/Branch. Links navigate to existing reviews;
        they do not validate, save or execute anything. A Week Transition status is not
        permission for other simulation operations.
      </p>
      {!available ? (
        <p role="status">Not verified: an active writable Branch with a Saved Revision head is required.</p>
      ) : !validSchedule ? (
        <p role="status">Not verified: Week Schedule preflight belongs to another scope or is invalid.</p>
      ) : needsSchedule ? (
        <>
          <p role="status">Week Schedule is not adopted. Current Position cannot be treated as verified.</p>
          {schedulePreflight.blockers.length > 0 ? (
            <ul aria-label="Week Schedule preparation blockers">
              {schedulePreflight.blockers.map((code, index) => (
                <li key={index}><code>{code}</code> — Review canonical tournament preparation; no automatic repair is available.</li>
              ))}
            </ul>
          ) : null}
          {scheduleInspectionAvailable ? (
            <a href="#canonical-week-schedule">Inspect Week Schedule review</a>
          ) : null}
        </>
      ) : !verified ? (
        <p role="status">Not verified: canonical position is loading, unavailable, or inconsistent with its Run/Branch/Week. No action is recommended.</p>
      ) : position.transition_blockers.length > 0 ? (
        <>
          <p role="status">Week Transition is blocked by {position.transition_blockers.length} authoritative condition(s).</p>
          <ul aria-label="Authoritative blocker guidance">
            {position.transition_blockers.map((code, index) => {
              const guidance = blockerGuidance(code, position)
              return (
                <li key={index}>
                  <code>{code}</code> — {guidance.explanation}{' '}
                  {guidance.target ? <a href={`#${guidance.target}`}>{guidance.action}</a> : null}
                </li>
              )
            })}
          </ul>
        </>
      ) : position.week_ready_for_transition && position.current_week.week !== 61 ? (
        <p role="status">
          Engine reports this Week Transition ready for review.{' '}
          <a href="#canonical-week-transition">Inspect Week Transition review</a>
        </p>
      ) : position.current_week.week === 61 ? (
        <p role="status">
          Week 61 is a season boundary, not an ordinary Week Transition.{' '}
          <a href="#canonical-season-transition">Inspect season preflight</a>
        </p>
      ) : (
        <p role="status">No blocker codes were reported, but the engine has not confirmed Week Transition readiness. Do not advance automatically.</p>
      )}
    </section>
  )
}
