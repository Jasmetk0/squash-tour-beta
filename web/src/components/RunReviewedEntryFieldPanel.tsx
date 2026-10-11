import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  commitRunReviewedEntryField, getBranchWorkingDraft, getCanonicalTournamentEntryFieldState,
  getCanonicalTournamentPreparation, getRunContainer, listRunBranches,
  previewRunReviewedEntryField
} from '../api/client'
import type { TournamentEntryFieldCapacity } from '../api/types'
import {
  strictCapacity, verifiedEntryFieldSource, verifiedReviewedEntryField,
  verifiedStoredEntryField, type ReviewedEntryFieldPreview
} from '../api/runReviewedEntryField'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type Review = {
  runId: string
  branchId: string
  eventId: string
  savedHead: string
  draftVersion: number
  sourcePreparationFingerprint: string
  preview: ReviewedEntryFieldPreview
  commandId: string
}

const numeric = (value: string): number => value.trim() !== '' && /^\d+$/.test(value)
  ? Number(value) : Number.NaN

export function RunReviewedEntryFieldPanel({ runId, branchId, eventId }: {
  runId: string; branchId: string; eventId: string
}): JSX.Element {
  const queryClient = useQueryClient()
  const [capacity, setCapacity] = useState({
    main_draw_size: '', qualification_draw_size: '',
    qualifier_spots: '', wild_card_slots: '', bye_slots: ''
  })
  const [review, setReview] = useState<Review | null>(null)
  const [approved, setApproved] = useState(false)
  const [notice, setNotice] = useState('')

  const runQuery = useQuery({
    queryKey: ['admin-run-container', runId],
    queryFn: () => getRunContainer(runId), retry: false
  })
  const branchQuery = useQuery({
    queryKey: ['admin-run-branches', runId],
    queryFn: () => listRunBranches(runId), retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId), retry: false
  })
  const sourceQuery = useQuery({
    queryKey: ['canonical-tournament-preparation', runId, branchId, eventId],
    queryFn: () => getCanonicalTournamentPreparation(runId, branchId, eventId),
    retry: false
  })
  const fieldQuery = useQuery({
    queryKey: ['canonical-entry-field', runId, branchId, eventId],
    queryFn: () => getCanonicalTournamentEntryFieldState(runId, branchId, eventId),
    retry: false
  })
  const branch = branchQuery.data?.run_branches.find(item =>
    item.run_id === runId && item.branch_id === branchId)
  const head = branch?.saved_head_revision_id ?? ''
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const writable = Boolean(runQuery.data?.run_id === runId &&
    runQuery.data.storage_kind === 'custom_local' &&
    !runQuery.data.read_only &&
    branch?.status === 'active' && !branch.read_only && head &&
    draft?.base_saved_revision_id === head && draft.status === 'clean')
  const preparation = sourceQuery.data
  const sourceReady = verifiedEntryFieldSource(preparation, runId, branchId, eventId)
  const existingField = fieldQuery.data?.run_id === runId &&
    fieldQuery.data.branch_id === branchId &&
    fieldQuery.data.event_id === eventId ? fieldQuery.data : null
  const fieldAbsent = fieldQuery.isSuccess ? false :
    !fieldQuery.isFetching && isApiNotFound(fieldQuery.error)
  const suggestion = sourceReady ? preparation.entry_capacity_suggestion : null
  const suggestedFingerprint = suggestion?.source_event_fingerprint ?? ''

  useEffect(() => {
    if (!suggestion) return
    setCapacity({
      main_draw_size: String(suggestion.main_draw_size),
      qualification_draw_size: String(suggestion.qualification_draw_size),
      qualifier_spots: String(suggestion.qualifier_spots),
      wild_card_slots: String(suggestion.wild_card_slots),
      bye_slots: String(suggestion.bye_slots)
    })
    setReview(null)
    setApproved(false)
  }, [runId, branchId, eventId, suggestedFingerprint])

  useEffect(() => {
    setReview(null)
    setApproved(false)
  }, [head, draft?.draft_version, preparation?.preparation_fingerprint])

  const inputCapacity: TournamentEntryFieldCapacity = {
    main_draw_size: numeric(capacity.main_draw_size),
    qualification_draw_size: numeric(capacity.qualification_draw_size),
    qualifier_spots: numeric(capacity.qualifier_spots),
    wild_card_slots: numeric(capacity.wild_card_slots),
    bye_slots: numeric(capacity.bye_slots)
  }
  const loading = runQuery.isFetching || branchQuery.isFetching || draftQuery.isFetching ||
    sourceQuery.isFetching || fieldQuery.isFetching
  const canPreview = writable && sourceReady && fieldAbsent &&
    !loading && strictCapacity(inputCapacity)

  const previewAction = useMutation({
    mutationFn: async (): Promise<Review> => {
      if (!canPreview || !draft || !preparation?.preparation_fingerprint)
        throw new Error('A clean saved Branch, authoritative ranking and real validated submissions are required.')
      const preview = await previewRunReviewedEntryField(runId, branchId, eventId, inputCapacity)
      if (!verifiedReviewedEntryField(preview, preparation, runId, branchId, eventId, inputCapacity))
        throw new Error('Entry Field preview does not match this Run, tournament, ranking authority or application count.')
      return { runId, branchId, eventId, savedHead: head,
        draftVersion: draft.draft_version,
        sourcePreparationFingerprint: preparation.preparation_fingerprint,
        preview, commandId: `admin-reviewed-entry-field-${crypto.randomUUID()}` }
    },
    onSuccess: (value) => { setReview(value); setApproved(false); setNotice('') },
    onError: () => { setReview(null); setApproved(false) }
  })
  const reviewedIsCurrent = Boolean(review && canPreview && draft && preparation &&
    review.runId === runId && review.branchId === branchId && review.eventId === eventId &&
    review.savedHead === head && review.draftVersion === draft.draft_version &&
    review.sourcePreparationFingerprint === preparation.preparation_fingerprint &&
    verifiedReviewedEntryField(review.preview, preparation, runId, branchId, eventId, inputCapacity))

  const commitAction = useMutation({
    mutationFn: async (current: Review) => {
      // Refresh current authority before committing; server performs a *second*
      // compare-and-swap atomically with the database write.
      const [freshPreparation, freshDraft, freshPreview] = await Promise.all([
        getCanonicalTournamentPreparation(runId, branchId, eventId),
        getBranchWorkingDraft(runId, branchId),
        previewRunReviewedEntryField(runId, branchId, eventId, current.preview.field.capacity)
      ])
      if (freshDraft.run_id !== runId || freshDraft.branch_id !== branchId ||
        freshDraft.base_saved_revision_id !== current.savedHead ||
        freshDraft.status !== 'clean' ||
        freshDraft.draft_version !== current.draftVersion ||
        freshPreparation.preparation_fingerprint !== current.sourcePreparationFingerprint ||
        !verifiedReviewedEntryField(freshPreview, freshPreparation, runId, branchId, eventId, current.preview.field.capacity) ||
        freshPreview.field_fingerprint !== current.preview.field_fingerprint) {
        throw new Error('Entry Field review became stale. Reopen the latest source before saving.')
      }
      await commitRunReviewedEntryField(
        current.runId, current.branchId, current.eventId, current.preview, current.commandId
      )
      const reloaded = await getCanonicalTournamentEntryFieldState(
        current.runId, current.branchId, current.eventId
      )
      if (!verifiedStoredEntryField(reloaded, current.preview))
        throw new Error('Field was submitted but the persisted Entry Field readback does not match. Refresh and inspect before retrying.')
      return reloaded
    },
    onSuccess: async (field) => {
      setReview(null); setApproved(false)
      setNotice(`Persisted and reloaded Entry Field #${field.field_sequence}: ${field.direct_main_player_ids.length} Main, ${field.qualification_player_ids.length} Qualification, ${field.below_qualification_cut_player_ids.length} reserve. It is not a generated Draw or match result.`)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['canonical-entry-field', runId, branchId, eventId] }),
        queryClient.invalidateQueries({ queryKey: ['canonical-tournament-preparation', runId, branchId, eventId] }),
        queryClient.invalidateQueries({ queryKey: ['canonical-tournament-draw-state', runId, branchId, eventId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-week-schedule-preflight', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['authoritative-simulation-save-preview', runId, branchId] })
      ])
    },
    onError: async () => {
      setReview(null); setApproved(false)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['canonical-entry-field', runId, branchId, eventId] }),
        queryClient.invalidateQueries({ queryKey: ['canonical-tournament-preparation', runId, branchId, eventId] })
      ])
    }
  })

  const updateCapacity = (key: keyof typeof capacity, value: string) => {
    setCapacity(old => ({ ...old, [key]: value }))
    setReview(null); setApproved(false)
  }

  return <SectionCard title="Reviewed tournament Entry Field">
    <p className="status">Build the real Main, Qualification and reserve lists from persisted, explicitly validated applications. This is a server-resolved preview with a source fingerprint, not a guessed ranking or a Draw. Reviewed Commit fails if a player, ranking source or capacity changed before the transaction.</p>
    {runQuery.error && <p role="alert" className="error">Product Run unavailable: {formatApiError(runQuery.error)}</p>}
    {branchQuery.error && <p role="alert" className="error">Branch unavailable: {formatApiError(branchQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {sourceQuery.error && <p role="alert" className="error">Tournament preparation unavailable: {formatApiError(sourceQuery.error)}</p>}
    {fieldQuery.error && !isApiNotFound(fieldQuery.error) &&
      <p role="alert" className="error">Existing field inspection unavailable: {formatApiError(fieldQuery.error)}</p>}
    {!writable && <p>A writable active Product Run Branch with a clean saved Working Draft is required.</p>}
    {preparation && !sourceReady && !existingField &&
      <p role="status">First adopt a Ranking Snapshot and persist valid player applications. The backend must provide a unique Calendar capacity suggestion.</p>}
    {existingField && <section aria-label="Persisted tournament Entry Field">
      <p role="status">Entry Field saved and reloaded: fingerprint <code>{existingField.field_fingerprint.slice(0, 16)}…</code>, version {existingField.field_sequence}.</p>
      <p>{existingField.direct_main_player_ids.length} direct Main · {existingField.qualification_player_ids.length} Qualification · {existingField.below_qualification_cut_player_ids.length} reserves · {existingField.effective_main_bye_count} BYEs.</p>
      <p className="status">No duplicate initial creation is allowed. Continue with the existing Wild Card, Draw Input and Draw controls.</p>
    </section>}
    {sourceReady && !existingField && <>
      <p>Valid applications: <strong>{preparation.valid_submission_count}</strong> ({preparation.valid_main_submission_count} Main; {preparation.valid_qualification_submission_count} Qualification).</p>
      <p className="status">Calendar suggestion: {suggestion?.source_package_id}, source fingerprint <code>{suggestion?.source_event_fingerprint.slice(0,16)}…</code>. All capacities can be reviewed before Preview.</p>
      <div className="grid">
        {([
          ['main_draw_size','Main Draw capacity'],
          ['qualification_draw_size','Qualification Draw capacity'],
          ['qualifier_spots','Qualifier spots'],
          ['wild_card_slots','Wild Card slots'],
          ['bye_slots','Explicit BYEs']
        ] as Array<[keyof typeof capacity,string]>).map(([key,label])=>
          <label key={key}>{label}
            <input type="number" min={0} aria-label={`Reviewed ${label}`}
              value={capacity[key]} onChange={event => updateCapacity(key,event.target.value)} />
          </label>
        )}
      </div>
      {!strictCapacity(inputCapacity) && <p role="status">Choose integer capacities: Main 2–128 power of two, nonnegative Qualification/reserved slots and no over-reservation.</p>}
      <button type="button" disabled={!canPreview || previewAction.isPending || commitAction.isPending}
        onClick={() => { setReview(null); setApproved(false); previewAction.mutate() }}>
        {previewAction.isPending ? 'Resolving Entry Field…' : 'Preview actual Entry Field'}
      </button>
    </>}
    {previewAction.error && <p role="alert" className="error">Entry Field preview failed: {formatApiError(previewAction.error)}</p>}
    {review && <section aria-label="Review exact Entry Field players">
      <h4>Confirm exact player partitions</h4>
      <p>Main: {review.preview.field.direct_main_player_ids.length} · Qualification: {review.preview.field.qualification_player_ids.length} · Reserve: {review.preview.field.below_qualification_cut_player_ids.length}.</p>
      <p>Field SHA-256: <code>{review.preview.field_fingerprint}</code></p>
      <p><strong>Main:</strong> {review.preview.field.direct_main_player_ids.join(', ') || 'None'}</p>
      <p><strong>Qualification:</strong> {review.preview.field.qualification_player_ids.join(', ') || 'None'}</p>
      <p><strong>Reserves:</strong> {review.preview.field.below_qualification_cut_player_ids.join(', ') || 'None'}</p>
      {!reviewedIsCurrent && <p role="alert" className="error">Source, Branch, Draft or capacities changed. Preview again.</p>}
      <label><input type="checkbox" checked={approved} aria-label="Approve reviewed Entry Field"
        onChange={event => setApproved(event.target.checked)} />
        Persist this exact ranked field, with the displayed capacities.</label>
      <button type="button" disabled={!approved || !reviewedIsCurrent || commitAction.isPending}
        onClick={() => commitAction.mutate(review)}>
        {commitAction.isPending ? 'Persisting Entry Field…' : 'Commit reviewed Entry Field'}
      </button>
    </section>}
    {commitAction.error && <p role="alert" className="error">Entry Field commit/readback failed: {formatApiError(commitAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
  </SectionCard>
}
