import { useQueries, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  getAuthoritativeSimulationPosition,
  getPreAlphaFaxEntryValidationPolicyGate,
  getSavedRevision
} from '../api/client'
import type {
  AuthoritativeSimulationPosition,
  PreAlphaFaxEntryValidationPolicyGate,
  RunBranch,
  RunContainer,
  SavedRevisionHistoryDetail
} from '../api/types'
import { formatApiError } from '../utils/apiErrors'
import { EmptyState, MetadataList, SectionCard } from './RunScopedUi'

type BranchReadinessPanelProps = {
  run: RunContainer
  branches: RunBranch[]
}

const positionKey = (runId: string, branchId: string) =>
  ['admin-branch-operational-position', runId, branchId] as const
const revisionKey = (runId: string, branchId: string, revisionId: string | null) =>
  ['admin-branch-operational-revision', runId, branchId, revisionId] as const
const entryGateKey = (runId: string, branchId: string) =>
  ['admin-branch-operational-entry-gate', runId, branchId] as const

function validPosition(
  value: AuthoritativeSimulationPosition | undefined,
  runId: string,
  branchId: string
): value is AuthoritativeSimulationPosition {
  return Boolean(
    value && value.run_id === runId && value.branch_id === branchId &&
    Number.isInteger(value.current_week?.season_index) &&
    value.current_week.season_index >= 0 && value.current_week.season_index < 50 &&
    Number.isInteger(value.current_week?.week) &&
    value.current_week.week >= 1 && value.current_week.week <= 61 &&
    Array.isArray(value.transition_blockers)
  )
}

function validRevision(
  value: SavedRevisionHistoryDetail | undefined,
  runId: string,
  branchId: string,
  revisionId: string | null
): value is SavedRevisionHistoryDetail {
  return Boolean(
    value && value.run_id === runId && value.branch_id === branchId &&
    value.revision_id === revisionId && value.is_branch_head &&
    value.content_hash && value.content_hash_algorithm
  )
}

function validEntryGate(
  value: PreAlphaFaxEntryValidationPolicyGate | undefined,
  runId: string,
  branchId: string,
  position: AuthoritativeSimulationPosition
): value is PreAlphaFaxEntryValidationPolicyGate {
  return Boolean(
    value && value.run_id === runId && value.branch_id === branchId &&
    value.current_week.season_index === position.current_week.season_index &&
    value.current_week.week === position.current_week.week &&
    value.current_position_fingerprint === position.position_fingerprint
  )
}

function readinessReason(run: RunContainer, branch: RunBranch): string | null {
  if (branch.run_id !== run.run_id) return 'Branch belongs to another Run.'
  if (run.status !== 'active') return 'Run is not active.'
  if (run.read_only) return 'Run is read-only.'
  if (branch.status !== 'active') return 'Branch is not active.'
  if (branch.read_only) return 'Branch is read-only.'
  if (!branch.saved_head_revision_id) return 'Branch has no saved head revision.'
  return null
}

/** Read-only inspection. No mutation or simulated readiness inferred from legacy checkpoints. */
export function RunBranchReadinessPanel({ run, branches }: BranchReadinessPanelProps): JSX.Element {
  const client = useQueryClient()
  const positions = useQueries({
    queries: branches.map(branch => ({
      queryKey: positionKey(run.run_id, branch.branch_id),
      queryFn: () => getAuthoritativeSimulationPosition(run.run_id, branch.branch_id),
      enabled: branch.run_id === run.run_id && Boolean(branch.saved_head_revision_id),
      retry: false
    }))
  })
  const revisions = useQueries({
    queries: branches.map(branch => ({
      queryKey: revisionKey(run.run_id, branch.branch_id, branch.saved_head_revision_id ?? null),
      queryFn: () => getSavedRevision(run.run_id, branch.branch_id, branch.saved_head_revision_id!),
      enabled: branch.run_id === run.run_id && Boolean(branch.saved_head_revision_id),
      retry: false
    }))
  })
  const gates = useQueries({
    queries: branches.map((branch, index) => {
      const position = positions[index]?.data
      return {
        queryKey: entryGateKey(run.run_id, branch.branch_id),
        queryFn: () => getPreAlphaFaxEntryValidationPolicyGate(run.run_id, branch.branch_id),
        enabled: validPosition(position, run.run_id, branch.branch_id) &&
          position.current_slot_kind === 'entry',
        retry: false
      }
    })
  })

  return (
    <SectionCard title="Branch operating status">
      <p className="status">
        Read-only status from each Branch's own Saved Revision and authoritative simulation position.
        A Week Transition indicator does not authorize other simulation actions; open the Branch to review their preflights.
      </p>
      <button type="button" onClick={() => {
        void Promise.all([
          client.invalidateQueries({ queryKey: ['admin-branch-operational-position', run.run_id] }),
          client.invalidateQueries({ queryKey: ['admin-branch-operational-revision', run.run_id] }),
          client.invalidateQueries({ queryKey: ['admin-branch-operational-entry-gate', run.run_id] })
        ])
      }}>Refresh Branch operating status</button>
      {branches.length === 0 && <EmptyState message="No Branches exist in this Run." />}
      {branches.map((branch, index) => {
        const positionQuery = positions[index]
        const revisionQuery = revisions[index]
        const gateQuery = gates[index]
        const hasPosition = validPosition(positionQuery.data, run.run_id, branch.branch_id)
        const position = hasPosition ? positionQuery.data : null
        const hasRevision = validRevision(
          revisionQuery.data, run.run_id, branch.branch_id, branch.saved_head_revision_id ?? null
        )
        const revision = hasRevision ? revisionQuery.data : null
        const needsGate = position?.current_slot_kind === 'entry'
        const hasGate = Boolean(position && validEntryGate(gateQuery.data, run.run_id, branch.branch_id, position))
        const gate = hasGate ? gateQuery.data : null
        const blocker = readinessReason(run, branch)
        const positionWarning = !branch.saved_head_revision_id
          ? 'No saved revision; authoritative position cannot be inspected.'
          : positionQuery.isPending
            ? 'Loading authoritative position…'
            : positionQuery.error
              ? `Authoritative position unavailable: ${formatApiError(positionQuery.error)}`
              : !position
                ? 'Authoritative position has a mismatched or invalid Run, Branch, or week identity.'
                : null
        const revisionWarning = !branch.saved_head_revision_id
          ? null
          : revisionQuery.isPending
            ? 'Loading saved revision head…'
            : revisionQuery.error
              ? `Saved revision head unavailable: ${formatApiError(revisionQuery.error)}`
              : !revision
                ? 'Saved revision head identity or head status is inconsistent.'
                : null
        const gateWarning = !needsGate
          ? null
          : gateQuery.isPending
            ? 'Checking entry-validation policy…'
            : gateQuery.error
              ? `Entry-validation policy unavailable: ${formatApiError(gateQuery.error)}`
              : !gate
                ? 'Entry-validation policy identity is inconsistent.'
                : null
        const canInspect = !blocker && position && revision && (!needsGate || gate)
        return (
          <article className="panel nested-panel" aria-label={`Operating status for ${branch.branch_id}`} key={branch.branch_id}>
            <h4>{branch.display_name} {branch.branch_id === (run.viewer_branch_id ?? run.official_branch_id) && <span className="status">Viewer Branch</span>}</h4>
            <MetadataList items={[
              { label: 'Branch ID', value: branch.branch_id },
              { label: 'Season', value: position ? `${2000 + position.current_week.season_index}/${2001 + position.current_week.season_index}` : 'Not verified' },
              { label: 'Week', value: position ? `W${position.current_week.week} / 61` : 'Not verified' },
              { label: 'Current slot', value: position?.current_slot_kind ?? 'None / unavailable' },
              { label: 'Saved Revision HEAD', value: branch.saved_head_revision_id ?? 'None' },
              { label: 'Saved revision type', value: revision?.kind ?? 'Not verified' },
              { label: 'Week Transition', value: position ? (
                position.week_ready_for_transition && position.transition_blockers.length === 0
                  ? 'Reported ready by the engine'
                  : 'Not ready'
              ) : 'Not verified' }
            ]} />
            {blocker && <p role="alert" className="error">Branch unavailable: {blocker}</p>}
            {positionWarning && <p role="status">{positionWarning}</p>}
            {revisionWarning && <p role="status">{revisionWarning}</p>}
            {gateWarning && <p role="status">{gateWarning}</p>}
            {position?.transition_blockers.length ? (
              <div>
                <strong>Week Transition blockers</strong>
                <ul>{position.transition_blockers.map((reason, index) => <li key={index}>{reason}</li>)}</ul>
              </div>
            ) : null}
            {needsGate && gate && gate.current_blocker_code === 'application_validation_policy_unresolved' && (
              <p role="alert" className="error">
                Application validation requires explicit Admin review; automatic eligibility policy remains unresolved.
              </p>
            )}
            {canInspect ? (
              <Link to={`/admin/runs/${encodeURIComponent(run.run_id)}/simulate?branch=${encodeURIComponent(branch.branch_id)}`}>
                Inspect authoritative simulation and available actions
              </Link>
            ) : (
              <p className="status">Simulation readiness is not verified. Review the warnings above; no action is executed from this panel.</p>
            )}
          </article>
        )
      })}
    </SectionCard>
  )
}
