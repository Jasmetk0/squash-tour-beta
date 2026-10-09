import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  confirmRunDerivedInitialRanking, getBranchWorkingDraft, getRankingCandidates,
  getRunOwnedInitialWorld, previewRankingSave, previewRunDerivedInitialRanking,
  saveRunDerivedInitialRankingRevision
} from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import type { RankingPreparationPreview } from '../api/rankingCandidates'
import {
  initialRankingCandidate, type DerivedInitialRankingIntent
} from '../api/runInitialRankingSetup'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type Review = {
  runId: string
  branchId: string
  head: string
  draftVersion: number
  worldKey: string
  bestN: number
  intent: DerivedInitialRankingIntent
  preview: RankingPreparationPreview
}
type WaitingSave = {
  runId: string
  branchId: string
  head: string
  candidateFingerprint: string
}

const sha = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{64}$/.test(value)

export function RunInitialRankingSetupPanel({ run, branch }: {
  run: RunContainer
  branch: RunBranch | null
}): JSX.Element {
  const queryClient = useQueryClient()
  const runId = run.run_id
  const branchId = branch?.run_id === runId ? branch.branch_id : ''
  const head = branch?.run_id === runId ? branch.saved_head_revision_id ?? '' : ''
  const editable = run.storage_kind === 'custom_local' && !run.read_only &&
    ['working', 'active', 'completed'].includes(run.status) &&
    Boolean(branchId && head && branch?.status === 'active' && !branch.read_only)
  const [reason, setReason] = useState('Prepare the first-week ranking candidate from the saved Run-owned player population.')
  const [review, setReview] = useState<Review | null>(null)
  const [approved, setApproved] = useState(false)
  const [waitingSave, setWaitingSave] = useState<WaitingSave | null>(null)
  const [saveApproved, setSaveApproved] = useState(false)
  const [notice, setNotice] = useState('')

  const worldQuery = useQuery({
    queryKey: ['run-owned-initial-world', runId, branchId],
    queryFn: () => getRunOwnedInitialWorld(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const historyQuery = useQuery({
    queryKey: ['ranking-candidates', runId, branchId],
    queryFn: () => getRankingCandidates(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })

  const world = worldQuery.data?.run_id === runId &&
    worldQuery.data.branch_id === branchId ? worldQuery.data : null
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const history = historyQuery.data?.run_id === runId &&
    historyQuery.data.branch_id === branchId ? historyQuery.data : null
  const candidate = initialRankingCandidate(history?.candidates ?? [])
  const bestN = world?.policies.length === 1 ? world.policies[0].best_n : null
  const worldKey = world ? [
    world.adoption_request_fingerprint, world.bootstrap_seed,
    world.world_package_id, world.players.length, bestN
  ].join(':') : ''
  const validWorld = Boolean(world && world.source_kind === 'run_world_generated_pool.v1' &&
    world.season === '2000/2001' && world.players.length > 0 &&
    sha(world.adoption_request_fingerprint) &&
    world.policies.length === 1 && bestN != null && bestN >= 1 &&
    Number.isInteger(bestN))
  const cleanScope = editable && validWorld && draft?.status === 'clean' &&
    draft.base_saved_revision_id === head && historyQuery.isSuccess && Boolean(history)
  const canPreview = cleanScope && !candidate && !waitingSave &&
    reason.trim().length > 0 && reason.trim().length <= 1000

  useEffect(() => {
    setReview(null)
    setApproved(false)
    setWaitingSave(null)
    setSaveApproved(false)
    setNotice('')
  }, [runId, branchId, head, reason])

  const previewAction = useMutation({
    mutationFn: async (): Promise<Review> => {
      if (!canPreview || !draft || bestN == null)
        throw new Error('Save the Run-owned InitialWorld before preparing the initial ranking.')
      const intent: DerivedInitialRankingIntent = {
        command_id: `run-initial-ranking-${crypto.randomUUID()}`,
        audit: {
          actor_label: 'Run Admin initial ranking',
          reason: reason.trim()
        }
      }
      const preview = await previewRunDerivedInitialRanking(runId, branchId, intent, bestN)
      return {
        runId, branchId, head, draftVersion: draft.draft_version,
        worldKey, bestN, intent, preview
      }
    },
    onSuccess: value => { setReview(value); setApproved(false); setNotice('') }
  })

  const reviewReady = Boolean(review && editable && !candidate && draft &&
    draft.status === 'clean' && draft.base_saved_revision_id === head &&
    draft.draft_version === review.draftVersion &&
    review.runId === runId && review.branchId === branchId &&
    review.head === head && review.worldKey === worldKey &&
    review.bestN === bestN && review.intent.audit.reason === reason.trim() &&
    !historyQuery.isFetching && !worldQuery.isFetching && !draftQuery.isFetching)

  const confirmAction = useMutation({
    mutationFn: async (current: Review) => {
      const confirmed = await confirmRunDerivedInitialRanking(
        current.runId, current.branchId, current.intent, current.preview, current.bestN
      )
      return { current, confirmed }
    },
    onSuccess: async ({ current, confirmed }) => {
      setReview(null)
      setApproved(false)
      setWaitingSave({
        runId: current.runId, branchId: current.branchId,
        head: current.head, candidateFingerprint: confirmed.fingerprint
      })
      setNotice('The derived Week-1 candidate was prepared. It is not saved or published yet.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', current.runId, current.branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', current.runId, current.branchId] })
      ])
    },
    onError: () => {
      setReview(null); setApproved(false)
      setNotice('Ranking preparation was not verified. Refresh the current Branch and review a new preview.')
      void queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] })
    }
  })

  const savePreviewQuery = useQuery({
    queryKey: ['ranking-save', runId, branchId, draft?.draft_version, candidate?.fingerprint],
    queryFn: () => previewRankingSave(runId, branchId),
    enabled: Boolean(editable && candidate && draft && draft.base_saved_revision_id === head),
    retry: false
  })
  const savePreview = savePreviewQuery.data
  const saveMatches = Boolean(editable && draft && candidate &&
    draft.base_saved_revision_id === head && (draft.status === 'dirty' || draft.status === 'clean') &&
    savePreview && savePreview.run_id === runId &&
    savePreview.branch_id === branchId && savePreview.saved_head_revision_id === head &&
    savePreview.draft_version === draft.draft_version &&
    savePreview.has_unsaved_changes === true && savePreview.can_save === true &&
    sha(savePreview.ranking_fingerprint) &&
    !draftQuery.isFetching && !historyQuery.isFetching && !savePreviewQuery.isFetching)
  const canResume = Boolean(!waitingSave && saveMatches)
  const canSave = Boolean(waitingSave && saveMatches &&
    waitingSave.runId === runId && waitingSave.branchId === branchId &&
    waitingSave.head === head && candidate?.fingerprint === waitingSave.candidateFingerprint)

  const saveAction = useMutation({
    mutationFn: async () => {
      if (!canSave || !savePreview) throw new Error('Current ranking Save preflight is missing or stale.')
      return saveRunDerivedInitialRankingRevision(
        runId, branchId, savePreview.draft_version, savePreview.ranking_fingerprint
      )
    },
    onSuccess: async () => {
      setWaitingSave(null); setSaveApproved(false)
      setNotice('The initial ranking candidate is saved in immutable Branch history, but it has not been published to Viewer.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['ranking-candidates', runId, branchId] })
      ])
    },
    onError: () => { setSaveApproved(false); void savePreviewQuery.refetch() }
  })

  return <SectionCard title="Prepare initial ranking">
    <p className="status">Compute the 2000/01 Week-1 ranking candidate from the saved Run-owned InitialWorld. The backend derives the complete roster, first-season Best N policy and tie-break identities. No historical tournament points are invented.</p>
    {worldQuery.error && !isApiNotFound(worldQuery.error) &&
      <p role="alert" className="error">InitialWorld unavailable: {formatApiError(worldQuery.error)}</p>}
    {historyQuery.error && <p role="alert" className="error">Ranking history unavailable: {formatApiError(historyQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {!world && isApiNotFound(worldQuery.error) && <p>First generate, adopt and save players in the InitialWorld section above.</p>}
    {world && <p>Run-owned roster: <strong>{world.players.length}</strong> players · Initial policy: Best {bestN ?? 'unavailable'}.</p>}
    {candidate && <p role="status">Week-1 ranking candidate exists. It contains {candidate.snapshot.rows.length} classified rows. {savePreview?.has_unsaved_changes ? 'It needs Saved Revision confirmation.' : 'Review the ranking Save preflight for persistence status.'}</p>}
    {candidate && candidate.snapshot.rows.length === 0 &&
      <p className="status">Zero classified players is expected at the Week-1 bootstrap before sporting results. All players remain in InitialWorld.</p>}
    {draft && draft.status !== 'clean' && !waitingSave && !candidate &&
      <p className="status">The current Working Draft is dirty. Save it before preparing the ranking.</p>}
    <label>Audit reason <input aria-label="Initial ranking audit reason" maxLength={1000}
      value={reason} onChange={event => setReason(event.target.value)} /></label>
    <button type="button" disabled={!canPreview || previewAction.isPending ||
      confirmAction.isPending || saveAction.isPending}
      onClick={() => { setReview(null); setApproved(false); previewAction.mutate() }}>
      {previewAction.isPending ? 'Deriving Week-1 preview…' : 'Preview initial ranking'}
    </button>
    {previewAction.error && <p role="alert" className="error">Ranking preview failed: {formatApiError(previewAction.error)}</p>}
    {review && <section aria-label="Review initial ranking">
      <h4>Review Week-1 ranking candidate</h4>
      <p>InitialWorld players: {world?.players.length ?? '—'} · Best {review.bestN} · Classified rows: {review.preview.candidate.snapshot.rows.length}</p>
      <p className="status">This creates an unpublished ranking candidate and records source/audit provenance. It does not advance the calendar or make up historical results.</p>
      {!reviewReady && <p role="alert" className="error">The Run, Branch, Saved Revision, World or Working Draft changed. Preview again.</p>}
      <label><input type="checkbox" aria-label="Approve initial ranking preparation" checked={approved}
        onChange={event => setApproved(event.target.checked)} /> I reviewed this candidate and want to prepare it in this Branch.</label>
      <button type="button" disabled={!reviewReady || !approved || confirmAction.isPending}
        onClick={() => review && confirmAction.mutate(review)}>
        {confirmAction.isPending ? 'Preparing ranking…' : 'Confirm initial ranking'}
      </button>
    </section>}
    {confirmAction.error && <p role="alert" className="error">Ranking confirmation failed: {formatApiError(confirmAction.error)}</p>}
    {canResume && <section aria-label="Recover ranking save">
      <p>A prepared Week-1 ranking exists in an unsaved Working Draft. You can review its Save without deriving another ranking.</p>
      <button type="button" onClick={() => candidate && setWaitingSave({
        runId, branchId, head, candidateFingerprint: candidate.fingerprint
      })}>Review existing ranking save</button>
    </section>}
    {waitingSave && <section aria-label="Save initial ranking">
      <p>Ranking preparation is not yet a Saved Revision. Saving preserves the candidate, but does not publish it to Viewer.</p>
      {savePreviewQuery.error && <p role="alert" className="error">Ranking Save preflight failed: {formatApiError(savePreviewQuery.error)}</p>}
      {!canSave && !savePreviewQuery.isLoading &&
        <p role="alert" className="error">Ranking, Saved head or Working Draft no longer matches the reviewed candidate. Refresh to recover safely.</p>}
      <label><input type="checkbox" aria-label="Approve initial ranking save" checked={saveApproved}
        onChange={event => setSaveApproved(event.target.checked)} /> Create a Saved Revision with the prepared initial ranking.</label>
      <button type="button" disabled={!canSave || !saveApproved || saveAction.isPending}
        onClick={() => saveAction.mutate()}>
        {saveAction.isPending ? 'Saving ranking revision…' : 'Save initial ranking revision'}
      </button>
    </section>}
    {saveAction.error && <p role="alert" className="error">Ranking Save failed: {formatApiError(saveAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
  </SectionCard>
}
