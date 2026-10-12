import { acknowledgeSavedRunForm } from './RunNavigationSafeguard'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  adoptRunOwnedInitialWorld, getBranchWorkingDraft, getRunOwnedInitialWorld,
  getRunGenerationProposals, saveRunGenerationProposal, loadRunGenerationProposal,
  inspectRunGenerationProposal, revalidateRunGenerationProposal, deleteRunGenerationProposal,
  getRunPackageState, getRunWorldGenerationOptions, previewRunInitialWorldSave, previewRunOwnedInitialWorld,
  saveRunOwnedInitialWorld
} from '../api/client'
import type { RunBranch, RunContainer } from '../api/types'
import {
  ageConditionConflict, countryQuotaConflict, generatorConditionConflict, runOwnedWorldIds, verifiedGenerationOptions, verifiedInitialWorldPreview,
  orderedPreviewFieldLocks, PREVIEW_FIELD_KEYS,
  type GeneratedPlayerFieldKey, type RunWorldExactCountryQuota, type RunWorldPreviewFieldLock,
  type RunInitialWorldAdoption, type RunInitialWorldPreview,
  type RunSavedGenerationProposal, type RunGenerationProposalInspection,
  type RunGenerationProposalRevalidation
} from '../api/runInitialWorldSetup'
import { formatApiError, isApiNotFound } from '../utils/apiErrors'
import { SectionCard } from './RunScopedUi'
import { GeneratedPlayerReviewInspector } from './GeneratedPlayerReviewInspector'
import { GeneratedPlayerFieldLockEditor } from './GeneratedPlayerFieldLockEditor'
import { RunInitialWorldSelectedAppendPanel } from './RunInitialWorldSelectedAppendPanel'
import { playerGeneratorCopy } from './playerGeneratorCopy'
import {
  prepareGeneratedBulkPlan, prepareGeneratedBulkAutomaticPlan, type GeneratedBulkPlan
} from './generatedBulkPreview'

type ReviewedWorld = {
  runId: string
  branchId: string
  head: string
  sourceFingerprint: string
  draftVersion: number
  request: RunInitialWorldAdoption
  preview: RunInitialWorldPreview
}

type PendingSave = { runId: string; branchId: string; head: string; fingerprint: string }

export function RunInitialWorldSetupPanel({ run, branch, locale = 'en' }: {
  run: RunContainer; branch: RunBranch | null; locale?: 'cs' | 'en'
}): JSX.Element {
  const cs = locale === 'cs'
  const tr = (english: string) => playerGeneratorCopy(locale, english)
  const queryClient = useQueryClient()
  const runId = run.run_id
  const branchId = branch?.run_id === runId ? branch.branch_id : ''
  const head = branch?.run_id === runId ? branch.saved_head_revision_id ?? '' : ''
  const editable = run.storage_kind === 'custom_local' && !run.read_only &&
    ['working', 'active', 'completed'].includes(run.status) &&
    Boolean(branchId && head && branch?.status === 'active' && !branch.read_only)
  const [sourceId, setSourceId] = useState('')
  const [seed, setSeed] = useState(20261009)
  const [poolSize, setPoolSize] = useState(64)
  const [countryCode, setCountryCode] = useState('')
  const [countryQuotas, setCountryQuotas] = useState<RunWorldExactCountryQuota[]>([])
  const [region, setRegion] = useState('')
  const [travelRegion, setTravelRegion] = useState('')
  const [minAge, setMinAge] = useState('')
  const [maxAge, setMaxAge] = useState('')
  const [bestN, setBestN] = useState(15)
  const [auditReason, setAuditReason] = useState('Create the first-season player population from the reviewed Run-owned World snapshot.')
  const [review, setReview] = useState<ReviewedWorld | null>(null)
  const [reviewBaseSeed, setReviewBaseSeed] = useState<number | null>(null)
  const [approved, setApproved] = useState(false)
  const [keptIds, setKeptIds] = useState<string[]>([])
  const [rerollSeed, setRerollSeed] = useState(20261010)
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [pendingFieldLocks, setPendingFieldLocks] = useState<RunWorldPreviewFieldLock[]>([])
  const [bulkSelectedIds, setBulkSelectedIds] = useState<string[]>([])
  const [bulkField, setBulkField] = useState<GeneratedPlayerFieldKey>('attributes.technique')
  const [bulkMode, setBulkMode] = useState<'value'|'automatic'>('value')
  const [bulkValue, setBulkValue] = useState('')
  const [bulkStagedFingerprint, setBulkStagedFingerprint] = useState<string | null>(null)
  const [bulkUndo, setBulkUndo] = useState<{previous: ReviewedWorld; appliedFingerprint: string} | null>(null)
  const [pendingSave, setPendingSave] = useState<PendingSave | null>(null)
  const [saveApproved, setSaveApproved] = useState(false)
  const [notice, setNotice] = useState('')
  const [proposalName, setProposalName] = useState('Generation proposal')
  const [selectedProposalId, setSelectedProposalId] = useState('')
  const [restoringProposal, setRestoringProposal] = useState<RunSavedGenerationProposal | null>(null)
  const [restoringRevalidated, setRestoringRevalidated] = useState(false)
  const [inspection, setInspection] = useState<RunGenerationProposalInspection | null>(null)
  const [revalidated, setRevalidated] = useState<RunGenerationProposalRevalidation | null>(null)

  const packageQuery = useQuery({
    queryKey: ['run-package-state', runId, branchId],
    queryFn: () => getRunPackageState(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const draftQuery = useQuery({
    queryKey: ['package-working-draft', runId, branchId],
    queryFn: () => getBranchWorkingDraft(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const existingQuery = useQuery({
    queryKey: ['run-owned-initial-world', runId, branchId],
    queryFn: () => getRunOwnedInitialWorld(runId, branchId),
    enabled: Boolean(branchId),
    retry: false
  })
  const proposalQuery = useQuery({
    queryKey: ['generation-proposals', runId, branchId],
    queryFn: () => getRunGenerationProposals(runId, branchId),
    enabled: Boolean(branchId && run.storage_kind === 'custom_local'),
    retry: false
  })
  const worldIds = runOwnedWorldIds(packageQuery.data?.state)
  const selectedWorldId = worldIds.includes(sourceId) ? sourceId : (worldIds[0] ?? '')
  const draft = draftQuery.data?.run_id === runId &&
    draftQuery.data.branch_id === branchId ? draftQuery.data : null
  const existing = existingQuery.data?.run_id === runId &&
    existingQuery.data.branch_id === branchId ? existingQuery.data : null
  const unexpectedExistingError = existingQuery.error && !isApiNotFound(existingQuery.error)
  const validParameters = Number.isSafeInteger(seed) && Number.isInteger(poolSize) &&
    poolSize >= 1 && poolSize <= 1000 && Number.isInteger(bestN) && bestN >= 1 &&
    auditReason.trim().length >= 1 && auditReason.trim().length <= 1000
  const snapshotFingerprint = packageQuery.data?.fingerprint ?? null
  const optionsQuery = useQuery({
    queryKey: ['run-world-generation-options', runId, branchId, head, draft?.draft_version,
      snapshotFingerprint, selectedWorldId],
    queryFn: () => getRunWorldGenerationOptions(
      runId, branchId, selectedWorldId, head, draft!.draft_version, snapshotFingerprint!
    ),
    enabled: editable && Boolean(selectedWorldId && snapshotFingerprint && draft &&
      draft.status === 'clean' && draft.base_saved_revision_id === head && !existing),
    retry: false,
  })
  const options = optionsQuery.data && draft && snapshotFingerprint &&
    verifiedGenerationOptions(optionsQuery.data, runId, branchId, head,
      draft.draft_version, snapshotFingerprint, selectedWorldId)
    ? optionsQuery.data : null
  const conditionConflict = optionsQuery.isSuccess
    ? generatorConditionConflict(countryCode, '', options, region, travelRegion)
    : null
  const ageConflict = ageConditionConflict(minAge, maxAge)
  const quotaConflict = countryQuotaConflict(countryQuotas, poolSize, options, countryCode, region, travelRegion)
  const eligibleQuotaCountries = (options?.countries ?? []).filter(c =>
    (!countryCode || c.code === countryCode) && (!region || c.region === region) &&
    (!travelRegion || c.travel_region === travelRegion))
  const fixedQuotaTotal = countryQuotas.reduce((sum,q) => sum + q.count,0)
  const canPreview = editable && worldIds.length > 0 && validParameters &&
    packageQuery.isSuccess && Boolean(options) && !conditionConflict && !ageConflict && !quotaConflict &&
    draft?.base_saved_revision_id === head &&
    draft.status === 'clean' && !existing && existingQuery.isSuccess === false &&
    isApiNotFound(existingQuery.error) && !pendingSave

  useEffect(() => {
    setReview(null)
    setReviewBaseSeed(null)
    setKeptIds([])
    setPendingFieldLocks([])
    setBulkSelectedIds([]); setBulkStagedFingerprint(null); setBulkUndo(null)
    setSelectedPlayerId(null)
    setPendingSave(null)
    setApproved(false)
    setSaveApproved(false)
    setNotice('')
  }, [runId, branchId, head, sourceId, seed, poolSize, countryCode, countryQuotas, region, travelRegion, minAge, maxAge, bestN, auditReason])

  const previewAction = useMutation({
    mutationFn: async () => {
      if (!canPreview || !selectedWorldId || !draft || !snapshotFingerprint)
        throw new Error('Run World, clean Saved Revision and writable target must be verified.')
      const request: RunInitialWorldAdoption = {
        command_id: `admin-initial-world-${crypto.randomUUID()}`,
        generation: {
          world_package_id: selectedWorldId,
          season: '2000/2001',
          seed, target_pool_size: poolSize,
          naming_policy: 'country_serial.v1',
          ...(countryCode ? { country_code: countryCode } : {}),
          ...(countryQuotas.length ? { country_quotas: countryQuotas } : {}),
          ...(region ? { geographic_region: region } : {}),
          ...(travelRegion ? { travel_region: travelRegion } : {}),
          ...(minAge ? { min_age: Number(minAge) } : {}),
          ...(maxAge ? { max_age: Number(maxAge) } : {})
        },
        audit_label: 'Run Admin first-season player setup',
        audit_reason: auditReason.trim(),
        official_run: false,
        best_n: bestN,
        automatic_retirement_age: 46
      }
      const preview = await previewRunOwnedInitialWorld(runId, branchId, request)
      if (!verifiedInitialWorldPreview(preview, runId, branchId, request, options))
        throw new Error('InitialWorld preview is inconsistent with the requested World, Run, Branch or policy.')
      return { runId, branchId, head, sourceFingerprint: snapshotFingerprint,
        draftVersion: draft.draft_version, request, preview }
    },
    onSuccess: value => {
      setReview(value); setReviewBaseSeed(seed); setKeptIds([]); setRerollSeed(seed + 1)
      setBulkSelectedIds([]); setBulkStagedFingerprint(null); setBulkUndo(null)
      setPendingFieldLocks([]); setSelectedPlayerId(null)
      setApproved(false); setNotice('')
    }
  })
  const reviewMatches = Boolean(review && review.runId === runId &&
    review.branchId === branchId && review.head === head &&
    review.sourceFingerprint === snapshotFingerprint &&
    review.draftVersion === draft?.draft_version &&
    draft?.base_saved_revision_id === head && draft?.status === 'clean' &&
    review.request.generation.world_package_id === selectedWorldId &&
    reviewBaseSeed === seed &&
    review.request.generation.target_pool_size === poolSize &&
    (review.request.generation.country_code ?? '') === countryCode &&
    JSON.stringify(review.request.generation.country_quotas ?? []) === JSON.stringify(countryQuotas) &&
    (review.request.generation.geographic_region ?? '') === region &&
    (review.request.generation.travel_region ?? '') === travelRegion &&
    String(review.request.generation.min_age ?? '') === minAge &&
    String(review.request.generation.max_age ?? '') === maxAge &&
    Boolean(options) && !conditionConflict && !ageConflict && !quotaConflict &&
    review.request.best_n === bestN && review.request.audit_reason === auditReason.trim() &&
    !existing && isApiNotFound(existingQuery.error))

  const approvedFieldLocks = orderedPreviewFieldLocks(review?.request.generation.field_locks ?? [])
  const locksDirty = JSON.stringify(approvedFieldLocks) !==
    JSON.stringify(orderedPreviewFieldLocks(pendingFieldLocks))
  const fieldEditingEnabled = Boolean(reviewMatches && review && canPreview)
  const lastSessionKeep = [...(review?.request.generation.session_steps ?? [])]
    .reverse().find(step => step.kind === 'keep')
  const reviewedKeepIds = lastSessionKeep?.keep_player_ids ??
    review?.request.generation.keep_player_ids ?? []
  const keepSelectionDirty = keptIds.join('|') !== reviewedKeepIds.join('|')
  const onPreviewFieldChange = (field: GeneratedPlayerFieldKey, value: number | null) => {
    if (!selectedPlayerId || !fieldEditingEnabled) return
    setPendingFieldLocks(current => orderedPreviewFieldLocks(
      value == null
        ? current.filter(lock => !(lock.player_id === selectedPlayerId && lock.field === field))
        : [...current.filter(lock => !(lock.player_id === selectedPlayerId && lock.field === field)),
          { player_id: selectedPlayerId, field, value }]
    ))
    setApproved(false); setBulkUndo(null); setBulkStagedFingerprint(null)
  }
  // Action selection is not the Keep selection or the current display filter.
  // It is valid only within one exact reviewed preview fingerprint.
  useEffect(() => {
    setBulkSelectedIds([])
    setBulkStagedFingerprint(null)
    // A successful bulk server preview is an Undo boundary. Keep its verified
    // predecessor even though the current fingerprint necessarily changes.
  }, [review?.preview.fingerprint, runId, branchId, head])

  let bulkPlan: GeneratedBulkPlan | null = null
  let bulkError: string | null = null
  if (bulkSelectedIds.length && reviewMatches && review) {
    if (bulkMode === 'value' && !/^[0-9]+$/.test(bulkValue))
      bulkError = 'Enter a whole-number source value from 1 to 99.'
    else {
      try {
        bulkPlan = bulkMode === 'automatic'
          ? prepareGeneratedBulkAutomaticPlan(
            review.preview.state.players, bulkSelectedIds, bulkField, approvedFieldLocks
          )
          : prepareGeneratedBulkPlan(
            review.preview.state.players, bulkSelectedIds,
            bulkField, Number(bulkValue), approvedFieldLocks
          )
      } catch (error) {
        bulkError = error instanceof Error ? error.message : String(error)
      }
    }
  }
  const canStageBulk = Boolean(bulkPlan?.changes.length && fieldEditingEnabled &&
    !locksDirty && !keepSelectionDirty && !bulkStagedFingerprint)

  const sessionSteps = (review?.request.generation.keep_history?.length ?? 0) +
    (review?.request.generation.keep_from_seed == null ? 0 : 1) +
    (review?.request.generation.session_steps?.filter(step=>step.kind==='keep').length ?? 0)
  const canKeepPreview = Boolean(reviewMatches && review && canPreview && sessionSteps < 17)
  const canRegenerate = canKeepPreview && !locksDirty &&
    keptIds.length > 0 && keptIds.length < poolSize &&
    Number.isSafeInteger(rerollSeed) && rerollSeed !== review?.request.generation.seed

  const regenerateAction = useMutation({
    mutationFn: async () => {
      if (!canRegenerate || !review || !draft || !snapshotFingerprint)
        throw new Error('Verified source preview, Keep selection and new seed are required.')
      const sourceIds = new Set(review.preview.state.players.map(p => p.player_id))
      const retained = [...new Set(keptIds)].sort()
      if (retained.length !== keptIds.length || retained.some(id => !sourceIds.has(id)))
        throw new Error('Session Keep contains unknown or duplicate source players.')
      const previous = review.request.generation
      const history = previous.keep_from_seed == null
        ? []
        : [...(previous.keep_history ?? []), {
            seed: previous.seed,
            keep_from_seed: previous.keep_from_seed,
            keep_from_preview_fingerprint: previous.keep_from_preview_fingerprint!,
            keep_player_ids: previous.keep_player_ids ?? []
          }]
      const nextLocks = orderedPreviewFieldLocks((previous.field_locks ?? []).filter(
        lock => retained.includes(lock.player_id)))
      const nextGeneration = previous.session_schema_version === 'run_world_generation_session.v2'
        ? {
            ...previous, seed: rerollSeed, field_locks: nextLocks,
            session_steps: [...(previous.session_steps ?? []), {
              kind: 'keep' as const,
              source_preview_fingerprint: review.preview.state.run_world_pool_preview_fingerprint,
              seed: rerollSeed, keep_player_ids: retained, field_locks: nextLocks
            }]
          }
        : {
            ...previous,
            seed: rerollSeed,
            ...(history.length ? { keep_history: history } : {}),
            keep_from_seed: review.request.generation.seed,
            keep_from_preview_fingerprint: review.preview.state.run_world_pool_preview_fingerprint,
            keep_player_ids: retained
          }
      const request: RunInitialWorldAdoption = {
        ...review.request,
        command_id: `admin-initial-world-${crypto.randomUUID()}`,
        generation: nextGeneration,
      }
      const preview = await previewRunOwnedInitialWorld(runId, branchId, request)
      if (!verifiedInitialWorldPreview(preview, runId, branchId, request, options))
        throw new Error('Regenerated preview is inconsistent with the exact reviewed source.')
      const original = new Map(review.preview.state.players.map(p => [p.player_id, p]))
      for (const id of retained) {
        const before = original.get(id)
        const after = preview.state.players.find(p => p.player_id === id)
        if (!before || !after || before.name !== after.name ||
          before.country_code !== after.country_code ||
          before.age_years_at_season_start !== after.age_years_at_season_start ||
          before.current_ability !== after.current_ability ||
          before.potential_ability !== after.potential_ability ||
          before.potential_tier !== after.potential_tier)
          throw new Error('A Keep player changed in the regenerated preview.')
      }
      return { runId, branchId, head, sourceFingerprint: snapshotFingerprint,
        draftVersion: draft.draft_version, request, preview, retained }
    },
    onSuccess: value => {
      setReview(value); setKeptIds(value.retained)
      setBulkSelectedIds([]); setBulkStagedFingerprint(null); setBulkUndo(null)
      setPendingFieldLocks(orderedPreviewFieldLocks(value.request.generation.field_locks ?? []))
      setRerollSeed(value.request.generation.seed + 1)
      setApproved(false); setNotice(
        'Regenerated the remaining players. Keep selections remain available for another pass; Adopt and Save are separate.'
      )
    }
  })

  // No field value supplied by the browser is authoritative until the server
  // returns a fresh exact preview. A failed edit leaves the prior review intact.
  const fieldPreviewAction = useMutation({
    mutationFn: async ({regenerate, bulk = false}: {regenerate: boolean; bulk?: boolean}) => {
      if (bulk && (!bulkStagedFingerprint ||
          review?.preview.fingerprint !== bulkStagedFingerprint || !locksDirty))
        throw new Error('Bulk changes must be staged from this exact verified preview.')
      if (!fieldEditingEnabled || !review || !draft || !snapshotFingerprint ||
          keepSelectionDirty)
        throw new Error('Apply or revert pending Keep selection before editing source fields.')
      if (regenerate && (locksDirty || !pendingFieldLocks.length ||
          !Number.isSafeInteger(rerollSeed) ||
          rerollSeed === review.request.generation.seed))
        throw new Error('Apply all locks first and choose a new seed before regenerating unlocked fields.')
      const previous = review.request.generation
      const nextLocks = orderedPreviewFieldLocks(pendingFieldLocks)
      const versioned = previous.session_schema_version === 'run_world_generation_session.v2'
      const needsVersioned = versioned || previous.keep_from_seed != null
      if (regenerate && needsVersioned)
        throw new Error('After Keep, apply edits then regenerate using Session Keep.')
      const automaticFields = approvedFieldLocks
        .filter(locked => !nextLocks.some(next =>
          locked.player_id === next.player_id && locked.field === next.field))
        .map(locked => ({player_id: locked.player_id, field: locked.field}))
      const step = {
        kind: 'edit' as const,
        seed: previous.seed,
        source_preview_fingerprint: review.preview.state.run_world_pool_preview_fingerprint,
        keep_player_ids: [],
        field_locks: nextLocks,
        ...(automaticFields.length ? {automatic_fields: automaticFields} : {})
      }
      const generation = needsVersioned ? {
        ...previous, field_locks: nextLocks,
        session_schema_version: 'run_world_generation_session.v2' as const,
        session_origin_request: versioned ? previous.session_origin_request : previous,
        session_origin_fingerprint: versioned
          ? previous.session_origin_fingerprint
          : review.preview.state.run_world_pool_preview_fingerprint,
        session_steps: [...(previous.session_steps ?? []), step],
      } : {
        ...previous, seed: regenerate ? rerollSeed : previous.seed,
        field_locks: nextLocks,
      }
      const request: RunInitialWorldAdoption = {
        ...review.request,
        command_id: `admin-initial-world-${crypto.randomUUID()}`,
        generation,
      }
      const preview = await previewRunOwnedInitialWorld(runId, branchId, request)
      if (!verifiedInitialWorldPreview(preview, runId, branchId, request, options))
        throw new Error('Server preview does not match all verified locked values or generation scope.')
      return { runId, branchId, head, sourceFingerprint: snapshotFingerprint,
        draftVersion: draft.draft_version, request, preview, regenerate,
        bulk, undoPrevious: bulk ? review : null }
    },
    onSuccess: value => {
      setReview(value)
      setPendingFieldLocks(orderedPreviewFieldLocks(value.request.generation.field_locks ?? []))
      setBulkUndo(value.bulk && value.undoPrevious
        ? {previous:value.undoPrevious, appliedFingerprint:value.preview.fingerprint} : null)
      setBulkStagedFingerprint(null); setBulkSelectedIds([])
      setApproved(false)
      if (value.regenerate) setRerollSeed(value.request.generation.seed + 1)
      setNotice(value.regenerate
        ? 'Unlocked source fields regenerated; locked values were verified. Review before Adopt and Save.'
        : value.bulk
          ? 'Bulk changes verified by server preview. Run unchanged; one session Undo is available.'
          : 'Field locks applied to the exact server preview; Run remains unchanged.')
    }
  })

  const adoptAction = useMutation({
    mutationFn: async (current: ReviewedWorld) => {
      const result = await adoptRunOwnedInitialWorld(
        current.runId, current.branchId, current.request, current.preview.fingerprint,
        { head: current.head, draftVersion: current.draftVersion,
          packageFingerprint: current.sourceFingerprint }
      )
      if (result.run_id !== current.runId || result.branch_id !== current.branchId ||
        result.adopted_by_command_id !== current.request.command_id ||
        result.world_package_id !== current.request.generation.world_package_id ||
        result.players.length !== current.preview.state.players.length ||
        result.adoption_request_fingerprint !== current.preview.state.adoption_request_fingerprint)
        throw new Error('Adoption response has unexpected ownership or source identity. Inspect stored state before saving.')
      return { current, result }
    },
    onSuccess: async ({ current }) => {
      setReview(null); setApproved(false)
      setPendingSave({ runId: current.runId, branchId: current.branchId,
        head: current.head, fingerprint: current.preview.fingerprint })
      setNotice('Players were adopted to Run-owned InitialWorld. A separate Saved Revision is still required.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-owned-initial-world', current.runId, current.branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', current.runId, current.branchId] })
      ])
    },
    onError: () => {
      setReview(null); setApproved(false)
      setNotice('Adoption was not verified. Read the stored InitialWorld before trying again.')
      void queryClient.invalidateQueries({ queryKey: ['run-owned-initial-world', runId, branchId] })
    }
  })

  const savePreviewQuery = useQuery({
    queryKey: ['initial-world-save-preview', runId, branchId, pendingSave?.fingerprint],
    queryFn: () => previewRunInitialWorldSave(runId, branchId),
    enabled: Boolean(pendingSave || existing),
    retry: false
  })
  const savePreflight = savePreviewQuery.data
  const canResume = Boolean(!pendingSave && editable && existing && draft?.status === 'clean' &&
    draft.base_saved_revision_id === head && savePreflight &&
    /^[a-f0-9]{64}$/.test(savePreflight.initial_world_fingerprint) &&
    savePreflight.draft_version === draft.draft_version &&
    (savePreflight.run_id === undefined || savePreflight.run_id === runId) &&
    (savePreflight.branch_id === undefined || savePreflight.branch_id === branchId) &&
    (savePreflight.saved_head_revision_id === undefined || savePreflight.saved_head_revision_id === head) &&
    savePreflight.has_unsaved_changes === true && savePreflight.can_save === true)
  const saveReady = Boolean(pendingSave && pendingSave.runId === runId &&
    pendingSave.branchId === branchId && pendingSave.head === head &&
    existing && existing.adopted_by_command_id &&
    existing.world_package_id &&
    draft?.base_saved_revision_id === head && draft?.status === 'clean' &&
    savePreflight && savePreflight.initial_world_fingerprint === pendingSave.fingerprint &&
    savePreflight.draft_version === draft?.draft_version &&
    (savePreflight.run_id === undefined || savePreflight.run_id === runId) &&
    (savePreflight.branch_id === undefined || savePreflight.branch_id === branchId) &&
    (savePreflight.saved_head_revision_id === undefined || savePreflight.saved_head_revision_id === head) &&
    savePreflight.has_unsaved_changes === true && savePreflight.can_save === true)

  const saveAction = useMutation({
    mutationFn: async () => {
      if (!pendingSave || !savePreflight || !saveReady)
        throw new Error('InitialWorld Save preflight no longer matches the reviewed adoption.')
      const saved = await saveRunOwnedInitialWorld(
        runId, branchId, savePreflight.draft_version, pendingSave.fingerprint
      )
      if (!saved.saved_revision.revision_id ||
        saved.working_draft.run_id !== runId || saved.working_draft.branch_id !== branchId ||
        saved.working_draft.base_saved_revision_id !== saved.saved_revision.revision_id ||
        saved.working_draft.status !== 'clean')
        throw new Error('Saved Revision was not verified. Refresh Run-owned state.')
      return saved
    },
    onSuccess: async () => {
      setPendingSave(null); setSaveApproved(false)
      acknowledgeSavedRunForm(runId, branchId)
      setNotice('First-season InitialWorld is saved and recoverable. Next: derive the initial ranking.')
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['admin-run-branches', runId] }),
        queryClient.invalidateQueries({ queryKey: ['saved-revision-history', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['run-owned-initial-world', runId, branchId] }),
        queryClient.invalidateQueries({ queryKey: ['package-working-draft', runId, branchId] })
      ])
    }
  })

  const proposalSaveAction = useMutation({
    mutationFn: async () => {
      if (!review || !reviewMatches || !canPreview ||
          !proposalName.trim() || proposalName.trim().length > 160 ||
          !Number.isSafeInteger(rerollSeed))
        throw new Error('A verified reviewed cohort and a valid proposal name are required.')
      const data = await saveRunGenerationProposal(runId, branchId, {
        proposal_id: crypto.randomUUID(),
        label: proposalName.trim(),
        saved_revision_id: review.head,
        draft_version: review.draftVersion,
        package_fingerprint: review.sourceFingerprint,
        preview_fingerprint: review.preview.fingerprint,
        source_seed: reviewBaseSeed!,
        next_seed: rerollSeed,
        selected_keep_ids: [...keptIds].sort(),
        pending_field_locks: orderedPreviewFieldLocks(pendingFieldLocks),
        request: review.request
      })
      if (data.run_id !== runId || data.branch_id !== branchId ||
          data.preview_fingerprint !== review.preview.fingerprint ||
          data.saved_revision_id !== review.head)
        throw new Error('The saved proposal confirmation does not match the reviewed source.')
      return data
    },
    onSuccess: data => {
      setSelectedProposalId(data.proposal_id)
      setNotice('Generation proposal saved separately; no InitialWorld Adopt or Run Save occurred.')
      void queryClient.invalidateQueries({queryKey:['generation-proposals',runId,branchId]})
    }
  })

  // Historical inspection is intentionally separate from Open/Adopt. It
  // works when current HEAD, Working Draft or the World snapshot has changed.
  const inspectProposalAction = useMutation({
    mutationFn: async () => {
      if (!selectedProposalId || !branchId)
        throw new Error('Select a proposal from this Run/Branch for inspection.')
      const response = await inspectRunGenerationProposal(runId, branchId, selectedProposalId)
      const saved = response.proposal
      if (response.schema_version !== 'run_generation_proposal_inspection.v1' ||
          response.historical_only !== true ||
          saved.run_id !== runId || saved.branch_id !== branchId ||
          saved.proposal_id !== selectedProposalId ||
          saved.preview_fingerprint !== saved.preview.fingerprint ||
          saved.preview.state.run_id !== runId || saved.preview.state.branch_id !== branchId ||
          saved.request.generation.world_package_id !== saved.preview.state.world_package_id ||
          saved.preview.state.players.length !== saved.request.generation.target_pool_size)
        throw new Error('Historical proposal inspection returned inconsistent Run/Branch data.')
      return response
    },
    onSuccess: data => {
      setInspection(data); setRevalidated(null); setReview(null); setApproved(false)
      setNotice('Historical proposal opened read-only. No generation, Adopt or Save performed.')
    }
  })

  const revalidateProposalAction = useMutation({
    mutationFn: async () => {
      if (!inspection || inspection.proposal.proposal_id !== selectedProposalId ||
          !editable || !draft || draft.status !== 'clean' || !snapshotFingerprint ||
          existing || pendingSave)
        throw new Error('Revalidation needs the same owned Branch with a clean, writable Saved HEAD.')
      const current = {saved_revision_id: head, draft_version: draft.draft_version,
        package_fingerprint: snapshotFingerprint}
      const response = await revalidateRunGenerationProposal(runId, branchId,
        selectedProposalId, {
          expected_head: current.saved_revision_id,
          expected_draft_version: current.draft_version,
          expected_package_fingerprint: current.package_fingerprint
        })
      if (response.schema_version !== 'run_generation_proposal_revalidation.v1' ||
          response.preview_only !== true || response.proposal_id !== selectedProposalId ||
          response.original_preview_fingerprint !== inspection.proposal.preview_fingerprint ||
          JSON.stringify(response.request) !== JSON.stringify(inspection.proposal.request) ||
          response.current_context.saved_revision_id !== current.saved_revision_id ||
          response.current_context.draft_version !== current.draft_version ||
          response.current_context.package_fingerprint !== current.package_fingerprint ||
          response.preview.state.run_id !== runId || response.preview.state.branch_id !== branchId ||
          !/^[a-f0-9]{64}$/.test(response.preview.fingerprint))
        throw new Error('Current-target revalidation returned unexpected provenance.')
      return response
    },
    onSuccess: data => {
      setRevalidated(data); setApproved(false)
      setNotice('Fresh server preview available for comparison. Explicitly select it before Adopt.')
    }
  })

  const useRevalidatedProposal = () => {
    if (!inspection || !revalidated || !canPreview || !draft || !snapshotFingerprint ||
        selectedProposalId !== inspection.proposal.proposal_id ||
        revalidated.proposal_id !== selectedProposalId ||
        revalidated.current_context.saved_revision_id !== head ||
        revalidated.current_context.draft_version !== draft.draft_version ||
        revalidated.current_context.package_fingerprint !== snapshotFingerprint)
      return
    setRestoringRevalidated(true)
    setRestoringProposal({
      ...inspection.proposal,
      saved_revision_id: head,
      draft_version: draft.draft_version,
      package_fingerprint: snapshotFingerprint,
      preview_fingerprint: revalidated.preview.fingerprint,
      request: revalidated.request,
      preview: revalidated.preview,
    })
    const generation = revalidated.request.generation
    setSourceId(generation.world_package_id)
    setSeed(inspection.proposal.source_seed)
    setPoolSize(generation.target_pool_size)
    setCountryCode(generation.country_code ?? '')
    setCountryQuotas(generation.country_quotas ?? [])
    setRegion(generation.geographic_region ?? '')
    setTravelRegion(generation.travel_region ?? '')
    setMinAge(String(generation.min_age ?? ''))
    setMaxAge(String(generation.max_age ?? ''))
    setBestN(revalidated.request.best_n)
    setAuditReason(revalidated.request.audit_reason)
    setApproved(false)
  }

  useEffect(() => {
    setInspection(null); setRevalidated(null)
  }, [runId, branchId, head, snapshotFingerprint, draft?.draft_version, selectedProposalId])

  const proposalLoadAction = useMutation({
    mutationFn: async () => {
      if (!selectedProposalId || !canPreview || !draft || !snapshotFingerprint)
        throw new Error('Select a proposal in the current writable Run/Branch.')
      const data = await loadRunGenerationProposal(runId, branchId, selectedProposalId)
      if (data.run_id !== runId || data.branch_id !== branchId ||
          data.saved_revision_id !== head ||
          data.draft_version !== draft.draft_version ||
          data.package_fingerprint !== snapshotFingerprint ||
          data.preview_fingerprint !== data.preview.fingerprint ||
          data.preview.state.run_id !== runId || data.preview.state.branch_id !== branchId ||
          data.request.generation.world_package_id !== data.preview.state.world_package_id)
        throw new Error('Saved proposal belongs to an outdated or different Run/Branch/World.')
      return data
    },
    onSuccess: data => {
      // Inputs change first. The restoration effect below runs only after the
      // matching exact saved World/conditions/options are available.
      const generation = data.request.generation
      setRestoringProposal(data)
      setSourceId(generation.world_package_id)
      setSeed(data.source_seed); setPoolSize(generation.target_pool_size)
      setCountryCode(generation.country_code ?? '')
      setCountryQuotas(generation.country_quotas ?? [])
      setRegion(generation.geographic_region ?? '')
      setTravelRegion(generation.travel_region ?? '')
      setMinAge(String(generation.min_age ?? ''))
      setMaxAge(String(generation.max_age ?? ''))
      setBestN(data.request.best_n ?? 15)
      setAuditReason(data.request.audit_reason)
      setApproved(false)
    }
  })

  useEffect(()=>{
    if (!restoringProposal || !canPreview || !draft || !snapshotFingerprint || !options)
      return
    const data=restoringProposal
    const generation=data.request.generation
    if (selectedWorldId !== generation.world_package_id || seed !== data.source_seed ||
        poolSize !== generation.target_pool_size ||
        countryCode !== (generation.country_code ?? '') ||
        JSON.stringify(countryQuotas) !== JSON.stringify(generation.country_quotas ?? []) ||
        region !== (generation.geographic_region ?? '') ||
        travelRegion !== (generation.travel_region ?? '') ||
        minAge !== String(generation.min_age ?? '') ||
        maxAge !== String(generation.max_age ?? '') ||
        bestN !== data.request.best_n || auditReason !== data.request.audit_reason)
      return
    if (!verifiedInitialWorldPreview(
      data.preview, runId, branchId, data.request, options,
    )) {
      setNotice('Saved proposal validation failed; the saved review was not restored.')
      setRestoringProposal(null)
      return
    }
    setReview({
      runId, branchId, head, sourceFingerprint:snapshotFingerprint,
      draftVersion:draft.draft_version, request:data.request, preview:data.preview
    })
    setReviewBaseSeed(data.source_seed)
    setKeptIds(data.selected_keep_ids)
    setPendingFieldLocks(orderedPreviewFieldLocks(data.pending_field_locks))
    setRerollSeed(data.next_seed)
    setSelectedPlayerId(null)
    setApproved(false)
    setNotice(restoringRevalidated
      ? 'Explicitly revalidated preview selected. Review and approve before Adopt; manual Save remains separate.'
      : 'Exact saved review restored from SQLite without regenerating. Adopt and Run Save remain separate.')
    setRestoringProposal(null)
    setRestoringRevalidated(false)
  }, [restoringProposal, canPreview, draft, snapshotFingerprint, options,
      selectedWorldId, seed, poolSize, countryCode, countryQuotas, region, travelRegion,
      minAge, maxAge, bestN, auditReason, runId, branchId, head])

  const proposalDeleteAction = useMutation({
    mutationFn: async () => {
      if (!selectedProposalId || !editable) throw new Error('Select a saved proposal first.')
      await deleteRunGenerationProposal(runId, branchId, selectedProposalId)
    },
    onSuccess: () => {
      setSelectedProposalId('')
      setNotice('Only the saved proposal was deleted; Run and players were unchanged.')
      void queryClient.invalidateQueries({queryKey:['generation-proposals',runId,branchId]})
    }
  })

  const pendingKeepChange = keepSelectionDirty
  const canAdopt = reviewMatches && approved && !pendingKeepChange && !locksDirty &&
    !fieldPreviewAction.isPending &&
    !regenerateAction.isPending && !adoptAction.isPending && !previewAction.isPending
  const viewedPlayers = review?.preview.state.players ?? []

  return <SectionCard title={cs ? 'Generovat hráče — první úplná dávka' : 'Generate first-season players'}>
    <p className="status">{cs
      ? 'První funkční dávka 1–1000 hráčů pro sezónu 2000/01. Používá pouze uložený World Package dané branche. Náhled nic nezapisuje; potvrzení připraví InitialWorld a teprve ruční Save vytváří Saved Revision.'
      : 'First supported complete batch (1–1000 players) for season 2000/01. Uses the saved Run-owned World Package only. Preview never writes; confirmation stages InitialWorld, then manual Save creates a Saved Revision.'}</p>
    <p className="status">{cs
      ? 'Závazné podmínky země, regionu a věku platí pro všechny hráče dávky. Prázdná pole zachovávají automatické rozdělení. Přesné kvóty zemí a automatické doplnění jsou podporované; překrývající se skupiny zatím ne.'
      : 'Hard country, region and age conditions apply to every player. Blank conditions preserve automatic allocation. Exact country quotas and the non-quota remainder are supported; overlapping groups are not yet supported.'}</p>
    {existing && <p role="status">{cs ? 'InitialWorld obsahuje' : 'InitialWorld exists:'} {existing.players.length} {cs ? 'hráčů ze světa' : 'players from'} {existing.world_package_id}; seed {existing.bootstrap_seed}. {cs ? 'Stávající hráči se bez potvrzení nepřegenerují ani nepřepíší.' : 'Existing players cannot be silently regenerated or overwritten.'}</p>}
    {unexpectedExistingError && <p role="alert" className="error">Cannot verify whether this Run already has InitialWorld: {formatApiError(existingQuery.error)}</p>}
    {packageQuery.isError && <p role="alert" className="error">Run World state unavailable: {formatApiError(packageQuery.error)}</p>}
    {draftQuery.isError && <p role="alert" className="error">Working Draft unavailable: {formatApiError(draftQuery.error)}</p>}
    {!existing && worldIds.length === 0 && <p>{cs
      ? 'Nejprve musíš zkopírovat World Package do Runu a ručně jej uložit.'
      : 'First copy a World Package into the Run and manually Save its revision.'}
      {' '}<Link to={'/admin/runs/' + encodeURIComponent(runId) + '/manage'}>
        {cs ? 'Otevřít správu Runu →' : 'Open Run Management →'}
      </Link></p>}
    {draft && draft.status !== 'clean' && !pendingSave && <p className="status">Save or resolve existing Working Draft changes before generating new players.</p>}
    <div className="generator-workspace" aria-label="Player generator workspace">
      <details className="generator-conditions" open>
        <summary>{cs ? 'Podmínky generování' : 'Generation conditions'}
          <span>{cs ? ' · rozbalit / sbalit' : ' · expand / collapse'}</span>
        </summary>
        <div className="generator-conditions-body">
    <label>{tr('Run-owned World')}{' '}
      <select aria-label="Run World for player generation" value={selectedWorldId}
        onChange={event => { setSourceId(event.target.value); setCountryCode(''); setCountryQuotas([]); setRegion(''); setTravelRegion('') }}>
        {worldIds.map(id => <option key={id} value={id}>{id}</option>)}
      </select>
    </label>
    <div className="form-grid" aria-label="Hard player generation conditions">
      <label>{cs ? 'Sportovní země' : 'Sport country'}
        <select aria-label="Player generation sport country" value={countryCode}
          disabled={!options} onChange={event => setCountryCode(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.countries ?? []).map(country =>
            <option key={country.code} value={country.code}>{country.code} — {country.name}</option>)}
        </select>
      </label>
      <label>{cs ? 'Geografický region' : 'Geographic Region'}
        <select aria-label="Player generation geographic region" value={region}
          disabled={!options} onChange={event => setRegion(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.geographic_regions ?? [...new Set(options?.countries.map(c => c.region) ?? [])].sort()).map(item =>
            <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <label>{cs ? 'Cestovní region' : 'Travel Region'}
        <select aria-label="Player generation travel region" value={travelRegion}
          disabled={!options} onChange={event => setTravelRegion(event.target.value)}>
          <option value="">{cs ? 'Automaticky podle světa' : 'Automatic from World'}</option>
          {(options?.travel_regions ?? [...new Set(options?.countries.map(c => c.travel_region) ?? [])].sort()).map(item =>
            <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
    </div>
    {optionsQuery.isPending && editable && selectedWorldId && !existing &&
      <p role="status">{cs ? 'Ověřuji země a regiony uloženého světa…' : 'Checking saved World countries and regions…'}</p>}
    {optionsQuery.error && <p role="alert" className="error">
      {cs ? 'Podmínky uloženého světa nelze ověřit' : 'Saved World conditions unavailable'}: {formatApiError(optionsQuery.error)}
    </p>}
    {optionsQuery.isSuccess && !options && <p role="alert" className="error">
      {cs ? 'Odpověď podmínek nepatří této branchi, revizi nebo světu.' : 'World condition response does not match this Branch, revision or World.'}
    </p>}
    {conditionConflict && <p role="alert" className="error">{cs ? 'Rozpor podmínek' : 'Condition conflict'}: {conditionConflict}</p>}
    {options && !conditionConflict && <p className="status">
      {cs ? 'Závazný výběr' : 'Hard selection'}: {countryCode || (cs ? 'všechny země' : 'all countries')} ·
      {' '}{region || (cs ? 'všechny geografické regiony' : 'all geographic regions')} ·
      {' '}{travelRegion || (cs ? 'všechny cestovní regiony' : 'all travel regions')}.
      {' '}{cs ? 'Nevybrané vlastnosti zůstanou přirozeně proměnlivé.' : 'Unconstrained attributes remain naturally variable.'}
    </p>}
    <div className="form-grid" aria-label="Hard first-season age conditions">
      <label>{cs ? 'Minimální věk (15–45)' : 'Minimum age (15–45)'}
        <input type="number" min={15} max={45} step={1}
          aria-label="Player generation minimum age"
          placeholder={cs ? 'Automaticky' : 'Automatic'}
          value={minAge} onChange={e => setMinAge(e.target.value)} />
      </label>
      <label>{cs ? 'Maximální věk (15–45)' : 'Maximum age (15–45)'}
        <input type="number" min={15} max={45} step={1}
          aria-label="Player generation maximum age"
          placeholder={cs ? 'Automaticky' : 'Automatic'}
          value={maxAge} onChange={e => setMaxAge(e.target.value)} />
      </label>
    </div>
    {ageConflict && <p role="alert" className="error">{cs ? 'Rozpor věkových podmínek' : 'Age condition conflict'}: {ageConflict}</p>}
    <p className="status">{cs
      ? 'Věk k prvnímu týdnu sezóny 2000/01. Při omezení věku se přepočítají pravděpodobnosti existujících kariérních fází, nikoli potenciál hráčů podle země.'
      : 'Age at Week 1 of 2000/01. Age bounds condition the existing career-stage weights, not nationality-based innate potential.'}</p>
    <label>Seed <input aria-label="Player generation seed" type="number" value={seed}
      onChange={event => setSeed(Number(event.target.value))} /></label>
    <label>{tr('Number of players (1–1000)')}{' '}<input aria-label="Number of generated players" type="number"
      min={1} max={1000} value={poolSize} onChange={event => setPoolSize(Number(event.target.value))} /></label>
    <section aria-label="Exact country quotas" className="section-subtle">
      <h4>{cs ? 'Přesné počty zemí' : 'Exact country quotas'}</h4>
      <p className="status">{cs
        ? 'Kvóty platí v celé dávce, nikoli jako další hráči. Zbytek tvoří jiné způsobilé země. Kvóta 0 vyloučí zemi.'
        : 'Whole-batch quotas, not extra players. Only other eligible countries fill the remainder. Zero excludes a country.'}</p>
      {countryQuotas.map(quota => <div key={quota.country_code} className="form-grid">
        <label>{cs ? 'Země kvóty' : 'Quota country'}
          <select aria-label={`Quota country ${quota.country_code}`} value={quota.country_code}
            onChange={e => setCountryQuotas(current => current.map(item =>
              item.country_code === quota.country_code
                ? { ...item, country_code: e.target.value } : item
            ).sort((a,b) => a.country_code.localeCompare(b.country_code)))}>
            {eligibleQuotaCountries.filter(c => c.code === quota.country_code ||
              !countryQuotas.some(item => item.country_code === c.code))
              .map(c => <option key={c.code} value={c.code}>{c.code} — {c.name}</option>)}
          </select>
        </label>
        <label>{cs ? 'Přesně hráčů' : 'Exact players'}
          <input type="number" min={0} max={poolSize} step={1}
            aria-label={`Exact quota ${quota.country_code}`} value={quota.count}
            onChange={e => setCountryQuotas(current => current.map(item =>
              item.country_code === quota.country_code
                ? { ...item, count: Number(e.target.value) } : item))} />
        </label>
        <button type="button" aria-label={`Remove country quota ${quota.country_code}`}
          onClick={() => setCountryQuotas(current =>
            current.filter(item => item.country_code !== quota.country_code))}>
          {cs ? 'Odebrat' : 'Remove'}
        </button>
      </div>)}
      <button type="button" aria-label="Add country quota"
        disabled={!options || eligibleQuotaCountries.every(c => countryQuotas.some(q => q.country_code === c.code))}
        onClick={() => {
          const next = eligibleQuotaCountries.find(c => !countryQuotas.some(q => q.country_code === c.code))
          if (next) setCountryQuotas(current => [...current, {
            country_code: next.code, count: 0
          }].sort((a,b) => a.country_code.localeCompare(b.country_code)))
        }}>
        {cs ? 'Přidat kvótu země' : 'Add country quota'}
      </button>
      <p className="status" aria-label="Country quota summary">
        {poolSize} {cs ? 'celkem' : 'total'} · {fixedQuotaTotal} {cs ? 'přesně určeno' : 'exact'} ·
        {' '}{poolSize - fixedQuotaTotal} {cs ? 'automaticky' : 'automatic'}
      </p>
      {quotaConflict && <p role="alert" className="error">
        {cs ? 'Rozpor kvót' : 'Country quota conflict'}: {quotaConflict}
      </p>}
    </section>
    <label>{tr('First-season ranking Best N')}{' '}<input aria-label="First-season ranking Best N" type="number"
      min={1} value={bestN} onChange={event => setBestN(Number(event.target.value))} /></label>
    <label>{tr('Audit reason')}{' '}<input aria-label="InitialWorld audit reason" maxLength={1000}
      value={auditReason} onChange={event => setAuditReason(event.target.value)} /></label>
    <p className="status">Lifecycle retirement-age input: 46 (current first-season policy). No player talent calibration is changed.</p>
    <button type="button" disabled={!canPreview || previewAction.isPending || regenerateAction.isPending ||
        adoptAction.isPending || saveAction.isPending}
      onClick={() => { setReview(null); setApproved(false); previewAction.mutate() }}>
      {previewAction.isPending ? (cs ? 'Generuji náhled…' : 'Generating preview…') : (cs ? 'Generovat – zobrazit náhled' : 'Preview generated players')}
    </button>
    {previewAction.error && <p role="alert" className="error">Preview failed: {formatApiError(previewAction.error)}</p>}
        </div>
      </details>
      <div className="generator-results" aria-label="Generator results and review">
        <header className="generator-review-header">
          <h4>{cs ? 'Návrh a další kroky' : 'Review and next steps'}</h4>
          <p role="status">{review
            ? (cs ? `Ověřený návrh: ${viewedPlayers.length} hráčů. Run se náhledem nezměnil.`
              : `Verified proposal: ${viewedPlayers.length} players. Preview made no Run changes.`)
            : existing
              ? (cs ? `Počáteční svět: ${existing.players.length} hráčů.`
                : `Opening world: ${existing.players.length} players.`)
              : (cs ? 'Nejprve nastav podmínky a vygeneruj náhled.'
                : 'Set conditions and generate a preview first.')}</p>
          <p className="status">{cs
            ? 'Postup: Generovat → zkontrolovat hráče → potvrdit přidání → samostatně ručně uložit revizi. Uložit návrh neznamená přidat hráče.'
            : 'Workflow: Generate → review players → confirm addition → manually Save the revision. Saving a proposal does not add players.'}</p>
          {(conditionConflict || ageConflict || quotaConflict) && <p className="status">
            {cs ? 'Před pokračováním oprav rozporné podmínky v levém panelu.'
              : 'Resolve conflicting conditions in the left panel before continuing.'}
          </p>}
          {existing && <p className="status">{cs
            ? 'Přidat vybrané funguje jen před prvním rankingem a sportovní aktivitou; nejedná se o přidávání během sezóny.'
            : 'Add Selected is available only before ranking and sporting activity; this is not in-season player creation.'}</p>}
        </header>
    {existing && savePreflight && draft && snapshotFingerprint && <RunInitialWorldSelectedAppendPanel
      key={runId+':'+branchId+':'+head}
      runId={runId} branchId={branchId} head={head}
      draftVersion={draft.draft_version}
      packageFingerprint={snapshotFingerprint}
      currentFingerprint={savePreflight.initial_world_fingerprint}
      current={existing} locale={locale}
      enabled={editable && draft.status === 'clean' &&
        draft.base_saved_revision_id === head &&
        savePreflight.has_unsaved_changes === false &&
        !pendingSave}
    />}
    <section aria-label="Saved player generation proposals" className="section-subtle">
      <h4>{cs ? 'Uložené generační návrhy' : 'Saved generation proposals'}</h4>
      <p className="status">{cs
        ? 'Uloží celý náhled i rozpracované Keep a zámky do SQLite. Obnovení nic znovu negeneruje a nemění Run. Přijetí a uložení hráčů se potvrzuje zvlášť.'
        : 'Save the entire reviewed cohort plus pending Keep/field locks to SQLite. Reopening does not regenerate or modify Run. Adopt and Run Save remain separate.'}</p>
      <label>{cs ? 'Název návrhu' : 'Proposal name'}
        <input aria-label="Generation proposal name" maxLength={160}
          value={proposalName} onChange={e=>setProposalName(e.target.value)} />
      </label>
      <button type="button"
        disabled={!reviewMatches || !canPreview || !proposalName.trim() ||
          !Number.isSafeInteger(rerollSeed) ||
          proposalSaveAction.isPending || proposalLoadAction.isPending}
        onClick={()=>proposalSaveAction.mutate()}>
        {proposalSaveAction.isPending ? tr('Saving proposal…') : tr('Save generation proposal')}
      </button>
      <label>{cs ? 'Existující návrhy' : 'Saved proposals'}
        <select aria-label="Select saved generation proposal"
          value={selectedProposalId} onChange={e=>setSelectedProposalId(e.target.value)}>
          <option value="">— {cs?'Vyber návrh':'Select proposal'} —</option>
          {(proposalQuery.data?.proposals ?? []).map(p=>
            <option key={p.proposal_id} value={p.proposal_id}>
              {p.label} · {p.preview_fingerprint.slice(0,10)}
            </option>
          )}
        </select>
      </label>
      <button type="button" disabled={!selectedProposalId || !canPreview || proposalLoadAction.isPending}
        onClick={()=>proposalLoadAction.mutate()}>
        {proposalLoadAction.isPending ? tr('Restoring…') : tr('Open saved proposal')}
      </button>
      <button type="button"
        disabled={!selectedProposalId || inspectProposalAction.isPending || !branchId}
        onClick={()=>inspectProposalAction.mutate()}>
        {inspectProposalAction.isPending ? tr('Inspecting…') : tr('Inspect historical proposal (read-only)')}
      </button>
      <button type="button" disabled={!selectedProposalId || !editable || proposalDeleteAction.isPending}
        onClick={()=>proposalDeleteAction.mutate()}>{tr('Delete saved proposal')}</button>
      {restoringProposal && <p role="status">{tr('Restoring reviewed proposal conditions…')}</p>}
      {proposalQuery.isError && <p role="alert">{tr('Saved proposals unavailable:')} {formatApiError(proposalQuery.error)}</p>}
      {proposalSaveAction.error && <p role="alert">{tr('Proposal Save failed:')} {formatApiError(proposalSaveAction.error)}</p>}
      {proposalLoadAction.error && <p role="alert">{tr('Proposal Restore failed:')} {formatApiError(proposalLoadAction.error)}</p>}
      {inspectProposalAction.error && <p role="alert">{tr('Historical inspection failed:')} {formatApiError(inspectProposalAction.error)}</p>}
      {revalidateProposalAction.error && <p role="alert">{tr('Proposal revalidation failed:')} {formatApiError(revalidateProposalAction.error)}</p>}
      {inspection && inspection.proposal.proposal_id === selectedProposalId && <section
        aria-label="Historical generation proposal inspection">
        <h5>{tr('Historical snapshot')} · {inspection.proposal.label}</h5>
        <p role="status">{tr('Read-only saved cohort from')} {inspection.proposal.saved_revision_id},
          Draft v{inspection.proposal.draft_version}, World {inspection.proposal.request.generation.world_package_id}.
          {tr('Original preview')} <code>{inspection.proposal.preview_fingerprint.slice(0, 16)}…</code>.
          {tr('No regeneration performed.')}</p>
        <p>{inspection.context.head_matches ? tr('HEAD matches') : tr('Saved HEAD changed')} ·
          {' '}{inspection.context.draft_matches ? tr('Draft matches and clean') : tr('Draft changed or dirty')} ·
          {' '}{inspection.context.package_matches ? tr('World snapshot matches') : tr('World snapshot changed')} ·
          {' '}{inspection.context.initial_world_exists ? tr('InitialWorld already exists') : tr('No InitialWorld adopted')}</p>
        {inspection.context.revalidation_required && <p role="alert">
          {cs ? 'Historický snímek nelze přímo převzít do aktuálního Runu. Je nutné nové ověření serverem; uložený návrh se nezmění.' : 'Historical snapshot is not authorized for current-target Adopt. An explicit new server verification is required; the stored proposal will not be modified.'}
        </p>}
        <GeneratedPlayerReviewInspector
          key={'historical-' + inspection.proposal.preview_fingerprint}
          players={inspection.proposal.preview.state.players} locale={locale} />
        <button type="button" disabled={!editable || !draft || draft.status !== 'clean' ||
            !snapshotFingerprint || Boolean(existing) || Boolean(pendingSave) ||
            revalidateProposalAction.isPending}
          onClick={()=>revalidateProposalAction.mutate()}>
          {revalidateProposalAction.isPending ? tr('Revalidating current target…') :
            tr('Revalidate against current Run (new preview)')}
        </button>
        {revalidated && revalidated.proposal_id === selectedProposalId && <section
          aria-label="Revalidated generation proposal comparison">
          <h5>{tr('Fresh result versus saved historical snapshot')}</h5>
          <p>{tr('Old')} {revalidated.comparison.old_count}, {tr('new')} {revalidated.comparison.new_count} ·
            {' '}{tr('added')} {revalidated.comparison.added_identities} ·
            {' '}{tr('removed')} {revalidated.comparison.removed_identities} ·
            {' '}{tr('changed profiles')} {revalidated.comparison.changed_profiles} ·
            {' '}{tr('unchanged')} {revalidated.comparison.unchanged_profiles}.</p>
          <p>{tr('New preview')} <code>{revalidated.preview.fingerprint.slice(0, 16)}…</code>.
            {cs ? 'Opětovné ověření nepovoluje převzetí ani nic nezapisuje do Runu.' : 'Revalidation itself does not approve adoption or write any Run state.'}</p>
          <button type="button" disabled={!canPreview ||
              revalidated.current_context.saved_revision_id !== head ||
              revalidated.current_context.draft_version !== draft?.draft_version ||
              revalidated.current_context.package_fingerprint !== snapshotFingerprint}
            onClick={useRevalidatedProposal}>{tr('Use revalidated preview for review')}</button>
        </section>}
      </section>}
      {proposalDeleteAction.error && <p role="alert">{tr('Proposal Delete failed:')} {formatApiError(proposalDeleteAction.error)}</p>}
    </section>

    {review && <section aria-label="Generated player review">
      <h4>{tr('Review')} {viewedPlayers.length} {tr('players')}</h4>
      <p>Run: {review.runId} · Branch: {review.branchId} · Saved HEAD: <code>{review.head}</code></p>
      <p>{cs ? 'Svět' : 'World'}: {review.request.generation.world_package_id} · Seed: {review.request.generation.seed} · First-season Best {review.request.best_n} · Draft v{review.draftVersion}</p>
      <p>{cs ? 'Použité závazné podmínky' : 'Reviewed hard conditions'}:
        {' '}{countryCode || (cs ? 'země automaticky' : 'country automatic')} ·
        {' '}{region || (cs ? 'geografický region automaticky' : 'geographic region automatic')} ·
        {' '}{travelRegion || (cs ? 'cestovní region automaticky' : 'travel region automatic')} ·
        {' '}{minAge || '15'}–{maxAge || '45'} {cs ? 'let' : 'years'}.</p>
      {options && <p className="status">{cs ? 'Kontrola splnění' : 'Fulfilment'}:
        {' '}{viewedPlayers.every(player => (!countryCode || player.country_code === countryCode) &&
          (!region || options.countries.some(country => country.code === player.country_code &&
            country.region === region)) &&
          (!travelRegion || options.countries.some(country => country.code === player.country_code &&
            country.travel_region === travelRegion)) &&
          (!minAge || player.age_years_at_season_start >= Number(minAge)) &&
          (!maxAge || player.age_years_at_season_start <= Number(maxAge)))
          ? (cs ? 'Všichni hráči splňují závazné podmínky.' : 'Every player satisfies the hard conditions.')
          : (cs ? 'Konflikt! Někteří hráči nesplňují podmínky.' : 'Conflict! Some players fail hard conditions.')}
      </p>}
      <p>{cs ? 'Model' : 'Model'}: <code>{review.preview.state.source_kind}</code> · {cs ? 'Otisk náhledu' : 'Preview fingerprint'}: <code>{review.preview.fingerprint.slice(0, 20)}…</code></p>
      <GeneratedPlayerReviewInspector key={review.preview.fingerprint} players={viewedPlayers} locale={locale}
        verifiedFieldLocks={review.request.generation.field_locks ?? []}
        pendingFieldLocks={pendingFieldLocks}
        selectedPlayerId={selectedPlayerId}
        bulkSelectedIds={bulkSelectedIds}
        bulkSelectionDisabled={Boolean(bulkStagedFingerprint)}
        onBulkSelectionChange={reviewMatches ? setBulkSelectedIds : undefined}
        onSelectPlayer={fieldEditingEnabled ? setSelectedPlayerId : undefined}
        keepIds={keptIds}
        onKeepChange={canKeepPreview ? (id, checked) => {
          setKeptIds(current => checked
            ? [...new Set([...current, id])].sort()
            : current.filter(item => item !== id))
          setApproved(false)
        } : undefined} />
      <section aria-label="Bulk preview field changes" className="section-subtle">
        <h5>{cs ? 'Hromadné úpravy vybraných hráčů' : 'Bulk changes for selected players'}</h5>
        <p className="status">{cs
          ? 'Hromadný výběr je nezávislý na Keep. Žádná hodnota se nezmění bez nového serverového náhledu, výslovného Adopt a ručního Save.'
          : 'Action selection is independent of Keep. No field becomes verified until a fresh server preview; Adopt and manual Save remain separate.'}</p>
        <div className="form-grid">
          <label>{cs ? 'Hromadná operace' : 'Bulk operation'}
            <select aria-label="Bulk operation mode" value={bulkMode}
              disabled={Boolean(bulkStagedFingerprint)}
              onChange={event=>setBulkMode(event.target.value as 'value'|'automatic')}>
              <option value="value">{cs ? 'Nastavit hodnotu a zamknout' : 'Set value and lock'}</option>
              <option value="automatic">{cs ? 'Automaticky podle modelu (odemknout)' : 'Automatic from model (unlock)'}</option>
            </select>
          </label>
          <label>{cs ? 'Zdrojový atribut' : 'Source field'}
            <select aria-label="Bulk source field" value={bulkField}
              disabled={Boolean(bulkStagedFingerprint)}
              onChange={event=>setBulkField(event.target.value as GeneratedPlayerFieldKey)}>
              {PREVIEW_FIELD_KEYS.map(field=>
                <option key={field} value={field}>{field} (1–99)</option>)}
            </select>
          </label>
          {bulkMode === 'value' && <label>{cs ? 'Nová hodnota' : 'New value'}
            <input aria-label="Bulk new source value" type="number" min={1} max={99} step={1}
              disabled={Boolean(bulkStagedFingerprint)}
              value={bulkValue}
              onChange={event=>setBulkValue(event.target.value)} />
          </label>}
        </div>
        {bulkMode === 'automatic' && <p className="status">{cs
          ? 'Automatic odebere jen zámky vybraného atributu u označených hráčů. Výsledná čísla určí až nový ověřený serverový náhled; bez serveru je nelze předpovědět.'
          : 'Automatic removes only selected players’ locks on this field. Final numeric values are unknown until the server replays and verifies the new preview.'}</p>}
        {bulkError && <p role="alert">{tr('Bulk preview conflict:')} {bulkError}</p>}
        {bulkPlan && <div aria-label="Bulk before after preview">
          <p role="status">{tr('Action selection')} {bulkPlan.selectedCount} ·
            {' '}{bulkMode === 'automatic'
              ? (cs ? 'k odemknutí' : 'to unlock')
              : tr('changed')} {bulkPlan.changes.length} · {tr('unchanged')} {bulkPlan.unchangedCount}.
            {bulkMode === 'value' && <> {' · '}{cs ? 'změny čísel' : 'numeric changes'} {' '}
              {bulkPlan.changes.filter(change => change.before !== change.after).length} ·
              {' '}{cs ? 'nové zámky' : 'new locks'} {' '}
              {bulkPlan.changes.filter(change => !change.beforeLocked && change.afterLocked).length}.</>}
            {' '}{cs ? 'Jde pouze o místní návrh změn před/po, nikoli potvrzené hodnoty hráčů.' : 'This is a local before/after proposal, not accepted player values.'}</p>
          <details>
            <summary>{tr('Review exact before/after values')} · {bulkPlan.changes.length} {tr('changed profiles')}</summary>
            <div className="table-responsive"><table>
              <thead><tr><th>{tr('Player ID')}</th><th>{tr('Player')}</th><th>{tr('Before')}</th><th>{cs ? 'Zámek před' : 'Lock before'}</th><th>{tr('After')}</th><th>{cs ? 'Zámek po' : 'Lock after'}</th></tr></thead>
              <tbody>{bulkPlan.changes.map(change=><tr key={change.playerId}>
                <td>{change.playerId}</td><td>{change.name}</td>
                <td>{change.before}</td>
                <td>{change.beforeLocked ? (cs ? 'Zamčeno' : 'Locked') : 'Automatic'}</td>
                <td>{change.after == null
                  ? (cs ? 'Automaticky – určí server' : 'Automatic – server decides')
                  : change.after}</td>
                <td>{change.afterLocked ? (cs ? 'Zamčeno' : 'Locked') : 'Automatic'}</td>
              </tr>)}</tbody>
            </table></div>
          </details>
        </div>}
        <div className="actions">
          <button type="button" disabled={!canStageBulk || fieldPreviewAction.isPending ||
            regenerateAction.isPending || adoptAction.isPending}
            onClick={()=>{
              if (!bulkPlan || !canStageBulk || !review) return
              setPendingFieldLocks(bulkPlan.nextLocks)
              setBulkStagedFingerprint(review.preview.fingerprint)
              setBulkUndo(null); setApproved(false); setSelectedPlayerId(null)
            }}>{bulkMode === 'automatic'
              ? (cs ? 'Připravit odemknutí (bez zápisu)' : 'Stage bulk Automatic (no Run write)')
              : tr('Stage reviewed bulk locks (no Run write)')}</button>
          <button type="button" disabled={!bulkStagedFingerprint ||
            review.preview.fingerprint !== bulkStagedFingerprint ||
            !fieldEditingEnabled || !locksDirty || keepSelectionDirty ||
            fieldPreviewAction.isPending || regenerateAction.isPending}
            onClick={()=>fieldPreviewAction.mutate({regenerate:false,bulk:true})}>
            {fieldPreviewAction.isPending ? tr('Verifying bulk preview…') :
              bulkMode === 'automatic'
                ? (cs ? 'Ověřit Automatic na serveru' : 'Verify Automatic on server')
                : tr('Verify staged bulk changes on server')}
          </button>
          <button type="button" disabled={!bulkStagedFingerprint || fieldPreviewAction.isPending}
            onClick={()=>{
              setPendingFieldLocks(approvedFieldLocks)
              setBulkStagedFingerprint(null);setApproved(false)
            }}>{tr('Discard staged bulk edits')}</button>
          <button type="button" disabled={!bulkUndo || !reviewMatches || !canPreview ||
            locksDirty || keepSelectionDirty || fieldPreviewAction.isPending ||
            regenerateAction.isPending || adoptAction.isPending ||
            bulkUndo.appliedFingerprint !== review.preview.fingerprint ||
            bulkUndo.previous.head !== head ||
            bulkUndo.previous.draftVersion !== draft?.draft_version ||
            bulkUndo.previous.sourceFingerprint !== snapshotFingerprint}
            onClick={()=>{
              if (!bulkUndo) return
              const previous=bulkUndo.previous
              setReview(previous)
              setPendingFieldLocks(orderedPreviewFieldLocks(
                previous.request.generation.field_locks ?? []))
              setBulkUndo(null);setBulkStagedFingerprint(null)
              setBulkSelectedIds([]);setSelectedPlayerId(null);setApproved(false)
              setNotice(cs ? 'Vrácen předchozí ověřený náhled; do Runu se nic nezapsalo.' : 'One-step session Undo restored the preceding verified preview; no Run write.')
            }}>{tr('Undo last verified bulk preview')}</button>
        </div>
        {bulkStagedFingerprint && <p role="alert">{bulkMode === 'automatic'
          ? (cs ? 'Odemknutí je jen připravené. Převzetí je blokované do nového ověření serverem.' : 'Automatic unlocks are staged, not applied. Adopt remains blocked until server verification.')
          : tr('Bulk locks are staged locally and block Adopt until freshly verified on the server.')}</p>}
      </section>
      {selectedPlayerId && viewedPlayers.some(p=>p.player_id===selectedPlayerId) &&
        <GeneratedPlayerFieldLockEditor
          key={selectedPlayerId + ':' + review.preview.fingerprint}
          player={viewedPlayers.find(p=>p.player_id===selectedPlayerId)!}
          locks={pendingFieldLocks}
          onChange={onPreviewFieldChange}
          onApply={()=>fieldPreviewAction.mutate({regenerate:false})}
          onRegenerate={()=>fieldPreviewAction.mutate({regenerate:true})}
           regenerateDisabled={review.request.generation.session_schema_version ===
             'run_world_generation_session.v2' || review.request.generation.keep_from_seed != null}
          onClose={()=>setSelectedPlayerId(null)}
          dirty={locksDirty}
          busy={fieldPreviewAction.isPending || regenerateAction.isPending ||
            previewAction.isPending || adoptAction.isPending}
          disabled={!fieldEditingEnabled || keepSelectionDirty}
          error={fieldPreviewAction.error ? formatApiError(fieldPreviewAction.error) : null}
          seed={rerollSeed}
        />}
      {fieldPreviewAction.error && !selectedPlayerId &&
        <p role="alert">{tr('Field edit conflict:')} {formatApiError(fieldPreviewAction.error)}</p>}
      {canKeepPreview && <section aria-label="Session Keep regeneration">
        <h5>{cs ? 'Keep vybraných a regenerace ostatních' : 'Keep selected, regenerate remaining'}</h5>
        <p className="status">{cs
          ? 'Vyber Keep u hráčů v tabulce a zadej jiný seed. Server znovu ověří původní náhled a přegeneruje ostatní bez zápisu do Runu. Keep není trvalý Lock.'
          : 'Mark Keep on preview players and supply a different seed. The server verifies the original preview and regenerates the remaining players without writing to the Run. Keep is not a permanent Lock.'}</p>
        <label>{cs ? 'Nový seed' : 'New regeneration seed'}
          <input type="number" aria-label="Session Keep regeneration seed" value={rerollSeed}
            onChange={e => setRerollSeed(Number(e.target.value))} />
        </label>
        <p>{cs ? 'Ponecháno' : 'Kept'}: {keptIds.length} / {poolSize} ·
          {' '}{cs ? 'K regeneraci' : 'Regenerate'}: {poolSize - keptIds.length}</p>
        {keptIds.length === poolSize && <p role="alert">{cs
          ? 'Ponechání všech hráčů nenechává nic k regeneraci.'
          : 'Keeping every player leaves nothing to regenerate.'}</p>}
        {rerollSeed === review.request.generation.seed && <p role="alert">{cs
          ? 'Pro regeneraci je potřeba jiný seed.'
          : 'A different seed is required for regeneration.'}</p>}
        <button type="button" disabled={!canRegenerate || regenerateAction.isPending ||
          adoptAction.isPending || previewAction.isPending}
          onClick={() => regenerateAction.mutate()}>
          {regenerateAction.isPending ? (cs ? 'Regeneruji…' : 'Regenerating…')
            : (cs ? 'Regenerovat ostatní – nový náhled' : 'Regenerate remaining – new preview')}
        </button>
        {pendingKeepChange && <p className="status">{cs
          ? 'Keep výběr dosud nic nemění. Nejprve spusť regeneraci, pak potvrď nový celý náhled.'
          : 'Keep selection alone changes nothing. Regenerate first, then confirm the entire new preview.'}</p>}
      </section>}
      {sessionSteps > 0 && <p className="status">
        {cs ? `Počet ověřených regenerací v relaci: ${sessionSteps}. Keep je dočasný, bez trvalých zámků.`
          : `Verified session Keep regenerations: ${sessionSteps}. Keep is temporary, not a permanent player lock.`}
      </p>}
      {regenerateAction.error && <p role="alert" className="error">
        {cs ? 'Regenerace selhala' : 'Regeneration failed'}: {formatApiError(regenerateAction.error)}
      </p>}

      {!reviewMatches && <p role="alert" className="error">{tr('Review expired: selected Run, Branch, World, revision or generation inputs changed.')}</p>}
      <label><input type="checkbox" aria-label="Approve InitialWorld adoption" checked={approved}
        onChange={event => setApproved(event.target.checked)} /> {tr('Adopt this exact generated InitialWorld to the current Branch.')}</label>
      <button type="button" disabled={!canAdopt} onClick={() => review && adoptAction.mutate(review)}>
        {adoptAction.isPending ? (cs ? 'Připravuji dávku…' : 'Staging players…') : (cs ? 'Potvrdit a připravit Working Draft' : 'Adopt generated players')}
      </button>
    </section>}
    {adoptAction.error && <p role="alert" className="error">{tr('Adoption failed:')} {formatApiError(adoptAction.error)}</p>}
    {canResume && <section aria-label="Recover InitialWorld save">
      <p role="status">{cs ? 'V této branchi je převzatý InitialWorld s neuloženými změnami. Potvrď uložení revize bez nového generování.' : 'This Branch contains an adopted InitialWorld with unsaved changes. Confirm its Saved Revision without regenerating players.'}</p>
      <p>{existing?.players.length} {cs ? 'stávajících hráčů ze světa' : 'existing players from'} {existing?.world_package_id}. {cs ? 'Zdrojový seed' : 'Source seed'}: {existing?.bootstrap_seed}.</p>
      <button type="button" onClick={() => savePreflight && setPendingSave({
        runId, branchId, head, fingerprint: savePreflight.initial_world_fingerprint
      })}>{tr('Review existing InitialWorld save')}</button>
    </section>}
    {pendingSave && <section aria-label="Save InitialWorld revision">
      <p>{cs ? 'Hráči jsou připraveni v Run-owned InitialWorld. Saved Revision vznikne až výslovným uložením.' : 'Players are staged in Run-owned InitialWorld. Saved Revision is only created by an explicit Save.'}</p>
      {savePreviewQuery.error && <p role="alert" className="error">{tr('Save preflight failed:')} {formatApiError(savePreviewQuery.error)}</p>}
      {!saveReady && !savePreviewQuery.isLoading && <p role="alert" className="error">{cs ? 'Uložený HEAD, pracovní návrh nebo otisk InitialWorld nesouhlasí. Před uložením obnov údaje.' : 'The saved head, Draft or InitialWorld fingerprint does not match. Refresh before saving.'}</p>}
      <label><input type="checkbox" aria-label="Approve InitialWorld revision save" checked={saveApproved}
        onChange={event => setSaveApproved(event.target.checked)} /> {tr('Create the immutable Saved Revision.')}</label>
      <button type="button" disabled={!saveReady || !saveApproved || saveAction.isPending}
        onClick={() => saveAction.mutate()}>
        {saveAction.isPending ? (cs ? 'Ukládám revizi…' : 'Saving InitialWorld…') : (cs ? 'Ruční Save nové revize' : 'Save InitialWorld revision')}
      </button>
    </section>}
    {saveAction.error && <p role="alert" className="error">{tr('Save failed:')} {formatApiError(saveAction.error)}</p>}
    {notice && <p role="status">{notice}</p>}
      </div>
    </div>
  </SectionCard>
}
