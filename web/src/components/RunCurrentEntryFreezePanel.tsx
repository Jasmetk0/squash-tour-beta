import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  applyRunCurrentEntryDecisions, getAuthoritativeSimulationPosition,
  getBranchWorkingDraft, getRunContainer, listRunBranches,
  previewRunCurrentEntryDecisions
} from '../api/client'
import { verifiedCurrentEntryPreview, type CurrentEntryDecisionPreview } from '../api/runCurrentEntryFreeze'
import { formatApiError } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type Review = {
  runId: string
  branchId: string
  eventId: string
  head: string
  draftVersion: number
  positionFingerprint: string
  preview: CurrentEntryDecisionPreview
  commandId: string
}

export function RunCurrentEntryFreezePanel({ runId, branchId, eventId }: {
  runId: string; branchId: string; eventId: string
}): JSX.Element {
  const queryClient = useQueryClient()
  const [review, setReview] = useState<Review | null>(null)
  const [approved, setApproved] = useState(false)
  const [notice, setNotice] = useState('')

  const runQuery = useQuery({
    queryKey: ['admin-run-container', runId],
    queryFn: () => getRunContainer(runId), retry: false
  })
  const branchesQuery = useQuery({
    queryKey: ['admin-run-branches', runId],
    queryFn: () => listRunBranches(runId), retry: false
  })
  const branch = branchesQuery.data?.run_branches.find(item =>
    item.run_id === runId && item.branch_id === branchId)
  const head = branch?.saved_head_revision_id ?? ''
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId), retry: false
  })
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data?.branch_id === branchId ? draftQuery.data : null
  const editable = Boolean(runQuery.data?.run_id === runId &&
    runQuery.data.storage_kind === 'custom_local' && !runQuery.data.read_only &&
    branch?.status === 'active' && !branch.read_only && head &&
    draft?.status === 'clean' && draft.base_saved_revision_id === head)

  const positionQuery = useQuery({
    queryKey: ['authoritative-simulation-position', runId, branchId],
    queryFn: () => getAuthoritativeSimulationPosition(runId, branchId),
    enabled: editable, retry: false
  })
  const position = positionQuery.data?.run_id === runId &&
    positionQuery.data.branch_id === branchId ? positionQuery.data : null
  const entryReady = Boolean(editable && position?.current_slot_kind === 'entry' &&
    position.slot_ordinal != null && position.slot_ordinal >= 1)
  const scopeFetching = runQuery.isFetching || branchesQuery.isFetching ||
    draftQuery.isFetching || positionQuery.isFetching

  useEffect(() => {
    setReview(null)
    setApproved(false)
    setNotice('')
  }, [runId, branchId, eventId, head, draft?.draft_version, position?.position_fingerprint])

  const previewAction = useMutation({
    mutationFn: async (): Promise<Review> => {
      if (!entryReady || !position || !draft || scopeFetching)
        throw new Error('A current writable Entry slot and saved Branch are required.')
      const preview = await previewRunCurrentEntryDecisions(runId, branchId)
      if (!verifiedCurrentEntryPreview(preview, position, runId, branchId, eventId, head))
        throw new Error('The server Entry preview does not match this Run, Branch, current Week, Saved Revision or Event.')
      if (preview.persisted || preview.decision_count === 0)
        throw new Error(preview.persisted
          ? 'The Entry decision slot is already frozen. Review its real decisions below.'
          : 'The actual Entry generator proposed no applications. Nothing can be committed as a populated Entry slot.')
      return {
        runId, branchId, eventId, head, draftVersion: draft.draft_version,
        positionFingerprint: position.position_fingerprint,
        preview, commandId: `admin-entry-freeze-${crypto.randomUUID()}`
      }
    },
    onSuccess: value => {
      setReview(value)
      setApproved(false)
      setNotice('')
    },
    onError: () => { setReview(null); setApproved(false) }
  })
  const reviewReady = Boolean(review && entryReady && !scopeFetching &&
    review.runId === runId && review.branchId === branchId &&
    review.eventId === eventId && review.head === head &&
    review.draftVersion === draft?.draft_version &&
    review.positionFingerprint === position?.position_fingerprint &&
    verifiedCurrentEntryPreview(review.preview, position, runId, branchId, eventId, head) &&
    !review.preview.persisted && review.preview.decision_count > 0)

  const applyAction = useMutation({
    mutationFn: (current: Review) =>
      applyRunCurrentEntryDecisions(current.runId, current.branchId, current.preview, current.commandId),
    onSuccess: async data => {
      setReview(null)
      setApproved(false)
      setNotice(`Frozen ${data.decision_count} real Entry decisions in the shared Week ${data.current_week.week} Slot ${data.decision_slot_ordinal}. Automatic eligibility remains unresolved; review every application below.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['authoritative-entry-decision-slot', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['canonical-tournament-preparation', runId, branchId] })
      ])
    },
    onError: async () => {
      setReview(null)
      setApproved(false)
      await queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-position', runId, branchId] })
    }
  })

  return <SectionCard title="Generate tournament Entry decisions">
    <p className="status">Preview production Entry AI decisions derived from the Run-owned player roster, sporting and country snapshots, and current-week Calendar. All concurrent World Tour tournaments share one deterministic Entry snapshot. Nothing is accepted as a valid submission until a separate explicit validation.</p>
    {!editable && <p role="status">Select an active writable Product Run Branch with a clean saved Working Draft.</p>}
    {runQuery.error && <p role="alert" className="error">Run unavailable: {formatApiError(runQuery.error)}</p>}
    {branchesQuery.error && <p role="alert" className="error">Branches unavailable: {formatApiError(branchesQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {positionQuery.error && <p role="alert" className="error">Authoritative current position unavailable: {formatApiError(positionQuery.error)}</p>}
    {position && position.current_slot_kind !== 'entry' && <p role="status">Current simulation position is not an Entry slot. Nothing will be generated for this Event.</p>}
    {position?.current_slot_kind === 'entry' &&
      <p>Authoritative Week {position.current_week.week} · Slot {position.slot_ordinal}. Generation uses the backend's fixed reviewed seed 12345.</p>}
    <button type="button" disabled={!entryReady || scopeFetching || previewAction.isPending || applyAction.isPending}
      onClick={() => { setReview(null); setApproved(false); previewAction.mutate() }}>
      {previewAction.isPending ? 'Generating Entry preview…' : 'Preview real Entry decisions'}
    </button>
    {previewAction.error && <p role="alert" className="error">Entry preview blocked: {formatApiError(previewAction.error)}</p>}
    {review && <section aria-label="Review frozen Entry proposal">
      <h4>Review shared Entry decision slot</h4>
      <p><strong>{review.preview.decision_count}</strong> generated player decisions, {review.preview.event_ids.length} World Tour event(s) in Week {review.preview.current_week.week}.</p>
      <p>Events: {review.preview.event_ids.join(', ')}.</p>
      <p>Generation fingerprint: <code>{review.preview.entry_batch_fingerprint.slice(0, 16)}…</code> · Slot fingerprint: <code>{review.preview.slot_fingerprint.slice(0, 16)}…</code>.</p>
      <p className="status">Confirming will freeze the full current shared Slot. The backend re-runs the same deterministic proposal and refuses any changed fingerprints, Saved Revision or position. This does not approve applications, build the draw, or advance simulation.</p>
      {!reviewReady && <p role="alert" className="error">The reviewed preview is stale. Generate a new one.</p>}
      <label><input type="checkbox" checked={approved}
        aria-label="Approve frozen Entry generation"
        onChange={value => setApproved(value.target.checked)} />
        Freeze exactly this Run-owned Entry proposal.</label>
      <button type="button" disabled={!reviewReady || !approved || applyAction.isPending}
        onClick={() => review && applyAction.mutate(review)}>
        {applyAction.isPending ? 'Freezing Entry slot…' : 'Confirm and freeze Entry decisions'}
      </button>
    </section>}
    {applyAction.error && <p role="alert" className="error">Entry freeze failed: {formatApiError(applyAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
    <p><Link to={`/admin/runs/${encodeURIComponent(runId)}/simulate?branch=${encodeURIComponent(branchId)}`}>
      Inspect authoritative simulation position and pending Entry policy
    </Link></p>
  </SectionCard>
}
