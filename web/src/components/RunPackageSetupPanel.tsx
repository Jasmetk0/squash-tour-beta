import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  confirmRunSourcePackage, getBranchWorkingDraft, getRunPackageState,
  listWorldPackages, previewRunSourcePackage, saveRunPackageWorkingDraft
} from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import {
  reviewedSourcePackage, type RunSourcePackageKind, type RunSourcePackagePreview
} from '../api/runPackageSetup'
import { formatApiError } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type Review = {
  runId: string
  branchId: string
  kind: RunSourcePackageKind
  sourceId: string
  preview: RunSourcePackagePreview
}

type PendingSave = {
  runId: string
  branchId: string
  draftVersion: number
  fingerprint: string
  previousHead: string
}

function seasonKey(value: string): boolean {
  return /^\d{4}-\d{4}$/.test(value)
}

export function RunPackageSetupPanel({ run, branch }: {
  run: RunContainer
  branch: RunBranch | null
}): JSX.Element {
  const queryClient = useQueryClient()
  const runId = run.run_id
  const branchId = branch?.run_id === runId ? branch.branch_id : ''
  const head = branch?.run_id === runId ? branch.saved_head_revision_id : null
  const editable = !run.read_only && run.storage_kind === 'custom_local' &&
    (run.status === 'working' || run.status === 'active' || run.status === 'completed') &&
    Boolean(branchId && branch?.status === 'active' && !branch.read_only && head)
  const [kind, setKind] = useState<RunSourcePackageKind>('world')
  const [worldId, setWorldId] = useState('')
  const [calendarSeason, setCalendarSeason] = useState('2000-2001')
  const [review, setReview] = useState<Review | null>(null)
  const [approved, setApproved] = useState(false)
  const [pendingSave, setPendingSave] = useState<PendingSave | null>(null)
  const [saveApproved, setSaveApproved] = useState(false)
  const [notice, setNotice] = useState('')

  useEffect(() => {
    setReview(null)
    setPendingSave(null)
    setApproved(false)
    setSaveApproved(false)
    setNotice('')
  }, [runId, branchId, head, kind, worldId, calendarSeason])

  const worldQuery = useQuery({
    queryKey: ['admin-world-packages'],
    queryFn: listWorldPackages,
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const packageQuery = useQuery({
    queryKey: ['run-package-state', runId, branchId],
    queryFn: () => getRunPackageState(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const candidates = (worldQuery.data?.packages ?? []).filter(pkg => pkg.status === 'active')
  const sourceId = kind === 'world' ? (worldId || candidates[0]?.world_id || '') : calendarSeason.trim()
  const validSource = kind === 'world'
    ? candidates.some(pkg => pkg.world_id === sourceId)
    : seasonKey(sourceId)
  const currentDraft = draftQuery.data?.run_id === runId && draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const currentState = packageQuery.isSuccess ? packageQuery.data : null
  const reviewMatches = Boolean(review && review.runId === runId && review.branchId === branchId &&
    review.kind === kind && review.sourceId === sourceId &&
    review.preview.saved_head_revision_id === head &&
    currentDraft && currentDraft.base_saved_revision_id === head &&
    currentDraft.draft_version === review.preview.draft_version &&
    currentState && currentState.fingerprint === review.preview.current_state_fingerprint)
  const blockedPreview = review && (review.preview.conflicts.length > 0 || review.preview.invalid.length > 0)
  const readyToConfirm = editable && validSource && reviewMatches && !blockedPreview && approved && !pendingSave

  const previewAction = useMutation({
    mutationFn: async (input: { runId: string; branchId: string; kind: RunSourcePackageKind; sourceId: string }) => {
      const preview = await previewRunSourcePackage(input.runId, input.branchId, input.kind, input.sourceId)
      if (!reviewedSourcePackage(preview, input.runId, input.branchId, input.kind, input.sourceId)) {
        throw new Error('Source preview identity or contract is invalid. No changes were applied.')
      }
      return { ...input, preview }
    },
    onSuccess: result => {
      setReview(result)
      setApproved(false)
    }
  })

  const confirmAction = useMutation({
    mutationFn: async (current: Review) => {
      const response = await confirmRunSourcePackage(current.runId, current.branchId, current.kind, current.sourceId, {
        command_id: `admin-source-${crypto.randomUUID()}`,
        expected_head_revision_id: current.preview.saved_head_revision_id,
        expected_draft_version: current.preview.draft_version,
        expected_state_fingerprint: current.preview.current_state_fingerprint,
        expected_preview_fingerprint: current.preview.preview_fingerprint,
        conflict_resolutions: {}
      })
      if (!response.state || response.state.run_id !== current.runId ||
          response.state.branch_id !== current.branchId || !response.state_fingerprint ||
          !Number.isInteger(response.draft_version) || response.draft_version < current.preview.draft_version) {
        throw new Error('Source confirm returned an unexpected Run/Branch state; inspect authoritative state before continuing.')
      }
      return { current, response }
    },
    onSuccess: async ({ current, response }) => {
      setReview(null)
      setApproved(false)
      setSaveApproved(false)
      setPendingSave(response.draft_version > current.preview.draft_version ? {
        runId: current.runId, branchId: current.branchId,
        draftVersion: response.draft_version, fingerprint: response.state_fingerprint!,
        previousHead: current.preview.saved_head_revision_id
      } : null)
      setNotice(response.draft_version > current.preview.draft_version
        ? 'Source content applied to the Working Draft. Save a new revision to make it recoverable.'
        : 'Source already matched the Working Draft; nothing new to save.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-package-state', current.runId, current.branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', current.runId, current.branchId] })
      ])
    },
    onError: () => { setApproved(false); setReview(null); setNotice('Confirm failed. Refresh and preview the source again; nothing was claimed as saved.') }
  })
  const saveReady = Boolean(pendingSave && pendingSave.runId === runId && pendingSave.branchId === branchId &&
    head === pendingSave.previousHead && currentDraft &&
    currentDraft.base_saved_revision_id === pendingSave.previousHead &&
    currentDraft.draft_version === pendingSave.draftVersion &&
    currentDraft.status === 'dirty' && currentState &&
    currentState.fingerprint === pendingSave.fingerprint)

  const saveAction = useMutation({
    mutationFn: async (pending: PendingSave) => {
      const result = await saveRunPackageWorkingDraft(pending.runId, pending.branchId, pending.draftVersion)
      if (result.run_id !== pending.runId || result.branch_id !== pending.branchId ||
          result.working_draft.run_id !== pending.runId ||
          result.working_draft.branch_id !== pending.branchId ||
          result.working_draft.status !== 'clean' ||
          !result.saved_revision.revision_id ||
          result.working_draft.base_saved_revision_id !== result.saved_revision.revision_id) {
        throw new Error('Save response did not verify the requested Run, Branch and clean revision.')
      }
      return result
    },
    onSuccess: async saved => {
      setPendingSave(null)
      setSaveApproved(false)
      setNotice('Saved Revision created. Reopen this Run to inspect the same independent Package snapshot.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-package-state', runId, branchId] })
      ])
      if (saved.run_id !== runId || saved.branch_id !== branchId) setNotice('Saved another Run/Branch; refresh the current context.')
    }
  })

  return <SectionCard title="World and Calendar copies">
    <p className="status">Use the existing Run/Branch Package authority. Preview is read-only, Confirm copies independent content to the Working Draft, and Save creates an immutable Saved Revision. Nothing is applied to the global source.</p>
    <p>Target: <strong>{run.display_name ?? 'Product Run'}</strong> · {branch?.display_name ?? 'No active timeline'}.</p>
    {!editable && <p role="alert" className="error">Select a writable Active Admin Branch with a Saved Revision. Protected Runs cannot import packages.</p>}
    <label>Source kind{' '}
      <select aria-label="Source kind" value={kind} onChange={event => setKind(event.target.value as RunSourcePackageKind)}>
        <option value="world">World</option>
        <option value="calendar">Calendar</option>
      </select>
    </label>
    {kind === 'world' ? <label>World source{' '}
      <select aria-label="World source" value={sourceId} onChange={event => setWorldId(event.target.value)}>
        {candidates.map(pkg => <option value={pkg.world_id} key={pkg.world_id}>{pkg.name}</option>)}
      </select>
    </label> : <label>Calendar source season (YYYY-YYYY){' '}
      <input aria-label="Calendar source season" value={calendarSeason}
        onChange={event => setCalendarSeason(event.target.value)} />
    </label>}
    {kind === 'world' && worldQuery.isError && <p role="alert" className="error">World sources unavailable: {formatApiError(worldQuery.error)}</p>}
    {(draftQuery.isError || packageQuery.isError) &&
      <p role="alert" className="error">Package state or Working Draft unavailable: {formatApiError(draftQuery.error ?? packageQuery.error)}</p>}
    <p className="status">Current Run copy: {currentState?.state ? 'Present' : 'Empty'}. Draft: {currentDraft?.status ?? 'Not verified'}.</p>
    <button type="button" disabled={!editable || !validSource || !currentDraft || !currentState ||
      previewAction.isPending || confirmAction.isPending || saveAction.isPending || Boolean(pendingSave)}
      onClick={() => {
        setReview(null); setApproved(false); setNotice('')
        previewAction.mutate({ runId, branchId, kind, sourceId })
      }}>
      {previewAction.isPending ? 'Loading source preview…' : 'Preview copy'}
    </button>
    {previewAction.error && <p role="alert" className="error">Preview failed: {formatApiError(previewAction.error)}</p>}
    {review && <section aria-label="Source copy review">
      <h4>Review proposed {review.kind} copy</h4>
      <p>New: {review.preview.additions.length} · Updated: {review.preview.updates.length} · Unchanged: {review.preview.unchanged.length} · Omitted from source: {review.preview.not_included.length}</p>
      {review.preview.unresolved.length > 0 && <p className="status">Unresolved source references: {review.preview.unresolved.length}. They are preserved as unresolved; review dependent content before simulation.</p>}
      {(review.preview.invalid.length > 0 || review.preview.conflicts.length > 0) &&
        <p role="alert" className="error">Copy blocked: {review.preview.invalid.length} invalid entities and {review.preview.conflicts.length} conflicts. Use source review or a later explicit conflict resolution; automatic overwrite is disabled.</p>}
      {!reviewMatches && <p role="alert" className="error">Preview is stale or does not match the current Run/Branch Working Draft. Refresh the preview.</p>}
      <label><input type="checkbox" aria-label="Confirm source copy" checked={approved} onChange={event => setApproved(event.target.checked)} /> I reviewed this copy and understand it changes only this Working Draft.</label>
      <button type="button" disabled={!readyToConfirm || confirmAction.isPending || previewAction.isPending}
        onClick={() => review && confirmAction.mutate(review)}>
        {confirmAction.isPending ? 'Applying reviewed copy…' : 'Confirm copy to Working Draft'}
      </button>
      <details><summary>Technical source and preview identifiers</summary><p>Package: {review.preview.document.package_id} · v{review.preview.document.source_version}</p><code>{review.preview.preview_fingerprint}</code></details>
    </section>}
    {confirmAction.error && <p role="alert" className="error">Copy failed: {formatApiError(confirmAction.error)}</p>}
    {pendingSave && <section aria-label="Save copied packages">
      <p>Copy is currently in the Working Draft. It is not a Saved Revision yet.</p>
      {!saveReady && <p role="alert" className="error">The reviewed Draft or Branch changed. Refresh before saving; no stale Save will be sent.</p>}
      <label><input type="checkbox" aria-label="Confirm save revision" checked={saveApproved} onChange={event => setSaveApproved(event.target.checked)} /> Create a Saved Revision with the current reviewed Working Draft.</label>
      <button type="button" disabled={!saveReady || !saveApproved || saveAction.isPending}
        onClick={() => pendingSave && saveAction.mutate(pendingSave)}>
        {saveAction.isPending ? 'Saving revision…' : 'Save copied packages'}
      </button>
    </section>}
    {saveAction.error && <p role="alert" className="error">Save failed: {formatApiError(saveAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
  </SectionCard>
}
