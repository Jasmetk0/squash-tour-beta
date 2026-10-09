import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import {
  commitCanonicalTournamentDrawInput, generateCanonicalTournamentDraw,
  getBranchWorkingDraft, getCanonicalTournamentDrawAuthority,
  getCanonicalTournamentDrawState, getCanonicalTournamentEntryFieldState,
  getCanonicalTournamentPreparation, getRunContainer, listRunBranches
} from '../api/client'
import {
  canReviewInitialDrawInput, verifiedCommittedDrawInput, verifiedGeneratedFirstDraw
} from '../api/runFirstDrawReview'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'

type ReviewedInput = {
  runId: string; branchId: string; eventId: string
  head: string; draftVersion: number; fieldFingerprint: string
  fieldSequence: number; preparationFingerprint: string
  drawSeed: number; commandId: string
}
type ReviewedGeneration = {
  runId: string; branchId: string; eventId: string
  head: string; draftVersion: number; fieldFingerprint: string
  fieldSequence: number; drawInputFingerprint: string
  drawSeed: number; commandId: string
}
const sha = (v: unknown): v is string =>
  typeof v === 'string' && /^[0-9a-f]{64}$/.test(v)

export function RunFirstDrawPanel({ runId, branchId, eventId }: {
  runId: string; branchId: string; eventId: string
}): JSX.Element {
  const qc = useQueryClient()
  const [seedText, setSeedText] = useState('12345')
  const [inputReview, setInputReview] = useState<ReviewedInput | null>(null)
  const [inputApproval, setInputApproval] = useState(false)
  const [generationReview, setGenerationReview] = useState<ReviewedGeneration | null>(null)
  const [generationApproval, setGenerationApproval] = useState(false)
  const [notice, setNotice] = useState('')

  const runQuery = useQuery({
    queryKey: ['admin-run-container',runId],
    queryFn: () => getRunContainer(runId), retry: false
  })
  const branchQuery = useQuery({
    queryKey: ['admin-run-branches',runId],
    queryFn: () => listRunBranches(runId), retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft',runId,branchId],
    queryFn: () => getBranchWorkingDraft(runId,branchId), retry: false
  })
  const preparationQuery = useQuery({
    queryKey: ['canonical-tournament-preparation',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentPreparation(runId,branchId,eventId), retry: false
  })
  const fieldQuery = useQuery({
    queryKey: ['canonical-entry-field',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentEntryFieldState(runId,branchId,eventId),
    retry: false
  })
  const drawQuery = useQuery({
    queryKey: ['canonical-tournament-draw-state',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentDrawState(runId,branchId,eventId),
    retry: false
  })
  const authorityQuery = useQuery({
    queryKey: ['canonical-tournament-draw-authority',runId,branchId,eventId],
    queryFn: () => getCanonicalTournamentDrawAuthority(runId,branchId,eventId),
    enabled: drawQuery.data?.initial_draw_generated === true,
    retry: false
  })
  const branch = branchQuery.data?.run_branches.find(b =>
    b.run_id === runId && b.branch_id === branchId)
  const head = branch?.saved_head_revision_id ?? ''
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const writable = Boolean(runQuery.data?.run_id === runId &&
    runQuery.data.storage_kind === 'custom_local' &&
    !runQuery.data.read_only &&
    branch?.status === 'active' && !branch.read_only &&
    head && draft?.base_saved_revision_id === head && draft.status === 'clean')
  const preparation = preparationQuery.data?.run_id === runId &&
    preparationQuery.data.branch_id === branchId &&
    preparationQuery.data.event_id === eventId ? preparationQuery.data : null
  const field = fieldQuery.data?.run_id === runId &&
    fieldQuery.data.branch_id === branchId &&
    fieldQuery.data.event_id === eventId ? fieldQuery.data : null
  const draw = drawQuery.data?.run_id === runId &&
    drawQuery.data.branch_id === branchId &&
    drawQuery.data.event_id === eventId ? drawQuery.data : null
  const busy = runQuery.isFetching || branchQuery.isFetching || draftQuery.isFetching ||
    preparationQuery.isFetching || fieldQuery.isFetching || drawQuery.isFetching
  const seed = /^-?\d+$/.test(seedText.trim()) ? Number(seedText.trim()) : Number.NaN
  const canInput = Boolean(writable && !busy &&
    canReviewInitialDrawInput(preparation,field,draw,runId,branchId,eventId) &&
    Number.isSafeInteger(seed))
  const canGenerate = Boolean(writable && !busy && preparation && field && draw &&
    preparation.schema_version === 'canonical_tournament_preparation_state.v1' &&
    preparation.authority_source === 'run_owned_db_authorities.v1' &&
    preparation.next_required_action === 'generate_draw' &&
    preparation.entry_source_kind === 'ranking_applications' &&
    !preparation.blockers.length &&
    draw.draw_input_committed && !draw.initial_draw_generated &&
    sha(draw.draw_input_fingerprint) &&
    field.field_fingerprint === draw.field_fingerprint &&
    field.field_sequence === draw.field_sequence &&
    draw.draw_seed !== null && Number.isSafeInteger(draw.draw_seed))

  useEffect(() => {
    setInputReview(null); setInputApproval(false)
    setGenerationReview(null); setGenerationApproval(false)
    setNotice('')
  }, [runId,branchId,eventId,head,draft?.draft_version,
    field?.field_fingerprint,draw?.draw_input_fingerprint,draw?.draw_authority_fingerprint])

  const currentInput = Boolean(inputReview && canInput && preparation && draft && field && draw &&
    inputReview.runId === runId && inputReview.branchId === branchId &&
    inputReview.eventId === eventId && inputReview.head === head &&
    inputReview.draftVersion === draft.draft_version &&
    inputReview.fieldSequence === field.field_sequence &&
    inputReview.fieldFingerprint === field.field_fingerprint &&
    inputReview.preparationFingerprint === preparation.preparation_fingerprint &&
    inputReview.drawSeed === seed)
  const inputMutation = useMutation({
    mutationFn: async (review: ReviewedInput) => {
      const [freshDraft,freshField,freshDraw,freshPreparation] = await Promise.all([
        getBranchWorkingDraft(runId,branchId),
        getCanonicalTournamentEntryFieldState(runId,branchId,eventId),
        getCanonicalTournamentDrawState(runId,branchId,eventId),
        getCanonicalTournamentPreparation(runId,branchId,eventId)
      ])
      if (freshDraft.base_saved_revision_id !== review.head ||
        freshDraft.status !== 'clean' ||
        freshDraft.draft_version !== review.draftVersion ||
        freshField.field_fingerprint !== review.fieldFingerprint ||
        freshField.field_sequence !== review.fieldSequence ||
        freshPreparation.preparation_fingerprint !== review.preparationFingerprint ||
        !canReviewInitialDrawInput(freshPreparation,freshField,freshDraw,runId,branchId,eventId))
        throw new Error('Draw Input source changed. Review the current field before retrying.')
      const data = await commitCanonicalTournamentDrawInput(runId,branchId,eventId,{
        schema_version:'canonical_tournament_draw_input_commit_command.v1',
        command_id:review.commandId,run_id:runId,branch_id:branchId,event_id:eventId,
        expected_field_fingerprint:review.fieldFingerprint,draw_seed:review.drawSeed
      })
      if (!verifiedCommittedDrawInput(data,freshField,runId,branchId,eventId,review.drawSeed))
        throw new Error('Draw Input was submitted but its authoritative response does not match.')
      const saved = await getCanonicalTournamentDrawState(runId,branchId,eventId)
      if (!verifiedCommittedDrawInput(saved,freshField,runId,branchId,eventId,review.drawSeed) ||
        saved.draw_input_fingerprint !== data.draw_input_fingerprint)
        throw new Error('Draw Input may have committed, but persisted readback did not verify. Refresh first.')
      return saved
    },
    onSuccess: async (saved) => {
      setInputReview(null);setInputApproval(false)
      setNotice(`Draw Input persisted and re-read, seed ${saved.draw_seed}, fingerprint ${saved.draw_input_fingerprint?.slice(0,16)}…. The bracket itself has not been drawn yet.`)
      await Promise.all([
        qc.invalidateQueries({queryKey:['canonical-tournament-draw-state',runId,branchId,eventId]}),
        qc.invalidateQueries({queryKey:['canonical-tournament-preparation',runId,branchId,eventId]}),
        qc.invalidateQueries({queryKey:['canonical-entry-field',runId,branchId,eventId]})
      ])
    },
    onError: async () => {
      setInputReview(null);setInputApproval(false)
      await qc.invalidateQueries({queryKey:['canonical-tournament-draw-state',runId,branchId,eventId]})
    }
  })
  const currentGeneration = Boolean(generationReview && canGenerate && field && draft && draw &&
    generationReview.runId === runId && generationReview.branchId === branchId &&
    generationReview.eventId === eventId && generationReview.head === head &&
    generationReview.draftVersion === draft.draft_version &&
    generationReview.fieldFingerprint === field.field_fingerprint &&
    generationReview.fieldSequence === field.field_sequence &&
    generationReview.drawInputFingerprint === draw.draw_input_fingerprint &&
    generationReview.drawSeed === draw.draw_seed)

  const generationMutation = useMutation({
    mutationFn: async (review: ReviewedGeneration) => {
      const [freshDraft,freshField,freshDraw,freshPreparation] = await Promise.all([
        getBranchWorkingDraft(runId,branchId),
        getCanonicalTournamentEntryFieldState(runId,branchId,eventId),
        getCanonicalTournamentDrawState(runId,branchId,eventId),
        getCanonicalTournamentPreparation(runId,branchId,eventId)
      ])
      if (freshDraft.base_saved_revision_id !== review.head ||
        freshDraft.status !== 'clean' ||
        freshDraft.draft_version !== review.draftVersion ||
        freshField.field_fingerprint !== review.fieldFingerprint ||
        freshField.field_sequence !== review.fieldSequence ||
        freshDraw.draw_input_fingerprint !== review.drawInputFingerprint ||
        freshDraw.initial_draw_generated ||
        freshDraw.draw_seed !== review.drawSeed ||
        freshPreparation.next_required_action !== 'generate_draw' ||
        freshPreparation.blockers.length > 0)
        throw new Error('Draw generation evidence changed. Review the latest Draw Input.')
      const response = await generateCanonicalTournamentDraw(runId,branchId,eventId,{
        schema_version:'canonical_tournament_draw_generate_command.v1',
        command_id:review.commandId,
        run_id:runId,branch_id:branchId,event_id:eventId,
        expected_draw_input_fingerprint:review.drawInputFingerprint
      })
      if (!response.initial_draw_generated ||
        response.draw_input_fingerprint !== review.drawInputFingerprint ||
        response.field_fingerprint !== review.fieldFingerprint)
        throw new Error('The Draw-generation response did not match the reviewed inputs.')
      const [saved,authority] = await Promise.all([
        getCanonicalTournamentDrawState(runId,branchId,eventId),
        getCanonicalTournamentDrawAuthority(runId,branchId,eventId)
      ])
      if (!verifiedGeneratedFirstDraw(saved,authority,freshField,
        review.drawInputFingerprint,runId,branchId,eventId) ||
        saved.draw_authority_fingerprint !== response.draw_authority_fingerprint)
        throw new Error('Draw may have committed, but its stored player slots/BYEs could not be verified.')
      return {saved,authority}
    },
    onSuccess: async ({saved,authority}) => {
      setGenerationReview(null);setGenerationApproval(false)
      setNotice(`First real Draw persisted and re-read: ${authority.main.slots.length} Main slots and ${authority.main.bye_slot_indexes.length} BYEs. Fingerprint ${saved.draw_authority_fingerprint?.slice(0,16)}…. Match simulation is a separate step.`)
      await Promise.all([
        qc.invalidateQueries({queryKey:['canonical-tournament-draw-state',runId,branchId,eventId]}),
        qc.invalidateQueries({queryKey:['canonical-tournament-draw-authority',runId,branchId,eventId]}),
        qc.invalidateQueries({queryKey:['canonical-tournament-effective-draw-authority',runId,branchId,eventId]}),
        qc.invalidateQueries({queryKey:['canonical-tournament-preparation',runId,branchId,eventId]})
      ])
    },
    onError: async () => {
      setGenerationReview(null);setGenerationApproval(false)
      await qc.invalidateQueries({queryKey:['canonical-tournament-draw-state',runId,branchId,eventId]})
    }
  })
  const displayedDraw = Boolean(writable && field && draw && authorityQuery.data &&
    verifiedGeneratedFirstDraw(draw,authorityQuery.data,field,
      draw.draw_input_fingerprint ?? '',runId,branchId,eventId))
    ? authorityQuery.data : null
  const qBrackets = displayedDraw?.qualification_sections?.length
    ? displayedDraw.qualification_sections
    : displayedDraw?.qualification ? [displayedDraw.qualification] : []

  return <SectionCard title="First knockout Draw — reviewed authority">
    <p className="status">One canonical entry field, one immutable Draw Input and one deterministic initial bracket. The seed is only for repeatable shuffling. Main BYEs, seeding and Qualification are resolved by the existing backend — never invented in the UI.</p>
    {runQuery.error && <p role="alert" className="error">Run unavailable: {formatApiError(runQuery.error)}</p>}
    {branchQuery.error && <p role="alert" className="error">Branch unavailable: {formatApiError(branchQuery.error)}</p>}
    {draftQuery.error && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {preparationQuery.error && <p role="alert" className="error">Tournament authority unavailable: {formatApiError(preparationQuery.error)}</p>}
    {fieldQuery.error && !isApiNotFound(fieldQuery.error) && <p role="alert" className="error">Entry Field unavailable: {formatApiError(fieldQuery.error)}</p>}
    {drawQuery.error && !isApiNotFound(drawQuery.error) && <p role="alert" className="error">Draw authority unavailable: {formatApiError(drawQuery.error)}</p>}
    {authorityQuery.error && <p role="alert" className="error">Draw player slot readback unavailable: {formatApiError(authorityQuery.error)}</p>}
    {!writable && <p>Requires an active writable Run/Branch with a clean Working Draft based on the current Saved Revision.</p>}
    {!field && <p>No persisted Tournament Entry Field. Finish and verify the real Main/Qualification field first.</p>}
    {field && draw && <p>Field #{field.field_sequence} · Main capacity {field.main_draw_capacity} · {field.direct_main_player_ids.length} direct Main · {field.qualification_player_ids.length} Qualification · {field.effective_main_bye_count} BYEs.</p>}
    {preparation?.wild_card_required && !preparation.wild_card_ready &&
      <p role="status">Complete the existing Wild Card review before committing Draw Input.</p>}
    {preparation?.blockers?.length ? <p role="status">Backend blockers: {preparation.blockers.join(', ')}.</p> : null}
    {field && draw && !draw.draw_input_committed && <section aria-label="Review canonical Draw Input">
      <label>Reproducible Draw seed
        <input type="number" aria-label="Reviewed Draw seed" value={seedText}
          onChange={e => {setSeedText(e.target.value);setInputReview(null);setInputApproval(false)}}/>
      </label>
      <button type="button" disabled={!canInput || inputMutation.isPending || generationMutation.isPending}
        onClick={() => {
          if (!draft || !preparation || !field) return
          setInputReview({runId,branchId,eventId,head,draftVersion:draft.draft_version,
            fieldFingerprint:field.field_fingerprint,fieldSequence:field.field_sequence,
            preparationFingerprint:preparation.preparation_fingerprint ?? '',
            drawSeed:seed,commandId:`admin-first-draw-input-${crypto.randomUUID()}`})
          setInputApproval(false)
        }}>Review first Draw Input</button>
      {inputReview && <section aria-label="Confirm reviewed Draw Input">
        <p>Freeze Entry Field #{inputReview.fieldSequence}, fingerprint <code>{inputReview.fieldFingerprint}</code>, with seed {inputReview.drawSeed}.</p>
        {!currentInput && <p role="alert" className="error">Draw Input changed; preview again.</p>}
        <label><input type="checkbox" aria-label="Approve Draw Input" checked={inputApproval}
          onChange={e=>setInputApproval(e.target.checked)}/>
          Commit this exact Entry Field and technical seed.</label>
        <button type="button" disabled={!inputApproval || !currentInput || inputMutation.isPending}
          onClick={() => inputMutation.mutate(inputReview)}>
          {inputMutation.isPending ? 'Saving Draw Input…' : 'Commit reviewed Draw Input'}
        </button>
      </section>}
    </section>}
    {field && draw?.draw_input_committed && <p role="status">Draw Input saved: seed {draw.draw_seed} · <code>{draw.draw_input_fingerprint?.slice(0,16)}…</code>.</p>}
    {draw?.draw_input_committed && !draw.initial_draw_generated && <section aria-label="Review initial Draw generation">
      <button type="button" disabled={!canGenerate || generationMutation.isPending}
        onClick={() => {
          if (!draw || !draft || !field || !draw.draw_input_fingerprint || draw.draw_seed == null) return
          setGenerationReview({runId,branchId,eventId,head,draftVersion:draft.draft_version,
            fieldFingerprint:field.field_fingerprint,fieldSequence:field.field_sequence,
            drawInputFingerprint:draw.draw_input_fingerprint,drawSeed:draw.draw_seed,
            commandId:`admin-first-draw-generate-${crypto.randomUUID()}`})
          setGenerationApproval(false)
        }}>Review initial bracket generation</button>
      {generationReview && <section aria-label="Confirm immutable bracket">
        <p>Generate the initial bracket using saved Draw Input <code>{generationReview.drawInputFingerprint}</code> and seed {generationReview.drawSeed}. All player placements and BYEs are determined by the production draw algorithm.</p>
        {!currentGeneration && <p role="alert" className="error">Frozen inputs changed; review again.</p>}
        <label><input type="checkbox" aria-label="Approve initial bracket generation"
          checked={generationApproval} onChange={e=>setGenerationApproval(e.target.checked)}/>
          Generate one immutable canonical bracket.</label>
        <button type="button" disabled={!generationApproval || !currentGeneration || generationMutation.isPending}
          onClick={() => generationMutation.mutate(generationReview)}>
          {generationMutation.isPending ? 'Generating canonical bracket…' : 'Generate reviewed initial Draw'}
        </button>
      </section>}
    </section>}
    {inputMutation.error && <p role="alert" className="error">Draw Input failed: {formatApiError(inputMutation.error)}</p>}
    {generationMutation.error && <p role="alert" className="error">Draw generation/readback failed: {formatApiError(generationMutation.error)}</p>}
    {notice && <p role="status">{notice}</p>}
    {draw?.initial_draw_generated && !displayedDraw && <p role="alert" className="error">Stored Draw is not yet verified against this Branch's Entry Field, player slots, BYEs and Draw Input. Inspect the authority before continuing.</p>}
    {displayedDraw && <section aria-label="Verified real tournament bracket">
      <h4>Saved initial bracket · {displayedDraw.algorithm_version}</h4>
      <p>Actual Main slots: {displayedDraw.main.slots.length} · BYEs: {displayedDraw.main.bye_slot_indexes.length} · Qualification sections: {qBrackets.length}.</p>
      <table>
        <thead><tr><th>Slot</th><th>Actual player or placeholder</th><th>Seed</th><th>Kind</th></tr></thead>
        <tbody>{displayedDraw.main.slots.map(slot=>
          <tr key={slot.slot_index}>
            <td>{slot.slot_index}</td><td>{slot.player_id ?? slot.placeholder_id ?? 'BYE'}</td>
            <td>{slot.seed_number ?? '—'}</td><td>{slot.entrant_kind}</td>
          </tr>
        )}</tbody>
      </table>
      {qBrackets.map((q,i)=><section key={q.section_id ?? i} aria-label={`Qualification section ${i+1}`}>
        <h4>Qualification {q.section_id ?? i+1}</h4>
        <table><thead><tr><th>Slot</th><th>Player or placeholder</th><th>Seed</th></tr></thead>
          <tbody>{q.slots.map(slot=><tr key={slot.slot_index}>
            <td>{slot.slot_index}</td><td>{slot.player_id ?? slot.placeholder_id ?? 'BYE'}</td>
            <td>{slot.seed_number ?? '—'}</td>
          </tr>)}</tbody>
        </table>
      </section>)}
    </section>}
  </SectionCard>
}
