import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  getBranchWorkingDraft, getRankingCandidates, getViewerOfficialRanking,
  previewRankingSave, publishRunInitialRanking,
  saveRunDerivedInitialRankingRevision
} from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import { initialRankingCandidate } from '../api/runInitialRankingSetup'
import {
  validWeekOnePublicationCandidate, verifiedViewerInitialRanking
} from '../api/runInitialRankingPublication'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type PublicationReview = {
  runId: string
  branchId: string
  head: string
  draftVersion: number
  fingerprint: string
  viewerBranchId: string | null
}
type PublicationSaveReview = PublicationReview & {
  rankingStateFingerprint: string
}

const validFingerprint = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

/**
 * Initial publication has two durable boundaries:
 *  1. POST /publish-initial establishes the authoritative publication;
 *  2. POST /ranking-candidates/save commits that publication to Saved Revision,
 *     which is what the Viewer read model actually displays.
 */
export function RunInitialRankingPublicationPanel({ run, branch }: {
  run: RunContainer
  branch: RunBranch | null
}): JSX.Element {
  const queryClient = useQueryClient()
  const runId = run.run_id
  const branchId = branch?.run_id === runId ? branch.branch_id : ''
  const head = branch?.run_id === runId ? branch.saved_head_revision_id ?? '' : ''
  const viewerBranchId = run.official_branch_id ?? null
  const isViewerBranch = Boolean(branchId && viewerBranchId === branchId)
  const writable = run.storage_kind === 'custom_local' && !run.read_only &&
    ['working', 'active', 'completed'].includes(run.status) &&
    Boolean(branchId && head && branch?.status === 'active' && !branch.read_only)

  const [publicationReview, setPublicationReview] = useState<PublicationReview | null>(null)
  const [publicationApproved, setPublicationApproved] = useState(false)
  const [publishedHere, setPublishedHere] = useState<string | null>(null)
  const [saveReview, setSaveReview] = useState<PublicationSaveReview | null>(null)
  const [saveApproved, setSaveApproved] = useState(false)
  const [notice, setNotice] = useState('')

  const historyQuery = useQuery({
    queryKey: ['ranking-candidates', runId, branchId],
    queryFn: () => getRankingCandidates(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const history = historyQuery.data?.run_id === runId && historyQuery.data.branch_id === branchId
    ? historyQuery.data : null
  const draft = draftQuery.data?.run_id === runId && draftQuery.data.branch_id === branchId
    ? draftQuery.data : null
  const candidate = initialRankingCandidate(history?.candidates ?? [])
  const candidateValid = validWeekOnePublicationCandidate(candidate, runId, branchId) &&
    history?.candidates.length === 1
  const savePreviewQuery = useQuery({
    queryKey: ['ranking-publication-save', runId, branchId, draft?.draft_version, candidate?.fingerprint, publishedHere],
    queryFn: () => previewRankingSave(runId, branchId),
    enabled: Boolean(writable && candidateValid && draft?.base_saved_revision_id === head),
    retry: false
  })
  const preflight = savePreviewQuery.data
  const scopeValid = Boolean(writable && candidateValid && draft &&
    draft.base_saved_revision_id === head && draft.status === 'clean' &&
    !historyQuery.isFetching && !draftQuery.isFetching && !savePreviewQuery.isFetching &&
    preflight && preflight.run_id === runId && preflight.branch_id === branchId &&
    preflight.saved_head_revision_id === head && preflight.draft_version === draft.draft_version &&
    validFingerprint(preflight.ranking_fingerprint))
  const preparedIsSaved = scopeValid && preflight?.has_unsaved_changes === false
  const needsSave = scopeValid && preflight?.has_unsaved_changes === true &&
    preflight.can_save === true
  const viewerQuery = useQuery({
    queryKey: ['viewer-current-official-ranking', runId],
    queryFn: () => getViewerOfficialRanking(runId),
    enabled: isViewerBranch,
    retry: false
  })
  const viewerVerified = Boolean(isViewerBranch && candidate &&
    verifiedViewerInitialRanking(viewerQuery.data, runId, branchId, candidate.fingerprint))

  useEffect(() => {
    setPublicationReview(null)
    setPublicationApproved(false)
    setPublishedHere(null)
    setSaveReview(null)
    setSaveApproved(false)
    setNotice('')
  }, [runId, branchId, head, viewerBranchId])

  const canPublish = Boolean(preparedIsSaved && !viewerVerified &&
    !publishedHere && !saveReview && !viewerQuery.isFetching)
  const reviewReady = Boolean(publicationReview && canPublish &&
    publicationReview.runId === runId &&
    publicationReview.branchId === branchId &&
    publicationReview.head === head &&
    publicationReview.draftVersion === draft?.draft_version &&
    publicationReview.fingerprint === candidate?.fingerprint &&
    publicationReview.viewerBranchId === viewerBranchId)

  const publishAction = useMutation({
    mutationFn: async (review: PublicationReview) =>
      publishRunInitialRanking(review.runId, review.branchId, review.fingerprint),
    onSuccess: async (result) => {
      setPublicationReview(null)
      setPublicationApproved(false)
      setPublishedHere(result.ranking_fingerprint)
      setNotice(result.exact_retry
        ? 'Existing identical live publication verified. A Saved Revision may still be needed for Viewer.'
        : 'Initial ranking published to the live World state. Now save that publication as a Saved Revision for Viewer.')
      await queryClient.invalidateQueries({ queryKey: ['ranking-publication-save', runId, branchId] })
    },
    onError: () => {
      setPublicationReview(null)
      setPublicationApproved(false)
      setNotice('Publication result is not verified. Refresh authoritative ranking state before retrying.')
      void queryClient.invalidateQueries({ queryKey: ['ranking-publication-save', runId, branchId] })
    }
  })

  const canReviewSave = Boolean(needsSave && candidate &&
    (publishedHere === candidate.fingerprint || !publishedHere))
  const saveReady = Boolean(saveReview && needsSave && candidate &&
    saveReview.runId === runId &&
    saveReview.branchId === branchId &&
    saveReview.head === head &&
    saveReview.draftVersion === draft?.draft_version &&
    saveReview.viewerBranchId === viewerBranchId &&
    saveReview.fingerprint === candidate.fingerprint &&
    saveReview.rankingStateFingerprint === preflight?.ranking_fingerprint)

  const saveAction = useMutation({
    mutationFn: async (review: PublicationSaveReview) =>
      saveRunDerivedInitialRankingRevision(
        review.runId, review.branchId, review.draftVersion, review.rankingStateFingerprint
      ),
    onSuccess: async () => {
      setSaveReview(null)
      setSaveApproved(false)
      setPublishedHere(null)
      setNotice(isViewerBranch
        ? 'Saved Revision created. Verify below that Viewer now reads the published Week-1 ranking.'
        : 'Saved Revision created. This Branch is not the Viewer Branch; selecting it for Viewer requires a separate reviewed Save.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-publication-save', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['viewer-current-official-ranking', runId] })
      ])
    },
    onError: () => {
      setSaveApproved(false)
      void savePreviewQuery.refetch()
    }
  })

  return <SectionCard title="Publish initial ranking">
    <p className="status">Publishing and making a ranking visible are separate operations. Publish records the Week-1 authoritative World head. A subsequent Saved Revision makes it available to the Viewer read model on the selected Viewer Branch.</p>
    {historyQuery.error && <p role="alert" className="error">Cannot verify ranking candidate: {formatApiError(historyQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Cannot verify Working Draft: {formatApiError(draftQuery.error)}</p>}
    {savePreviewQuery.error && <p role="alert" className="error">Ranking publication preflight unavailable: {formatApiError(savePreviewQuery.error)}</p>}
    {!candidate && <p>First prepare and save the derived initial ranking in the section above.</p>}
    {candidate && <p>Week 1 · Best {candidate.snapshot.policy.best_n} · {candidate.snapshot.rows.length} classified rows · Fingerprint <code>{candidate.fingerprint.slice(0, 12)}…</code></p>}
    {candidate && !candidateValid && <p role="alert" className="error">Publication requires exactly one validated Week-1 ranking candidate in this Branch.</p>}
    <p>Viewer Branch: {isViewerBranch ? 'This Branch' : viewerBranchId ? 'Different Branch — this publication will not yet appear in Viewer' : 'Not selected'}</p>
    {candidateValid && preflight && <p className="status">Save state: {preflight.has_unsaved_changes
      ? 'Ranking state differs from its latest Saved Revision.'
      : 'Ranking state matches its latest Saved Revision.'}</p>}
    {viewerVerified && <p role="status">Viewer readback verified: correct Product Run, Viewer Branch, Week 1 and published candidate fingerprint. Ranking rows: {viewerQuery.data?.row_count}.</p>}
    {isViewerBranch && viewerQuery.error && !isApiNotFound(viewerQuery.error) && !viewerVerified &&
      <p className="status">Viewer has no verified saved publication yet: {formatApiError(viewerQuery.error)}</p>}

    <button type="button" disabled={!canPublish || publishAction.isPending || saveAction.isPending}
      onClick={() => {
        if (!candidate || !draft) return
        setPublicationReview({ runId, branchId, head,
          draftVersion: draft.draft_version, fingerprint: candidate.fingerprint, viewerBranchId })
        setPublicationApproved(false)
      }}>
      Review initial publication
    </button>
    {publicationReview && <section aria-label="Review initial publication">
      <h4>Confirm first public Week-1 head</h4>
      <p>This operation changes authoritative World state on this Branch, but does not itself create the Viewer-visible Saved Revision.</p>
      {!reviewReady && <p role="alert" className="error">The saved ranking, Branch or publication preflight changed. Refresh and review again.</p>}
      <label><input type="checkbox" checked={publicationApproved}
        aria-label="Approve initial publication"
        onChange={event => setPublicationApproved(event.target.checked)} />
        Publish this exact Week-1 ranking candidate.</label>
      <button type="button" disabled={!reviewReady || !publicationApproved || publishAction.isPending}
        onClick={() => publicationReview && publishAction.mutate(publicationReview)}>
        {publishAction.isPending ? 'Publishing…' : 'Publish initial ranking'}
      </button>
    </section>}
    {publishAction.error && <p role="alert" className="error">Publication failed: {formatApiError(publishAction.error)}</p>}

    {canReviewSave && <button type="button" disabled={saveAction.isPending}
      onClick={() => {
        if (!candidate || !draft || !preflight) return
        setSaveReview({runId, branchId, head, draftVersion: draft.draft_version,
          fingerprint: candidate.fingerprint, rankingStateFingerprint: preflight.ranking_fingerprint,
          viewerBranchId})
        setSaveApproved(false)
      }}>Review unsaved published ranking state</button>}
    {needsSave && !publishedHere && <p className="status">The persisted ranking component has unsaved changes. If a previous publication response was lost or the page was reopened, review and save this exact state. A publication is not claimed until Viewer readback verifies it.</p>}
    {saveReview && <section aria-label="Save published ranking revision">
      <h4>Save public ranking in Branch history</h4>
      <p>Saving captures the current ranking World head into the immutable Saved Revision. Viewer reads that saved revision on the selected Viewer Branch.</p>
      {!saveReady && <p role="alert" className="error">Ranking state, fingerprint or Draft changed. Refresh the save review.</p>}
      <label><input type="checkbox" checked={saveApproved}
        aria-label="Approve published ranking revision save"
        onChange={event => setSaveApproved(event.target.checked)} />
        Save this reviewed authoritative ranking state.</label>
      <button type="button" disabled={!saveReady || !saveApproved || saveAction.isPending}
        onClick={() => saveReview && saveAction.mutate(saveReview)}>
        {saveAction.isPending ? 'Saving publication…' : 'Save published ranking revision'}
      </button>
    </section>}
    {saveAction.error && <p role="alert" className="error">Publication Save failed: {formatApiError(saveAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
  </SectionCard>
}
