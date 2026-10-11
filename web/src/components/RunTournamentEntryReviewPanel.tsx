import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  getAuthoritativeSimulationPosition, getBranchWorkingDraft, getRunContainer,
  inspectAuthoritativeEntryDecisionSlot, listRunBranches, reviewAuthoritativeEntryDecisionSlot
} from '../api/client'
import {
  buildReviewedEntryValidation, decisionKey, verifiedFrozenEntrySlot,
  type EntryValidationOutcome, type ReviewedEntryValidation
} from '../api/runTournamentEntryReview'
import { formatApiError } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

/** Existing production frozen slot → explicit Admin validation → persisted valid submissions.
 * This NEVER resolves the currently undecided automatic validation policy. */
export function RunTournamentEntryReviewPanel({ runId, branchId, eventId }: {
  runId: string; branchId: string; eventId: string
}): JSX.Element {
  const queryClient = useQueryClient()
  const [outcomes, setOutcomes] = useState<Record<string, EntryValidationOutcome>>({})
  const [operator, setOperator] = useState('')
  const [reason, setReason] = useState('')
  const [review, setReview] = useState<ReviewedEntryValidation | null>(null)
  const [approved, setApproved] = useState(false)
  const [notice, setNotice] = useState('')

  const runQuery = useQuery({
    queryKey: ['admin-run-container', runId], queryFn: () => getRunContainer(runId),
    enabled: Boolean(runId), retry: false
  })
  const branchQuery = useQuery({
    queryKey: ['admin-run-branches', runId], queryFn: () => listRunBranches(runId),
    enabled: Boolean(runId), retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: Boolean(runId && branchId), retry: false
  })
  const branch = branchQuery.data?.run_branches.find(row =>
    row.run_id === runId && row.branch_id === branchId)
  const head = branch?.saved_head_revision_id ?? ''
  const editable = Boolean(runQuery.data?.run_id === runId &&
    runQuery.data.storage_kind === 'custom_local' && !runQuery.data.read_only &&
    branch && branch.status === 'active' && !branch.read_only &&
    draftQuery.data?.run_id === runId && draftQuery.data.branch_id === branchId &&
    draftQuery.data.base_saved_revision_id === head && draftQuery.data.status === 'clean' && head)

  const positionQuery = useQuery({
    queryKey: ['authoritative-simulation-position', runId, branchId],
    queryFn: () => getAuthoritativeSimulationPosition(runId, branchId),
    enabled: editable, retry: false
  })
  const position = positionQuery.data
  const slotOrdinal = position?.current_slot_kind === 'entry' ? position.slot_ordinal : null
  const slotQuery = useQuery({
    queryKey: ['authoritative-entry-decision-slot', runId, branchId, slotOrdinal],
    queryFn: () => inspectAuthoritativeEntryDecisionSlot(runId, branchId, slotOrdinal!),
    enabled: editable && Number.isInteger(slotOrdinal) && (slotOrdinal ?? 0) >= 1,
    retry: false
  })
  const inspection = slotQuery.data
  const verified = verifiedFrozenEntrySlot(position, inspection, runId, branchId, eventId)
  const decisions = verified ? inspection.authority.decisions : []
  const unreviewed = decisions.filter(item => !outcomes[decisionKey(item.event_id, item.player_id)]?.outcome)
  const rejectedMissingReason = decisions.some(item => {
    const data = outcomes[decisionKey(item.event_id, item.player_id)]
    return data?.outcome === 'invalid' && !data.reason.trim()
  })
  const validCount = decisions.filter(item => outcomes[decisionKey(item.event_id, item.player_id)]?.outcome === 'valid').length
  const canReview = Boolean(editable && verified && !positionQuery.isFetching && !slotQuery.isFetching &&
    !runQuery.isFetching && !branchQuery.isFetching && !draftQuery.isFetching &&
    unreviewed.length === 0 && !rejectedMissingReason && operator.trim() && reason.trim())

  useEffect(() => {
    setOutcomes({})
    setOperator('')
    setReason('')
    setReview(null)
    setApproved(false)
    setNotice('')
  }, [runId, branchId, eventId, slotQuery.data?.slot_fingerprint, positionQuery.data?.position_fingerprint, head])

  const reviewedIsCurrent = Boolean(review && canReview &&
    review.runId === runId && review.branchId === branchId &&
    review.selectedEventId === eventId && review.savedHeadId === head &&
    review.slotFingerprint === inspection?.slot_fingerprint &&
    review.positionFingerprint === position?.position_fingerprint &&
    review.decisionCount === decisions.length &&
    review.payload.operator_label === operator.trim() &&
    review.payload.reason === reason.trim() &&
    review.payload.reviews.every(row => {
      const current = outcomes[decisionKey(row.event_id, row.player_id)]
      return current?.outcome === row.outcome &&
        (row.outcome === 'valid' || (row.reasons[0] === current?.reason.trim()))
    })
  )
  const commit = useMutation({
    mutationFn: (current: ReviewedEntryValidation) =>
      reviewAuthoritativeEntryDecisionSlot(current.runId, current.branchId, current.payload),
    onSuccess: async (value) => {
      setReview(null)
      setApproved(false)
      setNotice(`Persisted ${value.valid_submission_count} explicitly valid tournament submissions. This does not implement automatic eligibility policy. Save/reopen must still be verified separately.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['canonical-tournament-preparation', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-entry-decision-slot', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['canonical-entry-field', runId, branchId] })
      ])
    },
    onError: async () => {
      setReview(null); setApproved(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-entry-decision-slot', runId, branchId] })
      ])
    }
  })

  return <SectionCard title="Review tournament applications">
    <p className="status">Only authoritative frozen Entry-decision evidence is reviewable. Each decision must be explicitly accepted or rejected. The automatic eligibility/deadline policy remains unresolved; no player is treated as valid by default.</p>
    {!editable && <p role="status">A writable canonical Run, active Branch, clean Working Draft and verified Saved Revision are required.</p>}
    {runQuery.error && <p role="alert" className="error">Product Run unavailable: {formatApiError(runQuery.error)}</p>}
    {branchQuery.error && <p role="alert" className="error">Branch authority unavailable: {formatApiError(branchQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {positionQuery.error && <p role="alert" className="error">Canonical simulation position unavailable: {formatApiError(positionQuery.error)}</p>}
    {position && position.current_slot_kind !== 'entry' &&
      <p role="status">Current canonical slot is not an Entry-decision slot. Finish its preceding engine steps first.</p>}
    {slotQuery.error && <p role="alert" className="error">Frozen Entry slot unavailable: {formatApiError(slotQuery.error)}</p>}
    {inspection?.validation_resolved && <p role="status">Entry validation is already resolved; immutable submissions cannot be overwritten here.</p>}
    {inspection && !inspection.validation_resolved && !verified &&
      <p role="alert" className="error">Frozen slot is not verified for this Run/Branch/Week or has no decisions for this event. No manual validation is authorized.</p>}
    {verified && <section aria-label="Frozen tournament entry decisions">
      <p>Current Week {position?.current_week.week} · Slot {slotOrdinal} · <strong>{decisions.length}</strong> frozen decisions across {new Set(decisions.map(x => x.event_id)).size} simultaneous event(s).</p>
      <p className="status">All events sharing the current slot must be reviewed as one atomic batch, including applications to other tournaments. No player IDs are invented.</p>
      <ul aria-label="Review every frozen entry decision">
        {decisions.map(item => {
          const key = decisionKey(item.event_id, item.player_id)
          const current = outcomes[key] ?? { outcome: '', reason: '' }
          return <li key={key}>
            <strong>{item.event_id} · {item.player_id} · {item.target}</strong>
            <label>Result for {item.event_id}/{item.player_id}
              <select aria-label={`Entry outcome ${key}`} value={current.outcome}
                disabled={commit.isPending}
                onChange={event => {
                  setReview(null); setApproved(false)
                  const outcome = event.target.value as EntryValidationOutcome['outcome']
                  setOutcomes(previous => ({ ...previous, [key]: {
                    outcome, reason: outcome === 'invalid' ? previous[key]?.reason ?? '' : ''
                  } }))
                }}>
                <option value="">Not reviewed</option>
                <option value="valid">Valid — explicitly approved</option>
                <option value="invalid">Invalid — explicit rejection</option>
              </select>
            </label>
            {current.outcome === 'invalid' && <label>Rejection reason
              <input aria-label={`Entry rejection ${key}`} value={current.reason}
                disabled={commit.isPending}
                onChange={event => {
                  setReview(null); setApproved(false)
                  setOutcomes(previous => ({ ...previous, [key]: { outcome: 'invalid', reason: event.target.value } }))
                }}/>
            </label>}
          </li>
        })}
      </ul>
      <label>Operator <input aria-label="Entry review operator" value={operator}
        onChange={event => { setOperator(event.target.value); setReview(null); setApproved(false) }}/></label>
      <label>Audit reason <input aria-label="Entry review audit reason" value={reason}
        onChange={event => { setReason(event.target.value); setReview(null); setApproved(false) }}/></label>
      <p>{validCount} explicitly approved · {decisions.length - validCount - unreviewed.length} rejected · {unreviewed.length} awaiting review.</p>
      <button type="button" disabled={!canReview || commit.isPending}
        onClick={() => {
          if (!position || !inspection) return
          try {
            setReview(buildReviewedEntryValidation(
              position, inspection, runId, branchId, eventId, head, outcomes,
              operator, reason, `admin-entry-review-${crypto.randomUUID()}`
            ))
            setApproved(false)
          } catch (error) {
            setNotice(formatApiError(error))
          }
        }}>Review entire application batch</button>
      {review && <section aria-label="Confirm entry validation">
        <h4>Confirm frozen entry validation</h4>
        <p>Approve {review.payload.reviews.filter(row => row.outcome === 'valid').length} valid and {review.payload.reviews.filter(row => row.outcome === 'invalid').length} invalid decisions, all from the same Slot fingerprint {review.slotFingerprint.slice(0, 12)}…</p>
        {!reviewedIsCurrent && <p role="alert" className="error">Review expired: Run/Branch/Position, fingerprint or decisions changed.</p>}
        <label><input type="checkbox" checked={approved}
          aria-label="Confirm reviewed application batch"
          onChange={event => setApproved(event.target.checked)}/> Commit exact audited decision batch.</label>
        <button type="button" disabled={!approved || !reviewedIsCurrent || commit.isPending}
          onClick={() => commit.mutate(review)}>
          {commit.isPending ? 'Committing…' : 'Commit reviewed applications'}
        </button>
      </section>}
    </section>}
    {commit.error && <p role="alert" className="error">Application validation failed: {formatApiError(commit.error)}</p>}
    {notice && <p role="status">{notice}</p>}
    <p><Link to={`/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`}>
      Open authoritative Simulation to freeze the Entry decision slot, inspect the next Slot or save the Branch
    </Link></p>
  </SectionCard>
}
